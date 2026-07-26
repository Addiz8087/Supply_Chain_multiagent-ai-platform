"""
services/live_data.py
======================
Live mineral price and country data fetcher.

Two layers — exactly like the paper's structured-data baseline:
  1. LIVE  — yfinance futures prices + World Bank WGI API (free, no key)
  2. STATIC FALLBACK — published reference prices from USGS Mineral
     Commodity Summaries 2024/2025 and LME average prices, so the
     platform always shows *something* real even when offline.

Every price is tagged with its source + year so the UI can show
whether it is live or a cited static reference.

Cambridge GSCO inspiration
--------------------------
The Cambridge Global Supply Chain Observatory (app.cambridge-gsco.co.uk)
maps supply-chain risk at country level. This module feeds the same
kind of country-level risk + price data into the world-map page added
to this platform, but using fully open / free data sources.
"""

from __future__ import annotations

import time
import requests
from typing import Dict, Optional

# ── Static reference prices (USGS MCS 2025 + LME 2024 averages) ──────────
# Source: U.S. Geological Survey Mineral Commodity Summaries 2025
#         https://www.usgs.gov/centers/national-minerals-information-center/
#         mineral-commodity-summaries
# Source: London Metal Exchange average prices 2024
#         https://www.lme.com/Market-data/Reports-and-data/Average-prices
# These are the authentic published prices — live data supplements them.

STATIC_PRICES: Dict[str, Dict] = {
    "Lithium": {
        "price": 13_000, "unit": "USD/t (lithium carbonate, battery grade)",
        "source": "USGS MCS 2025 / Fastmarkets 2024 average",
        "year": 2024, "confidence": "HIGH",
        "note": "Price fell sharply from 2022–23 peak (~80k USD/t) due to oversupply",
        "ticker": None,
    },
    "Cobalt": {
        "price": 26_000, "unit": "USD/t",
        "source": "LME average 2024 / USGS MCS 2025",
        "year": 2024, "confidence": "HIGH",
        "ticker": None,
    },
    "Gallium": {
        "price": 220, "unit": "USD/kg",
        "source": "USGS MCS 2025",
        "year": 2024, "confidence": "HIGH",
        "note": "China export restrictions (2023) caused significant price volatility",
        "ticker": None,
    },
    "Germanium": {
        "price": 1_050, "unit": "USD/kg",
        "source": "USGS MCS 2025",
        "year": 2024, "confidence": "HIGH",
        "note": "China export licence regime (2023) restricts supply",
        "ticker": None,
    },
    "Copper": {
        "price": 9_200, "unit": "USD/t",
        "source": "LME average 2024",
        "year": 2024, "confidence": "HIGH",
        "ticker": "HG=F",  # yfinance COMEX copper futures (USD/lb → convert)
    },
    "Rare Earth Elements": {
        "price": 700, "unit": "USD/t (mixed rare earth oxides, indicative)",
        "source": "USGS MCS 2025 (cerium oxide benchmark)",
        "year": 2024, "confidence": "MEDIUM",
        "note": "Prices vary widely by specific element (La, Ce, Nd, Dy, etc.)",
        "ticker": None,
    },
    "Nickel": {
        "price": 16_000, "unit": "USD/t",
        "source": "LME average 2024",
        "year": 2024, "confidence": "HIGH",
        "ticker": None,
    },
    "Silicon": {
        "price": 1_450, "unit": "USD/t (metallurgical grade)",
        "source": "USGS MCS 2025",
        "year": 2024, "confidence": "HIGH",
        "ticker": None,
    },
    "Graphite": {
        "price": 500, "unit": "USD/t (flake graphite, 94–97% C)",
        "source": "USGS MCS 2025",
        "year": 2024, "confidence": "MEDIUM",
        "ticker": None,
    },
    "Aluminium": {
        "price": 2_400, "unit": "USD/t",
        "source": "LME average 2024",
        "year": 2024, "confidence": "HIGH",
        "ticker": None,
    },
}

# Production data: world mine output by country (USGS MCS 2025, kt/yr or t/yr)
PRODUCTION_DATA: Dict[str, Dict] = {
    "Lithium": {
        "unit": "kt lithium content",
        "source": "USGS MCS 2025",
        "countries": {
            "Australia": 86, "Chile": 44, "China": 33,
            "Argentina": 9,  "Brazil": 4,  "Zimbabwe": 3,
        },
    },
    "Cobalt": {
        "unit": "kt",
        "source": "USGS MCS 2025",
        "countries": {
            "Democratic Republic of Congo": 220, "Russia": 8,
            "Australia": 5, "Philippines": 4, "Cuba": 3,
        },
    },
    "Gallium": {
        "unit": "t",
        "source": "USGS MCS 2025",
        "countries": {
            "China": 290, "Russia": 6, "South Korea": 5, "Japan": 4,
        },
    },
    "Germanium": {
        "unit": "t",
        "source": "USGS MCS 2025",
        "countries": {
            "China": 80, "Russia": 5, "Belgium": 2, "Finland": 1,
        },
    },
    "Copper": {
        "unit": "kt",
        "source": "USGS MCS 2025",
        "countries": {
            "Chile": 5_600, "Democratic Republic of Congo": 2_400,
            "Peru": 2_400, "China": 1_900, "USA": 870,
            "Australia": 840, "Russia": 810, "Zambia": 800,
        },
    },
    "Rare Earth Elements": {
        "unit": "kt REO",
        "source": "USGS MCS 2025",
        "countries": {
            "China": 270, "USA": 45, "Australia": 18,
            "Myanmar": 38, "India": 3,
        },
    },
    "Nickel": {
        "unit": "kt",
        "source": "USGS MCS 2025",
        "countries": {
            "Indonesia": 1_800, "Philippines": 330,
            "Russia": 200, "New Caledonia": 190, "Australia": 160,
            "Canada": 130,
        },
    },
    "Graphite": {
        "unit": "kt",
        "source": "USGS MCS 2025",
        "countries": {
            "China": 950, "Mozambique": 120, "Madagascar": 55,
            "Brazil": 27, "Russia": 26,
        },
    },
}

