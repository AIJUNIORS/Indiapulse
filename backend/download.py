#!/usr/bin/env python3
"""
IndiaPulse - Download Engine
Milestone 4 - Download Engine

Reads universe CSVs, merges & deduplicates symbols, selects a provider
per AssetClass, downloads historical OHLCV data with retry logic, and
saves one CSV per symbol under data/historical/. Supports incremental
("update-only") downloads.
"""

from __future__ import annotations

import time
from pathlib import Path

import pandas as pd

from backend.config import UNIVERSE_DIR, HISTORICAL_DIR, DEFAULT_PERIOD, \
    DEFAULT_INTERVAL, MAX_RETRIES, RETRY_BACKOFF, RATE_LIMIT_SLEEP
from backend.logger import get_logger
from backend.sources import get_provider_for_asset_class, get_yfinance_ticker
from backend.utils import read_universe_csv, safe_symbol_filename

log = get_logger("download")

UNIVERSE_FILES = [
    "broad_market.csv",
    "sectors.csv",
    "industries.csv",
    "themes.csv",
    "factors.csv",
    "fixed_income.csv",
    "commodities.csv",
]


# ---------------------------------------------------------------------
# Universe loading
# ---------------------------------------------------------------------

def load_universe() -> list[dict]:
    """Read every universe CSV, merge and de-duplicate by Symbol."""
    merged: dict[str, dict] = {}
    for filename in UNIVERSE_FILES:
        rows = read_universe_csv(UNIVERSE_DIR / filename)
        for row in rows:
            symbol = row.get("Symbol")
            if not symbol:
                continue
            if row.get("Active", "True").strip().lower() not in ("true", "1", "yes"):
                continue
            # First occurrence wins; log duplicates for visibility.
            if symbol in merged:
                log.warning("Duplicate symbol '%s' found in %s (keeping first)", symbol, filename)
                continue
            merged[symbol] = row
    log.info("Loaded %d unique active symbols from universe", len(merged))
    return list(merged.values())


# ---------------------------------------------------------------------
# Download core
# ---------------------------------------------------------------------

def _download_with_retry(ticker: str, period: str, interval: str) -> pd.DataFrame | None:
    """Attempt a yfinance download with exponential-ish backoff retries."""
    import yfinance as yf

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            df = yf.download(
                ticker,
                period=period,
                interval=interval,
                progress=False,
                auto_adjust=True,
            )
            if df is None or df.empty:
                raise ValueError(f"Empty dataframe returned for {ticker}")
            # yfinance sometimes returns MultiIndex columns for single tickers
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            return df
        except Exception as exc:  # noqa: BLE001
            log.warning(
                "Attempt %d/%d failed for %s: %s", attempt, MAX_RETRIES, ticker, exc
            )
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF * attempt)
    log.error("All %d attempts failed for %s", MAX_RETRIES, ticker)
    return None


def validate_dataframe(df: pd.DataFrame, symbol: str) -> bool:
    """Basic sanity checks on downloaded data before saving."""
    required_cols = {"Open", "High", "Low", "Close", "Volume"}
    if not required_cols.issubset(set(df.columns)):
        log.error("%s: missing required columns, got %s", symbol, list(df.columns))
        return False
    if df["Close"].isna().all():
        log.error("%s: all Close values are NaN", symbol)
        return False
    if (df["Close"] <= 0).any():
        log.warning("%s: contains non-positive Close values", symbol)
    return True


def _existing_data_path(symbol: str) -> Path:
    return HISTORICAL_DIR / f"{safe_symbol_filename(symbol)}.csv"


def download_symbol(row: dict, incremental: bool = False,
                     period: str = DEFAULT_PERIOD,
                     interval: str = DEFAULT_INTERVAL) -> bool:
    """Download (or incrementally update) historical data for one symbol row."""
    symbol = row["Symbol"]
    asset_class = row.get("AssetClass", "Equity")
    provider = get_provider_for_asset_class(asset_class)

    if provider != "yfinance":
        log.info("Skipping %s: provider '%s' not yet implemented", symbol, provider)
        return False

    ticker = get_yfinance_ticker(symbol)
    if not ticker:
        log.warning("No ticker mapping found for symbol '%s'; skipping", symbol)
        return False

    out_path = _existing_data_path(symbol)

    dl_period = period
    if incremental and out_path.exists():
        try:
            existing = pd.read_csv(out_path, index_col=0, parse_dates=True)
            if not existing.empty:
                last_date = existing.index.max()
                days_missing = (pd.Timestamp.now() - last_date).days
                if days_missing <= 0:
                    log.info("%s already up to date (last=%s)", symbol, last_date.date())
                    return True
                dl_period = f"{max(days_missing + 2, 5)}d"
        except Exception as exc:  # noqa: BLE001
            log.warning("Could not read existing data for %s (%s); doing full download", symbol, exc)

    df = _download_with_retry(ticker, dl_period, interval)
    if df is None:
        return False

    if not validate_dataframe(df, symbol):
        return False

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

    log.info("Saved %s -> %s (%d rows)", symbol, out_path.name, len(df))
    time.sleep(RATE_LIMIT_SLEEP)
    return True


def download_universe(incremental: bool = False) -> dict:
    """Download historical data for the entire merged universe."""
    universe = load_universe()
    results = {"success": [], "failed": [], "skipped": []}

    for row in universe:
        symbol = row["Symbol"]
        try:
            provider = get_provider_for_asset_class(row.get("AssetClass", "Equity"))
            if provider != "yfinance":
                results["skipped"].append(symbol)
                continue
            ok = download_symbol(row, incremental=incremental)
            (results["success"] if ok else results["failed"]).append(symbol)
        except Exception as exc:  # noqa: BLE001
            log.error("Unexpected error downloading %s: %s", symbol, exc)
            results["failed"].append(symbol)

    log.info(
        "Download complete: %d success, %d failed, %d skipped",
        len(results["success"]), len(results["failed"]), len(results["skipped"]),
    )
    return results


if __name__ == "__main__":
    download_universe(incremental=False)
