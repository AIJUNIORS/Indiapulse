#!/usr/bin/env python3
"""
Run from the repo root: python diagnose_coverage.py
Reports exactly why each universe symbol would show "Insufficient Data",
without needing to run the full analytics pipeline.
"""
import sys
sys.path.insert(0, ".")

import pandas as pd
from backend.config import HISTORICAL_DIR, UNIVERSE_DIR
from backend.utils import read_universe_csv, safe_symbol_filename

UNIVERSE_FILES = ["broad_market", "sectors", "industries", "themes",
                  "factors", "fixed_income", "commodities"]

TREND_MIN, MOMENTUM_MIN, SEASONALITY_MIN_YEARS = 210, 60, 5

rows = []
for f in UNIVERSE_FILES:
    for r in read_universe_csv(UNIVERSE_DIR / f"{f}.csv"):
        sym = r["Symbol"]
        path = HISTORICAL_DIR / f"{safe_symbol_filename(sym)}.csv"
        if not path.exists():
            rows.append((sym, f, "NO FILE", 0, 0))
            continue
        try:
            df = pd.read_csv(path, index_col=0, parse_dates=True)
            n = len(df["Close"].dropna()) if "Close" in df.columns else 0
            years = df.index.year.nunique() if n else 0
        except Exception as e:
            rows.append((sym, f, f"READ ERROR: {e}", 0, 0))
            continue
        reasons = []
        if n < TREND_MIN: reasons.append(f"trend {n}/{TREND_MIN}")
        if n < MOMENTUM_MIN: reasons.append(f"momentum {n}/{MOMENTUM_MIN}")
        if years < SEASONALITY_MIN_YEARS: reasons.append(f"seasonality {years}/{SEASONALITY_MIN_YEARS}yrs")
        if reasons:
            rows.append((sym, f, "; ".join(reasons), n, years))

print(f"{'Symbol':<24}{'Category':<16}{'Rows':<7}{'Years':<7}Reason")
for sym, cat, reason, n, years in rows:
    print(f"{sym:<24}{cat:<16}{n:<7}{years:<7}{reason}")
print(f"\n{len(rows)} symbols would show Insufficient Data")
