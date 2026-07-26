#!/usr/bin/env python3
"""
Breadth Analytics

Cross-sectional participation metrics computed across a group of
constituents' trend scores (e.g. all sectors, or all broad-market
indices). This is applied at the "market" or "group" level rather
than to a single symbol.
"""

from __future__ import annotations


def compute_breadth(trend_scores: list[float]) -> dict:
    """
    trend_scores: list of 0-100 trend scores (one per constituent).
    """
    if not trend_scores:
        return {"breadth": "Insufficient Data", "score": 50.0}

    above_50 = sum(1 for s in trend_scores if s >= 50)
    pct_bullish = (above_50 / len(trend_scores)) * 100

    if pct_bullish >= 65:
        label = "Strong Breadth"
    elif pct_bullish <= 35:
        label = "Weak Breadth"
    else:
        label = "Mixed Breadth"

    return {
        "breadth": label,
        "score": round(pct_bullish, 2),
        "constituents": len(trend_scores),
        "pct_above_50": round(pct_bullish, 2),
    }
