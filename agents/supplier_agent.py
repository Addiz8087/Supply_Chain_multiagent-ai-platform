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
    "3) call finish() with the complete report text.\n\n"
    "DATA ACCURACY RULE (mandatory, no exceptions): only state a specific "
    "number (a dollar figure, a percentage, a market share, a stock level, "
    "a timeline in months) if that exact number came from a tool result "
    "earlier in this run. If a tool did not return a number for something, "
    "describe it qualitatively instead — e.g. 'significant revenue exposure' "
    "rather than inventing '$2B in losses'; 'a dominant supplier' rather than "
    "inventing '70% market share'. Do not estimate, round, or extrapolate a "
    "precise-sounding figure that no tool actually provided. This applies "
    "even under time pressure to produce a 'board-ready' report — a "
    "qualitative statement grounded in real tool output is more defensible "
    "than an invented statistic."
)

ScenarioReportingAgent = SpecialistAgent(
    name          = "Scenario & Reporting Agent",
    system_prompt = SCENARIO_SYSTEM_PROMPT,
    tool_registry = SCENARIO_TOOLS,
    tool_schemas  = SCENARIO_SCHEMAS,
    max_steps     = 15,
)
