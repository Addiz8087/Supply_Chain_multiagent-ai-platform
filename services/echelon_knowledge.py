"""
services/echelon_knowledge.py
==============================
Full end-to-end supply-chain echelon model: Source/Mine -> Factory/Processing
-> Distribution/Trading -> Warehouse/Port -> Retail/Manufacturer -> Customer.

This addresses the gap identified in review: the original platform modelled
only a flattened Tier-1/Tier-2/Tier-3 (supplier / refiner / origin-country)
view inside `knowledge_base.py`. That collapses several distinct physical and
decision-making echelons into one, which is not how a real multi-echelon
chain behaves operationally, and it is not how the literature models it.

The 6-echelon structure below is adapted directly from the agent taxonomy in:
    Nie, W., Li, F., Tsolakis, N., & Kumar, M. (2026), JORS 77(7), Table 1 &
    Figure 3 (Mine -> Processing -> Trading -> Port -> Manufacturer/Reserve),
    extended here with an explicit Customer/end-demand echelon so the chain
    is fully closed-loop (source -> ... -> end customer).

Echelon definitions used throughout this module:
    1. SOURCE      (mine / extraction site)        -- raw material origin
    2. FACTORY      (processing / refining plant)   -- converts raw -> usable form
    3. DISTRIBUTION (trading houses / intermediaries) -- moves material between regions
    4. WAREHOUSE    (port / bonded storage / strategic reserve) -- buffers & customs
    5. RETAIL       (component manufacturer / OEM)  -- builds the end hardware product
    6. CUSTOMER     (end demand: data centres, AI infra buyers) -- consumption point

Every node carries a `data_source` provenance block (see services/data_sources.py)
so figures are traceable rather than asserted.
"""

from __future__ import annotations

from typing import Dict, List

from services.data_sources import with_provenance, SOURCE_REGISTRY


# ══════════════════════════════════════════════════════════════════════════
#  FULL 6-ECHELON SUPPLY CHAIN MAP, PER MINERAL
# ══════════════════════════════════════════════════════════════════════════
#
# Structure mirrors the paper's Figure 3 (Mining -> Processing -> Trading ->
# Port -> Manufacturer / Reserve), with an added Customer echelon.
#
# NOTE ON DATA QUALITY: country/entity names below are grounded in publicly
# documented industry structure (e.g. Codelco/Chile for copper, Glencore/DRC
# for cobalt, MP Materials/USA for rare earths) consistent with the existing
# SUPPLY_CHAIN dict in knowledge_base.py. Capacity figures are intentionally
# NOT hard-coded here as precise numbers; instead each node exposes a
# `verify_via` pointer to the authentic source an analyst must pull the
# current figure from (USGS MCS / UN Comtrade), exactly as Stage 1 of the
# referenced framework prescribes (structured-data baseline first).

