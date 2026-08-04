"""
agents/logistics_agent.py
==========================
Hardware Dependency Agent — maps AI hardware products to their mineral
dependencies, computes portfolio-level risk scores, and identifies chokepoints.
"""

from agents.base_agent import SpecialistAgent
from services.knowledge_base import HARDWARE_TOOLS, HARDWARE_SCHEMAS

HARDWARE_SYSTEM_PROMPT = (
    "You are the Hardware Dependency Agent. You specialise in mapping AI hardware "
    "products to their mineral dependencies and computing portfolio-level risk scores. "
    "Use your tools (map_dependencies, portfolio_overview, identify_chokepoints, "
    "compare_minerals, get_recommendations) to analyse hardware risk. "
    "Always identify chokepoints and produce risk-ranked recommendations.\n\n"
    "DATA ACCURACY RULE: only state a specific number if a tool actually "
    "returned it. Never invent a precise dollar figure, percentage, or "
    "inventory level — describe risk qualitatively when no tool supplied "
    "an exact number."
)

HardwareDependencyAgent = SpecialistAgent(
    name          = "Hardware Dependency Agent",
    system_prompt = HARDWARE_SYSTEM_PROMPT,
    tool_registry = HARDWARE_TOOLS,
    tool_schemas  = HARDWARE_SCHEMAS,
    max_steps     = 12,
)
