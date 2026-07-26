#!/usr/bin/env python3
"""
IndiaPulse - Custom Index Builder
Milestone 4 - Data Download Engine

Builds an IndiaPulse Custom Index for symbols where neither a Yahoo
index nor a Yahoo ETF exists (per backend/sources.py, source="CUSTOM").

Method: equal-weight, base-100 rebased composite of the constituent
stocks' daily closes (top-3 market leaders per category -- see the
"symbols" list on each CUSTOM entry in sources.py).

    index_t = 100 * mean( close_i,t / close_i,0 for i in constituents )

This is a downloader concern only: it produces the same standardized
OHLCV-shaped DataFrame the rest of the pipeline expects (Open/High/Low/
Close/Volume), so analytics code never needs to know a given symbol's
history came from a synthetic composite rather than a single ticker.
"""

from __future__ import annotations

import pandas as pd

from backend.logger import get_logger

log = get_logger("custom_index")


def build_equal_weight_index(
    symbols: list[str],
    period: str,
    interval: str,
) -> pd.DataFrame | None:
    """Download each constituent and combine into one equal-weight,
    base-100 composite OHLCV series.

    Returns None if fewer than 2 of the constituents have usable data
    (a 1-stock "index" isn't a meaningful proxy and should be skipped
    rather than silently returned).
    """
    import yfinance as yf

    frames: dict[str, pd.DataFrame] = {}
    for sym in symbols:
        try:
            df = yf.download(sym, period=period, interval=interval,
                              progress=False, auto_adjust=True)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            if df is None or df.empty:
                log.warning("Custom index constituent %s returned no data", sym)
                continue
            frames[sym] = df
        except Exception as exc:  # noqa: BLE001
            log.warning("Custom index constituent %s failed: %s", sym, exc)

    if len(frames) < 2:
        log.error(
            "Not enough constituents with data to build custom index "
            "(%d/%d usable: %s)", len(frames), len(symbols), list(frames)
        )
        return None

    # Align on a common date index (inner join -- only dates all/most
    # constituents traded on) so the composite doesn't fabricate values
    # for a stock that wasn't listed yet.
    closes = pd.DataFrame({sym: f["Close"] for sym, f in frames.items()}).dropna(how="all")
    closes = closes.ffill().dropna()

    if closes.empty:
        log.error("No overlapping trading history across constituents")
        return None

    normalized = closes / closes.iloc[0]
    composite_close = 100 * normalized.mean(axis=1)

    # Build OHLCV-shaped output. True Open/High/Low across a synthetic
    # composite isn't well-defined, so we derive them from the
    # equal-weight composite of each constituent's own O/H/L, and sum
    # Volume as a rough liquidity proxy.
    def _composite(field: str) -> pd.Series:
        vals = pd.DataFrame({sym: f[field] for sym, f in frames.items() if field in f.columns})
        vals = vals.reindex(closes.index).ffill()
        vals_norm = vals / closes.iloc[0]
        return 100 * vals_norm.mean(axis=1)

    out = pd.DataFrame({
        "Open": _composite("Open"),
        "High": _composite("High"),
        "Low": _composite("Low"),
        "Close": composite_close,
    })

    volumes = pd.DataFrame({sym: f["Volume"] for sym, f in frames.items() if "Volume" in f.columns})
    out["Volume"] = volumes.reindex(closes.index).ffill().sum(axis=1)

    out = out.dropna(subset=["Close"])
    return out