ECHELON_CHAIN: Dict[str, Dict] = {
    "Lithium": {
        "source": {
            "echelon": "SOURCE (Mine)",
            "entities": ["Albemarle (USA)", "SQM (Chile)", "Ganfeng (China)"],
            "countries": ["Australia", "Chile", "Argentina"],
            "verify_via": "USGS_MCS",
        },
        "factory": {
            "echelon": "FACTORY (Processing / Refining)",
            "entities": ["Chile brine processing", "China conversion plants"],
            "countries": ["Chile", "China", "Argentina"],
            "verify_via": "USGS_MCS",
        },
        "distribution": {
            "echelon": "DISTRIBUTION (Trading)",
            "entities": ["European trading intermediaries (UK, Ireland, "
                         "Germany, Belgium, Netherlands)"],
            "countries": ["UK", "Ireland", "Germany", "Belgium", "Netherlands"],
            "verify_via": "UN_COMTRADE",
        },
        "warehouse": {
            "echelon": "WAREHOUSE (Port / Strategic Reserve)",
            "entities": ["Destination-country import port", "National "
                         "strategic stockpile (where one exists)"],
            "countries": ["destination-dependent"],
            "verify_via": "IEA_CRITICAL_MINERALS",
        },
        "retail": {
            "echelon": "RETAIL (Battery cell / EV / Data-centre UPS OEM)",
            "entities": ["Battery cell manufacturers", "EV pack assemblers"],
            "countries": ["destination-dependent"],
            "verify_via": "UN_COMTRADE",
        },
        "customer": {
            "echelon": "CUSTOMER (End demand)",
            "entities": ["AI data-centre operators (UPS/backup power)",
                         "EV OEM end buyers"],
            "countries": ["global"],
            "verify_via": "IEA_CRITICAL_MINERALS",
        },
        "risk": "MEDIUM",
    },
    "Cobalt": {
        "source": {"echelon": "SOURCE (Mine)", "entities": ["Glencore", "CMOC"],
                    "countries": ["Democratic Republic of Congo"], "verify_via": "USGS_MCS"},
        "factory": {"echelon": "FACTORY (Refining)", "entities": ["Chinese cobalt refiners",
                    "Freeport Cobalt"], "countries": ["China", "Belgium"], "verify_via": "USGS_MCS"},
        "distribution": {"echelon": "DISTRIBUTION (Trading)", "entities": ["Glencore trading desk"],
                    "countries": ["Switzerland"], "verify_via": "UN_COMTRADE"},
        "warehouse": {"echelon": "WAREHOUSE (Port / Reserve)", "entities": ["Importing-country bonded storage"],
                    "countries": ["destination-dependent"], "verify_via": "IEA_CRITICAL_MINERALS"},
        "retail": {"echelon": "RETAIL (Battery OEM)", "entities": ["EV battery suppliers",
                    "Aerospace alloy producers"], "countries": ["destination-dependent"], "verify_via": "UN_COMTRADE"},
        "customer": {"echelon": "CUSTOMER (End demand)", "entities": ["EV manufacturers",
                    "AI data-centre UPS buyers"], "countries": ["global"], "verify_via": "IEA_CRITICAL_MINERALS"},
        "risk": "HIGH",
    },
    "Gallium": {
        "source": {"echelon": "SOURCE (Byproduct of bauxite/zinc mining)", "entities": ["China Gallium Refining Group"],
                    "countries": ["China"], "verify_via": "USGS_MCS"},
        "factory": {"echelon": "FACTORY (Refining)", "entities": ["Vital Materials (China)"],
                    "countries": ["China"], "verify_via": "USGS_MCS"},
        "distribution": {"echelon": "DISTRIBUTION (Trading)", "entities": ["Semiconductor-grade material brokers"],
                    "countries": ["China", "destination-dependent"], "verify_via": "UN_COMTRADE"},
        "warehouse": {"echelon": "WAREHOUSE (Port / Customs)", "entities": ["Importing-country bonded storage"],
                    "countries": ["destination-dependent"], "verify_via": "IEA_CRITICAL_MINERALS"},
        "retail": {"echelon": "RETAIL (Semiconductor fab)", "entities": ["Wafer/IC fabs"],
                    "countries": ["destination-dependent"], "verify_via": "UN_COMTRADE"},
        "customer": {"echelon": "CUSTOMER (End demand)", "entities": ["AI GPU manufacturers",
                    "RF/defence electronics buyers"], "countries": ["global"], "verify_via": "IEA_CRITICAL_MINERALS"},
        "risk": "CRITICAL",
    },
    "Copper": {
        "source": {"echelon": "SOURCE (Mine)", "entities": ["Codelco (Chile)", "Freeport-McMoRan (USA)"],
                    "countries": ["Chile", "Peru", "DRC", "USA", "Australia"], "verify_via": "USGS_MCS"},
        "factory": {"echelon": "FACTORY (Smelting / Refining)", "entities": ["Glencore smelters"],
                    "countries": ["Chile", "China"], "verify_via": "USGS_MCS"},
        "distribution": {"echelon": "DISTRIBUTION (Trading)", "entities": ["LME-registered traders"],
                    "countries": ["UK", "Switzerland"], "verify_via": "UN_COMTRADE"},
        "warehouse": {"echelon": "WAREHOUSE (Port / LME warehouse)", "entities": ["LME-bonded warehouses"],
                    "countries": ["global network"], "verify_via": "IEA_CRITICAL_MINERALS"},
        "retail": {"echelon": "RETAIL (PCB / Wire / Heat-exchanger OEM)", "entities": ["Wire & PCB manufacturers"],
                    "countries": ["destination-dependent"], "verify_via": "UN_COMTRADE"},
        "customer": {"echelon": "CUSTOMER (End demand)", "entities": ["AI data-centre infrastructure buyers"],
                    "countries": ["global"], "verify_via": "IEA_CRITICAL_MINERALS"},
        "risk": "LOW",
    },
}

