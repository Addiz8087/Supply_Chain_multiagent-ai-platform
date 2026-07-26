"""
services/knowledge_base.py
===========================
Domain knowledge: hardware deps, supply chains, geo-risks, substitutes,
scenarios, risk weights. Plus all live API fetchers and tool functions.
Extracted 1-to-1 from notebook v8.0.
"""

import time
import math
import json
from collections import Counter
from typing import Any, Dict, List, Optional

import requests
import pandas as pd

from app.config import MISTRAL_API_KEY  # noqa: F401 (ensures .env is loaded)


# ══════════════════════════════════════════════════════════════════════════
#  LIVE API LAYER — three free public APIs, no keys required
# ══════════════════════════════════════════════════════════════════════════

_API_CACHE: Dict[str, Any] = {}


def _cached_get(url: str, timeout: int = 15) -> Any:
    """GET with in-memory cache. Returns parsed JSON or None on failure."""
    if url in _API_CACHE:
        return _API_CACHE[url]
    try:
        r = requests.get(
            url, timeout=timeout,
            headers={"Accept": "application/json",
                     "User-Agent": "supply-chain-agent/8.0"},
        )
        if r.status_code == 200:
            data = r.json()
            _API_CACHE[url] = data
            return data
    except Exception:
        pass
    return None


WB_INDICATOR = "PV.EST"  # Political Stability & Absence of Violence

ISO3_MAP: Dict[str, str] = {
    "China": "CHN", "Russia": "RUS", "Australia": "AUS",
    "Chile": "CHL", "Indonesia": "IDN", "DRC": "COD",
    "Democratic Republic of Congo": "COD",
    "USA": "USA", "Germany": "DEU", "South Korea": "KOR",
    "Belgium": "BEL", "Brazil": "BRA",
    "Myanmar": "MMR", "Mozambique": "MOZ", "Madagascar": "MDG",
    "UAE": "ARE", "Canada": "CAN", "Norway": "NOR",
    "Peru": "PER", "Philippines": "PHL",
}


def fetch_wb_stability(country_iso3: str) -> Optional[float]:
    """World Bank Political Stability score (-2.5 to +2.5). None if unavailable."""
    url = (
        f"https://api.worldbank.org/v2/country/{country_iso3}/indicator/"
        f"{WB_INDICATOR}?format=json&mrv=1&per_page=1"
    )
    data = _cached_get(url)
    try:
        return data[1][0]["value"]
    except Exception:
        return None


def fetch_country_info(country_name: str) -> Optional[Dict]:
    """Fetch region, subregion, population from REST Countries API."""
    url = f"https://restcountries.com/v3.1/name/{requests.utils.quote(country_name)}?fullText=true"
    data = _cached_get(url)
    if data and isinstance(data, list) and len(data) > 0:
        c = data[0]
        return {
            "name":      c.get("name", {}).get("common", country_name),
            "region":    c.get("region", "Unknown"),
            "subregion": c.get("subregion", "Unknown"),
            "population": c.get("population", 0),
        }
    return None


def fetch_stability_for_country(country: str) -> Dict:
    """Combine REST Countries + World Bank stability data for a country."""
    iso3  = ISO3_MAP.get(country, country[:3].upper())
    score = fetch_wb_stability(iso3)
    ci    = fetch_country_info(country)
    return {
        "country":        country,
        "iso3":           iso3,
        "wb_stability":   round(score, 3) if score is not None else "unavailable",
        "stability_band": (
            "HIGH"   if score and score > 0.5 else
            "MEDIUM" if score and score > -0.5 else
            "LOW"
        ),
        "region":    ci["region"]    if ci else "Unknown",
        "subregion": ci["subregion"] if ci else "Unknown",
    }


# ══════════════════════════════════════════════════════════════════════════
#  LIVE DATA — GDELT NEWS (free, no API key, updates every 15 minutes)
# ══════════════════════════════════════════════════════════════════════════

