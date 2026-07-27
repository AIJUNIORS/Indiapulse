#!/usr/bin/env python3
"""
Trend Analytics

Classifies price trend as Bullish / Neutral / Bearish using moving
average alignment and price position relative to key MAs.
"""

import pandas as pd

from backend.indicators.moving_average import sma
from backend.config import INDICATORS


def compute_trend(df: pd.DataFrame) -> dict:
    """
    df must contain a 'Close' column with a DatetimeIndex.
    Returns a dict describing the current trend state.

    When there isn't enough history to compute the 200-day SMA
    reliably, this returns score=None (not a fabricated neutral 50) so
    downstream code (opportunity.py, export.py) can tell the difference
    between "genuinely neutral" and "we don't actually know yet."
    """
    close = df["Close"].dropna()
    if len(close) < 210:
        return {
            "trend": "Insufficient Data",
            "score": None,
            "data_sufficient": False,
            "rows_available": len(close),
            "rows_required": 210,
        }

    sma20 = sma(close, 20).iloc[-1]
    sma50 = sma(close, 50).iloc[-1]
    sma100 = sma(close, 100).iloc[-1]
    sma200 = sma(close, 200).iloc[-1]
    price = close.iloc[-1]

    checks = [
        price > sma20,
        sma20 > sma50,
        sma50 > sma100,
        sma100 > sma200,
        price > sma200,
    ]
    bullish_count = sum(checks)
    score = (bullish_count / len(checks)) * 100

    if score >= 70:
        label = "Bullish"
    elif score <= 30:
        label = "Bearish"
    else:
        label = "Neutral"

    return {
        "trend": label,
        "score": round(score, 2),
        "data_sufficient": True,
        "price": round(float(price), 2),
        "sma20": round(float(sma20), 2),
        "sma50": round(float(sma50), 2),
        "sma100": round(float(sma100), 2),
        "sma200": round(float(sma200), 2),
    }