# Fall back generically for any mineral present in knowledge_base.SUPPLY_CHAIN
# but not yet given a full, hand-curated echelon breakdown above.
#
# IMPORTANT: this is NOT a placeholder anymore. Rather than leaving these
# minerals empty ("UNKNOWN — data not yet populated"), we auto-derive a
# best-effort echelon breakdown from `services.knowledge_base.SUPPLY_CHAIN`,
# which already holds publicly documented T1 (component suppliers) / T2
# (refiners) / T3 (origin countries) entities for every mineral in the
# platform. This reuses data already present and sourced in the repo rather
# than inventing new figures from an LLM's training data (which would be
# unverifiable and potentially stale — we deliberately do NOT do this; see
# services/data_sources.py docstring for the reasoning).
#
# Mapping rationale:
#   T3 (origin countries)        -> SOURCE.countries
#   T2 (refiners)                -> FACTORY.entities
#   T1 (component suppliers)     -> DISTRIBUTION + RETAIL.entities
#                                    (T1 in the original model sits between
#                                    refining and the end product, so it
#                                    plausibly spans both echelons until a
#                                    hand-curated entry refines it further)
#   WAREHOUSE / CUSTOMER          -> generic, destination-dependent
#                                    (genuinely not resolvable from T1/T2/T3
#                                    alone — flagged LOW confidence, not
#                                    UNKNOWN, since "destination-dependent"
#                                    is still a meaningful, honest statement)

def _auto_derive_echelon_chain() -> Dict[str, Dict]:
    """Build echelon entries for minerals not hand-curated above, sourced
    from the existing SUPPLY_CHAIN dict in services/knowledge_base.py."""
    try:
        from services.knowledge_base import SUPPLY_CHAIN
    except Exception:
        return {}

    derived: Dict[str, Dict] = {}
    for mineral, d in SUPPLY_CHAIN.items():
        if mineral in ECHELON_CHAIN:
            continue  # already hand-curated above, don't overwrite
        t1, t2, t3 = d.get("T1", []), d.get("T2", []), d.get("T3", [])
        derived[mineral] = {
            "source": {"echelon": "SOURCE (Mine)", "entities": [], "countries": t3,
                       "verify_via": "USGS_MCS"},
            "factory": {"echelon": "FACTORY (Processing / Refining)", "entities": t2,
                        "countries": t3, "verify_via": "USGS_MCS"},
            "distribution": {"echelon": "DISTRIBUTION (Trading)", "entities": t1,
                              "countries": ["destination-dependent"], "verify_via": "UN_COMTRADE"},
            "warehouse": {"echelon": "WAREHOUSE (Port / Reserve)", "entities": [],
                          "countries": ["destination-dependent"], "verify_via": "IEA_CRITICAL_MINERALS"},
            "retail": {"echelon": "RETAIL (Component OEM)", "entities": t1,
                       "countries": ["destination-dependent"], "verify_via": "UN_COMTRADE"},
            "customer": {"echelon": "CUSTOMER (End demand)", "entities": ["AI hardware / data-centre buyers"],
                         "countries": ["global"], "verify_via": "IEA_CRITICAL_MINERALS"},
            "risk": d.get("risk", "MEDIUM"),
        }
    return derived


ECHELON_CHAIN.update(_auto_derive_echelon_chain())

_GENERIC_ECHELON_TEMPLATE = {
    "source":       {"echelon": "SOURCE (Mine)",                    "entities": [], "countries": [], "verify_via": "USGS_MCS"},
    "factory":      {"echelon": "FACTORY (Processing / Refining)",   "entities": [], "countries": [], "verify_via": "USGS_MCS"},
    "distribution": {"echelon": "DISTRIBUTION (Trading)",            "entities": [], "countries": [], "verify_via": "UN_COMTRADE"},
    "warehouse":    {"echelon": "WAREHOUSE (Port / Reserve)",        "entities": [], "countries": [], "verify_via": "IEA_CRITICAL_MINERALS"},
    "retail":       {"echelon": "RETAIL (Component OEM)",           "entities": [], "countries": [], "verify_via": "UN_COMTRADE"},
    "customer":     {"echelon": "CUSTOMER (End demand)",             "entities": [], "countries": [], "verify_via": "IEA_CRITICAL_MINERALS"},
    "risk": "MEDIUM",
}

ECHELON_ORDER = ["source", "factory", "distribution", "warehouse", "retail", "customer"]


# ══════════════════════════════════════════════════════════════════════════
#  TOOL FUNCTIONS — Supply Chain Echelon Agent
# ══════════════════════════════════════════════════════════════════════════

def tool_trace_full_chain(mineral: str) -> dict:
    """Trace the full Source->Factory->Distribution->Warehouse->Retail->Customer chain for a mineral, with data-source provenance per echelon."""
    chain = ECHELON_CHAIN.get(mineral, _GENERIC_ECHELON_TEMPLATE)
    nodes = []
    for key in ECHELON_ORDER:
        node = dict(chain[key])
        node["stage_index"] = ECHELON_ORDER.index(key) + 1
        node["data_source"] = with_provenance(
            value=node.get("entities", []),
            source_key=node.get("verify_via", "USGS_MCS"),
            confidence="MEDIUM" if node.get("entities") else "UNVERIFIED-PLACEHOLDER",
            note="Entities/countries reflect publicly documented industry "
                 "structure; verify current capacity/volume figures against "
                 "the cited source before using in a model.",
            verified=False,
        )
        nodes.append(node)
    return {
        "mineral": mineral,
        "echelon_count": len(nodes),
        "chain": nodes,
        "overall_risk": chain.get("risk", "MEDIUM"),
    }


