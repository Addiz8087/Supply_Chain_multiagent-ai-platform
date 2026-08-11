"""
app/config.py
=============
Central configuration.

Secret loading order (first one found wins):
  1. Streamlit Cloud "Secrets" (st.secrets)   -> used when deployed
  2. Local .env file in the project root      -> used when running locally
     MISTRAL_API_KEY=your_key_here

Either way, the key is NEVER hardcoded here and NEVER committed to git.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root (works from any working directory, no-op if missing)
_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env")


def _get_secret(key: str, default: str = "") -> str:
    """
    Look up a secret in Streamlit Cloud's st.secrets first (if available/deployed),
    then fall back to environment variables (.env locally).
    """
    try:
        import streamlit as st
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass  # not running under Streamlit, or no secrets.toml configured
    return os.getenv(key, default)


# ── Mistral (free tier) ────────────────────────────────────────────────────
MISTRAL_API_KEY: str = _get_secret("MISTRAL_API_KEY", "")
MISTRAL_MODEL: str   = _get_secret("MISTRAL_MODEL", "mistral-small-latest")
MISTRAL_URL: str     = "https://api.mistral.ai/v1/chat/completions"

# ── Agent behaviour ────────────────────────────────────────────────────────
# NOTE: these were previously (10, 22.0, 1400, 20). On the Mistral free
# tier that meant a single rate-limited call could block for up to
# 220 seconds, and each specialist agent could take up to 20 ReAct steps
# to finish — with 4 agents per goal, that's how a batch of 9 goals ended
# up taking ~30 minutes and occasionally stalling out. These lower values
# keep runs fast while still giving each agent enough steps to call its
# tools and finish.
MAX_RETRIES: int      = 4
RETRY_DELAY: float    = 8.0       # real Retry-After header (if present) still overrides this
MAX_TOKENS: int        = 800
AGENT_MAX_STEPS: int   = 8

# ── RAG pipeline ────────────────────────────────────────────────────────
CHROMA_DB_PATH: str = str(_ROOT / "data" / "chroma_db")
RAG_CHUNK_SIZE: int = 250       # words per chunk
RAG_CHUNK_OVERLAP: int = 50
RAG_TOP_K: int = 8

# ── Mesa simulation ────────────────────────────────────────────────────
SIM_N_REPLICATIONS: int = 30
SIM_HORIZON_MONTHS: int = 60

# ── Persistent memory ──────────────────────────────────────────────────────
DB_PATH: str = str(_ROOT / "data" / "supply_chain_memory.db")

# ── Validation ─────────────────────────────────────────────────────────────
def validate():
    """Call at startup to catch missing config early."""
    if not MISTRAL_API_KEY:
        raise EnvironmentError(
            "MISTRAL_API_KEY is not set.\n"
            "Locally: create a .env file in the project root:\n"
            "  MISTRAL_API_KEY=your_key_here\n"
            "On Streamlit Cloud: go to your app -> Settings -> Secrets, and add:\n"
            "  MISTRAL_API_KEY = \"your_key_here\"\n"
            "Get a free key at: https://console.mistral.ai"
        )
