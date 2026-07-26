#!/usr/bin/env python3
"""
IndiaPulse - Macro Data Reader & Cycle Inputs
Milestone 5 (partial) - Macro Pipeline

Reads data/universe/macro.csv (its own schema -- no AssetClass column,
since macro series don't come from yfinance) and whatever historical
CSVs exist for each macro symbol under data/historical/, then derives
the growth_trend / inflation_trend / rate_direction inputs that
backend/analytics/cycle.py's compute_cycle() needs.

Most macro series (CPI, WPI, GDP, IIP, PMI, GST, FII/DII, REPO_RATE,
CRR, FOREX) come from RBI/MOSPI/GSTN/S&P and aren't downloadable via
yfinance yet -- see backend/external.py for the connector status.
USDINR is the one exception (Yahoo: "USDINR=X") and can be fetched
like any other FX pair; MACRO_SOURCE_REGISTRY below reflects that.

Until the RBI/MOSPI/GSTN connectors exist, this module works with
whatever has been manually dropped into data/historical/<SYMBOL>.csv
in the standard shape (only a "Close" column is required for macro
series -- Open/High/Low/Volume don't apply).
"""

from __future__ import annotations

import time

import pandas as pd

from backend.config import UNIVERSE_DIR, HISTORICAL_DIR, DEFAULT_PERIOD, \
    DEFAULT_INTERVAL, RATE_LIMIT_SLEEP
from backend.download import _download_with_retry, validate_dataframe, _existing_data_path
from backend.external import fetch_external
from backend.logger import get_logger
from backend.utils import read_universe_csv, safe_symbol_filename

log = get_logger("macro")

MACRO_UNIVERSE_FILE = "macro.csv"

# Which macro symbols feed each cycle input, in priority order -- the
# first symbol with usable data wins. Never blend a proxy in silently;
# if nothing is available we fall back to a neutral default and say so.
GROWTH_SYMBOLS = ["GDP", "IIP", "PMI_MFG", "PMI_SERV"]
INFLATION_SYMBOLS = ["CPI", "WPI"]
RATE_SYMBOL = "REPO_RATE"

# Macro symbols that ARE fetchable via Yahoo today. Everything else in
# macro.csv needs an RBI/MOSPI/GSTN connector (Milestone 5+).
MACRO_SOURCE_REGISTRY = {
    "USDINR": {"source": "FX", "ticker": "USDINR=X"},
}


def load_macro_universe() -> list[dict]:
    """Read data/universe/macro.csv (separate schema from the other universe files)."""
    rows = read_universe_csv(UNIVERSE_DIR / MACRO_UNIVERSE_FILE)
    log.info("Loaded %d macro series definitions", len(rows))
    return rows


def _load_series(symbol: str) -> pd.DataFrame | None:
    path = HISTORICAL_DIR / f"{safe_symbol_filename(symbol)}.csv"
    if not path.exists():
        return None
    try:
        df = pd.read_csv(path, index_col=0, parse_dates=True)
        if df.empty or "Close" not in df.columns:
            return None
        return df.sort_index()
    except Exception as exc:  # noqa: BLE001
        log.warning("Could not read macro series %s: %s", symbol, exc)
        return None


def _pct_change(df: pd.DataFrame) -> float | None:
    """Latest value vs the prior observation, as a percent delta."""
    closes = df["Close"].dropna()
    if len(closes) < 2:
        return None
    latest, prior = closes.iloc[-1], closes.iloc[-2]
    if prior == 0:
        return None
    return float((latest - prior) / abs(prior) * 100)


def _first_available_trend(symbols: list[str]) -> tuple[float, str] | None:
    """Return (pct_change, symbol_used) for the first symbol with >=2 data points."""
    for sym in symbols:
        df = _load_series(sym)
        if df is None:
            continue
        change = _pct_change(df)
        if change is not None:
            return change, sym
    return None


def get_growth_trend() -> tuple[float, str | None]:
    result = _first_available_trend(GROWTH_SYMBOLS)
    if result is None:
        log.warning("No growth data available yet (%s); defaulting growth_trend=0.0", GROWTH_SYMBOLS)
        return 0.0, None
    change, sym = result
    log.info("growth_trend=%.2f%% (from %s)", change, sym)
    return change, sym


