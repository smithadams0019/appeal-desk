# Appeal Desk

Helps a FEMA disaster-assistance denial turn into an appeal or a fix: reads the letter, computes the 60-day appeal date, checks FEMA's current guidance, decides appeal-or-fix, drafts the letter. Legal information, not legal advice; the user files it themselves.

Live: https://2xerwbwiap.ap-southeast-1.awsapprunner.com

## NVIDIA Nemotron and Nebius Token Factory
Nebius Token Factory, OpenAI-compatible, key kept server-side (`NEBIUS_API_KEY`).

| Step | Model | Call |
|---|---|---|
| Choose the FEMA search | Nemotron 3.5 Lightning | function calling (`fema_search`) |
| Parse a pasted letter | Nemotron 3 Super | JSON, low reasoning |
| Appeal on merits / send a document / nothing to fix | Nemotron 3 Ultra | one call, high reasoning |
| Draft the letter | Nemotron 3 Super | plain text |

Model ids: `nvidia/Nemotron-3_5-Lightning`, `nvidia/nemotron-3-super-120b-a12b`, `nvidia/Nemotron-3-Ultra-550b-a55b`.

Every model call runs on Nebius Token Factory, which is serverless and OpenAI-compatible, so one base URL and the standard OpenAI client reached every model with no GPU and no dedicated endpoint to provision. That is what let this be built and deployed quickly, and the tiering puts each call on the right-sized, right-priced model: Lightning for tool calls, Super for parsing and drafting, Ultra only for the appeal decision. Other services: Tavily search and extract for live FEMA guidance (below). No vision or embedding model is used.

## Tavily
`backend/tavily_live.py` calls Tavily `/search` and `/extract` at runtime, restricted to fema.gov, federalregister.gov, ecfr.gov, govinfo.gov, disasterassistance.gov, NC state sites and Legal Aid NC. It uses `TAVILY_API_KEY` if set and keyless mode otherwise. fema.gov returns 403 to plain fetchers, so Tavily is how the app reads it.

## Data
Sources: OpenFEMA DR-4827 registrations (282,711; 121,666 ineligible), GAO-20-503 (3.5% appeal, 30.2% of those won), the 2024 IA Program Equity rule (89 FR 3990), and the court record (ACORN v. FEMA, later vacated; LUPE v. FEMA; Ridgely v. FEMA).

## Cost
The three example letters show pre-computed results. "Run live" runs the agent once per input and caches it to `backend/cache/`; live runs are capped at 25 per hour per instance.

## Run
```
python -m venv venv && source venv/bin/activate && pip install -r requirements.txt
npm --prefix frontend install && npm --prefix frontend run build   # writes backend/static
export NEBIUS_API_KEY=...        # optional: TAVILY_API_KEY
cd backend && uvicorn main:app --port 8000
```
Docker: `docker build -t appeal-desk . && docker run -p 8080:8080 -e NEBIUS_API_KEY=... appeal-desk`

Stack: Python, FastAPI, React (Vite), NVIDIA Nemotron on Nebius Token Factory, Tavily search.

Licensed under the Apache License 2.0.
