#!/usr/bin/env python3
"""
Seasonality Analytics (Core Feature)

Builds a normalized Seasonal Index per calendar month for a symbol by
analyzing historical monthly returns across many years, with outlier
removal to reduce distortion.
"""

import numpy as np
import pandas as pd

from backend.indicators.returns import monthly_returns
from backend.config import SEASONALITY
from backend.utils import normalize


def _remove_outliers(values: pd.Series, std_threshold: float) -> pd.Series:
    mean = values.mean()
    std = values.std()
    if std == 0 or np.isnan(std):
        return values
    return values[(values - mean).abs() <= std_threshold * std]


def build_seasonal_index(close: pd.Series) -> dict:
    """
    Returns per-month average return (outlier-trimmed) and a 0-100
    seasonal score for the *current* calendar month.

    Returns score=None (not a fabricated neutral 50) when there's no
    monthly-return history at all, or when there's less history than
    SEASONALITY['min_years'] -- a seasonal average built from only 1-2
    years isn't statistically reliable enough to rank a symbol on.
    """
    m_returns = monthly_returns(close).dropna()
    if m_returns.empty:
        return {"seasonality": "Insufficient Data", "score": None, "data_sufficient": False,
                "years_covered": 0}

    years_covered = m_returns.index.year.nunique()
    df = m_returns.to_frame("ret")
    df["month"] = df.index.month

    monthly_avg = {}
    std_threshold = SEASONALITY["outlier_std_threshold"]
    for month in range(1, 13):
        month_vals = df.loc[df["month"] == month, "ret"]
        if month_vals.empty:
            continue
        trimmed = _remove_outliers(month_vals, std_threshold)
        monthly_avg[month] = float(trimmed.mean()) if not trimmed.empty else float(month_vals.mean())

    if not monthly_avg:
        return {"seasonality": "Insufficient Data", "score": None, "data_sufficient": False,
                "years_covered": int(years_covered)}

    min_years = SEASONALITY["min_years"]
    if years_covered < min_years:
        return {
            "seasonality": "Insufficient Data",
            "score": None,
            "data_sufficient": False,
            "years_covered": int(years_covered),
            "years_required": min_years,
            "monthly_index": {str(k): round(v, 2) for k, v in monthly_avg.items()},
        }

    all_vals = list(monthly_avg.values())
    current_month = pd.Timestamp.now().month
    current_avg = monthly_avg.get(current_month, 0.0)
    score = normalize(current_avg, min(all_vals), max(all_vals))

    if score >= 65:
        label = "Seasonally Strong"
    elif score <= 35:
        label = "Seasonally Weak"
    else:
        label = "Seasonally Neutral"

    return {
        "seasonality": label,
        "score": round(score, 2),
        "data_sufficient": True,
        "years_covered": int(years_covered),
        "current_month_avg_return_pct": round(current_avg, 2),
        "monthly_index": {str(k): round(v, 2) for k, v in monthly_avg.items()},
    }
