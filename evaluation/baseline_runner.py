"""
evaluation/baseline_runner.py
==============================
Two deterministic, NON-LLM comparators for the AgencyEvaluator, run for
real against your existing tool functions (no new data collection, no
new APIs, no participants — fully within the approved OREMS secondary-
data ethics application; this only re-exercises tools already approved).

WHY THIS EXISTS
---------------
Right now your agency_report.csv has 16 real scores, all from LLM-driven
orchestrator runs, all landing in "MODERATELY AGENTIC" (0.54-0.70). That
is not evidence the metric discriminates anything — it is evidence you
have only ever measured one *kind* of run. A Results chapter needs
contrast points at the edges, not just replicates in the middle.

This module gives you TWO deliberately different non-agentic anchors,
because a single "scripted baseline" is not enough — it can accidentally
score high on entropy even though it's not agentic at all (see note
below). Reporting both makes the limitation transparent instead of
letting an examiner find it.

  1. SCRIPTED_DIVERSE  — fixed order, 12 different tools called once
     each (mirrors BASELINE_PIPELINE exactly). Zero deviation, but
     HIGH entropy, because entropy measures tool-usage evenness, not
     decision randomness. Demonstrates entropy alone is not sufficient
     evidence of agency.

  2. SCRIPTED_REPETITIVE — fixed order, ONE tool called repeatedly.
     Zero deviation AND near-zero entropy. This is your genuine
     "NON-AGENTIC" floor.

Reporting all three (LLM runs, SCRIPTED_DIVERSE, SCRIPTED_REPETITIVE)
together lets you show the composite score actually spans the range,
and lets you explain in your Discussion chapter *why* two very
different non-agentic behaviours don't land in the same place.
"""

from typing import Dict, List

from agents.orchestrator import AgencyEvaluator, PersistentMemory
from services.knowledge_base import (
    tool_map_dependencies, tool_portfolio_overview, tool_assess_geo_risk,
    tool_trace_supply_chain, tool_find_substitutes, tool_identify_chokepoints,
    tool_compare_minerals, tool_get_recommendations,
    tool_list_scenarios, tool_run_scenario,
)
from services.echelon_knowledge import (
    tool_trace_full_chain, tool_echelon_risk_profile,
    tool_identify_echelon_bottleneck, tool_customer_demand_signal,
)

# NOTE: adjust these import names if your actual function names in
# knowledge_base.py / echelon_knowledge.py differ slightly — match them
# to whatever TOOL_REGISTRY / *_TOOLS dict keys you already use, e.g.
# HARDWARE_TOOLS["map_dependencies"] instead of a direct import.

SCRIPTED_DIVERSE_SEQUENCE: List[str] = [
    "portfolio_overview", "map_dependencies", "trace_supply_chain",
    "assess_geo_risk", "find_substitutes", "trace_full_chain",
    "echelon_risk_profile", "identify_echelon_bottleneck",
    "list_scenarios", "run_scenario", "get_recommendations", "finish",
]

SCRIPTED_REPETITIVE_SEQUENCE: List[str] = ["assess_geo_risk"] * 12 + ["finish"]

TOOL_FN_MAP = {
    "portfolio_overview":          lambda: tool_portfolio_overview(),
    "map_dependencies":            lambda: tool_map_dependencies("NVIDIA H100"),
    "trace_supply_chain":          lambda: tool_trace_supply_chain("Gallium"),
    "assess_geo_risk":             lambda: tool_assess_geo_risk("Gallium"),
    "find_substitutes":            lambda: tool_find_substitutes("Gallium"),
    "trace_full_chain":            lambda: tool_trace_full_chain("Gallium"),
    "echelon_risk_profile":        lambda: tool_echelon_risk_profile("Gallium"),
    "identify_echelon_bottleneck": lambda: tool_identify_echelon_bottleneck("Gallium"),
    "list_scenarios":              lambda: tool_list_scenarios(["Gallium"]),
    "run_scenario":                lambda: tool_run_scenario("China_Gallium_Export_Ban"),
    "get_recommendations":         lambda: tool_get_recommendations("NVIDIA H100"),
    "finish":                      lambda: {"status": "COMPLETE"},
}


def _run_sequence(goal: str, sequence: List[str], run_type: str, save: bool) -> Dict:
    print(f"    [{run_type}] starting ({len(sequence)} tool calls)...", flush=True)
    executed = []
    for i, tool_name in enumerate(sequence, 1):
        print(f"      ({i}/{len(sequence)}) calling {tool_name}...", flush=True)
        fn = TOOL_FN_MAP.get(tool_name)
        if fn:
            try:
                fn()
            except Exception as e:
                print(f"        (tool errored, continuing: {e})", flush=True)
        else:
            print(f"        (no function mapped for '{tool_name}' — skipped)", flush=True)
        executed.append(tool_name)
    print(f"    [{run_type}] done.", flush=True)

    scores = AgencyEvaluator().compute(goal, executed)
    scores["run_type"] = run_type

    if save:
        mem = PersistentMemory()
        run_id = mem.save_run(
            goal=goal,
            agent=f"Deterministic Baseline ({run_type})",
            steps=len(executed), tool_calls=len(executed),
            report=f"[{run_type} comparator — no LLM report generated, "
                   f"exists only to anchor the AgencyEvaluator range]",
            tools_used=list(dict.fromkeys(executed)),
        )
        mem.save_agency_metrics(run_id, scores)
        scores["run_id"] = run_id

    return scores


def run_all_baselines(goal: str, save: bool = True) -> Dict[str, Dict]:
    return {
        "SCRIPTED_DIVERSE":    _run_sequence(goal, SCRIPTED_DIVERSE_SEQUENCE, "SCRIPTED_DIVERSE", save),
        "SCRIPTED_REPETITIVE": _run_sequence(goal, SCRIPTED_REPETITIVE_SEQUENCE, "SCRIPTED_REPETITIVE", save),
    }


if __name__ == "__main__":
    # All 3 goals enabled now that the script is confirmed working.
    BENCHMARK_GOALS = [
        "Assess supply chain resilience of NVIDIA AI GPU, board-ready report",
        "Analyse geopolitical risk for Gallium, Germanium, Rare Earth Elements",
        "Trace full source-to-customer chain for a smartphone chipset",
    ]

    print(f"{'goal':50s} {'type':22s} {'entropy':>8s} {'align':>8s} {'deviation':>10s} {'composite':>10s} tier")
    for g in BENCHMARK_GOALS:
        print(f"\n=== GOAL: {g} ===", flush=True)
        results = run_all_baselines(g)
        for run_type, s in results.items():
            print(f"{g[:50]:50s} {run_type:22s} "
                  f"{s['tool_entropy']:8.4f} {s['goal_alignment']:8.4f} "
                  f"{s['pipeline_deviation']:10.4f} {s['composite_score']:10.4f} {s['agency_tier']}")
    print("\nALL DONE.", flush=True)