GDELT_MINERAL_KEYWORDS: Dict[str, str] = {
    "Gallium":             "gallium export restriction China",
    "Germanium":           "germanium export restriction China",
    "Graphite":            "graphite export restriction China",
    "Rare Earth Elements": "rare earth export restriction China",
    "Cobalt":              "cobalt DRC Congo instability mining",
    "Nickel":              "nickel Indonesia Russia export ban sanction",
    "Lithium":             "lithium Chile Argentina supply disruption",
    "Copper":              "copper Chile Peru supply disruption strike",
    "Silicon":             "silicon semiconductor supply shortage",
    "Aluminium":           "aluminium Russia sanction RUSAL supply",
}


def fetch_gdelt_news(mineral: str) -> List[Dict]:
    """
    Fetch live news from GDELT about a mineral's supply risks.
    Free, no API key, updates every 15 minutes.
    Returns up to 5 recent articles. Falls back to [] silently on failure.
    """
    query = GDELT_MINERAL_KEYWORDS.get(mineral, f"{mineral} supply chain risk")
    url = (
        "https://api.gdeltproject.org/api/v2/doc/doc"
        f"?query={requests.utils.quote(query)}"
        "&mode=artlist"
        "&maxrecords=10"
        "&timespan=30d"
        "&format=json"
        "&sourcelang=english"
    )
    try:
        r = requests.get(url, timeout=15,
                         headers={"User-Agent": "supply-chain-agent/8.0"})
        if r.status_code != 200:
            return []
        articles = r.json().get("articles", [])
        return [
            {
                "title":  a.get("title", ""),
                "url":    a.get("url", ""),
                "date":   a.get("seendate", "")[:8],
                "source": a.get("domain", ""),
            }
            for a in articles[:5]
        ]
    except Exception:
        return []


# ══════════════════════════════════════════════════════════════════════════
#  DOMAIN KNOWLEDGE BASE
# ══════════════════════════════════════════════════════════════════════════

HW_DEPS: Dict[str, List[str]] = {
    "NVIDIA AI GPU":                        ["Gallium", "Germanium", "Rare Earth Elements", "Copper", "Silicon"],
    "AI Accelerator Chip":                  ["Gallium", "Silicon", "Copper", "Rare Earth Elements"],
    "Semiconductor Fabrication Plant":      ["Silicon", "Copper", "Nickel", "Rare Earth Elements"],
    "EV Battery for AI Data Center Backup": ["Lithium", "Cobalt", "Nickel", "Graphite"],
    "Data Center Cooling Infrastructure":   ["Copper", "Aluminium", "Rare Earth Elements"],
}