_PRICE_CACHE: Dict[str, Dict] = {}
_STABILITY_CACHE: Dict[str, float] = {}

# ── Live price fetch (yfinance) ───────────────────────────────────────────

def fetch_live_price(mineral: str) -> Dict:
    """
    Try to get a live price via yfinance. Falls back to static USGS/LME
    reference price if yfinance is unavailable or the mineral has no ticker.
    Returns a dict with value, unit, source, confidence, is_live.
    """
    if mineral in _PRICE_CACHE:
        return _PRICE_CACHE[mineral]

    static = STATIC_PRICES.get(mineral, {})
    ticker = static.get("ticker")

    if ticker:
        try:
            import yfinance as yf
            hist = yf.Ticker(ticker).history(period="5d")
            if not hist.empty:
                raw = float(hist["Close"].iloc[-1])
                # COMEX copper is USD/lb → convert to USD/t (×2204.62)
                price = round(raw * 2204.62, 0) if ticker == "HG=F" else round(raw, 2)
                result = {
                    "price": price,
                    "unit": static.get("unit", "USD"),
                    "source": f"yfinance ({ticker}) — live",
                    "confidence": "HIGH",
                    "is_live": True,
                    "retrieved": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()),
                }
                _PRICE_CACHE[mineral] = result
                return result
        except Exception:
            pass  # fall through to static

    # Return static reference price
    result = {
        "price": static.get("price"),
        "unit": static.get("unit", "USD"),
        "source": static.get("source", "USGS MCS 2025"),
        "confidence": static.get("confidence", "MEDIUM"),
        "is_live": False,
        "note": static.get("note", ""),
        "year": static.get("year", 2024),
    }
    _PRICE_CACHE[mineral] = result
    return result


def fetch_all_prices() -> Dict[str, Dict]:
    """Return price data for every mineral in the platform."""
    return {m: fetch_live_price(m) for m in STATIC_PRICES}


# ── World Bank political stability (free JSON API, no key) ────────────────

def fetch_country_stability(iso2: str) -> Optional[float]:
    """
    Fetch the World Bank Political Stability & Absence of Violence score
    for a country (scale: -2.5 worst → +2.5 best).
    Returns None if the API is unreachable.
    Source: https://api.worldbank.org/v2/  (free, no key required)
    """
    if iso2 in _STABILITY_CACHE:
        return _STABILITY_CACHE[iso2]
    try:
        url = (
            f"https://api.worldbank.org/v2/country/{iso2}/indicator/"
            f"PV.EST?format=json&mrv=1&per_page=1"
        )
        r = requests.get(url, timeout=8)
        if r.status_code == 200:
            data = r.json()
            if len(data) > 1 and data[1]:
                val = data[1][0].get("value")
                if val is not None:
                    _STABILITY_CACHE[iso2] = round(float(val), 3)
                    return _STABILITY_CACHE[iso2]
    except Exception:
        pass
    return None


# ── Production map data (for choropleth) ─────────────────────────────────

# ISO-3 country codes needed by Plotly choropleth
_NAME_TO_ISO3 = {
    "Australia": "AUS", "Chile": "CHL", "China": "CHN",
    "Argentina": "ARG", "Brazil": "BRA", "Zimbabwe": "ZWE",
    "Democratic Republic of Congo": "COD", "Russia": "RUS",
    "Philippines": "PHL", "Cuba": "CUB", "South Korea": "KOR",
    "Japan": "JPN", "Belgium": "BEL", "Finland": "FIN",
    "Peru": "PER", "USA": "USA", "Zambia": "ZMB",
    "Myanmar": "MMR", "India": "IND", "Indonesia": "IDN",
    "New Caledonia": "NCL", "Canada": "CAN",
    "Mozambique": "MOZ", "Madagascar": "MDG",
    "Netherlands": "NLD", "United Kingdom": "GBR",
    "Switzerland": "CHE", "Germany": "DEU", "Taiwan": "TWN",
    "Malaysia": "MYS", "Singapore": "SGP",
}


def production_map_data(mineral: str) -> Dict:
    """
    Return data formatted for a Plotly choropleth map:
    list of {country, iso3, production, unit, source}.
    """
    prod = PRODUCTION_DATA.get(mineral)
    if not prod:
        return {"rows": [], "unit": "", "source": "USGS MCS 2025", "mineral": mineral}

    rows = []
    for country, value in prod["countries"].items():
        iso3 = _NAME_TO_ISO3.get(country, "")
        rows.append({
            "country": country,
            "iso3": iso3,
            "production": value,
        })
    return {
        "mineral": mineral,
        "rows": rows,
        "unit": prod["unit"],
        "source": prod["source"],
    }
