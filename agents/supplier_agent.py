"""
agents/supplier_agent.py
=========================
Scenario & Reporting Agent — runs supply-shock simulations and synthesises
intelligence from other agents into board-ready executive reports.
"""

from agents.base_agent import SpecialistAgent
from services.knowledge_base import SCENARIO_TOOLS, SCENARIO_SCHEMAS

SCENARIO_SYSTEM_PROMPT = (
    "You are the Scenario & Reporting Agent. You run supply-shock simulations "
    "and synthesise intelligence from other agents into board-ready executive reports. "
    "Use your tools (list_scenarios, run_scenario, generate_report, finish) to: "
    "1) identify and run all relevant scenarios for the minerals provided, "
    "2) synthesise all findings into a comprehensive executive report, "
    "3) call finish() with the complete report text."
)

ScenarioReportingAgent = SpecialistAgent(
    name          = "Scenario & Reporting Agent",
    system_prompt = SCENARIO_SYSTEM_PROMPT,
    tool_registry = SCENARIO_TOOLS,
    tool_schemas  = SCENARIO_SCHEMAS,
    max_steps     = 15,
)
