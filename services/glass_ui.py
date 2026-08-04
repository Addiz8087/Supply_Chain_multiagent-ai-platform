"""
services/glass_ui.py
=====================
Liquid Glass UI — Apple iOS 26-inspired glassmorphism theme.

Design language:
  - Soft light background with animated colour orbs
  - Frosted white glass panels (backdrop-filter blur + white semi-transparent)
  - Dark, fully readable text on every surface
  - Colourful iridescent accents — cyan, indigo, violet — on borders and highlights
  - Every interactive element feels like a pane of cut crystal

Call inject_glass_ui() once at the top of streamlit_app.py main().
"""

import streamlit as st


def inject_glass_ui():
    st.markdown(_CSS, unsafe_allow_html=True)


_CSS = """
<style>

/* ═══════════════════════════════════════════════════════════════
   GOOGLE FONT — Inter (clean, modern, readable)
   ═══════════════════════════════════════════════════════════════ */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* ═══════════════════════════════════════════════════════════════
   ROOT VARIABLES
   ═══════════════════════════════════════════════════════════════ */
:root {
    --glass-white:   rgba(255, 255, 255, 0.62);
    --glass-border:  rgba(255, 255, 255, 0.85);
    --glass-shadow:  rgba(80, 100, 180, 0.13);
    --text-primary:  #0f172a;
    --text-secondary:#334155;
    --text-muted:    #64748b;
    --accent-indigo: #6366f1;
    --accent-cyan:   #06b6d4;
    --accent-violet: #a855f7;
    --accent-rose:   #f43f5e;
    --bg-from:       #e8eaf6;
    --bg-to:         #f0f9ff;
}

/* ═══════════════════════════════════════════════════════════════
   BACKGROUND — light gradient with floating colour orbs
   ═══════════════════════════════════════════════════════════════ */
html, body {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    background: var(--bg-from) !important;
    min-height: 100vh;
}

.stApp {
    background:
        radial-gradient(ellipse 75% 55% at 10% 15%,  rgba(99,102,241,0.18)  0%, transparent 65%),
        radial-gradient(ellipse 65% 50% at 88% 75%,  rgba(6,182,212,0.16)   0%, transparent 60%),
        radial-gradient(ellipse 55% 55% at 50% 45%,  rgba(168,85,247,0.10)  0%, transparent 55%),
        radial-gradient(ellipse 70% 40% at 25% 80%,  rgba(244,63,94,0.08)   0%, transparent 55%),
        linear-gradient(145deg, #dde8ff 0%, #e8f4ff 40%, #f0e8ff 75%, #e8f8ff 100%) !important;
    background-attachment: fixed !important;
    min-height: 100vh;
}

/* ═══════════════════════════════════════════════════════════════
   TYPOGRAPHY — dark text everywhere (the critical fix)
   ═══════════════════════════════════════════════════════════════ */
.stApp, .stApp * {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
}

/* Reset ALL text to dark — overrides the old white-text rules */
.stMarkdown, .stMarkdown p, .stMarkdown li, .stMarkdown span,
.stText, p, li, span, div, label, td, th {
    color: var(--text-primary) !important;
}

h1 {
    color: #0f172a !important;
    font-weight: 700 !important;
    font-size: 2rem !important;
    letter-spacing: -0.6px !important;
}
h2 {
    color: #1e293b !important;
    font-weight: 600 !important;
    letter-spacing: -0.4px !important;
}
h3 {
    color: #1e293b !important;
    font-weight: 600 !important;
}

.stCaption, small, caption {
    color: var(--text-muted) !important;
    font-size: 0.8rem !important;
}

hr {
    border: none !important;
    border-top: 1px solid rgba(100,116,139,0.18) !important;
    margin: 1rem 0 !important;
}

/* ═══════════════════════════════════════════════════════════════
   MAIN CONTENT AREA
   ═══════════════════════════════════════════════════════════════ */
.main .block-container {
    background: transparent !important;
    padding-top: 2rem !important;
    padding-bottom: 3rem !important;
}

/* ═══════════════════════════════════════════════════════════════
   SIDEBAR — frosted glass panel (light version)
   ═══════════════════════════════════════════════════════════════ */
[data-testid="stSidebar"] {
    background: rgba(255, 255, 255, 0.52) !important;
    backdrop-filter: blur(32px) saturate(180%) !important;
    -webkit-backdrop-filter: blur(32px) saturate(180%) !important;
    border-right: 1.5px solid rgba(255,255,255,0.9) !important;
    box-shadow: 4px 0 40px rgba(99,102,241,0.10), 2px 0 12px rgba(0,0,0,0.06) !important;
}

[data-testid="stSidebar"] * {
    color: var(--text-primary) !important;
}

[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
    color: #0f172a !important;
}

/* ═══════════════════════════════════════════════════════════════
   GLASS CARD PANELS — the core liquid glass effect
   ═══════════════════════════════════════════════════════════════ */
div[data-testid="stVerticalBlockBorderWrapper"] {
    background: var(--glass-white) !important;
    backdrop-filter: blur(24px) saturate(160%) !important;
    -webkit-backdrop-filter: blur(24px) saturate(160%) !important;
    border: 1.5px solid var(--glass-border) !important;
    border-radius: 20px !important;
    box-shadow:
        0 8px 32px var(--glass-shadow),
        0 2px 8px rgba(0,0,0,0.06),
        inset 0 1.5px 0 rgba(255,255,255,0.95),
        inset 0 -1px 0 rgba(255,255,255,0.4) !important;
    padding: 1.2rem !important;
    transition: transform 0.25s ease, box-shadow 0.25s ease !important;
    position: relative !important;
    overflow: hidden !important;
}

div[data-testid="stVerticalBlockBorderWrapper"]::before {
    content: '';
    position: absolute;
    inset: 0;
    border-radius: 20px;
    background: linear-gradient(135deg,
        rgba(255,255,255,0.6) 0%,
        rgba(255,255,255,0.1) 50%,
        rgba(255,255,255,0.3) 100%);
    pointer-events: none;
    z-index: 0;
}

div[data-testid="stVerticalBlockBorderWrapper"]:hover {
    transform: translateY(-2px) !important;
    box-shadow:
        0 16px 48px rgba(99,102,241,0.18),
        0 4px 16px rgba(0,0,0,0.08),
        inset 0 1.5px 0 rgba(255,255,255,0.98),
        inset 0 -1px 0 rgba(255,255,255,0.6) !important;
}

/* ═══════════════════════════════════════════════════════════════
   METRIC CARDS — iridescent glass border
   ═══════════════════════════════════════════════════════════════ */
[data-testid="metric-container"] {
    background: rgba(255,255,255,0.68) !important;
    backdrop-filter: blur(20px) saturate(160%) !important;
    -webkit-backdrop-filter: blur(20px) saturate(160%) !important;
    border-radius: 18px !important;
    border: 1.5px solid rgba(255,255,255,0.92) !important;
    box-shadow:
        0 4px 24px rgba(99,102,241,0.12),
        0 1px 4px rgba(0,0,0,0.05),
        inset 0 1.5px 0 rgba(255,255,255,1),
        inset 0 -1px 0 rgba(200,210,255,0.3) !important;
    padding: 1.1rem 1.2rem !important;
    transition: transform 0.22s ease, box-shadow 0.22s ease !important;
    position: relative !important;
    overflow: hidden !important;
}

/* Iridescent shimmer top-left */
[data-testid="metric-container"]::before {
    content: '';
    position: absolute;
    top: 0; left: 0;
    right: 0; height: 2px;
    background: linear-gradient(90deg,
        rgba(99,102,241,0.0) 0%,
        rgba(99,102,241,0.7) 25%,
        rgba(6,182,212,0.7) 50%,
        rgba(168,85,247,0.7) 75%,
        rgba(99,102,241,0.0) 100%);
    border-radius: 18px 18px 0 0;
}

[data-testid="metric-container"]:hover {
    transform: translateY(-3px) scale(1.01) !important;
    box-shadow:
        0 12px 40px rgba(99,102,241,0.2),
        0 2px 8px rgba(0,0,0,0.08),
        inset 0 1.5px 0 rgba(255,255,255,1) !important;
}

[data-testid="stMetricValue"] {
    color: #0f172a !important;
    font-size: 1.9rem !important;
    font-weight: 700 !important;
    letter-spacing: -0.5px !important;
}

[data-testid="stMetricLabel"] {
    color: #64748b !important;
    font-size: 0.75rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.07em !important;
    font-weight: 500 !important;
}

[data-testid="stMetricDelta"] {
    font-size: 0.82rem !important;
    font-weight: 500 !important;
}

/* ═══════════════════════════════════════════════════════════════
   BUTTONS — glass pill with iridescent border
   ═══════════════════════════════════════════════════════════════ */
.stButton > button {
    background: rgba(255,255,255,0.72) !important;
    backdrop-filter: blur(16px) !important;
    -webkit-backdrop-filter: blur(16px) !important;
    border: 1.5px solid rgba(99,102,241,0.35) !important;
    border-radius: 14px !important;
    color: #1e293b !important;
    font-weight: 600 !important;
    font-size: 0.88rem !important;
    letter-spacing: 0.01em !important;
    padding: 0.55rem 1.3rem !important;
    transition: all 0.22s cubic-bezier(0.34, 1.56, 0.64, 1) !important;
    box-shadow:
        0 4px 15px rgba(99,102,241,0.15),
        inset 0 1px 0 rgba(255,255,255,0.9) !important;
    position: relative !important;
    overflow: hidden !important;
}

.stButton > button:hover {
    background: rgba(99,102,241,0.12) !important;
    border-color: rgba(99,102,241,0.6) !important;
    transform: translateY(-2px) scale(1.02) !important;
    box-shadow:
        0 8px 28px rgba(99,102,241,0.28),
        inset 0 1px 0 rgba(255,255,255,0.95) !important;
    color: #3730a3 !important;
}

.stButton > button:active {
    transform: translateY(0px) scale(0.99) !important;
}

/* Primary button — gradient glass */
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg,
        rgba(99,102,241,0.85) 0%,
        rgba(168,85,247,0.80) 100%) !important;
    border-color: rgba(99,102,241,0.5) !important;
    color: #fff !important;
    box-shadow:
        0 6px 20px rgba(99,102,241,0.35),
        inset 0 1px 0 rgba(255,255,255,0.4) !important;
}

.stButton > button[kind="primary"]:hover {
    background: linear-gradient(135deg,
        rgba(99,102,241,0.95) 0%,
        rgba(168,85,247,0.90) 100%) !important;
    color: #fff !important;
    box-shadow:
        0 10px 32px rgba(99,102,241,0.45),
        inset 0 1px 0 rgba(255,255,255,0.5) !important;
}

/* ═══════════════════════════════════════════════════════════════
   INPUTS — liquid glass fields
   ═══════════════════════════════════════════════════════════════ */
.stSelectbox > div > div,
.stMultiSelect > div > div {
    background: rgba(255,255,255,0.72) !important;
    backdrop-filter: blur(16px) !important;
    -webkit-backdrop-filter: blur(16px) !important;
    border: 1.5px solid rgba(255,255,255,0.88) !important;
    border-radius: 12px !important;
    color: #0f172a !important;
    box-shadow: 0 2px 10px rgba(99,102,241,0.08), inset 0 1px 0 rgba(255,255,255,0.9) !important;
}

.stSelectbox > div > div:hover,
.stMultiSelect > div > div:hover {
    border-color: rgba(99,102,241,0.45) !important;
    box-shadow: 0 4px 16px rgba(99,102,241,0.14), inset 0 1px 0 rgba(255,255,255,0.95) !important;
}

/* Force dropdown text dark */
.stSelectbox > div > div > div,
.stSelectbox span {
    color: #0f172a !important;
}

.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
    background: rgba(255,255,255,0.72) !important;
    backdrop-filter: blur(16px) !important;
    -webkit-backdrop-filter: blur(16px) !important;
    border: 1.5px solid rgba(255,255,255,0.88) !important;
    border-radius: 12px !important;
    color: #0f172a !important;
    font-size: 0.92rem !important;
    caret-color: #6366f1 !important;
    box-shadow: 0 2px 10px rgba(99,102,241,0.08), inset 0 1px 0 rgba(255,255,255,0.9) !important;
}

.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: rgba(99,102,241,0.55) !important;
    box-shadow:
        0 0 0 3px rgba(99,102,241,0.12),
        0 4px 16px rgba(99,102,241,0.12),
        inset 0 1px 0 rgba(255,255,255,0.95) !important;
    outline: none !important;
}

::placeholder {
    color: rgba(100,116,139,0.6) !important;
}

/* ═══════════════════════════════════════════════════════════════
   RADIO BUTTONS (sidebar nav)
   ═══════════════════════════════════════════════════════════════ */
.stRadio > div {
    gap: 3px !important;
}

.stRadio > div > label {
    border-radius: 10px !important;
    padding: 0.3rem 0.7rem !important;
    transition: all 0.18s ease !important;
    color: #334155 !important;
    font-weight: 450 !important;
}

.stRadio > div > label:hover {
    background: rgba(99,102,241,0.09) !important;
    color: #3730a3 !important;
}

.stRadio > div > label[data-checked="true"],
.stRadio > div > label[aria-checked="true"] {
    background: rgba(99,102,241,0.14) !important;
    color: #3730a3 !important;
    font-weight: 600 !important;
}

/* ═══════════════════════════════════════════════════════════════
   EXPANDERS — glass accordion
   ═══════════════════════════════════════════════════════════════ */

/* Hide raw Material Icon name text (arrow_down, expand_more etc.)
   that bleeds through before the icon font loads */
[data-testid="stExpander"] summary p,
[data-testid="stExpanderToggleIcon"],
[data-testid="stExpander"] details > summary > div:first-child span,
.streamlit-expanderHeader svg + span,
.streamlit-expanderHeader > div > span[style],
[data-testid="stExpander"] summary span[style*="font-family"],
[data-testid="stExpander"] summary span[style*="material"] {
    display: none !important;
    visibility: hidden !important;
    width: 0 !important;
    overflow: hidden !important;
    font-size: 0 !important;
}

.streamlit-expanderHeader,
[data-testid="stExpander"] > details > summary {
    background: rgba(255,255,255,0.60) !important;
    backdrop-filter: blur(16px) !important;
    -webkit-backdrop-filter: blur(16px) !important;
    border-radius: 12px !important;
    border: 1.5px solid rgba(255,255,255,0.88) !important;
    color: #1e293b !important;
    font-weight: 500 !important;
    box-shadow: 0 2px 8px rgba(99,102,241,0.08) !important;
    transition: all 0.2s ease !important;
}

.streamlit-expanderHeader:hover,
[data-testid="stExpander"] > details > summary:hover {
    background: rgba(99,102,241,0.08) !important;
    border-color: rgba(99,102,241,0.3) !important;
}

.streamlit-expanderContent,
[data-testid="stExpander"] > details > div {
    background: rgba(255,255,255,0.40) !important;
    backdrop-filter: blur(12px) !important;
    -webkit-backdrop-filter: blur(12px) !important;
    border: 1.5px solid rgba(255,255,255,0.80) !important;
    border-top: none !important;
    border-radius: 0 0 12px 12px !important;
}

/* ═══════════════════════════════════════════════════════════════
   ALERTS — tinted glass versions
   ═══════════════════════════════════════════════════════════════ */
div[data-testid="stInfoMessage"],
div[data-baseweb="notification"] {
    background: rgba(6,182,212,0.10) !important;
    border: 1.5px solid rgba(6,182,212,0.35) !important;
    backdrop-filter: blur(16px) !important;
    -webkit-backdrop-filter: blur(16px) !important;
    border-radius: 14px !important;
    color: #0c4a6e !important;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.8) !important;
}

div[data-testid="stWarningMessage"] {
    background: rgba(245,158,11,0.10) !important;
    border: 1.5px solid rgba(245,158,11,0.35) !important;
    backdrop-filter: blur(16px) !important;
    -webkit-backdrop-filter: blur(16px) !important;
    border-radius: 14px !important;
    color: #78350f !important;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.8) !important;
}

div[data-testid="stErrorMessage"] {
    background: rgba(239,68,68,0.10) !important;
    border: 1.5px solid rgba(239,68,68,0.35) !important;
    backdrop-filter: blur(16px) !important;
    -webkit-backdrop-filter: blur(16px) !important;
    border-radius: 14px !important;
    color: #7f1d1d !important;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.8) !important;
}

div[data-testid="stSuccessMessage"] {
    background: rgba(34,197,94,0.10) !important;
    border: 1.5px solid rgba(34,197,94,0.35) !important;
    backdrop-filter: blur(16px) !important;
    -webkit-backdrop-filter: blur(16px) !important;
    border-radius: 14px !important;
    color: #14532d !important;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.8) !important;
}

/* Force alert text to be dark */
div[data-testid="stInfoMessage"] *,
div[data-testid="stWarningMessage"] *,
div[data-testid="stErrorMessage"] *,
div[data-testid="stSuccessMessage"] * {
    color: inherit !important;
}

/* ═══════════════════════════════════════════════════════════════
   DATAFRAME / TABLES
   ═══════════════════════════════════════════════════════════════ */
[data-testid="stDataFrame"] {
    background: rgba(255,255,255,0.60) !important;
    backdrop-filter: blur(16px) !important;
    -webkit-backdrop-filter: blur(16px) !important;
    border: 1.5px solid rgba(255,255,255,0.88) !important;
    border-radius: 16px !important;
    overflow: hidden !important;
    box-shadow: 0 4px 20px rgba(99,102,241,0.10) !important;
}

/* ═══════════════════════════════════════════════════════════════
   TABS — pill tab bar
   ═══════════════════════════════════════════════════════════════ */
.stTabs [data-baseweb="tab-list"] {
    background: rgba(255,255,255,0.55) !important;
    backdrop-filter: blur(20px) !important;
    -webkit-backdrop-filter: blur(20px) !important;
    border-radius: 14px !important;
    padding: 5px !important;
    gap: 4px !important;
    border: 1.5px solid rgba(255,255,255,0.88) !important;
    box-shadow: 0 2px 12px rgba(99,102,241,0.10) !important;
}

.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    border-radius: 10px !important;
    color: #475569 !important;
    font-weight: 500 !important;
    transition: all 0.2s ease !important;
    padding: 0.4rem 1.1rem !important;
}

.stTabs [data-baseweb="tab"]:hover {
    background: rgba(99,102,241,0.10) !important;
    color: #3730a3 !important;
}

.stTabs [aria-selected="true"] {
    background: rgba(255,255,255,0.88) !important;
    color: #3730a3 !important;
    font-weight: 600 !important;
    box-shadow:
        0 2px 12px rgba(99,102,241,0.20),
        inset 0 1px 0 rgba(255,255,255,1) !important;
}

.stTabs [data-baseweb="tab-border"] {
    display: none !important;
}

/* ═══════════════════════════════════════════════════════════════
   PLOTLY CHARTS
   ═══════════════════════════════════════════════════════════════ */
.stPlotlyChart {
    background: rgba(255,255,255,0.55) !important;
    backdrop-filter: blur(16px) !important;
    -webkit-backdrop-filter: blur(16px) !important;
    border: 1.5px solid rgba(255,255,255,0.88) !important;
    border-radius: 18px !important;
    padding: 0.6rem !important;
    overflow: hidden !important;
    box-shadow: 0 4px 20px rgba(99,102,241,0.10) !important;
}

.js-plotly-plot .plotly,
.js-plotly-plot .plotly .main-svg {
    background: transparent !important;
}

/* ═══════════════════════════════════════════════════════════════
   SIDEBAR COLLAPSE BUTTON — hide keyboard_double tooltip
   ═══════════════════════════════════════════════════════════════ */

[data-testid="stSidebarCollapseButton"] span,
[data-testid="collapsedControl"] span,
button[data-testid="stSidebarCollapseButton"] span {
    display: none !important;
    visibility: hidden !important;
}

[data-testid="stSidebarCollapseButton"]::after,
[data-testid="collapsedControl"]::after {
    display: none !important;
}

[data-testid="stSidebarCollapseButton"] button,
[data-testid="collapsedControl"] button {
    background: rgba(255,255,255,0.60) !important;
    backdrop-filter: blur(12px) !important;
    border: 1.5px solid rgba(255,255,255,0.88) !important;
    border-radius: 10px !important;
    box-shadow: 0 2px 10px rgba(99,102,241,0.12) !important;
    color: #334155 !important;
}

[data-testid="stSidebarCollapseButton"] button:hover,
[data-testid="collapsedControl"] button:hover {
    background: rgba(99,102,241,0.12) !important;
    border-color: rgba(99,102,241,0.35) !important;
}

/* ═══════════════════════════════════════════════════════════════
   TOP HEADER BAR
   ═══════════════════════════════════════════════════════════════ */
header[data-testid="stHeader"] {
    background: rgba(255,255,255,0.65) !important;
    backdrop-filter: blur(24px) saturate(160%) !important;
    -webkit-backdrop-filter: blur(24px) saturate(160%) !important;
    border-bottom: 1.5px solid rgba(255,255,255,0.9) !important;
    box-shadow: 0 2px 20px rgba(99,102,241,0.10) !important;
}

/* ═══════════════════════════════════════════════════════════════
   PROGRESS BAR
   ═══════════════════════════════════════════════════════════════ */
.stProgress > div > div > div > div {
    background: linear-gradient(90deg, #6366f1, #06b6d4, #a855f7) !important;
    border-radius: 4px !important;
}

.stProgress > div > div {
    background: rgba(255,255,255,0.55) !important;
    border-radius: 4px !important;
    border: 1px solid rgba(255,255,255,0.8) !important;
}

/* ═══════════════════════════════════════════════════════════════
   SPINNER
   ═══════════════════════════════════════════════════════════════ */
div[data-testid="stSpinner"] > div {
    border-top-color: #6366f1 !important;
    border-right-color: #06b6d4 !important;
}

/* ═══════════════════════════════════════════════════════════════
   CODE BLOCKS
   ═══════════════════════════════════════════════════════════════ */
.stCode, code, pre {
    background: rgba(15,23,42,0.07) !important;
    border: 1.5px solid rgba(255,255,255,0.8) !important;
    border-radius: 10px !important;
    color: #1e3a5f !important;
    backdrop-filter: blur(8px) !important;
}

/* ═══════════════════════════════════════════════════════════════
   SCROLLBAR — subtle glass style
   ═══════════════════════════════════════════════════════════════ */
::-webkit-scrollbar { width: 7px; height: 7px; }
::-webkit-scrollbar-track {
    background: rgba(255,255,255,0.3);
    border-radius: 4px;
}
::-webkit-scrollbar-thumb {
    background: rgba(99,102,241,0.28);
    border-radius: 4px;
    border: 1px solid rgba(255,255,255,0.6);
}
::-webkit-scrollbar-thumb:hover {
    background: rgba(99,102,241,0.50);
}

/* ═══════════════════════════════════════════════════════════════
   CUSTOM UTILITY CLASSES (used in streamlit_app.py HTML)
   ═══════════════════════════════════════════════════════════════ */

/* Section header line */
.section-header {
    font-size: 1.0rem !important;
    font-weight: 700 !important;
    color: #1e293b !important;
    margin: 1.4rem 0 0.65rem 0 !important;
    border-bottom: 2.5px solid;
    border-image: linear-gradient(90deg, #6366f1, #06b6d4) 1 !important;
    padding-bottom: 0.35rem !important;
    letter-spacing: -0.2px !important;
}

/* Report blockquote */
.report-box {
    background: rgba(255,255,255,0.65) !important;
    backdrop-filter: blur(16px) !important;
    border-left: 4px solid #6366f1 !important;
    padding: 1.25rem 1.5rem !important;
    border-radius: 0 14px 14px 0 !important;
    font-size: 0.93rem !important;
    line-height: 1.75 !important;
    white-space: pre-wrap !important;
    color: #1e293b !important;
    box-shadow: 0 4px 20px rgba(99,102,241,0.10), inset 0 1px 0 rgba(255,255,255,0.9) !important;
}

/* Agent log box */
.agent-log {
    background: rgba(15,23,42,0.82) !important;
    backdrop-filter: blur(16px) !important;
    color: #94a3b8 !important;
    padding: 1rem 1.25rem !important;
    border-radius: 12px !important;
    border: 1px solid rgba(99,102,241,0.20) !important;
    font-family: 'JetBrains Mono', 'Fira Code', monospace !important;
    font-size: 0.80rem !important;
    max-height: 380px !important;
    overflow-y: auto !important;
    white-space: pre-wrap !important;
}

/* Risk tier badges */
.badge-critical {
    background: rgba(239,68,68,0.14);
    color: #7f1d1d;
    border: 1px solid rgba(239,68,68,0.30);
    padding: 3px 11px;
    border-radius: 20px;
    font-size: 11.5px;
    font-weight: 700;
    letter-spacing: 0.02em;
    backdrop-filter: blur(8px);
}
.badge-high {
    background: rgba(245,158,11,0.14);
    color: #78350f;
    border: 1px solid rgba(245,158,11,0.30);
    padding: 3px 11px;
    border-radius: 20px;
    font-size: 11.5px;
    font-weight: 700;
    backdrop-filter: blur(8px);
}
.badge-medium {
    background: rgba(34,197,94,0.14);
    color: #14532d;
    border: 1px solid rgba(34,197,94,0.30);
    padding: 3px 11px;
    border-radius: 20px;
    font-size: 11.5px;
    font-weight: 700;
    backdrop-filter: blur(8px);
}
.badge-low {
    background: rgba(59,130,246,0.14);
    color: #1e3a8a;
    border: 1px solid rgba(59,130,246,0.30);
    padding: 3px 11px;
    border-radius: 20px;
    font-size: 11.5px;
    font-weight: 700;
    backdrop-filter: blur(8px);
}

/* Glass info pill (general purpose) */
.glass-pill {
    display: inline-block;
    background: rgba(255,255,255,0.65);
    backdrop-filter: blur(12px);
    border: 1.5px solid rgba(255,255,255,0.88);
    border-radius: 999px;
    padding: 4px 14px;
    font-size: 12px;
    font-weight: 600;
    color: #334155;
    box-shadow: 0 2px 8px rgba(99,102,241,0.10);
}

/* ═══════════════════════════════════════════════════════════════
   GLOBAL FIX — nuke ALL raw Material Icons text bleed
   Streamlit injects spans with style="font-family: 'Material Icons'"
   Before the font loads these render as raw text (arrow_down etc.)
   Nuclear approach: zero size + transparent + no pointer events
   ═══════════════════════════════════════════════════════════════ */

/* Target every possible Material icon span variant */
span[style*="Material Icons"],
span[style*="material-icons"],
span[style*="Material Symbols"],
span[style*="MaterialIcons"],
[data-testid="stExpanderToggleIcon"],
.material-icons,
.material-symbols-rounded,
.material-symbols-outlined,
[data-testid="stExpander"] summary span[style],
[data-testid="stSidebarCollapseButton"] button span[style] {
    font-size: 0 !important;
    line-height: 0 !important;
    color: transparent !important;
    width: 0 !important;
    height: 0 !important;
    overflow: hidden !important;
    display: inline-block !important;
    pointer-events: none !important;
    opacity: 0 !important;
}

/* ── Custom chevron on expander ──────────────────────────────── */
/* Add a clean ❯ chevron via ::after so the expander still looks good */
[data-testid="stExpander"] details > summary {
    position: relative !important;
    padding-right: 2.2rem !important;
    list-style: none !important;
}

[data-testid="stExpander"] details > summary::-webkit-details-marker {
    display: none !important;
}

[data-testid="stExpander"] details > summary::after {
    content: '›' !important;
    position: absolute !important;
    right: 1rem !important;
    top: 50% !important;
    transform: translateY(-50%) rotate(0deg) !important;
    font-size: 1.4rem !important;
    font-weight: 300 !important;
    color: #6366f1 !important;
    transition: transform 0.22s ease !important;
    line-height: 1 !important;
    opacity: 0.8 !important;
}

[data-testid="stExpander"] details[open] > summary::after {
    transform: translateY(-50%) rotate(90deg) !important;
}

/* ── Custom chevron on sidebar collapse ──────────────────────── */
[data-testid="stSidebarCollapseButton"] button::after {
    content: '‹' !important;
    font-size: 1.3rem !important;
    color: #6366f1 !important;
    font-weight: 300 !important;
    line-height: 1 !important;
}

/* Re-show SVG if Streamlit uses it as fallback */
[data-testid="stExpander"] summary svg,
[data-testid="stSidebarCollapseButton"] svg {
    display: none !important;
}

/* ═══════════════════════════════════════════════════════════════
   FILE UPLOADER — glass-styled dropzone, extra breathing room so
   the icon and instruction text can never visually overlap
   ═══════════════════════════════════════════════════════════════ */
[data-testid="stFileUploaderDropzone"] {
    background: rgba(255,255,255,0.55) !important;
    border: 1.5px dashed rgba(99,102,241,0.35) !important;
    border-radius: 12px !important;
    padding: 14px 16px !important;
    gap: 8px !important;
}

/* Mute ALL native icon/text inside the instructions area — regardless of
   whether it's an svg, span, i, or leftover icon-font ligature text —
   by collapsing its font-size to zero, then draw one clean label
   ourselves via ::before. This can't overlap because nothing else in
   here is visible. */
[data-testid="stFileUploaderDropzoneInstructions"] {
    display: flex !important;
    align-items: center !important;
    gap: 8px !important;
    font-size: 0 !important;
    line-height: 0 !important;
    position: relative !important;
    min-height: 28px !important;
}

[data-testid="stFileUploaderDropzoneInstructions"] * {
    font-size: 0 !important;
}

[data-testid="stFileUploaderDropzoneInstructions"] svg {
    display: none !important;
}

/* The one visible label, drawn cleanly instead of relying on
   whatever native markup was overlapping */
[data-testid="stFileUploaderDropzoneInstructions"]::before {
    content: "📤  Drag and drop files here, or click Browse" !important;
    font-size: 14px !important;
    line-height: 1.4 !important;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    color: var(--text-secondary) !important;
}

/* Keep the "Browse files" button itself visible and normal-sized —
   it's a real <button>, not text content, so font-size:0 above
   doesn't blank it out; this just makes sure of it. */
[data-testid="stFileUploaderDropzone"] button {
    font-size: 14px !important;
}
[data-testid="stFileUploaderDropzone"] button * {
    font-size: 14px !important;
}

/* ═══════════════════════════════════════════════════════════════
   REDUCE MOTION
   ═══════════════════════════════════════════════════════════════ */
@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
        animation-duration: 0.01ms !important;
        transition-duration: 0.01ms !important;
    }
}

</style>

<script>
(function() {
  // Clears text from any span whose font-family contains "Material"
  // This fires immediately AND watches for dynamic Streamlit re-renders
  function killMaterialText(root) {
    // Broadened from 'span[style]' to any element, since the file
    // uploader's icon can be a <span> or <i> depending on Streamlit
    // version — both leave a raw ligature name ("upload", "cloud_upload")
    // as fallback text before the icon font paints over it.
    var iconEls = (root || document).querySelectorAll('[style]');
    iconEls.forEach(function(el) {
      var style = el.getAttribute('style') || '';
      if (style.toLowerCase().indexOf('material') !== -1) {
        el.textContent = '';
      }
    });
    // Also catch by data-testid
    var toggleIcons = (root || document).querySelectorAll('[data-testid="stExpanderToggleIcon"]');
    toggleIcons.forEach(function(el) { el.textContent = ''; });

    // File uploader: clear any stray literal icon-ligature text
    // ("upload", "cloud_upload", etc.) that renders behind/next to the
    // "Browse files" button label, causing overlapping text.
    var uploaderIcons = (root || document).querySelectorAll(
      '[data-testid="stFileUploaderDropzoneInstructions"] span, ' +
      '[data-testid="stFileUploaderDropzoneInstructions"] i'
    );
    uploaderIcons.forEach(function(el) {
      var txt = (el.textContent || '').trim().toLowerCase();
      if (txt === 'upload' || txt === 'cloud_upload' || txt === 'file_upload') {
        el.textContent = '';
      }
    });
  }

  // Run immediately once DOM ready
  document.addEventListener('DOMContentLoaded', function() { killMaterialText(); });
  killMaterialText();

  // Watch for Streamlit re-renders (it replaces DOM nodes on navigation)
  var observer = new MutationObserver(function(mutations) {
    mutations.forEach(function(m) {
      if (m.addedNodes.length) { killMaterialText(); }
    });
  });
  observer.observe(document.body || document.documentElement, {
    childList: true,
    subtree: true
  });

  // Fallback: keep polling for 5 seconds after load
  var count = 0;
  var interval = setInterval(function() {
    killMaterialText();
    count++;
    if (count > 10) clearInterval(interval);
  }, 500);
})();
</script>
"""
