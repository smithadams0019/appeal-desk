"""Live FEMA/state guidance lookup through Tavily.

This is the load-bearing part of Appeal Desk and the reason it is the Tavily-bonus
entry: FEMA's own pages (fema.gov) return HTTP 403 to a plain fetcher from most
machines, and deadlines and guidance move by press release. Tavily reaches those
pages and returns the exact passage to quote.

If TAVILY_API_KEY is set we use it; otherwise we fall back to Tavily's keyless mode
(header X-Tavily-Access-Mode: keyless), which is rate-limited but needs no account.
Every successful call is cached to backend/cache/ keyed by (endpoint, payload) so a
judge clicking "Run it" twice does not spend a second credit.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.request
from pathlib import Path
from typing import Any

BASE = "https://api.tavily.com"
CACHE_DIR = Path(__file__).resolve().parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)

# Keep every lookup inside official / legal-aid sources.
OFFICIAL_DOMAINS = [
    "fema.gov",
    "disasterassistance.gov",
    "federalregister.gov",
    "ecfr.gov",
    "govinfo.gov",
    "ncdps.gov",
    "ncdhhs.gov",
    "rebuild.nc.gov",
    "legalaidnc.org",
]


def _key() -> str | None:
    v = os.environ.get("TAVILY_API_KEY")
    if v:
        return v.strip()
    env = Path(__file__).resolve().parent.parent.parent.parent / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if line.strip().startswith("TAVILY_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def mode() -> str:
    return "api-key" if _key() else "keyless"


def _cache_path(endpoint: str, payload: dict[str, Any]) -> Path:
    h = hashlib.sha1(
        (endpoint + json.dumps(payload, sort_keys=True)).encode()
    ).hexdigest()[:16]
    return CACHE_DIR / f"tavily-{endpoint}-{h}.json"


def _post(endpoint: str, payload: dict[str, Any], *, timeout: float = 45.0) -> dict[str, Any]:
    headers = {"Content-Type": "application/json"}
    key = _key()
    body = dict(payload)
    if key:
        headers["Authorization"] = f"Bearer {key}"
    else:
        headers["X-Tavily-Access-Mode"] = "keyless"
    req = urllib.request.Request(
        f"{BASE}/{endpoint}", data=json.dumps(body).encode(), headers=headers, method="POST"
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def call(endpoint: str, payload: dict[str, Any], *, use_cache: bool = True) -> dict[str, Any]:
    """One Tavily call, cached. Returns the parsed JSON plus a `_meta` block saying
    whether it was live or from cache and which auth mode was used."""
    cp = _cache_path(endpoint, payload)
    if use_cache and cp.exists():
        data = json.loads(cp.read_text())
        data.setdefault("_meta", {})
        data["_meta"]["cached"] = True
        return data
    t0 = time.time()
    data = _post(endpoint, payload)
    data["_meta"] = {
        "cached": False,
        "mode": mode(),
        "endpoint": endpoint,
        "elapsed_ms": round((time.time() - t0) * 1000),
        "retrieved": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    try:
        cp.write_text(json.dumps(data, indent=1))
    except OSError:
        pass
    return data


def search(query: str, *, domains: list[str] | None = None, depth: str = "advanced",
           max_results: int = 5, time_range: str | None = None,
           use_cache: bool = True) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "query": query,
        "include_domains": domains or OFFICIAL_DOMAINS,
        "search_depth": depth,
        "max_results": max_results,
        "topic": "general",
    }
    if time_range:
        payload["time_range"] = time_range
    return call("search", payload, use_cache=use_cache)


def extract(urls: list[str], *, use_cache: bool = True) -> dict[str, Any]:
    return call("extract", {"urls": urls}, use_cache=use_cache)


def best_passage(extract_result: dict[str, Any], must_contain: list[str] | None = None,
                 max_len: int = 320) -> str:
    """Pull a clean quotable sentence out of an /extract result."""
    results = extract_result.get("results") or []
    if not results:
        return ""
    raw = results[0].get("raw_content") or results[0].get("content") or ""
    # collapse whitespace
    text = " ".join(raw.split())
    if must_contain:
        low = text.lower()
        for needle in must_contain:
            i = low.find(needle.lower())
            if i >= 0:
                start = max(0, text.rfind(".", 0, i) + 1)
                end = text.find(".", i)
                end = end + 1 if end >= 0 else min(len(text), i + max_len)
                return text[start:end].strip()[:max_len]
    return text[:max_len].strip()


def clean_passage(texts: list[str], max_len: int = 300) -> str:
    """Best quotable sentence across page text: prose only (no markdown, links or
    nav), about appeals or documents, preferring one that names the 60-day window."""
    import re
    best, best_score = "", 0
    for raw in texts:
        flat = " ".join((raw or "").split())
        for s in re.split(r"(?<=[.!?])\s+", flat):
            if not 50 <= len(s) <= max_len:
                continue
            if re.search(r"[\[\]|#*<>]|\(/|http|png|node/", s):
                continue
            low = s.lower()
            score = (3 if "60 days" in low else 0) + (2 if "appeal" in low else 0) \
                + (1 if "document" in low or "letter" in low else 0)
            if score >= 3 and score > best_score:
                best, best_score = s.strip(), score
    return best
