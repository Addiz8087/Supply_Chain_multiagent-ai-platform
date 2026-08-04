"""
streamlit_app.py
================
Multi-Agent AI Supply Chain Resilience Platform 
Production Streamlit dashboard. Run with:
    streamlit run streamlit_app.py
"""

import json
import time
from collections import Counter

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import threading
from streamlit.runtime.scriptrunner import add_script_run_ctx
from services.glass_ui import inject_glass_ui
# RAGSimulationAgent import removed — the RAG/Mesa lithium-stockpiling
# module is out of scope for the approved OREMS ethics application and
# is no longer wired into the orchestrator (see agents/orchestrator.py).

def _run_orchestrator_background(goal, session_state):
    """Runs off the main Streamlit thread so switching pages can't kill it."""
    try:
        orch = OrchestratorAgent(verbose=False)
        result = orch.run(goal)
        session_state["last_analysis_result"] = result
        session_state["analysis_status"] = "done"
    except Exception as e:
        session_state["analysis_error"] = str(e)
        session_state["analysis_status"] = "error"


def _run_batch_background(goals, session_state):
    """Runs a list of goals ONE AT A TIME (not in parallel — parallel calls
    would make the Mistral free-tier rate-limiting worse, not better).
    Updates progress after each goal so the UI can show live status. Each
    goal is still saved to the database individually via orch.run(), exactly
    like a single manual run, so nothing else downstream (export_agency_
    report.py etc.) needs to change."""
    session_state["batch_results"] = []
    session_state["batch_total"] = len(goals)
    for i, g in enumerate(goals):
        g = g.strip()
        if not g:
            continue
        session_state["batch_current"] = i + 1
        session_state["batch_current_goal"] = g
        try:
            orch = OrchestratorAgent(verbose=False)
            result = orch.run(g)
            session_state["batch_results"].append({"goal": g, "status": "done", "result": result})
        except Exception as e:
            session_state["batch_results"].append({"goal": g, "status": "error", "error": str(e)})
    session_state["batch_status"] = "done"
# ── Page config (must be first Streamlit call) ─────────────────────────────
st.set_page_config(
    page_title  = "Supply Chain AI Platform",
    page_icon   = "🤖",
    layout      = "wide",
    initial_sidebar_state = "expanded",
)

# ── Liquid Glass UI theme ──────────────────────────────────────────────────
inject_glass_ui()

# ── Bootstrap: validate config before importing agents ────────────────────
try:
    from app.config import validate
    validate()
except EnvironmentError as e:
    st.error(str(e))
    st.stop()

# ── Import platform modules ────────────────────────────────────────────────
from agents.orchestrator import OrchestratorAgent, PersistentMemory
from services.knowledge_base import (
    HW_DEPS, SUPPLY_CHAIN, GEO_RISKS, RISK_W, SUBSTITUTES, SCENARIOS,
    tool_assess_geo_risk, tool_portfolio_overview,
)
from services.echelon_knowledge import (
    ECHELON_CHAIN, ECHELON_ORDER,
    tool_trace_full_chain, tool_echelon_risk_profile,
    tool_identify_echelon_bottleneck, tool_customer_demand_signal,
)
from services.data_sources import list_sources
from services.live_data import (
    fetch_all_prices, fetch_live_price, production_map_data,
    PRODUCTION_DATA, STATIC_PRICES,
)
from services.mistral_service import get_mistral_service
# usgs_reference and rag_knowledge imports removed — those modules are
# out of scope for the approved OREMS ethics application and are no
# longer used anywhere in this app.


