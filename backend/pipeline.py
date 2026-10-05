"""The Appeal Desk agent.

Five steps, each on the model tier that fits, exactly as the research lays out:

  1. Read the letter      -> Super parses the transcription into structured fields.
  2. Pin the rule set     -> deterministic date comparison against the IA Program
                             Equity rule (a date test, not a guess), explained in words.
  3. Live rules check      -> Lightning (function calling) proposes the FEMA search;
                             we run it through Tavily; Super quotes the passage. REAL.
  4. Plan the fix          -> Ultra makes the one judged decision: appeal / cure / none.
  5. Draft                 -> Super writes the appeal or cover letter to sign.

Lightning is the only Nemotron tagged for tools, so step 3 routes there. Ultra is
called once (step 4) with reasoning_effort="high". Everything else runs "low".
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from typing import Any

import facts
import tavily_live
from nemotron import LIGHTNING, SUPER, ULTRA, think

EQUITY_DATE = date(2024, 3, 22)


# --- step 1: read the letter --------------------------------------------------
def parse_letter(transcription: str) -> dict[str, Any]:
    schema = (
        '{"disasterNumber": int|null, "letterDate": "YYYY-MM-DD"|null, '
        '"program": "HA"|"ONA"|"HA+ONA"|null, "applicationNumber": string|null, '
        '"determinations": [{"line": string, "code": string, "codeMeaning": string}]}'
    )
    msg = think(
        [
            {"role": "system", "content":
                "You read one FEMA disaster-assistance decision letter and return only "
                "facts that appear in it. Never invent a code, date or number. If a field "
                "is not present, use null. Output JSON only, matching this schema: " + schema},
            {"role": "user", "content": transcription},
        ],
        model=SUPER, json_out=True, reasoning_effort="low", max_tokens=2048,
    )
    return msg


# --- step 2: pin the rule set (deterministic) ---------------------------------
def pin_rule_set(declaration_date: str | None) -> dict[str, Any]:
    applies_equity = False
    decl = None
    if declaration_date:
        try:
            decl = datetime.fromisoformat(declaration_date.replace("Z", "")).date()
            applies_equity = decl >= EQUITY_DATE
        except ValueError:
            pass
    rule = facts.IA_EQUITY_RULE
    return {
        "declarationDate": declaration_date,
        "appliesEquityRule": applies_equity,
        "window": "Appeal postmarked within 60 days of the decision letter.",
        "explanation": rule["summary"] if applies_equity else rule["priorRule"],
        "citation": rule["citation"] if applies_equity else "44 C.F.R. § 206.115 (appeals)",
        "citationUrl": rule["url"] if applies_equity else facts.FEMA_APPEALS["url"],
    }


def compute_deadline(letter_date: str | None) -> dict[str, Any] | None:
    if not letter_date:
        return None
    try:
        d = datetime.fromisoformat(letter_date.replace("Z", "")).date()
    except ValueError:
        return None
    due = d + timedelta(days=60)
    return {
        "letterDate": d.isoformat(),
        "dueDate": due.isoformat(),
        "window": "60 days",
        "note": "Count 60 days from the date printed on the letter; the appeal must be postmarked by then.",
    }


# --- step 3: live rules check (Lightning function-calling + Tavily) ------------
FEMA_SEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "fema_search",
        "description": (
            "Search current FEMA, Federal Register and state disaster-recovery pages for "
            "the rule or document requirement that applies to a specific denial reason. "
            "Use this instead of recalling guidance from memory, because deadlines and "
            "guidance change by press release."),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "A focused search query, e.g. 'FEMA home safe to occupy appeal documents'."},
                "time_range": {"type": "string", "enum": ["day", "week", "month", "year"],
                               "description": "Set when looking for a recent change such as a deadline extension."},
            },
            "required": ["query"],
        },
    },
}


def live_rules_check(determination: dict[str, Any], disaster_name: str,
                     *, use_cache: bool = True) -> dict[str, Any]:
    """Ask Lightning what to search for, run it through Tavily for real, then have
    Super quote the exact passage. Returns the citations with the live metadata."""
    code = determination.get("code", "")
    meaning = determination.get("codeMeaning") or facts.REASON_CODES.get(code, "")
    # Lightning proposes the search (function calling).
    msg = think(
        [
            {"role": "system", "content":
                "You help research a FEMA denial. Call fema_search with the single best "
                "query to find the current rule and the documents this denial needs. "
                f"Disaster: {disaster_name}."},
            {"role": "user", "content":
                f"The denial reason is \"{meaning}\" (code {code}). Find the current FEMA "
                "guidance and the documents needed to fix or appeal it."},
        ],
        model=LIGHTNING, tools=[FEMA_SEARCH_TOOL],
        reasoning_effort="low", max_tokens=1024,
    )
    query = f"FEMA {meaning} appeal documents"
    time_range = None
    tcs = getattr(msg, "tool_calls", None) or []
    if tcs:
        try:
            args = json.loads(tcs[0].function.arguments)
            query = args.get("query") or query
            time_range = args.get("time_range")
        except (json.JSONDecodeError, AttributeError):
            pass

    # Run it for real.
    sr = tavily_live.search(query, depth="advanced", max_results=5,
                            time_range=time_range, use_cache=use_cache)
    hits = sr.get("results", [])
    citations: list[dict[str, Any]] = []
    top_urls = [h["url"] for h in hits[:2] if h.get("url")]
    passage = ""
    if top_urls:
        er = tavily_live.extract(top_urls[:1], use_cache=use_cache)
        texts = [r.get("raw_content") or r.get("content") or "" for r in er.get("results", [])]
        texts += [h.get("content", "") for h in hits]
        passage = tavily_live.clean_passage(texts)
    for h in hits[:4]:
        citations.append({
            "title": h.get("title", ""),
            "url": h.get("url", ""),
            "score": round(h.get("score", 0), 2),
            "snippet": (h.get("content", "") or "")[:280],
        })

    return {
        "query": query,
        "timeRange": time_range,
        "quotedPassage": passage,
        "citations": citations,
        "tavily": {
            "mode": sr.get("_meta", {}).get("mode", tavily_live.mode()),
            "cached": sr.get("_meta", {}).get("cached", True),
            "elapsedMs": sr.get("_meta", {}).get("elapsed_ms"),
        },
    }


# --- step 4: the one judged decision (Ultra) ----------------------------------
def decide(parsed: dict[str, Any], rules: dict[str, Any]) -> dict[str, Any]:
    dets = parsed.get("determinations", [])
    det_txt = "; ".join(f"{d.get('line','')} (code {d.get('code','')}: {d.get('codeMeaning','')})"
                        for d in dets) or "none parsed"
    quote = rules.get("quotedPassage", "")
    schema = ('{"decision": "appeal_merits"|"document_cure"|"nothing_to_fix", '
              '"oneLine": string, "rationale": string}')
    for attempt in range(3):
      try:
        out = think(
        [
            {"role": "system", "content":
                "You decide ONE thing for a FEMA denial: whether the right response is to "
                "appeal on the merits (the decision looks wrong on the facts), to cure a "
                "document (FEMA just needs a paper such as proof of occupancy, ownership, "
                "identity, or an insurance settlement), or that there is nothing to fix "
                "(a true duplicate, or fully insured and covered). Decide only from what is "
                "given. Do not predict the outcome. Output JSON only: " + schema},
            {"role": "user", "content":
                f"Determinations: {det_txt}\nCurrent FEMA guidance found: {quote or '(none)'}"},
        ],
        model=ULTRA, json_out=True, reasoning_effort="high", max_tokens=4096 + 2048 * attempt,
        )
        return out
      except (ValueError, KeyError):
        continue
    raise ValueError("decision JSON never parsed")


# --- step 5: draft ------------------------------------------------------------
def draft(parsed: dict[str, Any], decision: dict[str, Any],
          deadline: dict[str, Any] | None, rules: dict[str, Any] | None = None) -> str:
    dets = parsed.get("determinations", [])
    det_txt = "; ".join(d.get("line", "") for d in dets)
    due = deadline.get("dueDate") if deadline else "the 60-day deadline"
    kind = decision.get("decision", "document_cure")
    guidance = (rules or {}).get("quotedPassage", "")
    msg = think(
        [
            {"role": "system", "content":
                "You draft a short letter to FEMA for a disaster survivor to review and sign. "
                "Use ONLY the facts given. Do not invent office names, street addresses, "
                "departments, document types, notarisation, or dates. Anything the person "
                "must supply goes in [square brackets]. Format: a header block (To: FEMA "
                "Individuals and Households Program; Re:; Disaster number; Application "
                "number), then two short paragraphs: what is being appealed or cured and why, "
                "and what is enclosed as '[document you have]' options drawn only from the "
                "guidance text; end by saying it is sent within 60 days of the letter date, "
                "then a signature block. Under 170 words. Plain text, no markdown, no preamble."},
            {"role": "user", "content":
                f"Disaster number: {parsed.get('disasterNumber')}. Application number: "
                f"{parsed.get('applicationNumber') or '[your FEMA application number]'}. "
                f"Determination(s): {det_txt}. Decision: {kind} ({decision.get('oneLine','')}). "
                f"Postmark by: {due}. Current FEMA guidance: {guidance or '(none)'}"},
        ],
        model=SUPER, reasoning_effort="low", max_tokens=2048,
    )
    return (msg.content or "").strip()


# --- the whole thing ----------------------------------------------------------
def run(transcription: str, disaster_name: str = "", *, use_cache: bool = True) -> dict[str, Any]:
    parsed = parse_letter(transcription)
    rule_set = pin_rule_set_from_disaster(parsed.get("disasterNumber"))
    deadline = compute_deadline(parsed.get("letterDate"))
    dets = parsed.get("determinations", [])
    primary = dets[0] if dets else {"code": "", "codeMeaning": ""}
    rules = live_rules_check(primary, disaster_name or _disaster_label(parsed), use_cache=use_cache)
    decision = decide(parsed, rules)
    letter = draft(parsed, decision, deadline, rules)
    return {
        "parsed": parsed,
        "ruleSet": rule_set,
        "deadline": deadline,
        "liveRules": rules,
        "decision": decision,
        "draft": letter,
    }


def _disaster_label(parsed: dict[str, Any]) -> str:
    dn = parsed.get("disasterNumber")
    if dn == facts.DR4827["disasterNumber"]:
        return f"{facts.DR4827['name']} ({facts.DR4827['state']}, DR-{dn})"
    return f"DR-{dn}" if dn else "this disaster"


def pin_rule_set_from_disaster(disaster_number: Any) -> dict[str, Any]:
    # DR-4827 declaration date is known from OpenFEMA; otherwise fall back to unknown.
    if disaster_number == facts.DR4827["disasterNumber"]:
        return pin_rule_set(facts.DR4827["declarationDate"])
    return pin_rule_set(None)
