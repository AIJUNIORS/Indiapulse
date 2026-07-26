#!/usr/bin/env python3
"""
IndiaPulse
Milestone 2.1 - Market Universe Generator
"""

from pathlib import Path
import csv

# ---------------------------------------------------------------------
# Project Paths
# ---------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
UNIVERSE_DIR = PROJECT_ROOT / "data" / "universe"

UNIVERSE_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------
# CSV Writer
# ---------------------------------------------------------------------

def write_csv(filename, header, rows):
    filepath = UNIVERSE_DIR / filename

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)

    print(f"Created {filename} ({len(rows)} rows)")


HEADER = [
    "Symbol",
    "Name",
    "Category",
    "Exchange",
    "Provider",
    "AssetClass",
    "Frequency",
    "Priority",
    "Active",
    "Remarks"
]
