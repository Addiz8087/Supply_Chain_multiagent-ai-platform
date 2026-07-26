"""
services/data_sources.py
=========================
Authentic data-source registry and provenance/confidence utilities.

Why this file exists
---------------------
Earlier versions of this platform hard-coded mineral/country figures directly
inside `knowledge_base.py` with no indication of *where* they came from.
A reviewer flagged this as a credibility gap: in a real operational-research
pipeline, every parameter that feeds a model must be traceable back to an
authentic, citable source — structured (official statistics) or unstructured
(news / policy documents), each carrying a confidence rating.

This module follows the two-tier provenance pattern described in:
    Nie, W., Li, F., Tsolakis, N., & Kumar, M. (2026). "Integrating digitally
    enhanced data extraction and simulation modelling for AI-driven supply
    chain resilience...", Journal of the Operational Research Society, 77(7).

i.e. (1) a structured-data baseline from verifiable public institutions, and
(2) a confidence/traceability wrapper so every number returned by a tool can
be inspected, not just trusted blindly.

It does NOT invent numbers. Where this project does not (yet) have a live
feed wired up, it says so explicitly via `status="UNVERIFIED-PLACEHOLDER"`
rather than presenting an invented figure as fact. Replace placeholders with
values pulled from the cited source before using this in a real assessment.
"""

from __future__ import annotations

import time
from typing import Dict, List, Optional

import requests

# ══════════════════════════════════════════════════════════════════════════
#  AUTHORITATIVE SOURCE REGISTRY
#  Every structured number used anywhere in the platform should point here.
# ══════════════════════════════════════════════════════════════════════════

SOURCE_REGISTRY: Dict[str, Dict] = {
    "USGS_MCS": {
        "name":   "U.S. Geological Survey — Mineral Commodity Summaries",
        "url":    "https://www.usgs.gov/centers/national-minerals-information-center/mineral-commodity-summaries",
        "type":   "structured / government statistical publication",
        "covers": "annual global mine production, reserves, and processing "
                  "capacity by country, per mineral commodity",
        "update_cycle": "annual (published each January/February)",
    },
    "UN_COMTRADE": {
        "name":   "UN Comtrade Database (United Nations Statistics Division)",
        "url":    "https://comtradeplus.un.org/",
        "api":    "https://comtradeapi.un.org/data/v1/get",
        "type":   "structured / bilateral trade statistics",
        "covers": "import/export volumes and trading-partner relationships "
                  "by Harmonised System (HS) code, e.g. HS 283691 for "
                  "lithium carbonate",
        "update_cycle": "monthly, with reporting lag",
    },
    "IEA_CRITICAL_MINERALS": {
        "name":   "IEA Global Critical Minerals Outlook",
        "url":    "https://www.iea.org/reports/global-critical-minerals-outlook-2025",
        "type":   "structured + analytical / intergovernmental agency report",
        "covers": "supply concentration, demand projections, policy tracker "
                  "for critical minerals",
        "update_cycle": "annual",
    },
    "WORLD_BANK_WGI": {
        "name":   "World Bank Worldwide Governance Indicators — Political "
                  "Stability & Absence of Violence/Terrorism",
        "url":    "https://api.worldbank.org/v2",
        "type":   "structured / live API (already wired into this platform)",
        "covers": "country-level political stability score, -2.5 to +2.5",
        "update_cycle": "annual",
    },
    "REST_COUNTRIES": {
        "name":   "REST Countries API",
        "url":    "https://restcountries.com/",
        "type":   "structured / live API (already wired into this platform)",
        "covers": "country metadata: region, subregion, population",
        "update_cycle": "static reference data",
    },
    "FACTIVA_NEWS_CORPUS": {
        "name":   "Dow Jones Factiva (or equivalent news/policy corpus)",
        "url":    "https://www.dowjones.com/professional/factiva/",
        "type":   "unstructured / news & policy document archive",
        "covers": "export-restriction announcements, stockpiling activity, "
                  "facility expansion/closure news, market-event narratives",
        "update_cycle": "continuous; requires an LLM-RAG extraction step "
                         "(see services/echelon_knowledge.py extraction "
                         "schema) before it can feed simulation parameters",
    },
}


def list_sources() -> List[Dict]:
    """Return the full source registry as a flat list (for UI display)."""
    return [{"key": k, **v} for k, v in SOURCE_REGISTRY.items()]


