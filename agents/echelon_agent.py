"""
agents/echelon_agent.py
========================
Supply Chain Echelon Agent — covers the full physical chain that was missing
from the original three specialists: Source (Mine) -> Factory (Processing) ->
Distribution (Trading) -> Warehouse (Port/Reserve) -> Retail (Component OEM)
-> Customer (End demand).

Added in response to review feedback: the platform previously only modelled
a flattened Tier-1/2/3 supplier view and had no explicit warehouse, retail,
or end-customer echelon, and no traceable data-source citations.
"""

from agents.base_agent import SpecialistAgent
from services.echelon_knowledge import ECHELON_TOOLS, ECHELON_SCHEMAS

ECHELON_SYSTEM_PROMPT = (
    "You are the Supply Chain Echelon Agent. You specialise in mapping the "
    "FULL end-to-end physical supply chain for critical minerals: "
    "Source (Mine) -> Factory (Processing/Refining) -> Distribution (Trading) "
    "-> Warehouse (Port / Strategic Reserve) -> Retail (Component/OEM "
    "manufacturer) -> Customer (end demand). "
    "Use your tools (trace_full_chain, echelon_risk_profile, "
    "identify_echelon_bottleneck, customer_demand_signal, list_data_sources) "
    "to: 1) trace every echelon of the chain for the mineral(s) in scope, "
    "2) flag the weakest/most concentrated echelon, 3) characterise end-"
    "customer demand, and 4) always cite the authentic data source "
    "(USGS Mineral Commodity Summaries, UN Comtrade, IEA Critical Minerals "
    "Outlook) behind every figure you report — never assert a number "
    "without provenance. Call finish-equivalent by returning a structured "
    "summary once all relevant minerals have been traced."
)

SupplyChainEchelonAgent = SpecialistAgent(
    name          = "Supply Chain Echelon Agent",
    system_prompt = ECHELON_SYSTEM_PROMPT,
    tool_registry = ECHELON_TOOLS,
    tool_schemas  = ECHELON_SCHEMAS,
    max_steps     = 12,
)
