"""
export_agency_report.py
=========================
Run this AFTER you've done a handful of fresh, varied orchestrator runs
with the patched orchestrator.py (which now saves real per-run agency
metrics to the new agency_metrics table).

Usage:
    python export_agency_report.py

Produces: agency_report.csv in the current folder — paste straight into
your Results chapter, or load into pandas for a chart.

Rows for your OLD 23 runs (before the fix) will show blank/NaN in the
agency columns, since the true per-call tool sequence was never stored
for those — only a deduplicated list. State this honestly as a
limitation rather than backfilling guessed numbers: "Agency metrics were
instrumented from run N onward; earlier runs are reported using proxy
diversity/steps-per-call statistics only."
"""

from agents.orchestrator import PersistentMemory

if __name__ == "__main__":
    mem = PersistentMemory()
    df = mem.get_agency_report()
    print(df.to_string(index=False))
    df.to_csv("agency_report.csv", index=False)
    print("\nSaved to agency_report.csv")

    # Quick sanity summary for runs that DO have real agency metrics
    has_metrics = df.dropna(subset=["composite_score"])
    if len(has_metrics):
        print(f"\n{len(has_metrics)} run(s) have real agency metrics:")
        print(has_metrics[["run_id", "tool_entropy", "goal_alignment",
                            "pipeline_deviation", "composite_score", "agency_tier"]]
              .to_string(index=False))
    else:
        print("\nNo runs with real agency metrics yet — run the platform a few "
              "times with varied goals using the patched orchestrator.py first.")