SUPPLY_CHAIN: Dict[str, Dict] = {
    "Gallium":             {"T1": ["Semiconductor Component Suppliers"],
                            "T2": ["China Gallium Refining Group", "Vital Materials (China)"],
                            "T3": ["China"], "risk": "CRITICAL"},
    "Germanium":           {"T1": ["Optical & Semiconductor Suppliers"],
                            "T2": ["Asia Germanium Refiners", "Umicore (Belgium)"],
                            "T3": ["China", "Russia"], "risk": "HIGH"},
    "Rare Earth Elements": {"T1": ["Magnet & Electronics Manufacturers"],
                            "T2": ["China Rare Earth Group", "MP Materials (USA)"],
                            "T3": ["China", "USA", "Australia", "Myanmar"], "risk": "HIGH"},
    "Silicon":             {"T1": ["Wafer Manufacturers", "Polysilicon Producers"],
                            "T2": ["Wacker Chemie (Germany)", "OCI (South Korea)", "GCL-Poly (China)"],
                            "T3": ["China", "Germany", "South Korea", "USA"], "risk": "MEDIUM"},
    "Copper":              {"T1": ["Wire & PCB Manufacturers", "Heat Exchanger Suppliers"],
                            "T2": ["Codelco (Chile)", "Freeport-McMoRan (USA)", "Glencore (Swiss)"],
                            "T3": ["Chile", "Peru", "DRC", "USA", "Australia"], "risk": "LOW"},
    "Nickel":              {"T1": ["Battery Cell Manufacturers", "Steel Alloy Producers"],
                            "T2": ["Norilsk Nickel (Russia)", "Vale (Brazil)", "Tsingshan (China)"],
                            "T3": ["Indonesia", "Philippines", "Russia", "Australia"], "risk": "MEDIUM"},
    "Lithium":             {"T1": ["Battery Manufacturers", "Cell Producers"],
                            "T2": ["Albemarle (USA)", "SQM (Chile)", "Ganfeng (China)"],
                            "T3": ["Australia", "Chile", "Argentina"], "risk": "MEDIUM"},
    "Cobalt":              {"T1": ["EV Battery Suppliers", "Aerospace Alloy Producers"],
                            "T2": ["Glencore (Swiss)", "Freeport Cobalt", "Chinese Cobalt Refiners"],
                            "T3": ["Democratic Republic of Congo"], "risk": "HIGH"},
    "Graphite":            {"T1": ["Anode Material Manufacturers"],
                            "T2": ["BTR New Material (China)", "Shanshan (China)"],
                            "T3": ["China", "Mozambique", "Madagascar"], "risk": "HIGH"},
    "Aluminium":           {"T1": ["Heat Sink & Chassis Manufacturers"],
                            "T2": ["Alcoa (USA)", "RUSAL (Russia)", "Hydro (Norway)"],
                            "T3": ["China", "Russia", "UAE", "Canada", "Australia"], "risk": "MEDIUM"},
}

def _build_geo_risks() -> pd.DataFrame:
    """
    Builds GEO_RISKS from a verified baseline + USGS 2026 import-reliance data.
    Works offline (baseline always loads). USGS rows add extra live context.
    Source: USGS Mineral Commodity Summaries 2026 — free, no API key needed.
    """
    baseline = [
        {"country": "China",                        "mineral": "Gallium",             "restriction": "Export Restriction",    "level": "HIGH",   "year": 2023},
        {"country": "China",                        "mineral": "Germanium",           "restriction": "Export Licence Req.",   "level": "HIGH",   "year": 2023},
        {"country": "China",                        "mineral": "Graphite",            "restriction": "Export Restriction",    "level": "HIGH",   "year": 2023},
        {"country": "China",                        "mineral": "Rare Earth Elements", "restriction": "Processing Dominance",  "level": "HIGH",   "year": 2010},
        {"country": "Democratic Republic of Congo", "mineral": "Cobalt",              "restriction": "Political Instability", "level": "MEDIUM", "year": 2020},
        {"country": "Russia",                       "mineral": "Nickel",              "restriction": "Sanction Risk",         "level": "MEDIUM", "year": 2022},
        {"country": "Russia",                       "mineral": "Germanium",           "restriction": "Export Restrictions",   "level": "MEDIUM", "year": 2023},
        {"country": "Indonesia",                    "mineral": "Nickel",              "restriction": "Export Ore Ban",        "level": "MEDIUM", "year": 2020},
        # Extra rows from USGS MCS 2026 import-reliance data (source: pubs.usgs.gov/publication/mcs2026)
        {"country": "Chile",                        "mineral": "Lithium",             "restriction": "USGS: 55% US import reliance", "level": "MEDIUM", "year": 2026},
        {"country": "China",                        "mineral": "Silicon",             "restriction": "USGS: dominant polysilicon producer", "level": "MEDIUM", "year": 2026},
        {"country": "China",                        "mineral": "Cobalt",              "restriction": "USGS: 72% global refining share", "level": "HIGH",   "year": 2026},
        {"country": "China",                        "mineral": "Nickel",              "restriction": "USGS: dominant refiner",  "level": "MEDIUM", "year": 2026},
    ]
    return pd.DataFrame(baseline)

GEO_RISKS = _build_geo_risks()

