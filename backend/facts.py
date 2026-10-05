"""The verified facts Appeal Desk is allowed to state.

Every number, code meaning and court case here is transcribed from the research
pack (03-appeal-desk/research/) and carries the source it came from. Nothing in
this file is model-generated. The agent and the UI read from here; the models are
never asked to recall a figure.
"""

from __future__ import annotations

# --- DR-4827 (Hurricane Helene, North Carolina) -------------------------------
# OpenFEMA IndividualsAndHouseholdsProgramValidRegistrations, re-pulled 2026-10-04.
# See data/openfema-dr4827-counts.md.
DR4827 = {
    "disasterNumber": 4827,
    "name": "Hurricane Helene",
    "state": "North Carolina",
    "declarationDate": "2024-09-28",
    "registrations": 282711,
    "ineligible": 121666,
    "ineligiblePct": 43.0,
    "eligible": 161045,
    # reason-code breakdown among the ineligible
    "byReason": {
        "1": 15560,  # no disaster-eligible damage or need
        "2": 20861,  # has insurance
        "3": 22087,  # did not respond / withdrew
        "4": 7260,   # needs to submit documentation
        "5": 712,    # duplicate
        "7": 434,    # other
        "8": 80,     # pending
        "9": 4387,   # other non-identified
    },
    # people whose denial is something a person can act on: no-response + needs-docs
    "actionable": 29347,
    "buncombeCode4Count": 2622,  # Buncombe County, ineligibleReason 4 (needs docs)
    "source": "OpenFEMA IndividualsAndHouseholdsProgramValidRegistrations, pulled 2026-10-04",
    "sourceUrl": "https://www.fema.gov/api/open/v2/IndividualsAndHouseholdsProgramValidRegistrations",
}

# --- FEMA ineligibility reason codes (OpenFEMA field dictionary) ---------------
REASON_CODES = {
    "1": "Applicant does not have disaster-eligible damage or needs",
    "2": "Applicant has insurance",
    "3": "Applicant did not respond to FEMA outreach or voluntarily withdrew",
    "4": "Applicant needs to submit documentation",
    "5": "Duplicate application",
    "6": "Flood-zone related reason",
    "7": "Other",
    "8": "Pending",
    "9": "Other non-identified eligibility code",
}

# --- The GAO findings ---------------------------------------------------------
GAO = {
    "report": "GAO-20-503",
    "url": "https://www.gao.gov/products/gao-20-503",
    "appealRate": 3.5,   # 2016-2018, Table 1 (p.29)
    "winRate": 30.2,     # of those who appealed
    "appealRateWindow": "2016-2018",
    "letterLanguage": "ASSISTANCE NOT APPROVED",
    # GAO-20-503 p.47: the ineligible letter does not state the decision is not final
    "letterFinding": (
        "GAO found FEMA's ineligibility letter says \"ASSISTANCE NOT APPROVED\" and "
        "\"does not explicitly state that the determination is not final.\""
    ),
    "letterFindingPage": "GAO-20-503, p.47",
}

# --- The rule that pins to the declaration date -------------------------------
# Disasters declared on/after 22 Mar 2024 fall under the IA Program Equity rule.
IA_EQUITY_RULE = {
    "effectiveDate": "2024-03-22",
    "citation": "89 FR 3990 (Individual Assistance Program Equity, published 22 Jan 2024)",
    "url": "https://www.govinfo.gov/content/pkg/FR-2024-01-22/pdf/2024-00677.pdf",
    "summary": (
        "For disasters declared on or after 22 March 2024, an appeal must be "
        "postmarked within 60 days of the decision letter, and a signed written "
        "explanation is no longer required — supporting documents alone can be sent."
    ),
    "priorRule": (
        "For earlier disasters, the appeal had to be a signed written statement "
        "sent within 60 days of the decision letter."
    ),
}

# The live FEMA appeals page passage (saved 2026-10-04; last updated by FEMA 26 Jun 2026).
FEMA_APPEALS = {
    "url": "https://www.fema.gov/assistance/individual/after-applying/appeals",
    "quote": "If you disagree with FEMA’s decision, you may appeal within 60 days of the date of the letter.",
    "retrieved": "2026-10-04",
}

# --- Court cases (verified opinion/docket text; see court-cases/CASES.md) ------
CASES = [
    {
        "caption": "ACORN v. FEMA",
        "court": "U.S. District Court, D.D.C.",
        "year": "2006",
        "cite": "463 F. Supp. 2d 26",
        "docket": "No. 1:06-cv-01521 (RJL)",
        "holding": (
            "Judge Leon ordered FEMA to give Katrina/Rita evacuees more detailed "
            "explanations for each denial — the factual and statutory basis — and "
            "fuller instructions on how to cure the problem or appeal."
        ),
        "subsequent": "Later vacated as moot after the plaintiffs voluntarily dismissed (D.C. Cir.).",
        "url": "https://www.courtlistener.com/opinion/2319438/association-of-community-organizations-for-reform-now-v-federal-emergency/",
    },
    {
        "caption": "La Union del Pueblo Entero v. FEMA",
        "court": "U.S. District Court, S.D. Tex.",
        "year": "2015",
        "cite": "141 F. Supp. 3d 681",
        "docket": "No. 1:08-CV-487",
        "holding": (
            "Hurricane Dolly denials were decided on an unpublished \"deferred-maintenance "
            "policy\" the applicants could not see; the court held it operated as a "
            "substantive rule and granted partial summary judgment for the plaintiffs."
        ),
        "subsequent": "The Fifth Circuit had earlier vacated a preliminary injunction in the same case (608 F.3d 217, 2010).",
        "url": "https://www.courtlistener.com/opinion/7316526/la-union-del-pueblo-entero-v-federal-emergency-management-agency/",
    },
    {
        "caption": "Ridgely v. FEMA",
        "court": "U.S. Court of Appeals, 5th Cir.",
        "year": "2008",
        "cite": "512 F.3d 727",
        "docket": "No. 07-30615",
        "holding": (
            "Katrina/Rita renters charged that FEMA denied continued rent assistance "
            "with \"notices containing only confusing codes, instead of understandable "
            "explanations.\""
        ),
        "subsequent": "The Fifth Circuit vacated the injunction; the plaintiffs lost the appeal. Cited for the complaint, not the result.",
        "url": "https://www.courtlistener.com/opinion/1446051/ridgely-v-federal-emergency-management-agency/",
    },
]

# Safety lines shown in the UI footer / about.
SAFETY = [
    "Appeal Desk gives legal information, not legal advice.",
    "Every rule it states carries the source it was read from.",
    "It never predicts whether an appeal will succeed.",
    "It drafts the appeal for you to review and sign — it never files for you.",
]
