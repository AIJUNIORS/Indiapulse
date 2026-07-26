#!/usr/bin/env python3
"""
IndiaPulse - External Source Connectors
Milestone 4/5 - Data Download Engine

Handles symbols whose backend/sources.py entry is
{"source": "EXTERNAL", "provider": "..."} -- data that isn't available
through Yahoo Finance at all (RBI G-Sec/SDL/corp-bond series, NSE Debt
segment, etc), plus macro series from RBI/MOSPI/GSTN/S&P/NSDL routed
here by backend/macro.py.

None of RBI/NSE Debt/MOSPI/GSTN/S&P/NSDL have a clean free API the way
Yahoo Finance does -- RBI publishes G-Sec/SDL yields via DBIE (Database
on Indian Economy) and the Handbook of Statistics, typically as
downloadable Excel/CSV, not a REST endpoint. Rather than guess at a
scraper against a page that will change shape, this module supports a
**manual CSV drop-in**: if a file matching data/manual/<SYMBOL>.csv
exists (Date index + a "Close" column, same shape the rest of the
pipeline uses), it's picked up automatically on the next download run
and copied into data/historical/ like any other source. This makes
"paste in a CSV exported from DBIE" a real, working path today, while
leaving room for a real scraper/API connector later without changing
how the rest of the pipeline calls this module.
"""

from __future__ import annotations

import pandas as pd

from backend.config import MANUAL_DIR
from backend.logger import get_logger
from backend.utils import safe_symbol_filename

log = get_logger("external")

# Providers referenced by sources.py EXTERNAL entries (and macro.csv's
# Provider column, via backend/macro.py). None have an automated
# connector yet -- see the manual CSV drop-in path below instead.
SUPPORTED_PROVIDERS = {
    "RBI": "not_implemented",       # G-Sec buckets, SDL, corp bonds, repo/CRR, forex reserves
    "NSE_DEBT": "not_implemented",  # NSE Debt segment series
    "LME": "not_implemented",       # kept for any future series still needing true LME data
    "MOSPI": "not_implemented",     # CPI, GDP, IIP
    "GSTN": "not_implemented",      # GST collections
    "S&P": "not_implemented",       # PMI Manufacturing / Services
    "NSDL": "not_implemented",      # FII/DII net flows
    "Commerce": "not_implemented",  # WPI
}


def _manual_csv_path(symbol: str):
    return MANUAL_DIR / f"{safe_symbol_filename(symbol)}.csv"


def fetch_external(symbol: str, provider: str) -> pd.DataFrame | None:
    """Attempt to fetch data for an EXTERNAL-sourced symbol.

    First checks for a manually-provided CSV at data/manual/<SYMBOL>.csv
    (drop RBI DBIE / other exports there in Date,Open,High,Low,Close,Volume
    shape -- only Close is required, the rest may be blank/omitted and
    will be filled in). If found and valid, returns it directly. If not,
    logs clearly that this symbol needs either a manual drop-in or a
    real connector (Milestone 5+) rather than failing silently.
    """
    manual_path = _manual_csv_path(symbol)
    if manual_path.exists():
        try:
            df = pd.read_csv(manual_path, index_col=0, parse_dates=True)
            if "Close" not in df.columns or df["Close"].dropna().empty:
                log.error("%s: manual CSV at %s has no usable 'Close' column", symbol, manual_path)
                return None
            for col in ("Open", "High", "Low"):
                if col not in df.columns:
                    df[col] = df["Close"]
            if "Volume" not in df.columns:
                df["Volume"] = 0
            log.info("%s: loaded %d rows from manual drop-in %s", symbol, len(df), manual_path)
            return df.sort_index()
        except Exception as exc:  # noqa: BLE001
            log.error("%s: failed to read manual CSV at %s: %s", symbol, manual_path, exc)
            return None

    status = SUPPORTED_PROVIDERS.get(provider, "unknown_provider")
    log.info(
        "Skipping %s: external provider '%s' is %s and no manual CSV found at %s "
        "(drop a Date,Close CSV there to unblock this symbol today)",
        symbol, provider, status, manual_path,
    )
    return None