RISK_W: Dict[str, int] = {
    "Gallium": 10, "Germanium": 9, "Graphite": 9, "Rare Earth Elements": 9,
    "Cobalt": 7, "Nickel": 6, "Lithium": 5, "Copper": 3, "Silicon": 3, "Aluminium": 2,
}

SUBSTITUTES: Dict[str, List[Dict]] = {
    "Gallium":            [{"material": "Silicon Carbide (SiC)",      "feasibility": "HIGH",   "note": "Viable for RF chips; used in EV inverters"},
                           {"material": "Graphene-based materials",   "feasibility": "LOW",    "note": "Research phase only"}],
    "Germanium":          [{"material": "Silicon (advanced node)",    "feasibility": "MEDIUM", "note": "Lower optical performance"},
                           {"material": "InP (Indium Phosphide)",     "feasibility": "MEDIUM", "note": "High-speed photonics; Indium also China-concentrated"}],
    "Rare Earth Elements":[{"material": "Ferrite Magnets",            "feasibility": "HIGH",   "note": "Lower performance; viable for non-critical motors"},
                           {"material": "Switched reluctance motors", "feasibility": "MEDIUM", "note": "Motor redesign required"}],
    "Cobalt":             [{"material": "LFP (Lithium Iron Phosphate)","feasibility": "HIGH",  "note": "Dominant in stationary storage"},
                           {"material": "Nickel-rich NMC (low-Co)",   "feasibility": "HIGH",   "note": "Reduces Co by 80%"}],
    "Lithium":            [{"material": "Sodium-ion batteries",       "feasibility": "MEDIUM", "note": "CATL/BYD now shipping"}],
    "Silicon":            [{"material": "Silicon-on-Insulator (SOI)", "feasibility": "HIGH",   "note": "Process optimisation"},
                           {"material": "Gallium Arsenide (GaAs)",   "feasibility": "MEDIUM", "note": "RF/photonics"}],
    "Nickel":             [{"material": "LFP batteries (Co+Ni free)", "feasibility": "HIGH",   "note": "Displacing Ni-based chemistry"}],
    "Graphite":           [{"material": "Synthetic graphite (coal-tar)","feasibility": "HIGH", "note": "Reduces China dependency"},
                           {"material": "Silicon anode materials",    "feasibility": "MEDIUM", "note": "Swelling issues; partially deployed"}],
    "Copper":             [{"material": "Aluminium wiring",           "feasibility": "HIGH",   "note": "30% lower conductivity"}],
    "Aluminium":          [{"material": "Magnesium alloys",           "feasibility": "MEDIUM", "note": "Lighter but expensive"}],
}

SCENARIOS: Dict[str, Dict] = {
    "China Gallium Export Restrictions":
        {"minerals": ["Gallium"], "sector": "AI GPU Manufacturing", "impact": "SEVERE",
         "consequences": ["GPU production -30-50%", "Semiconductor prices surge", "AI infrastructure delayed 12-24 months"]},
    "Taiwan Semiconductor Disruption":
        {"minerals": ["Silicon", "Copper", "Rare Earth Elements"], "sector": "Global Semiconductor Industry", "impact": "CRITICAL",
         "consequences": ["AI chip shortage 2-4 years", "Data centre expansion halted", "Technology sector contraction"]},
    "Congo Cobalt Instability":
        {"minerals": ["Cobalt"], "sector": "Battery Supply Chains", "impact": "HIGH",
         "consequences": ["Battery manufacturing disruption", "Data centre UPS prices +40%", "EV market shortages"]},
    "AI Demand Surge Shock":
        {"minerals": ["Gallium", "Germanium", "Silicon", "Copper", "Rare Earth Elements"],
         "sector": "AI Infrastructure", "impact": "EXTREME",
         "consequences": ["Demand exceeds 2x baseline", "Fabs committed through 2030", "Spot prices +200-400%"]},
    "China Graphite Export Controls":
        {"minerals": ["Graphite"], "sector": "Battery & AI Data Centre Backup", "impact": "HIGH",
         "consequences": ["Anode material shortage", "Battery costs +25-35%", "UPS lead times 18 months"]},
}