# ══════════════════════════════════════════════════════════════════════════
#  PROVENANCE WRAPPER — mirrors the paper's confidence-rating scheme
#  (High / Medium / Low / None) and text-reference traceability field.
# ══════════════════════════════════════════════════════════════════════════

def with_provenance(
    value,
    source_key: str,
    confidence: str = "MEDIUM",
    note: str = "",
    verified: bool = False,
) -> Dict:
    """
    Wrap any data point with a provenance record so the UI / report can show
    where it came from and how much to trust it.

    confidence: "HIGH" | "MEDIUM" | "LOW" | "UNVERIFIED-PLACEHOLDER"
    """
    src = SOURCE_REGISTRY.get(source_key, {"name": source_key, "url": ""})
    return {
        "value":      value,
        "source":     src.get("name", source_key),
        "source_url": src.get("url", ""),
        "confidence": confidence,
        "verified":   verified,
        "note":       note,
        "retrieved_at": time.strftime("%Y-%m-%d", time.localtime()),
    }


# ══════════════════════════════════════════════════════════════════════════
#  LIVE FETCHERS — authentic public APIs, best-effort, never fabricate
# ══════════════════════════════════════════════════════════════════════════

_CACHE: Dict[str, Dict] = {}


def fetch_un_comtrade_trade_flow(
    reporter_iso3: str, partner_iso3: str, hs_code: str,
    year: int = 2024, subscription_key: Optional[str] = None,
) -> Dict:
    """
    Best-effort live call to the UN Comtrade public API for bilateral trade
    volume of a given HS code (e.g. '283691' = lithium carbonate,
    '740200' = unrefined copper, etc.).

    UN Comtrade's full API requires a free subscription key
    (https://comtradeplus.un.org/ -> API Management). If no key is supplied
    (via argument or COMTRADE_API_KEY in .env), this returns a structured
    "NOT_CONFIGURED" response rather than inventing a number — callers
    should fall back to the cited USGS/UN Comtrade published PDF tables in
    that case.
    """
    import os
    key = subscription_key or os.getenv("COMTRADE_API_KEY", "")
    if not key:
        return {
            "status": "NOT_CONFIGURED",
            "reason": "No COMTRADE_API_KEY set. Get a free key at "
                      "https://comtradeplus.un.org/ -> API Management, then "
                      "add COMTRADE_API_KEY=... to your .env file.",
            "source": SOURCE_REGISTRY["UN_COMTRADE"],
        }

    cache_key = f"{reporter_iso3}-{partner_iso3}-{hs_code}-{year}"
    if cache_key in _CACHE:
        return _CACHE[cache_key]

    url = (
        f"https://comtradeapi.un.org/data/v1/get/C/A/HS"
        f"?reporterCode={reporter_iso3}&partnerCode={partner_iso3}"
        f"&period={year}&cmdCode={hs_code}"
    )
    try:
        r = requests.get(url, headers={"Ocp-Apim-Subscription-Key": key}, timeout=20)
        if r.status_code == 200:
            data = r.json()
            result = {
                "status": "OK",
                "raw": data,
                "source": SOURCE_REGISTRY["UN_COMTRADE"],
                "hs_code": hs_code, "year": year,
            }
            _CACHE[cache_key] = result
            return result
        return {"status": "API_ERROR", "http_status": r.status_code,
                "source": SOURCE_REGISTRY["UN_COMTRADE"]}
    except Exception as e:
        return {"status": "FETCH_FAILED", "error": str(e),
                "source": SOURCE_REGISTRY["UN_COMTRADE"]}


def usgs_reference_note(mineral: str) -> Dict:
    """
    Returns the citation block analysts should use to manually pull/verify
    production-capacity figures for `mineral` from the USGS Mineral
    Commodity Summaries before they are entered into the knowledge base.
    No fabricated numbers are returned — this is a sourcing pointer only.
    """
    return {
        "mineral": mineral,
        "instruction": (
            f"Look up '{mineral}' in the latest USGS Mineral Commodity "
            f"Summaries (published annually, free PDF) for verified "
            f"world mine production, reserves, and major producing "
            f"countries, then update services/echelon_knowledge.py "
            f"MINE_PRODUCTION_DATA with the cited value."
        ),
        "source": SOURCE_REGISTRY["USGS_MCS"],
    }