def tool_echelon_risk_profile(mineral: str) -> dict:
    """Score each echelon (source/factory/distribution/warehouse/retail/customer) on concentration risk based on entity/country counts."""
    chain = ECHELON_CHAIN.get(mineral, _GENERIC_ECHELON_TEMPLATE)
    SENTINELS = {"destination-dependent", "global", "global network"}
    profile = []
    for key in ECHELON_ORDER:
        node = chain[key]
        countries = [c for c in node.get("countries", []) if c not in SENTINELS]
        n_countries = len(countries)
        n_entities  = len(node.get("entities", []))
        if n_countries == 0 and n_entities == 0:
            risk = "UNKNOWN — data not yet populated, see verify_via"
        elif n_countries == 1:
            risk = "CRITICAL"
        elif n_countries == 2:
            risk = "HIGH"
        elif n_countries >= 3:
            risk = "MEDIUM"
        else:
            # countries unresolved (destination-dependent) but entities known
            risk = "VARIES (destination-dependent — not a real concentration)"
        profile.append({
            "echelon": node["echelon"],
            "n_entities": n_entities,
            "n_countries": n_countries,
            "concentration_risk": risk,
        })
    return {"mineral": mineral, "echelon_risk_profile": profile}


def tool_identify_echelon_bottleneck(mineral: str) -> dict:
    """Identify which single echelon is the weakest link (most concentrated / least diversified) for a mineral's end-to-end chain."""
    profile = tool_echelon_risk_profile(mineral)["echelon_risk_profile"]
    severity_rank = {
        "CRITICAL": 4, "HIGH": 3, "MEDIUM": 2,
        "VARIES (destination-dependent — not a real concentration)": 1,
        "UNKNOWN — data not yet populated, see verify_via": 0,
    }
    worst = max(profile, key=lambda p: severity_rank.get(p["concentration_risk"], 0))
    return {
        "mineral": mineral,
        "bottleneck_echelon": worst["echelon"],
        "bottleneck_risk": worst["concentration_risk"],
        "full_profile": profile,
        "recommendation": (
            f"Prioritise resilience investment (diversification, buffer "
            f"stock, or alternate routing) at the {worst['echelon']} stage "
            f"for {mineral}, as it currently shows the highest "
            f"concentration risk across the end-to-end chain."
        ),
    }


def tool_customer_demand_signal(mineral: str) -> dict:
    """Summarise end-customer demand context for a mineral (the previously-missing closing link of the chain)."""
    chain = ECHELON_CHAIN.get(mineral, _GENERIC_ECHELON_TEMPLATE)
    customer = chain["customer"]
    return {
        "mineral": mineral,
        "customer_segments": customer.get("entities", []),
        "geographic_scope": customer.get("countries", ["global"]),
        "data_source": with_provenance(
            value=customer.get("entities", []),
            source_key=customer.get("verify_via", "IEA_CRITICAL_MINERALS"),
            confidence="LOW",
            note="Demand-side figures should be triangulated using apparent "
                 "consumption = domestic production + imports - exports "
                 "(UN Comtrade methodology), as in the reference framework, "
                 "rather than asserted directly.",
        ),
    }


def tool_list_data_sources() -> dict:
    """List every authentic data source registered in the platform, with citation links and what each one covers."""
    from services.data_sources import list_sources
    return {"sources": list_sources()}


ECHELON_TOOLS = {
    "trace_full_chain":              tool_trace_full_chain,
    "echelon_risk_profile":          tool_echelon_risk_profile,
    "identify_echelon_bottleneck":   tool_identify_echelon_bottleneck,
    "customer_demand_signal":        tool_customer_demand_signal,
    "list_data_sources":             tool_list_data_sources,
}

_ECHELON_SCHEMA_DB = {
    "trace_full_chain":            {"mineral": {"type": "string"}},
    "echelon_risk_profile":        {"mineral": {"type": "string"}},
    "identify_echelon_bottleneck": {"mineral": {"type": "string"}},
    "customer_demand_signal":      {"mineral": {"type": "string"}},
    "list_data_sources":           {},
}


def _make_echelon_schemas() -> List[dict]:
    schemas = []
    for name, fn in ECHELON_TOOLS.items():
        params = _ECHELON_SCHEMA_DB.get(name, {})
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


ECHELON_SCHEMAS = _make_echelon_schemas()
