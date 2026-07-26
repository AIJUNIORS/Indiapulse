#!/usr/bin/env python3
"""
Analytics Summary

Assembles all per-symbol analytics (trend, momentum, volatility, risk,
seasonality, valuation, opportunity) into a single result dict, ready
for JSON export to the frontend.
"""

import pandas as pd

from backend.analytics.trend import compute_trend
from backend.analytics.momentum import compute_momentum
from backend.analytics.volatility import compute_volatility
from backend.analytics.risk import compute_risk
from backend.analytics.seasonality import build_seasonal_index
from backend.analytics.valuation import compute_valuation
from backend.analytics.opportunity import compute_opportunity_score
from backend.analytics.cycle import compute_cycle
from backend.analytics.validation import validate_symbol_result


def summarize_symbol(symbol: str, df: pd.DataFrame, category: str = "",
                      macro_cycle_result: dict | None = None) -> dict:
    """Compute the full analytics stack for a single symbol's OHLCV data."""
    trend = compute_trend(df)
    momentum = compute_momentum(df)
    volatility = compute_volatility(df)
    risk = compute_risk(volatility)
    seasonality = build_seasonal_index(df["Close"].dropna())
    valuation = compute_valuation()  # neutral until fundamentals provider exists
    cycle = macro_cycle_result or {"cycle_stage": "Unknown", "score": 50.0}

    opportunity = compute_opportunity_score(
        seasonality_score=seasonality.get("score", 50.0),
        cycle_score=cycle.get("score", 50.0),
        momentum_score=momentum.get("score", 50.0),
        valuation_score=valuation.get("score", 50.0),
    )

    result = {
        "symbol": symbol,
        "category": category,
        "trend": trend,
        "momentum": momentum,
        "volatility": volatility,
        "risk": risk,
        "seasonality": seasonality,
        "valuation": valuation,
        "cycle": cycle,
        "opportunity": opportunity,
    }

    errors = validate_symbol_result(result)
    if errors:
        result["validation_errors"] = errors

    return result
