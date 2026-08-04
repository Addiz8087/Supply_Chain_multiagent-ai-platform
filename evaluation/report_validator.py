"""
evaluation/report_validator.py
================================
Enforces (rather than just prompts for) the "no fabricated numbers"
rule your agent system prompts already state as a DATA ACCURACY RULE.

WHY THIS EXISTS
---------------
Right now the only thing stopping an LLM from inventing a precise
figure ("$2.3B exposure", "63% market share") in the final report is a
system-prompt instruction. That is a mitigation, not a control. This
module gives you an actual check you can run against every
orchestrator output and report in your Methodology/Evaluation chapter:
"X% of numeric claims in generated reports were traceable to a tool
observation; Y% were flagged as unverifiable."

WHAT IT DOES
------------
1. Extracts every numeric token from the final report text (dollar
   figures, percentages, tonnages, plain numbers with >=2 digits —
   single digits like "3 agents" are ignored as noise).
2. Extracts every numeric token that appears anywhere in the
   scratchpad's tool OBSERVATIONS (i.e. actually came back from a
   tool call, not from the LLM's own reasoning text).
3. Flags any report number NOT found in the observation numbers as
   UNVERIFIED — meaning the LLM stated it without a traceable source.

LIMITATIONS TO STATE HONESTLY IN YOUR DISSERTATION
----------------------------------------------------
- This is a surface-level provenance check, not semantic verification.
  A number that happens to also appear in the observations by
  coincidence (e.g. "2024" as a year) will pass even if used in a
  different, unsupported context. Report this as a known limitation,
  not as proof of zero hallucination.
- It cannot catch qualitative fabrication (invented facts with no
  numbers attached).
- Recommended framing: "an automated lower-bound check on numeric
  fabrication," not "a hallucination detector."
"""

import re
from typing import Dict, List, Set


NUMBER_PATTERN = re.compile(
    r"\$?\d[\d,]*\.?\d*\s?%?|\d+\.\d+"
)


def _extract_numbers(text: str) -> Set[str]:
    """Extract numeric tokens, normalised (strip $, %, commas)."""
    raw = NUMBER_PATTERN.findall(text or "")
    cleaned = set()
    for tok in raw:
        norm = tok.replace("$", "").replace(",", "").replace("%", "").strip()
        # ignore trivial single-digit noise (e.g. "3 agents", "step 2")
        if norm and (len(norm.replace(".", "")) >= 2):
            cleaned.add(norm)
    return cleaned


def validate_report(report_text: str, agent_results: Dict) -> Dict:
    """
    agent_results: the same dict returned by OrchestratorAgent.run()
    under key "agent_results" — each value has a "scratch" Scratchpad
    object with the full ReAct trace for that agent.

    Returns a dict summarising verified vs unverified numeric claims.
    """
    report_numbers = _extract_numbers(report_text)

    observed_numbers: Set[str] = set()
    for agent_name, result in agent_results.items():
        scratch = result.get("scratch")
        if scratch is None:
            continue
        for entry in scratch._entries:
            if entry.role == "observation":
                obs_text = str(entry.content)
                observed_numbers |= _extract_numbers(obs_text)

    verified = report_numbers & observed_numbers
    unverified = report_numbers - observed_numbers

    total = len(report_numbers) or 1  # avoid div-by-zero
    return {
        "n_numbers_in_report":  len(report_numbers),
        "n_verified":           len(verified),
        "n_unverified":         len(unverified),
        "pct_verified":         round(100 * len(verified) / total, 1),
        "unverified_numbers":   sorted(unverified),
        "verified_numbers":     sorted(verified),
    }


def validate_run(run_output: Dict) -> Dict:
    """Convenience wrapper — pass the full dict from OrchestratorAgent.run()."""
    return validate_report(
        run_output.get("final_report", ""),
        run_output.get("agent_results", {}),
    )


if __name__ == "__main__":
    # Example usage after a real orchestrator run:
    #
    #   from agents.orchestrator import OrchestratorAgent
    #   from evaluation.report_validator import validate_run
    #
    #   orch = OrchestratorAgent()
    #   result = orch.run("Assess supply chain resilience of NVIDIA AI GPU...")
    #   check = validate_run(result)
    #   print(check)
    #
    # Then aggregate `check["pct_verified"]` across your whole benchmark
    # suite for a single reportable statistic in your Results chapter.
    pass