# ══════════════════════════════════════════════════════════════════════════
#  TOOL FUNCTIONS — one function per tool, used by agents
# ══════════════════════════════════════════════════════════════════════════

# ── Mineral Intelligence Agent tools ──────────────────────────────────────

def tool_assess_geo_risk(mineral: str) -> dict:
    """
    Return active geopolitical restrictions. Enriched with:
      - USGS 2026 import-reliance data (via GEO_RISKS)
      - Live World Bank political stability scores
      - Live GDELT news articles (last 30 days, free, no key)
    """
    # ── Static + USGS rows ──────────────────────────────────────────────────
    hits = GEO_RISKS[GEO_RISKS["mineral"] == mineral]

    # ── Live World Bank stability per supplier country ──────────────────────
    countries = SUPPLY_CHAIN.get(mineral, {}).get("T3", [])
    live_stability = {}
    for c in countries[:3]:
        live_stability[c] = fetch_stability_for_country(c)

    # ── Live GDELT news ─────────────────────────────────────────────────────
    live_news = fetch_gdelt_news(mineral)
    news_signal = "HIGH" if len(live_news) >= 3 else "MEDIUM" if live_news else "LOW"

    # ── Overall risk level (escalate if news confirms active disruption) ────
    static_worst = "HIGH" if (not hits.empty and "HIGH" in hits["level"].values) else \
                   "MEDIUM" if not hits.empty else "LOW"
    final_risk = "HIGH" if (news_signal == "HIGH" or static_worst == "HIGH") else static_worst

    return {
        "mineral":                mineral,
        "risk_level":             final_risk,
        "restrictions":           hits.to_dict(orient="records"),
        "live_country_stability": live_stability,
        "live_news_articles":     live_news,
        "news_risk_signal":       news_signal,
        "data_sources":           ["USGS MCS 2026", "World Bank PV.EST", "GDELT live news", "REST Countries"],
    }


def tool_trace_supply_chain(mineral: str) -> dict:
    """Trace Tier-1/2/3 supply chain. Flags single-source concentration."""
    d = SUPPLY_CHAIN.get(mineral)
    if not d:
        return {"error": f"Unknown mineral. Available: {list(SUPPLY_CHAIN.keys())}"}
    return {
        "mineral": mineral,
        "T1_suppliers": d["T1"],
        "T2_refiners": d["T2"],
        "T3_origin_countries": d["T3"],
        "concentration_risk": d["risk"],
        "single_source": len(d["T3"]) == 1,
    }


def tool_find_substitutes(mineral: str) -> dict:
    """Return substitute materials with feasibility ratings."""
    alts = SUBSTITUTES.get(mineral, [])
    if not alts:
        return {"mineral": mineral, "substitutes": [], "coverage": "NONE"}
    best = max(alts, key=lambda x: {"HIGH": 3, "MEDIUM": 2, "LOW": 1}.get(x["feasibility"], 0))
    return {"mineral": mineral, "substitutes": alts, "best": best, "coverage": best["feasibility"]}


def tool_fetch_live_country_stability(country: str) -> dict:
    """Fetch live World Bank + REST Countries stability data for a supplier nation."""
    return fetch_stability_for_country(country)


# ── Hardware Dependency Agent tools ───────────────────────────────────────

def tool_map_dependencies(product_name: str) -> dict:
    """Map hardware product to minerals + weighted risk score."""
    if product_name not in HW_DEPS:
        return {"error": f"Unknown product. Available: {list(HW_DEPS.keys())}"}
    deps  = HW_DEPS[product_name]
    score = sum(RISK_W.get(m, 1) for m in deps)
    tier  = ("CRITICAL" if score >= 30 else "HIGH" if score >= 20
             else "MEDIUM" if score >= 10 else "LOW")
    return {"product": product_name, "minerals": deps, "risk_score": score, "risk_tier": tier}