# ══════════════════════════════════════════════════════════════════════════
#  CUSTOM CSS — professional dark-accent theme
# ══════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
  /* Main background */
  .main .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }

  /* Metric cards */
  [data-testid="metric-container"] {
    background: #f8f9fb;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 1rem 1.25rem;
  }

  /* Risk tier badges */
  .badge-critical { background:#fee2e2; color:#991b1b; padding:3px 10px; border-radius:12px; font-size:12px; font-weight:600; }
  .badge-high     { background:#fef3c7; color:#92400e; padding:3px 10px; border-radius:12px; font-size:12px; font-weight:600; }
  .badge-medium   { background:#d1fae5; color:#065f46; padding:3px 10px; border-radius:12px; font-size:12px; font-weight:600; }
  .badge-low      { background:#dbeafe; color:#1e40af; padding:3px 10px; border-radius:12px; font-size:12px; font-weight:600; }

  /* Section headers */
  .section-header { font-size:1.1rem; font-weight:600; color:#1e293b; margin:1.5rem 0 0.75rem 0; border-bottom:2px solid #6366f1; padding-bottom:0.4rem; }

  /* Report box */
  .report-box { background:#f1f5f9; border-left:4px solid #6366f1; padding:1.25rem 1.5rem; border-radius:0 8px 8px 0; font-size:0.93rem; line-height:1.7; white-space:pre-wrap; }

  /* Agent log */
  .agent-log { background:#0f172a; color:#94a3b8; padding:1rem 1.25rem; border-radius:8px; font-family:monospace; font-size:0.82rem; max-height:360px; overflow-y:auto; white-space:pre-wrap; }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════
#  HELPERS & COLOUR MAPS
# ══════════════════════════════════════════════════════════════════════════

RISK_COLOURS = {
    "CRITICAL": "#ef4444",
    "HIGH":     "#f59e0b",
    "MEDIUM":   "#10b981",
    "LOW":      "#3b82f6",
    "EXTREME":  "#7c3aed",
    "SEVERE":   "#dc2626",
}

def risk_badge(tier: str) -> str:
    css = {"CRITICAL": "critical", "HIGH": "high", "MEDIUM": "medium", "LOW": "low"}.get(tier, "low")
    return f'<span class="badge-{css}">{tier}</span>'

def product_risk_df() -> pd.DataFrame:
    rows = []
    for p, mins in HW_DEPS.items():
        score = sum(RISK_W.get(m, 1) for m in mins)
        tier  = "CRITICAL" if score >= 30 else "HIGH" if score >= 20 else "MEDIUM" if score >= 10 else "LOW"
        rows.append({"Product": p, "Risk Score": score, "Risk Tier": tier,
                     "Minerals": len(mins), "Mineral List": ", ".join(mins)})
    return pd.DataFrame(rows).sort_values("Risk Score", ascending=False)


# ══════════════════════════════════════════════════════════════════════════
#  SIDEBAR
# ══════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("""
    <div style='background: linear-gradient(90deg, #6366f1, #8b5cf6); 
    padding: 15px; border-radius: 10px; text-align: center;'>
    <h2 style='color: white; margin: 0;'>⛓ Supply Chain AI</h2>
    </div>
""", unsafe_allow_html=True)
    st.markdown("Multi-Agent Platform")
    st.caption("© 2026 Aditya Khandale · MSc Business Analytics · University of Bristol, UK")
    st.divider()

    page = st.radio(
        "Navigation",
        ["🏠 Dashboard", "🤖 Run Analysis", "🌍 Mineral Intelligence",
         "🔗 Supply Chain Echelons", "🗺️ World Map & Production",
         "💰 Live Prices", "⚙️ Hardware Risk",
         "📊 Agency Evaluation", "💾 Memory & History", "📚 Data Sources"],
        label_visibility="collapsed",
    )

    st.divider()
    with st.expander("ℹ️ System Info"):
        st.caption(f"Model: mistral-small-latest")
        st.caption(f"Agents: 6 (Orchestrator + 5 Specialists)")
        st.caption(f"Tools: {len(HW_DEPS) + len(SUPPLY_CHAIN)} domain items")
        st.caption("APIs: World Bank · USGS · UN Comtrade · REST Countries")
        st.caption("Cost: £0 — all free tier")


# ══════════════════════════════════════════════════════════════════════════
#  PAGE: DASHBOARD
# ══════════════════════════════════════════════════════════════════════════

if page == "🏠 Dashboard":
    st.title("AI Supply Chain Resilience Platform")
    st.caption("Multi-Agent · Mistral AI · Live APIs · Persistent Memory · v8.0")

    # ── KPI Row ────────────────────────────────────────────────────────────
    col1, col2, col3, col4, col5 = st.columns(5)
    df_p = product_risk_df()
    n_critical = (df_p["Risk Tier"] == "CRITICAL").sum()
    n_high     = (df_p["Risk Tier"] == "HIGH").sum()
    avg_score  = df_p["Risk Score"].mean()

    col1.metric("Hardware Products", len(HW_DEPS))
    col2.metric("Critical Minerals Tracked", len(SUPPLY_CHAIN))
    col3.metric("Critical-Risk Products", int(n_critical), delta="urgent" if n_critical else None)
    col4.metric("High-Risk Products", int(n_high))
    col5.metric("Avg Portfolio Risk Score", f"{avg_score:.1f}")

    st.divider()

    # ── Charts Row 1 ───────────────────────────────────────────────────────
    c1, c2 = st.columns(2)

    with c1:
        st.markdown('<div class="section-header">Product Risk Scores</div>', unsafe_allow_html=True)
        fig = px.bar(
            df_p, x="Product", y="Risk Score", color="Risk Tier",
            color_discrete_map=RISK_COLOURS,
            text="Risk Score",
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(xaxis_tickangle=-20, height=380,
                          plot_bgcolor="rgba(255,255,255,0.04)", paper_bgcolor="rgba(0,0,0,0)",
                          margin=dict(t=20, b=80))
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.markdown('<div class="section-header">Mineral Criticality Weights</div>', unsafe_allow_html=True)
        df_m = pd.DataFrame({"Mineral": list(RISK_W.keys()), "Weight": list(RISK_W.values())}).sort_values("Weight", ascending=False)
        fig2 = px.bar(
            df_m, x="Mineral", y="Weight", color="Weight",
            color_continuous_scale=["#3b82f6", "#f59e0b", "#ef4444"],
            text="Weight",
        )
        fig2.update_traces(textposition="outside")
        fig2.update_layout(xaxis_tickangle=-20, height=380,
                           plot_bgcolor="rgba(255,255,255,0.04)", paper_bgcolor="rgba(0,0,0,0)",
                           margin=dict(t=20, b=80))
        st.plotly_chart(fig2, use_container_width=True)

    # ── Heatmap ────────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">Hardware × Mineral Risk Matrix</div>', unsafe_allow_html=True)
    products = list(HW_DEPS.keys())
    minerals = sorted(set(m for ms in HW_DEPS.values() for m in ms))
    matrix   = [[RISK_W.get(m, 1) if m in HW_DEPS[p] else 0 for m in minerals] for p in products]

    fig3 = go.Figure(go.Heatmap(
        z=matrix, x=minerals, y=products,
        colorscale=[[0, "#f8fafc"], [0.2, "#bfdbfe"], [0.6, "#fcd34d"], [1.0, "#ef4444"]],
        text=[[str(v) if v > 0 else "" for v in row] for row in matrix],
        texttemplate="%{text}", hoverongaps=False,
    ))
    fig3.update_layout(height=300, xaxis_tickangle=-25, margin=dict(t=10, b=60),
                       plot_bgcolor="rgba(255,255,255,0.04)", paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig3, use_container_width=True)

    # ── Geo risks ──────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">Active Geopolitical Risk Events</div>', unsafe_allow_html=True)
    st.dataframe(
        GEO_RISKS.style.map(
            lambda v: "background-color:#fee2e2; color:#991b1b; font-weight:600"
            if v == "HIGH" else "background-color:#fef3c7; color:#92400e",
            subset=["level"]
        ),
        use_container_width=True, hide_index=True,
    )


# ══════════════════════════════════════════════════════════════════════════
#  PAGE: RUN ANALYSIS
# ══════════════════════════════════════════════════════════════════════════

elif page == "🤖 Run Analysis":
    st.title("🤖 Multi-Agent Analysis")
    st.caption("The Orchestrator decomposes your goal and delegates to 3 specialist agents.")

    # ── Goal presets ───────────────────────────────────────────────────────
    presets = {
        "NVIDIA AI GPU — full analysis":
            "Assess the supply chain resilience of the NVIDIA AI GPU and produce a board-ready executive report with actionable recommendations.",
        "Full portfolio overview":
            "Assess supply chain resilience across the full AI hardware portfolio and identify the single highest-impact action to reduce aggregate risk.",
        "Chokepoints & substitutes":
            "Identify all supply chain chokepoints in the AI hardware portfolio and find the best substitute materials to reduce dependency.",
        "Scenario: Taiwan disruption":
            "Run the Taiwan Semiconductor Disruption scenario and assess the full impact on AI hardware supply chains with recovery recommendations.",
        "Custom goal": "",
    }

    col_pre, col_run = st.columns([3, 1])
    with col_pre:
        preset_choice = st.selectbox("Quick-start goal", list(presets.keys()))
    with col_run:
        st.write("")
        st.write("")

    default_goal = presets[preset_choice]
    # Bind the text box to session_state so a typed edit survives the
    # rerun that happens when you click "Run" — previously the box was
    # rebuilt from the preset on every rerun, silently discarding
    # whatever you'd typed the moment the analysis finished.
    if st.session_state.get("_last_preset") != preset_choice:
        st.session_state["_last_preset"] = preset_choice
        st.session_state["goal_input"] = default_goal
    goal = st.text_area("Analysis goal (edit or write your own)",
                         key="goal_input", height=100)

    col_a, col_b = st.columns([1, 4])
    with col_a:
        run_btn = st.button("🚀 Run Multi-Agent Analysis", type="primary", use_container_width=True)

    if run_btn and goal.strip():
        # Clear any previous run's state before starting a fresh one
        st.session_state["analysis_status"] = "running"
        st.session_state["analysis_start_time"] = time.time()
        st.session_state.pop("last_analysis_result", None)
        st.session_state.pop("analysis_error", None)

        # Run the orchestrator on a background thread. Unlike running it
        # directly in the script body, this survives the user navigating
        # to another page — Streamlit interrupting/rerunning the script
        # does NOT stop this thread, since it's independent of the
        # script's own execution lifecycle.
        thread = threading.Thread(
            target=_run_orchestrator_background,
            args=(goal, st.session_state),
            daemon=True,
        )
        add_script_run_ctx(thread)  # lets the thread safely touch session_state
        thread.start()
        st.session_state["analysis_thread"] = thread

    elif run_btn and not goal.strip():
        st.warning("Please enter a goal before running.")

    # ── Status banner: shown whether we just clicked Run, or navigated
    #    back to this page while a background run is still in progress
    status = st.session_state.get("analysis_status")

    if status == "running":
        elapsed = time.time() - st.session_state.get("analysis_start_time", time.time())
        mins, secs = divmod(int(elapsed), 60)
        st.info(
            f"⏳ Orchestrator is working ({mins}m {secs}s elapsed). Feel free "
            f"to browse other pages — the analysis keeps running in the "
            f"background. Just come back to this page and it'll show the "
            f"finished report automatically once it's done."
        )
        if elapsed > 240:  # 4 minutes — should be well past normal completion
            st.warning(
                "This is taking much longer than usual (normal runs finish "
                "in under 4 minutes). This almost always means the Mistral "
                "API is rate-limiting your requests. **Check the terminal "
                "window** where you ran `streamlit run` — if you see "
                "`⏳ Rate limit — waiting...` messages repeating, that's "
                "confirmed. Wait a minute for the rate limit to clear, then "
                "use the button below to reset and try again with a "
                "simpler goal (or fewer agents)."
            )
            if st.button("🔄 Reset stuck analysis"):
                st.session_state["analysis_status"] = None
                st.session_state.pop("analysis_start_time", None)
                st.session_state.pop("last_analysis_result", None)
                st.session_state.pop("analysis_error", None)
                st.rerun()
    elif status == "error":
        st.error(f"Analysis failed: {st.session_state.get('analysis_error')}")
    elif status == "done" and "last_analysis_result" in st.session_state:
        st.success(
            f"✅ Analysis complete — Run #{st.session_state['last_analysis_result']['run_id']}"
        )

    # ── Show the most recent result, even after switching to another page
    #    and coming back — pulled from session_state, not a local variable
    if "last_analysis_result" in st.session_state:
        result_holder = st.session_state["last_analysis_result"]

        st.divider()

        # ── Executive Report ───────────────────────────────────────────────
        st.markdown("### 📋 Executive Report")
        st.markdown(
            f'<div class="report-box">{result_holder["final_report"]}</div>',
            unsafe_allow_html=True,
        )
        with st.expander("ℹ️ Data provenance & limitations (read before citing figures)"):
            st.markdown(
                "- **Verified/cited data**: mineral production figures, country "
                "stability scores, and trade patterns are drawn from USGS "
                "Mineral Commodity Summaries and World Bank governance "
                "indicators (see the Data Sources page).\n"
                "- **AI-synthesised narrative**: risk assessments, "
                "recommendations, and scenario impact descriptions above are "
                "generated by the LLM, grounded in the tool outputs from this "
                "run — not independently fact-checked line by line.\n"
                "- **Any specific number** (e.g. a dollar figure or "
                "percentage) not visible in the Agent Summaries' tool outputs "
                "below should be treated as an illustrative estimate, not a "
                "verified fact, and reported as such in the dissertation."
            )

        st.divider()

        # ── Per-agent summary ──────────────────────────────────────────────
        st.markdown("### 🤖 Agent Summaries")
        cols = st.columns(len(result_holder["agent_results"]))
        for col, (agent_name, ar) in zip(cols, result_holder["agent_results"].items()):
            with col:
                st.metric(agent_name.split(" ")[0] + " Agent",
                          f"{ar['steps']} steps")
                st.caption(f"Tool calls: {ar['tool_calls']}")
                st.caption(f"Tools: {', '.join(ar['tools_used'][:3])}{'…' if len(ar['tools_used']) > 3 else ''}")

        st.divider()

        # ── Agency scores ──────────────────────────────────────────────────
        st.markdown("### 📊 Agency Evaluation")
        sc = result_holder["agency_scores"]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Composite Score", f"{sc['composite_score']:.3f}", help="0=non-agentic, 1=highly agentic")
        c2.metric("Tool Entropy",    f"{sc['tool_entropy']:.3f}",    help="Diversity of tool usage")
        c3.metric("Goal Alignment",  f"{sc['goal_alignment']:.3f}",  help="Relevance of tools to goal")
        c4.metric("Pipeline Deviation", f"{sc['pipeline_deviation']:.3f}", help="Deviation from scripted baseline")
        st.info(f"Agency Tier: **{sc['agency_tier']}** — {sc['n_tool_calls']} total tool calls, {sc['n_unique_tools']} unique tools")

        # Tool call chart
        if sc["tool_distribution"]:
            tc_df = pd.DataFrame({
                "Tool": list(sc["tool_distribution"].keys()),
                "Calls": list(sc["tool_distribution"].values()),
            }).sort_values("Calls", ascending=False)
            fig_tc = px.bar(tc_df, x="Tool", y="Calls",
                            title="Tool Call Frequency This Run",
                            color="Calls",
                            color_continuous_scale=["#bfdbfe", "#6366f1"])
            fig_tc.update_layout(xaxis_tickangle=-30, height=320,
                                 plot_bgcolor="rgba(255,255,255,0.04)", paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_tc, use_container_width=True)

        # ── Delegation plan ────────────────────────────────────────────────
        with st.expander("🗺️ Orchestrator delegation plan"):
            for i, step in enumerate(result_holder["plan"], 1):
                st.markdown(f"**{i}. {step['agent']}**")
                st.caption(step["task"])

    st.divider()

    # ══════════════════════════════════════════════════════════════════
    #  BATCH RUN — for collecting dissertation evaluation data across
    #  several varied goals without manually clicking Run each time.
    #  Runs SEQUENTIALLY (not parallel) to avoid stacking Mistral
    #  rate-limit retries on top of each other.
    # ══════════════════════════════════════════════════════════════════
    st.markdown("### 📦 Batch Run (multiple goals, one after another)")
    st.caption(
        "Paste one goal per line. Each is run sequentially and saved to "
        "the database exactly like a single manual run — use this to "
        "collect varied evaluation data for your Results chapter without "
        "clicking Run 9 separate times."
    )
    default_batch = (
        "Assess supply chain resilience of an AI server's memory chips (HBM)\n"
        "Analyse geopolitical risk for Gallium, Germanium, Rare Earth Elements\n"
        "Analyse geopolitical risk for Cobalt and Lithium in EV battery manufacturing\n"
        "Trace full source-to-customer chain for a smartphone chipset\n"
        "Simulate a China gallium export ban and its impact on AI hardware supply\n"
        "Simulate a Taiwan semiconductor disruption scenario\n"
        "Identify chokepoints across an AI datacentre hardware portfolio\n"
        "Compare mineral risk for silicon vs rare earths in AI chip production\n"
        "Assess resilience of AMD AI GPU, board-ready report"
    )
    batch_text = st.text_area("Remaining goals (one per line)", value=default_batch, height=200)

    batch_status = st.session_state.get("batch_status")
    batch_running = batch_status == "running"

    if st.button("🚀 Run Batch (sequential)", disabled=batch_running):
        goals = [g for g in batch_text.split("\n") if g.strip()]
        st.session_state["batch_status"] = "running"
        st.session_state["batch_results"] = []
        st.session_state["batch_current"] = 0
        st.session_state["batch_total"] = len(goals)
        t = threading.Thread(target=_run_batch_background, args=(goals, st.session_state), daemon=True)
        add_script_run_ctx(t)
        t.start()
        st.rerun()

    if batch_status == "running":
        cur = st.session_state.get("batch_current", 0)
        total = st.session_state.get("batch_total", 0)
        cur_goal = st.session_state.get("batch_current_goal", "")
        st.info(f"⏳ Running goal {cur} of {total}: *{cur_goal}*")
        st.progress(cur / total if total else 0)
        st.caption("This page auto-refreshes if you stay on it, or check back after a few minutes.")
        time.sleep(3)
        st.rerun()
    elif batch_status == "done":
        results = st.session_state.get("batch_results", [])
        n_done = sum(1 for r in results if r["status"] == "done")
        n_err = sum(1 for r in results if r["status"] == "error")
        st.success(f"✅ Batch complete — {n_done} succeeded, {n_err} failed")
        for r in results:
            icon = "✅" if r["status"] == "done" else "❌"
            with st.expander(f"{icon} {r['goal']}"):
                if r["status"] == "done":
                    st.markdown(r["result"]["final_report"][:1500] +
                                 ("..." if len(r["result"]["final_report"]) > 1500 else ""))
                else:
                    st.error(r["error"])
        if st.button("Clear batch results"):
            st.session_state.pop("batch_status", None)
            st.session_state.pop("batch_results", None)
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════
#  PAGE: MINERAL INTELLIGENCE
# ══════════════════════════════════════════════════════════════════════════

elif page == "🌍 Mineral Intelligence":
    st.title("🌍 Mineral Intelligence")

    col_sel, col_info = st.columns([1, 2])
    with col_sel:
        mineral = st.selectbox("Select mineral", list(SUPPLY_CHAIN.keys()))

    sc_data  = SUPPLY_CHAIN.get(mineral, {})
    geo_data = tool_assess_geo_risk(mineral)
    subs     = SUBSTITUTES.get(mineral, [])

    with col_info:
        tier = sc_data.get("risk", "LOW")
        st.markdown(f"**{mineral}** — Risk tier: {risk_badge(tier)}", unsafe_allow_html=True)
        st.caption(f"Risk weight: {RISK_W.get(mineral, 1)}/10")

    st.divider()

    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown("#### 🏭 Supply Chain Tiers")
        st.markdown(f"**Tier 1 — Processors**")
        for s in sc_data.get("T1", []):
            st.write(f"• {s}")
        st.markdown(f"**Tier 2 — Refiners**")
        for s in sc_data.get("T2", []):
            st.write(f"• {s}")
        st.markdown(f"**Tier 3 — Origin Countries**")
        countries = sc_data.get("T3", [])
        single = len(countries) == 1
        for c in countries:
            flag = "🔴" if single else "🟡"
            st.write(f"{flag} {c}")
        if single:
            st.warning("⚠️ Single-country dependency — critical chokepoint")

    with c2:
        st.markdown("#### 🌐 Geopolitical Restrictions")
        restrictions = geo_data.get("restrictions", [])
        if restrictions:
            for r in restrictions:
                colour = "#fee2e2" if r["level"] == "HIGH" else "#fef3c7"
                st.markdown(
                    f"""<div style="background:{colour};padding:8px 12px;border-radius:6px;margin-bottom:6px;font-size:13px;">
                    <strong>{r['country']}</strong> — {r['restriction']}<br>
                    Level: {r['level']} · Year: {r['year']}
                    </div>""",
                    unsafe_allow_html=True,
                )
        else:
            st.success("No active restrictions recorded.")

        # Live stability (from cache / API)
        live = geo_data.get("live_country_stability", {})
        if live:
            st.markdown("**Live World Bank Stability Scores**")
            for country, info in live.items():
                band  = info.get("stability_band", "?")
                score = info.get("wb_stability", "N/A")
                icon  = "🟢" if band == "HIGH" else "🟡" if band == "MEDIUM" else "🔴"
                st.caption(f"{icon} {country}: {score} ({band})")

    with c3:
        st.markdown("#### 🔄 Substitute Materials")
        if subs:
            for s in subs:
                feas = s["feasibility"]
                colour = "#d1fae5" if feas == "HIGH" else "#fef3c7" if feas == "MEDIUM" else "#fee2e2"
                st.markdown(
                    f"""<div style="background:{colour};padding:8px 12px;border-radius:6px;margin-bottom:6px;font-size:13px;">
                    <strong>{s['material']}</strong><br>
                    Feasibility: {feas}<br>
                    <span style="color:#64748b">{s['note']}</span>
                    </div>""",
                    unsafe_allow_html=True,
                )
        else:
            st.warning("No substitutes identified.")


# ══════════════════════════════════════════════════════════════════════════
#  PAGE: SUPPLY CHAIN ECHELONS (Source -> Factory -> Distribution ->
#  Warehouse -> Retail -> Customer)
# ══════════════════════════════════════════════════════════════════════════

elif page == "🔗 Supply Chain Echelons":
    st.title("🔗 Full Supply Chain — Source to Customer")
    st.caption(
        "Closes the gap between mine and end-customer: every node below is "
        "traceable to an authentic data source (USGS / UN Comtrade / IEA), "
        "inspired by the multi-echelon agent structure in Nie et al. (2026), "
        "JORS."
    )

    mineral = st.selectbox("Select mineral", list(SUPPLY_CHAIN.keys()), key="echelon_mineral")

    chain_result = tool_trace_full_chain(mineral)
    bottleneck   = tool_identify_echelon_bottleneck(mineral)
    customer     = tool_customer_demand_signal(mineral)

    st.markdown(
        f"**{mineral}** — overall chain risk: "
        f"{risk_badge(chain_result['overall_risk'])}", unsafe_allow_html=True,
    )
    st.warning(
        f"⚠️ Weakest echelon: **{bottleneck['bottleneck_echelon']}** "
        f"(risk: {bottleneck['bottleneck_risk']})"
    )

    # Horizontal flow diagram
    cols = st.columns(len(ECHELON_ORDER))
    icons = {"source": "⛏️", "factory": "🏭", "distribution": "🚢",
             "warehouse": "🏗️", "retail": "🏬", "customer": "🧑‍💻"}
    for i, key in enumerate(ECHELON_ORDER):
        node = chain_result["chain"][i]
        with cols[i]:
            st.markdown(f"### {icons.get(key, '🔹')}")
            st.markdown(f"**{node['echelon']}**")
            ents = node.get("entities", []) or ["— not yet populated —"]
            for e in ents[:3]:
                st.caption(f"• {e}")
            ds = node["data_source"]
            st.caption(f"📎 {ds['source']} ({ds['confidence']})")

    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### 📊 Echelon Concentration Risk")
        prof_df = pd.DataFrame(tool_echelon_risk_profile(mineral)["echelon_risk_profile"])
        st.dataframe(prof_df, use_container_width=True, hide_index=True)
    with c2:
        st.markdown("#### 🧑‍💻 End-Customer Demand")
        st.write(f"**Segments:** {', '.join(customer['customer_segments']) or '— not yet populated —'}")
        st.write(f"**Scope:** {', '.join(customer['geographic_scope'])}")
        ds = customer["data_source"]
        st.caption(f"📎 Source: {ds['source']} — confidence: {ds['confidence']}")
        st.caption(ds["note"])


# ══════════════════════════════════════════════════════════════════════════
#  PAGE: WORLD MAP & PRODUCTION
# ══════════════════════════════════════════════════════════════════════════

elif page == "🗺️ World Map & Production":
    st.title("🗺️ World Production Map")
    st.caption(
        "Mine production by country for each critical mineral. "
        "Data: USGS Mineral Commodity Summaries 2025 (free, government publication). "
        "Inspired by the country-level mapping approach of the "
        "[Cambridge Global Supply Chain Observatory](https://app.cambridge-gsco.co.uk/)."
    )

    mineral_map = st.selectbox(
        "Select mineral", list(PRODUCTION_DATA.keys()), key="map_mineral"
    )
    map_data = production_map_data(mineral_map)

    if map_data["rows"]:
        map_df = pd.DataFrame(map_data["rows"])

        # ── Choropleth ──────────────────────────────────────────────────
        fig_map = px.choropleth(
            map_df,
            locations="iso3",
            color="production",
            hover_name="country",
            hover_data={"production": True, "iso3": False},
            color_continuous_scale=[
                [0.0,  "#e8f5e9"],
                [0.25, "#a5d6a7"],
                [0.5,  "#4caf50"],
                [0.75, "#f57f17"],
                [1.0,  "#b71c1c"],
            ],
            labels={"production": map_data["unit"]},
            title=f"{mineral_map} — World Mine Production ({map_data['unit']})",
        )
        fig_map.update_layout(
            geo=dict(showframe=False, showcoastlines=True,
                     projection_type="natural earth",
                     bgcolor="rgba(0,0,0,0)"),
            coloraxis_colorbar=dict(title=map_data["unit"]),
            margin=dict(l=0, r=0, t=40, b=0),
            height=460,
            paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_map, use_container_width=True)
        st.caption(f"📎 Source: {map_data['source']}")

        # ── Bar chart ───────────────────────────────────────────────────
        fig_bar = px.bar(
            map_df.sort_values("production", ascending=True),
            x="production", y="country", orientation="h",
            color="production",
            color_continuous_scale=["#a5d6a7", "#f57f17", "#b71c1c"],
            labels={"production": map_data["unit"], "country": "Country"},
            title=f"Production by country — {mineral_map}",
        )
        fig_bar.update_layout(
            showlegend=False, coloraxis_showscale=False,
            height=max(250, len(map_df) * 42),
            margin=dict(l=0, r=20, t=40, b=0),
        )
        st.plotly_chart(fig_bar, use_container_width=True)

        # ── Concentration metric ─────────────────────────────────────────
        total = map_df["production"].sum()
        top1 = map_df.sort_values("production", ascending=False).iloc[0]
        top3_pct = round(
            map_df.sort_values("production", ascending=False)
            .head(3)["production"].sum() / total * 100, 1
        )
        c1, c2, c3 = st.columns(3)
        c1.metric("Top producer", top1["country"],
                  help="Country with highest mine output")
        c2.metric("Top producer share",
                  f"{round(top1['production']/total*100,1)}%")
        c3.metric("Top-3 country share", f"{top3_pct}%",
                  help="Supply concentration indicator — higher = more fragile")

        # ── Supply chain risk context ────────────────────────────────────
        st.divider()
        st.markdown("#### 🔗 How production concentration links to supply chain risk")
        st.info(
            f"A top-3 concentration of **{top3_pct}%** means that if the top 3 "
            f"producers of **{mineral_map}** faced simultaneous disruption "
            f"(export ban, conflict, mine closure), {top3_pct}% of global supply "
            f"would be at risk. This feeds directly into the risk scores on the "
            f"Hardware Risk and Supply Chain Echelon pages."
        )
    else:
        st.warning(
            f"No USGS production data recorded yet for {mineral_map}. "
            f"Add it to services/live_data.py PRODUCTION_DATA."
        )


# ══════════════════════════════════════════════════════════════════════════
#  PAGE: LIVE PRICES
# ══════════════════════════════════════════════════════════════════════════

elif page == "💰 Live Prices":
    st.title("💰 Mineral Prices")
    st.caption(
        "Live futures prices (via yfinance where available) or latest published "
        "reference prices from USGS Mineral Commodity Summaries 2025 / LME 2024 averages. "
        "Every figure shows its source and whether it is live or a static citation."
    )

    prices = fetch_all_prices()

    # ── Price dashboard cards ────────────────────────────────────────────
    minerals_list = list(prices.keys())
    for i in range(0, len(minerals_list), 3):
        cols = st.columns(3)
        for j, mineral in enumerate(minerals_list[i:i+3]):
            p = prices[mineral]
            with cols[j]:
                live_tag = "🟢 LIVE" if p.get("is_live") else "📋 REFERENCE"
                price_val = p.get("price")
                display = f"${price_val:,.0f}" if price_val else "N/A"
                st.metric(
                    label=f"{mineral}",
                    value=display,
                    help=f"{p['unit']} · {p['source']}"
                )
                st.caption(f"{live_tag} · {p['unit']}")
                if p.get("note"):
                    st.caption(f"ℹ️ {p['note']}")

    st.divider()

    # ── Price comparison bar chart ───────────────────────────────────────
    price_df = pd.DataFrame([
        {"Mineral": m, "Price (USD)": d.get("price", 0),
         "Unit": d.get("unit", ""), "Source": d.get("source", ""),
         "Type": "Live" if d.get("is_live") else "Reference"}
        for m, d in prices.items() if d.get("price")
    ]).sort_values("Price (USD)", ascending=False)

    fig_price = px.bar(
        price_df, x="Mineral", y="Price (USD)",
        color="Type",
        color_discrete_map={"Live": "#22c55e", "Reference": "#6366f1"},
        title="Mineral Prices (USD per unit — note: units vary, see hover)",
        hover_data={"Unit": True, "Source": True},
    )
    fig_price.update_layout(
        xaxis_tickangle=-30, height=380,
        legend_title="Data type",
        margin=dict(l=0, r=0, t=40, b=0),
    )
    st.plotly_chart(fig_price, use_container_width=True)
    st.caption(
        "⚠️ Units vary per mineral (USD/t for most base metals, USD/kg for "
        "specialty metals like Gallium and Germanium). Do not compare bars "
        "directly — use this for per-mineral trend context only."
    )

    # ── Full table ───────────────────────────────────────────────────────
    st.divider()
    st.markdown("#### Full price reference table")
    display_df = price_df[["Mineral", "Price (USD)", "Unit", "Type", "Source"]].copy()
    display_df["Price (USD)"] = display_df["Price (USD)"].apply(lambda x: f"${x:,.0f}")
    st.dataframe(display_df, use_container_width=True, hide_index=True)

    # ── How prices link to supply chain risk ────────────────────────────
    st.divider()
    st.markdown("#### 📈 Why mineral prices matter for supply chain resilience")
    st.write(
        "Price signals are a leading indicator of supply stress. A sharp price "
        "rise in a single-source mineral (like Gallium or Germanium, where "
        "China controls >90% of supply) may signal an export restriction or "
        "production cut before it is confirmed in official data — exactly the "
        "kind of early-warning signal this platform's agents monitor. "
        "The Cambridge GSCO and the IEA Critical Minerals Outlook both use "
        "price volatility alongside concentration ratios as key resilience "
        "indicators."
    )
    st.info(
        "🔑 To enable **live** prices: run `pip install yfinance` in your "
        "environment. Copper futures will update live automatically. "
        "For Lithium, Cobalt, Gallium and Germanium, no free real-time "
        "API exists — the USGS/LME annual reference prices shown are the "
        "same figures used in IEA and academic supply chain research."
    )


# ══════════════════════════════════════════════════════════════════════════
#  PAGE: HARDWARE RISK
# ══════════════════════════════════════════════════════════════════════════

elif page == "⚙️ Hardware Risk":
    st.title("⚙️ Hardware Risk Analysis")

    df_p = product_risk_df()

    # ── Product selector ───────────────────────────────────────────────────
    product = st.selectbox("Select product", list(HW_DEPS.keys()))
    mins    = HW_DEPS[product]
    score   = sum(RISK_W.get(m, 1) for m in mins)
    tier    = "CRITICAL" if score >= 30 else "HIGH" if score >= 20 else "MEDIUM" if score >= 10 else "LOW"

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Risk Score", score)
    c2.metric("Risk Tier",  tier)
    c3.metric("Minerals",   len(mins))
    c4.metric("Max Mineral Weight", max(RISK_W.get(m, 1) for m in mins))

    st.divider()

    # ── Mineral breakdown ──────────────────────────────────────────────────
    st.markdown("#### Mineral Dependency Breakdown")
    m_df = pd.DataFrame([{
        "Mineral":    m,
        "Risk Weight": RISK_W.get(m, 1),
        "Geo Risk":   tool_assess_geo_risk(m)["risk_level"],
        "Supply Risk": SUPPLY_CHAIN.get(m, {}).get("risk", "LOW"),
        "Countries":  ", ".join(SUPPLY_CHAIN.get(m, {}).get("T3", [])),
    } for m in mins]).sort_values("Risk Weight", ascending=False)

    st.dataframe(m_df, use_container_width=True, hide_index=True)

    # ── Radar chart ────────────────────────────────────────────────────────
    fig_r = go.Figure(go.Scatterpolar(
        r=[RISK_W.get(m, 1) for m in mins],
        theta=mins,
        fill="toself",
        fillcolor="rgba(99,102,241,0.2)",
        line_color="#6366f1",
    ))
    fig_r.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 10])),
        title=f"Mineral Risk Radar — {product}",
        height=380,
    )
    st.plotly_chart(fig_r, use_container_width=True)

    st.divider()

    # ── Scenarios ──────────────────────────────────────────────────────────
    st.markdown("#### Triggered Supply-Shock Scenarios")
    triggered = {
        name: s for name, s in SCENARIOS.items()
        if set(s["minerals"]) & set(mins)
    }
    if triggered:
        for name, s in triggered.items():
            with st.expander(f"📌 {name} — Impact: {s['impact']}"):
                st.write(f"**Sector:** {s['sector']}")
                st.write(f"**Affected minerals:** {', '.join(s['minerals'])}")
                st.write("**Consequences:**")
                for c in s["consequences"]:
                    st.write(f"• {c}")
    else:
        st.info("No scenarios triggered for this product.")


# ══════════════════════════════════════════════════════════════════════════
#  PAGE: AGENCY EVALUATION
# ══════════════════════════════════════════════════════════════════════════

elif page == "📊 Agency Evaluation":
    st.title("📊 Agency Evaluation Framework")
    st.caption("Novel 3-metric framework  ·  v8.0 contribution to the literature.")

    with st.expander("▶  How the metrics work", expanded=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("**Tool-Call Entropy**")
            st.write("Shannon entropy of tool usage distribution. High = diverse, exploratory behaviour. Low = repetitive pipeline.")
        with c2:
            st.markdown("**Goal-Step Alignment**")
            st.write("Fraction of tool calls genuinely relevant to the stated goal keywords. High = on-target. Low = off-task.")
        with c3:
            st.markdown("**Pipeline Deviation**")
            st.write("LCS distance from a naive scripted baseline. High = genuinely agentic decisions. Low = scripted sequence.")

    st.divider()

    # Pull from memory
    memory = PersistentMemory()
    runs   = memory.get_all_runs()

    if not runs:
        st.info("No runs in memory yet. Run an analysis on the '🤖 Run Analysis' page first.")
    else:
        st.markdown(f"**{len(runs)} analysis runs in memory**")
        runs_df = pd.DataFrame([{
            "Run ID":     r["id"],
            "Date":       time.strftime("%Y-%m-%d %H:%M", time.localtime(r["ts"])),
            "Goal":       r["goal"][:60] + "…" if len(r["goal"]) > 60 else r["goal"],
            "Steps":      r["steps"],
            "Tool Calls": r["tool_calls"],
            "Tools Used": ", ".join(r["tools_used"][:4]),
        } for r in runs])
        st.dataframe(runs_df, use_container_width=True, hide_index=True)

    st.divider()
    st.markdown("#### Metric Definitions (for dissertation)")

    st.code("""
# Tool-Call Entropy (Shannon H, normalised)
H = -sum(p_i * log2(p_i))  # where p_i = fraction of calls using tool i
H_norm = H / log2(N_unique_tools)  # normalised to [0, 1]

# Goal-Step Alignment
aligned = sum(1 for tc in tool_calls if any goal keyword matches tool keyword)
alignment = aligned / len(tool_calls)

# Pipeline Deviation (LCS distance)
lcs = longest_common_subsequence(agent_calls, baseline_pipeline)
deviation = 1 - (lcs / max(len(agent_calls), len(baseline_pipeline)))

# Composite Agency Score
composite = 0.4 * entropy + 0.4 * alignment + 0.2 * deviation
    """, language="python")


# ══════════════════════════════════════════════════════════════════════════
#  PAGE: MEMORY & HISTORY
# ══════════════════════════════════════════════════════════════════════════

elif page == "💾 Memory & History":
    st.title("💾 Persistent Memory & History")
    st.caption("SQLite database persists across sessions — agents build knowledge over time.")

    memory = PersistentMemory()

    # ── Run history ────────────────────────────────────────────────────────
    st.markdown("### Analysis Run History")
    runs = memory.get_all_runs()
    if not runs:
        st.info("No runs yet. Start on the '🤖 Run Analysis' page.")
    else:
        runs_df = pd.DataFrame([{
            "ID":         r["id"],
            "Date/Time":  time.strftime("%Y-%m-%d %H:%M", time.localtime(r["ts"])),
            "Goal":       r["goal"][:70] + "…" if len(r["goal"]) > 70 else r["goal"],
            "Steps":      r["steps"],
            "Tool Calls": r["tool_calls"],
        } for r in runs])
        st.dataframe(runs_df, use_container_width=True, hide_index=True)

    st.divider()

    # ── Country stability ──────────────────────────────────────────────────
    st.markdown("### Live Country Stability Scores")
    stability_df = memory.get_latest_country_stability()
    if not stability_df.empty:
        fig_s = px.bar(
            stability_df.sort_values("wb_score"),
            x="country", y="wb_score",
            color="wb_score",
            color_continuous_scale=["#ef4444", "#f59e0b", "#10b981"],
            title="World Bank Political Stability Scores (higher = more stable)",
        )
        fig_s.update_layout(xaxis_tickangle=-20, height=360,
                            plot_bgcolor="rgba(255,255,255,0.04)", paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_s, use_container_width=True)
    else:
        st.info("No stability data yet — will populate after first analysis run.")

    st.divider()

    # ── Mineral history ────────────────────────────────────────────────────
    st.markdown("### Mineral Risk History")
    selected_mineral = st.selectbox("Select mineral", list(SUPPLY_CHAIN.keys()), key="mem_mineral")
    hist = memory.get_mineral_history(selected_mineral)
    if hist:
        hist_df = pd.DataFrame([{
            "Time":     time.strftime("%Y-%m-%d %H:%M", time.localtime(h["ts"])),
            "Risk Weight": h["risk_w"],
            "Geo Risk": h["geo_risk"],
        } for h in hist])
        st.dataframe(hist_df, use_container_width=True, hide_index=True)
    else:
        st.info(f"No history for {selected_mineral} yet.")


# ══════════════════════════════════════════════════════════════════════════
#  PAGE: DATA SOURCES (provenance / citations)
# ══════════════════════════════════════════════════════════════════════════

elif page == "📚 Data Sources":
    st.title("📚 Data Sources & Provenance")
    st.caption(
        "Every structured figure used across this platform should trace back "
        "to one of the authentic sources below, following the two-tier "
        "structured-plus-unstructured methodology in Nie et al. (2026), "
        "Journal of the Operational Research Society."
    )

    for src in list_sources():
        with st.container(border=True):
            st.markdown(f"**{src['name']}**")
            st.caption(f"Type: {src['type']}  ·  Update cycle: {src['update_cycle']}")
            st.write(src["covers"])
            st.markdown(f"[{src['url']}]({src['url']})")
    st.divider()
    st.markdown("#### How provenance is enforced in this codebase")
    st.write(
        "`services/data_sources.py` exposes `with_provenance(value, source_key, "
        "confidence, note)`, which every echelon-level tool call wraps its "
        "output in. Values are tagged HIGH / MEDIUM / LOW / "
        "UNVERIFIED-PLACEHOLDER rather than presented as fact — mirroring the "
        "paper's High/Medium/Low/None evidence-rating scheme for LLM-extracted "
        "insights, so a reviewer can immediately see what still needs manual "
        "verification against the cited source before being trusted."
    )

