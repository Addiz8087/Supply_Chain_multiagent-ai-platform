"""
services/usgs_reference.py
============================
Manually-verified reference data pulled directly from the primary USGS
Mineral Commodity Summaries 2025 PDF (https://pubs.usgs.gov/periodicals/
mcs2025/mcs2025.pdf), cross-checked line-by-line against the published
tables — NOT estimated, NOT copied from a secondary source.

This is the "verified" tier described in services/data_sources.py's
provenance model. Anything NOT in VERIFIED_PRODUCTION below should be
treated as unverified/estimated until someone checks it against the PDF
the same way these entries were checked, and adds it here with a page
citation.

How each entry was verified:
  1. Fetched the individual mineral chapter PDF directly from USGS.
  2. Located the "World Mine Production and Reserves" table.
  3. Copied the 2024e (estimated) column values exactly as published.
  4. Recorded the page number for traceability.

To add another mineral: fetch https://pubs.usgs.gov/periodicals/mcs2025/
mcs2025-{mineral-name}.pdf, find the same table, and add an entry below
in the same format. Do not guess or round the published numbers.
"""

from typing import Dict

VERIFIED_PRODUCTION: Dict[str, Dict] = {
    "Lithium": {
        "unit": "metric tons, lithium content",
        "year": "2024e",
        "source": "USGS Mineral Commodity Summaries 2025",
        "source_url": "https://pubs.usgs.gov/periodicals/mcs2025/mcs2025-lithium.pdf",
        "page": 111,
        "verified": True,
        "countries": {
            "Australia": 88_000,
            "Chile": 49_000,
            "China": 41_000,
            "Zimbabwe": 22_000,
            "Argentina": 18_000,
            "Brazil": 10_000,
            "Canada": 4_300,
            "Namibia": 2_700,
            "Portugal": 380,
        },
        "world_total_excl_us": 240_000,
    },
    "Copper": {
        "unit": "thousand metric tons, copper content",
        "year": "2024e",
        "source": "USGS Mineral Commodity Summaries 2025",
        "source_url": "https://pubs.usgs.gov/periodicals/mcs2025/mcs2025-copper.pdf",
        "page": 65,
        "verified": True,
        "countries": {
            "Chile": 5_300,
            "Congo (Kinshasa)": 3_300,
            "Peru": 2_600,
            "China": 1_800,
            "Indonesia": 1_100,
            "United States": 1_100,
            "Australia": 800,
            "Russia": 930,
            "Kazakhstan": 740,
            "Mexico": 700,
            "Zambia": 680,
            "Canada": 450,
        },
        "world_total": 23_000,  # rounded, incl. USA, thousand metric tons
    },
    # ── Add more minerals here as you verify them ──────────────────────
    # Template:
    # "Cobalt": {
    #     "unit": "metric tons",
    #     "year": "2024e",
    #     "source": "USGS Mineral Commodity Summaries 2025",
    #     "source_url": "https://pubs.usgs.gov/periodicals/mcs2025/mcs2025-cobalt.pdf",
    #     "page": None,  # fill in after checking
    #     "verified": True,
    #     "countries": {...},
    # },
}


def get_verified_production(mineral: str) -> Dict:
    """
    Return manually-verified USGS production data for a mineral, or a
    clear 'not yet verified' marker if it hasn't been cross-checked.
    Use this in place of PRODUCTION_DATA where verification matters
    (e.g. dissertation methodology, supervisor review, viva demo).
    """
    if mineral in VERIFIED_PRODUCTION:
        return VERIFIED_PRODUCTION[mineral]
    return {
        "verified": False,
        "note": (
            f"'{mineral}' has not yet been manually cross-checked against "
            f"the USGS MCS 2025 PDF. The value shown elsewhere in this "
            f"platform is an estimate pending verification — see "
            f"services/usgs_reference.py for the verification process."
        ),
    }


def verification_status() -> Dict[str, bool]:
    """Quick summary: which minerals have genuinely verified data vs. not."""
    from services.live_data import PRODUCTION_DATA
    return {m: (m in VERIFIED_PRODUCTION) for m in PRODUCTION_DATA}
