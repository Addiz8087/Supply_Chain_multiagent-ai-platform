# Evaluation Protocol & Limitations Notes
### For: AI Supply Chain Resilience Platform (Aditya Khandale, 2731602)
### Cross-referenced to OREMS ethics application (Ref: 2026-32564-34655)

This document does two things:
1. Gives you a concrete benchmark design to run before your Results chapter,
   using only the tools/data already covered by your ethics approval.
2. Gives you draft text you can adapt for your Methodology / Limitations
   sections, addressing each weak point directly rather than leaving it
   for an examiner to find.

**Ethics scope check:** everything below re-exercises tool functions you've
already built (World Bank API, USGS static tables, GDELT, REST Countries,
scenario simulation, LLM report synthesis). No new data source, no human
participant, no personal data. This stays entirely inside "Secondary data
analysis" as declared on your WS2 form — you are not collecting anything
new, only running your own system more times and analysing what it does.

---

## 1. Benchmark suite design

Your current data has two structural problems: (a) 23/39 runs have no
agency metrics at all (pre-fix), and (b) of the 16 valid runs, 22-count
worth of raw runs are the same repeated goal, so you effectively have
weak coverage of the goal-space and zero non-agentic comparison points.

Run the following **before** writing your Results chapter:

| Tier | Purpose | Runs |
|---|---|---|
| A. Diverse LLM goals | Show the metric responds to different task types | 8 distinct goals × 2 reps = 16 |
| B. Repeated goal (reliability) | Show run-to-run variance for the *same* task | 1 goal × 5 reps (you already have ~7-8 of these — keep them, just label them explicitly as a reliability sub-study, not part of the diversity claim) |
| C. Scripted non-agentic baselines | Anchor the low end of the score range | `baseline_runner.py` — 2 baseline types × however many of your Tier-A goals you want anchors for |

Suggested Tier-A goal list (mix of narrow/single-mineral vs broad/cross-agent,
so the entropy and alignment metrics actually get exercised differently):

- "Assess supply chain resilience of NVIDIA AI GPU, board-ready report" (broad, multi-agent)
- "Assess supply chain resilience of AMD AI GPU, board-ready report" (broad, comparison case)
- "Assess supply chain resilience of an AI server's memory chips (HBM)" (broad, different hardware)
- "Analyse geopolitical risk for Gallium, Germanium, Rare Earth Elements" (narrow, single-agent-heavy)
- "Analyse geopolitical risk for Cobalt and Lithium in EV battery manufacturing" (narrow, out-of-core-domain check)
- "Trace full source-to-customer chain for a smartphone chipset" (echelon-agent-heavy)
- "Simulate a China gallium export ban and its impact on AI hardware supply" (scenario-agent-heavy)
- "Compare mineral risk for silicon vs rare earths in AI chip production" (comparison task)

You already have single runs of most of these — the fix is running each
**at least twice** and making sure `save_agency_metrics` fires (confirm the
DB write actually happens, since that's exactly what silently failed for
your first 23 runs).

**Reporting table for your Results chapter** should look like:

| Run type | n | Mean composite | Range | Tier(s) observed |
|---|---|---|---|---|
| LLM — diverse goals | 16 | … | … | … |
| LLM — repeated goal (reliability) | 7-8 | … | … | … |
| Scripted, diverse-order baseline | k | … | … | … |
| Scripted, repetitive baseline | k | … | … | … |

If the two scripted baselines land in different tiers from each other (they
should — see the entropy/deviation note below), that is your strongest piece
of evidence the framework discriminates *something*, even before you get to
the LLM runs.

---

## 2. Draft Limitations text (adapt to your voice/word count)