def tool_portfolio_overview() -> dict:
    """Risk overview of all hardware products in the portfolio."""
    rows = []
    for p, mins in HW_DEPS.items():
        score = sum(RISK_W.get(m, 1) for m in mins)
        tier  = ("CRITICAL" if score >= 30 else "HIGH" if score >= 20
                 else "MEDIUM" if score >= 10 else "LOW")
        rows.append({"product": p, "minerals": mins, "score": score, "tier": tier})
    rows.sort(key=lambda x: x["score"], reverse=True)
    return {"total_products": len(rows), "portfolio": rows}


def tool_identify_chokepoints() -> dict:
    """Identify minerals where a single country controls supply."""
    chokepoints = []
    for mineral, d in SUPPLY_CHAIN.items():
        if len(d["T3"]) == 1:
            chokepoints.append({
                "mineral": mineral, "sole_supplier": d["T3"][0],
                "concentration": d["risk"],
                "risk_weight": RISK_W.get(mineral, 1),
            })
    chokepoints.sort(key=lambda x: x["risk_weight"], reverse=True)
    return {"chokepoint_count": len(chokepoints), "chokepoints": chokepoints}


def tool_compare_minerals(minerals: list) -> dict:
    """Side-by-side risk and substitution comparison of minerals."""
    rows = []
    for m in minerals:
        geo  = tool_assess_geo_risk(m)
        subs = tool_find_substitutes(m)
        rows.append({
            "mineral": m,
            "risk_weight": RISK_W.get(m, 1),
            "geo_risk_level": geo["risk_level"],
            "substitute_coverage": subs.get("coverage", "NONE"),
            "best_substitute": subs.get("best", {}).get("material", "None"),
        })
    rows.sort(key=lambda x: x["risk_weight"], reverse=True)
    return {"comparison": rows}


def tool_get_recommendations(risk_tier: str, product: str) -> dict:
    """Return tier-calibrated strategic recommendations."""
    DB = {
        "CRITICAL": [
            "IMMEDIATE (0-30 days): activate strategic stockpiling for all CRITICAL minerals",
            "IMMEDIATE (0-90 days): sign offtake agreements with non-China Tier-2 refiners",
            "SHORT-TERM (3-6 months): dual-source Tier-1 suppliers across 2+ geopolitical blocs",
            "MEDIUM-TERM (6-24 months): fund substitution R&D — target production-ready alternatives",
            "STRATEGIC (1-3 years): develop in-house refining or joint ventures outside China",
        ],
        "HIGH": [
            "SHORT-TERM: diversify sourcing across 3+ origin countries per critical mineral",
            "SHORT-TERM: establish 6-12 month inventory buffers for HIGH-risk minerals",
            "MEDIUM-TERM: qualify substitute materials at commercial scale",
            "MEDIUM-TERM: map full Tier-3 chain — identify hidden China exposure",
        ],
        "MEDIUM": [
            "Implement quarterly supply chain risk reviews",
            "Develop contingency sourcing plans with pre-defined triggers",
            "Increase visibility to Tier-2 refiners",
        ],
        "LOW": [
            "Annual monitoring cadence — reassess if geo-political situation changes",
            "Track export policy changes in key supplier countries",
        ],
    }
    recs = DB.get(risk_tier, DB["LOW"])
    return {
        "product": product, "risk_tier": risk_tier,
        "recommendations": recs,
        "urgency": "URGENT" if risk_tier in ("CRITICAL", "HIGH") else "ROUTINE",
    }


# ── Scenario & Reporting Agent tools ──────────────────────────────────────

def tool_list_scenarios(minerals: list) -> dict:
    """Find all scenarios touching any of the given minerals."""
    found = []
    for name, s in SCENARIOS.items():
        if set(s["minerals"]) & set(minerals):
            found.append({"name": name, "impact": s["impact"],
                          "affected_minerals": s["minerals"]})
    return {"count": len(found), "scenarios": found}


