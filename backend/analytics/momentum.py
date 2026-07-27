#!/usr/bin/env python3
"""
Momentum Analytics

Combines RSI, MACD histogram, and Rate of Change into a single
momentum score (0-100).
"""

import pandas as pd

from backend.indicators.rsi import rsi
from backend.indicators.macd import macd
from backend.indicators.returns import rate_of_change
from backend.utils import normalize, clamp
from backend.config import INDICATORS


def compute_momentum(df: pd.DataFrame) -> dict:
    close = df["Close"].dropna()
    if len(close) < 60:
        return {
            "momentum": "Insufficient Data",
            "score": None,
            "data_sufficient": False,
            "rows_available": len(close),
            "rows_required": 60,
        }

    rsi_val = rsi(close, INDICATORS["rsi_period"]).iloc[-1]
    macd_df = macd(close, INDICATORS["macd_fast"], INDICATORS["macd_slow"], INDICATORS["macd_signal"])
    macd_hist = macd_df["Histogram"].iloc[-1]
    roc_val = rate_of_change(close, INDICATORS["roc_period"]).iloc[-1]

    rsi_score = clamp(float(rsi_val))
    macd_score = 100.0 if macd_hist > 0 else 0.0
    roc_score = normalize(float(roc_val), -15, 15)

    score = (rsi_score * 0.4) + (macd_score * 0.3) + (roc_score * 0.3)

    if score >= 65:
        label = "Strong"
    elif score <= 35:
        label = "Weak"
    else:
        label = "Neutral"

    return {
        "momentum": label,
        "score": round(score, 2),
        "data_sufficient": True,
        "rsi": round(float(rsi_val), 2),
        "macd_histogram": round(float(macd_hist), 4),
        "roc": round(float(roc_val), 2),
    }
