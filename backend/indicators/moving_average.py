#!/usr/bin/env python3
"""Moving average indicators: SMA and EMA."""

import pandas as pd


def sma(series: pd.Series, period: int) -> pd.Series:
    """Simple Moving Average."""
    return series.rolling(window=period, min_periods=period).mean()


def ema(series: pd.Series, period: int) -> pd.Series:
    """Exponential Moving Average."""
    return series.ewm(span=period, adjust=False, min_periods=period).mean()


def compute_all_mas(close: pd.Series, sma_periods: list[int], ema_periods: list[int]) -> pd.DataFrame:
    """Compute a DataFrame of SMA/EMA columns for the given periods."""
    out = pd.DataFrame(index=close.index)
    for p in sma_periods:
        out[f"SMA_{p}"] = sma(close, p)
    for p in ema_periods:
        out[f"EMA_{p}"] = ema(close, p)
    return out
