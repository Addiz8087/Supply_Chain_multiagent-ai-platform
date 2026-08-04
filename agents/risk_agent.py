"""
agents/risk_agent.py
====================
Mineral Intelligence Agent — handles geo-risk, supply chains, substitutes,
and live country stability data.
"""

from agents.base_agent import SpecialistAgent
from services.knowledge_base import MINERAL_TOOLS, MINERAL_SCHEMAS

MINERAL_SYSTEM_PROMPT = (
    "You are the Mineral Intelligence Agent. You specialise in critical mineral "
    "supply chains, geopolitical risk, and material substitution. "
    "Use your tools (assess_geo_risk, trace_supply_chain, find_substitutes, "
    "fetch_live_country_stability) to gather comprehensive intelligence on "
    "any mineral the Orchestrator assigns you. "
    "Be thorough: check geo risk, trace the supply chain, identify substitutes. "
    "Return your findings as a structured summary when done.\n\n"
    "DATA ACCURACY RULE: only state a specific number (percentage market "
    "share, dollar figure, tonnage, stability score) if a tool actually "
    "returned it. Never invent a precise statistic — describe risk "
    "qualitatively (e.g. 'highly concentrated in one country') when no "
    "tool provided an exact figure."
)

MineralIntelligenceAgent = SpecialistAgent(
    name          = "Mineral Intelligence Agent",
    system_prompt = MINERAL_SYSTEM_PROMPT,
    tool_registry = MINERAL_TOOLS,
    tool_schemas  = MINERAL_SCHEMAS,
    max_steps     = 15,
)