> **Agency Evaluator validation scope.** The AgencyEvaluator's three
> component metrics (tool-call entropy, goal-alignment, pipeline deviation)
> were validated against a benchmark suite of N LLM-driven runs across
> M distinct goals, alongside two deterministic non-agentic baselines
> (a fixed diverse-tool-order sequence and a fixed single-tool-repeat
> sequence) used to anchor the lower end of the composite score range.
> A notable finding from this baseline comparison is that tool-call
> entropy alone does not distinguish agentic from scripted behaviour: a
> fully deterministic sequence that happens to call many distinct tools
> scores similarly on entropy to an LLM-driven run, because entropy
> measures the evenness of tool usage rather than the presence of
> LLM-driven decision-making. Only pipeline deviation reliably separated
> the scripted baselines from the LLM-driven runs in this evaluation. This
> suggests the composite score should be interpreted as an aggregate
> signal across three distinct behavioural dimensions rather than as a
> single unified "agency" construct, and future work should weight or
> report these dimensions separately rather than only as a composite.

> **Goal-alignment measurement.** Goal-alignment is computed via
> [substring matching against a hand-authored keyword dictionary /
> TF-IDF cosine similarity between goal text and tool-keyword bags — state
> whichever version you actually shipped]. This is a lightweight proxy for
> semantic alignment, not a learned or validated alignment model; it will
> under- or over-count alignment for goal phrasings that use synonyms or
> indirect language not present in the keyword dictionary. A larger-scale
> evaluation using sentence-embedding similarity (e.g. against a
> transformer encoder) is left as future work.

> **Pipeline-deviation baseline.** The reference pipeline used to compute
> deviation was author-defined based on the logical order in which the
> platform's own tools are intended to be used (portfolio survey →
> dependency mapping → risk assessment → substitution analysis → scenario
> simulation → reporting), rather than empirically derived from expert
> annotation or a corpus of prior analyst workflows. This is a reasonable
> starting reference for a first iteration of the framework, but it
> represents the author's assumption of an "expected" pipeline rather than
> a ground-truth baseline, and deviation scores should be read
> accordingly.

> **Numeric provenance in generated reports.** Agent system prompts
> instruct the underlying LLM not to state a specific number unless it was
> returned by a tool call. This instruction was supplemented with an
> automated post-hoc check (`report_validator.py`) that cross-references
> every numeric token in the final report against numbers present in the
> tool-call observation log for that run. Across the benchmark suite, X%
> of numeric claims in generated reports were traceable to a tool
> observation [fill in your real number after running it]. This check is
> a lower-bound surface-level control — it can be satisfied by
> coincidental number matches and cannot detect qualitative (non-numeric)
> fabrication — and should not be read as a guarantee against
> hallucination, only as a partial, auditable mitigation.

> **Model capability constraint.** All agent reasoning was performed using
> Mistral's free-tier `mistral-small-latest` model, selected for
> zero-cost operation within the project's resource constraints. This is a
> capability ceiling on the reasoning depth achievable by each specialist
> agent, and it is plausible that some portion of the observed
> "MODERATELY AGENTIC" clustering reflects the reasoning capacity of a
> small model rather than a property of the multi-agent architecture
> itself. This is a confound the current evaluation cannot fully separate
> out; a comparison run against a larger model (e.g. `mistral-large-latest`
> or an equivalent) on a small subset of benchmark goals, resources
> permitting, would help isolate model-capability effects from
> architecture effects in future work.

---

## 3. What to actually run before you write Results

1. `pip install scikit-learn` if not already present (needed for
   `agency_evaluator_patch.py`).
2. Apply the `goal_alignment_tfidf` patch to `orchestrator.py`.
3. Run `baseline_runner.py` — this writes real rows to your existing
   SQLite DB via `PersistentMemory`, tagged as baseline run types.
4. Run the 8 Tier-A goals × 2 reps through your normal orchestrator flow
   (16 more runs, confirming `save_agency_metrics` actually fires each
   time — add a print/log check if you're not 100% sure it did before).
5. For each of those 16 runs, call `validate_run()` from
   `report_validator.py` and log the `pct_verified` figure.
6. Re-export with `export_agency_report.py` — you'll now have a CSV with
   real variance, real baseline anchors, and a numeric-provenance column
   you can cite directly in Results.
