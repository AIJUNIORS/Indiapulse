#!/usr/bin/env python3
"""
Volatility Analytics

ATR, historical (rolling) volatility, and maximum drawdown.
"""

import numpy as np
import pandas as pd

from backend.indicators.atr import atr
from backend.indicators.returns import log_returns
from backend.config import INDICATORS


def max_drawdown(close: pd.Series) -> float:
    cumulative_max = close.cummax()
    drawdown = (close - cumulative_max) / cumulative_max
    return float(drawdown.min() * 100)


def compute_volatility(df: pd.DataFrame) -> dict:
    close = df["Close"].dropna()
    if len(close) < 30:
        return {"volatility": "Insufficient Data", "score": 50.0}

    atr_val = atr(df["High"], df["Low"], df["Close"], INDICATORS["atr_period"]).iloc[-1]
    returns = log_returns(close).dropna()
    hist_vol = float(returns.tail(21).std() * np.sqrt(252) * 100)
    dd = max_drawdown(close)

    # Lower volatility -> higher "stability" score
    score = max(0.0, 100 - hist_vol)

    if hist_vol >= 35:
        label = "High"
    elif hist_vol <= 15:
        label = "Low"
    else:
        label = "Moderate"

    return {
        "volatility": label,
        "score": round(score, 2),
        "atr": round(float(atr_val), 2),
        "annualized_vol_pct": round(hist_vol, 2),
        "max_drawdown_pct": round(dd, 2),
    }
