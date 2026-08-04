"""
export_reports.py
==================
Pulls the FULL, untruncated report text for every saved run out of the
SQLite database and writes them into one readable text file — ready to
paste into a Word doc as a dissertation appendix.

Run from the project root:
    python export_reports.py

Produces: dissertation_data/all_reports.txt
"""

import sqlite3
import os
from app.config import DB_PATH

OUTPUT_DIR = "dissertation_data"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "all_reports.txt")

os.makedirs(OUTPUT_DIR, exist_ok=True)

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# Adjust table/column names here if yours differ — this assumes the
# same 'runs' table your export_agency_report.py already reads from.
cur.execute("""
    SELECT id, goal, report, tool_calls
    FROM runs
    ORDER BY id ASC
""")
rows = cur.fetchall()
conn.close()

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    f.write("SYSTEM-GENERATED EXECUTIVE REPORTS — FULL APPENDIX EXPORT\n")
    f.write("=" * 70 + "\n\n")
    for run_id, goal, report, tool_calls in rows:
        f.write(f"RUN ID: {run_id}\n")
        f.write(f"GOAL: {goal}\n")
        f.write(f"TOOL CALLS: {tool_calls}\n")
        f.write("-" * 70 + "\n")
        f.write((report or "[no report text saved for this run]") + "\n")
        f.write("\n" + "=" * 70 + "\n\n")

print(f"Exported {len(rows)} full reports to {OUTPUT_FILE}")
print("Open that file, copy the 9 you want, paste into Word.")
