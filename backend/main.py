"""Appeal Desk API + static front end on one port."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import cases
import facts
import pipeline
import tavily_live

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"
CACHE.mkdir(exist_ok=True)
STATIC = HERE / "static"

# Uncached live runs per process per hour: protects the shared credit.
LIVE_BUDGET = 25
_live_runs: list[float] = []

app = FastAPI(title="Appeal Desk")


class RunRequest(BaseModel):
    caseId: str | None = None
    letterText: str | None = None


def _example(case_id: str) -> dict[str, Any] | None:
    return next((c for c in cases.EXAMPLES if c["id"] == case_id), None)


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {"ok": True, "tavily": tavily_live.mode()}


@app.get("/api/examples")
def examples() -> list[dict[str, Any]]:
    return cases.EXAMPLES


@app.get("/api/queue")
def queue() -> dict[str, Any]:
    return {"summary": cases.queue_summary(), "rows": cases.QUEUE,
            "recheck": cases.nightly_recheck()}


@app.get("/api/facts")
def get_facts() -> dict[str, Any]:
    return {"dr4827": facts.DR4827, "gao": facts.GAO, "equity": facts.IA_EQUITY_RULE,
            "cases": facts.CASES, "reasonCodes": facts.REASON_CODES, "safety": facts.SAFETY}


def _budget_ok() -> bool:
    now = time.time()
    _live_runs[:] = [t for t in _live_runs if now - t < 3600]
    return len(_live_runs) < LIVE_BUDGET


@app.post("/api/run")
def run(req: RunRequest) -> dict[str, Any]:
    """The live path: Lightning picks the search, Tavily runs it for real, Super
    quotes it, Ultra decides, Super drafts. Cached by input so a repeat is free."""
    if req.caseId:
        ex = _example(req.caseId)
        if not ex:
            raise HTTPException(404, "unknown example")
        key = "case:" + req.caseId
    elif req.letterText and req.letterText.strip():
        key = "text:" + req.letterText.strip()
    else:
        raise HTTPException(400, "send a caseId or letterText")
    cp = CACHE / ("run-" + hashlib.sha1(key.encode()).hexdigest()[:16] + ".json")
    if cp.exists():
        out = json.loads(cp.read_text())
        out["fromCache"] = True
        return out
    if not _budget_ok():
        raise HTTPException(429, "Live runs are paused for the hour. The pre-computed examples still work.")
    _live_runs.append(time.time())
    t0 = time.time()
    try:
        if req.caseId:
            ex = _example(req.caseId)
            parsed = ex["parsed"]
            dets = parsed.get("determinations", [])
            rules = pipeline.live_rules_check(dets[0], ex["disasterName"], use_cache=True)
            decision = pipeline.decide(parsed, rules)
            deadline = ex["deadline"]
            result = {"parsed": parsed, "ruleSet": ex["ruleSet"], "deadline": deadline,
                      "liveRules": rules, "decision": decision,
                      "draft": pipeline.draft(parsed, decision, deadline, rules)}
        else:
            result = pipeline.run(req.letterText, use_cache=True)
    except BaseException as e:  # model helper raises SystemExit when keys are spent
        raise HTTPException(502, f"The live run failed ({type(e).__name__}). Pre-computed examples are unaffected.")
    result["elapsedSec"] = round(time.time() - t0, 1)
    result["fromCache"] = False
    cp.write_text(json.dumps(result, indent=1, default=str))
    return result


@app.get("/api/asset/{name}")
def asset(name: str):
    p = HERE / "assets" / name
    if not p.is_file() or p.parent != HERE / "assets":
        raise HTTPException(404)
    return FileResponse(p)


app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")