def tool_run_scenario(scenario_name: str) -> dict:
    """Run a named supply-shock scenario."""
    s = SCENARIOS.get(scenario_name)
    if not s:
        return {"error": "Not found.", "available": list(SCENARIOS.keys())}
    return {"name": scenario_name, **s}


def tool_generate_report(
    product: str, risk_tier: str, key_minerals: list,
    scenarios_triggered: list, recommendations: list,
) -> dict:
    """Compile a structured executive report dict."""
    return {
        "title": f"Supply Chain Resilience Report: {product}",
        "risk_tier": risk_tier,
        "key_minerals": key_minerals,
        "scenarios_triggered": scenarios_triggered,
        "recommendations": recommendations,
        "generated_by": "Scenario & Reporting Agent v8.0",
    }


def tool_finish(report: str) -> dict:
    """Signal analysis complete. Pass full executive report as report argument."""
    return {"status": "COMPLETE", "report": report}


# ── Tool registries (one per agent) ───────────────────────────────────────

MINERAL_TOOLS = {
    "assess_geo_risk":              tool_assess_geo_risk,
    "trace_supply_chain":           tool_trace_supply_chain,
    "find_substitutes":             tool_find_substitutes,
    "fetch_live_country_stability": tool_fetch_live_country_stability,
}

HARDWARE_TOOLS = {
    "map_dependencies":     tool_map_dependencies,
    "portfolio_overview":   tool_portfolio_overview,
    "identify_chokepoints": tool_identify_chokepoints,
    "compare_minerals":     tool_compare_minerals,
    "get_recommendations":  tool_get_recommendations,
}

SCENARIO_TOOLS = {
    "list_scenarios":  tool_list_scenarios,
    "run_scenario":    tool_run_scenario,
    "generate_report": tool_generate_report,
    "finish":          tool_finish,
}

ALL_TOOLS = {**MINERAL_TOOLS, **HARDWARE_TOOLS, **SCENARIO_TOOLS}


# ── Mistral function-call schemas ─────────────────────────────────────────

_SCHEMA_DB = {
    "assess_geo_risk":              {"mineral":       {"type": "string"}},
    "trace_supply_chain":           {"mineral":       {"type": "string"}},
    "find_substitutes":             {"mineral":       {"type": "string"}},
    "fetch_live_country_stability": {"country":       {"type": "string"}},
    "map_dependencies":             {"product_name":  {"type": "string"}},
    "portfolio_overview":           {},
    "identify_chokepoints":         {},
    "compare_minerals":             {"minerals":      {"type": "array", "items": {"type": "string"}}},
    "get_recommendations":          {"risk_tier":     {"type": "string", "enum": ["CRITICAL", "HIGH", "MEDIUM", "LOW"]},
                                     "product":       {"type": "string"}},
    "list_scenarios":               {"minerals":      {"type": "array", "items": {"type": "string"}}},
    "run_scenario":                 {"scenario_name": {"type": "string"}},
    "generate_report": {
        "product":             {"type": "string"},
        "risk_tier":           {"type": "string"},
        "key_minerals":        {"type": "array", "items": {"type": "string"}},
        "scenarios_triggered": {"type": "array", "items": {"type": "string"}},
        "recommendations":     {"type": "array", "items": {"type": "string"}},
    },
    "finish": {"report": {"type": "string", "description": "Full executive report text"}},
}


def make_schemas(tool_dict: dict) -> list:
    """Build Mistral function-call schemas from a tool registry dict."""
    schemas = []
    for name, fn in tool_dict.items():
        params = _SCHEMA_DB.get(name, {})
        schemas.append({
            "type": "function",
            "function": {
                "name": name,
                "description": fn.__doc__ or name,
                "parameters": {
                    "type": "object",
                    "properties": params,
                    "required": list(params.keys()),
                },
            },
        })
    return schemas


MINERAL_SCHEMAS  = make_schemas(MINERAL_TOOLS)
HARDWARE_SCHEMAS = make_schemas(HARDWARE_TOOLS)
SCENARIO_SCHEMAS = make_schemas(SCENARIO_TOOLS)
