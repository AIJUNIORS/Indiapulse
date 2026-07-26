#!/usr/bin/env python3
"""
Opportunity Scoring Engine (Phase 7)

Combines Seasonality (35%), Macro Cycle (30%), Momentum (20%), and
Valuation (15%) into a single 0-100 Opportunity Score, as agreed in
the IndiaPulse project blueprint.
"""

from backend.config import OPPORTUNITY_WEIGHTS


def compute_opportunity_score(seasonality_score: float, cycle_score: float,
                               momentum_score: float, valuation_score: float) -> dict:
    weights = OPPORTUNITY_WEIGHTS
    score = (
        seasonality_score * weights["seasonality"]
        + cycle_score * weights["macro_cycle"]
        + momentum_score * weights["momentum"]
        + valuation_score * weights["valuation"]
    )
    score = round(min(100.0, max(0.0, score)), 2)

    if score >= 70:
        label = "High Opportunity"
    elif score <= 40:
        label = "Low Opportunity"
    else:
        label = "Moderate Opportunity"

    return {
        "opportunity_score": score,
        "rating": label,
        "components": {
            "seasonality": seasonality_score,
            "macro_cycle": cycle_score,
            "momentum": momentum_score,
            "valuation": valuation_score,
        },
        "weights": weights,
    }