def get_inflation_trend() -> tuple[float, str | None]:
    result = _first_available_trend(INFLATION_SYMBOLS)
    if result is None:
        log.warning("No inflation data available yet (%s); defaulting inflation_trend=0.0", INFLATION_SYMBOLS)
        return 0.0, None
    change, sym = result
    log.info("inflation_trend=%.2f%% (from %s)", change, sym)
    return change, sym


def get_rate_direction() -> str:
    """'hiking' | 'cutting' | 'hold', based on the last two REPO_RATE readings."""
    df = _load_series(RATE_SYMBOL)
    if df is None:
        log.warning("No %s data available yet; defaulting rate_direction='hold'", RATE_SYMBOL)
        return "hold"
    closes = df["Close"].dropna()
    if len(closes) < 2:
        return "hold"
    latest, prior = closes.iloc[-1], closes.iloc[-2]
    if latest > prior:
        return "hiking"
    if latest < prior:
        return "cutting"
    return "hold"


def download_macro_universe(incremental: bool = False) -> dict:
    """Download whatever macro series have a real source today.

    Right now that's just USDINR (Yahoo FX pair). Everything else in
    macro.csv (CPI, WPI, GDP, IIP, PMI, GST, FII/DII, REPO_RATE, CRR,
    FOREX) needs an RBI/MOSPI/GSTN/S&P connector -- see
    backend/external.py -- and is logged + skipped, not guessed.
    """
    universe = load_macro_universe()
    results = {"success": [], "failed": [], "skipped": []}

    for row in universe:
        symbol = row.get("Symbol")
        if not symbol:
            continue
        if row.get("Active", "True").strip().lower() not in ("true", "1", "yes"):
            continue

        entry = MACRO_SOURCE_REGISTRY.get(symbol)
        if not entry:
            fetch_external(symbol, row.get("Provider", "unknown"))
            results["skipped"].append(symbol)
            continue

        out_path = _existing_data_path(symbol)
        dl_period = DEFAULT_PERIOD
        if incremental and out_path.exists():
            try:
                existing = pd.read_csv(out_path, index_col=0, parse_dates=True)
                if not existing.empty:
                    last_date = existing.index.max()
                    days_missing = (pd.Timestamp.now() - last_date).days
                    if days_missing <= 0:
                        log.info("%s already up to date (last=%s)", symbol, last_date.date())
                        results["success"].append(symbol)
                        continue
                    dl_period = f"{max(days_missing + 2, 5)}d"
            except Exception as exc:  # noqa: BLE001
                log.warning("Could not read existing macro data for %s (%s); full download", symbol, exc)

        df = _download_with_retry(entry["ticker"], dl_period, DEFAULT_INTERVAL)
        if df is None or not validate_dataframe(df, symbol):
            results["failed"].append(symbol)
            continue

        if incremental and out_path.exists():
            try:
                existing = pd.read_csv(out_path, index_col=0, parse_dates=True)
                combined = pd.concat([existing, df])
                combined = combined[~combined.index.duplicated(keep="last")].sort_index()
                combined.to_csv(out_path)
            except Exception as exc:  # noqa: BLE001
                log.warning("Merge failed for %s (%s); overwriting with fresh data", symbol, exc)
                df.to_csv(out_path)
        else:
            df.to_csv(out_path)

        log.info("Saved macro series %s -> %s (%d rows)", symbol, out_path.name, len(df))
        time.sleep(RATE_LIMIT_SLEEP)
        results["success"].append(symbol)

    log.info(
        "Macro download complete: %d success, %d failed, %d skipped",
        len(results["success"]), len(results["failed"]), len(results["skipped"]),
    )
    return results


def get_cycle_inputs() -> dict:
    """Bundle everything backend.analytics.cycle.compute_cycle() needs,
    derived from real macro data where available (falls back to a
    neutral 0.0/0.0/"hold" reading per-field, with a log line, if a
    given series hasn't been downloaded/populated yet).
    """
    growth_trend, growth_src = get_growth_trend()
    inflation_trend, inflation_src = get_inflation_trend()
    rate_direction = get_rate_direction()
    return {
        "growth_trend": growth_trend,
        "inflation_trend": inflation_trend,
        "rate_direction": rate_direction,
        "growth_source": growth_src,
        "inflation_source": inflation_src,
    }
