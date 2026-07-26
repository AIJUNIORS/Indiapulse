#!/usr/bin/env python3
"""
Valuation Analytics

Milestone note: PE / PB / dividend-yield data is not yet part of the
download pipeline (Phase 5+ will add a fundamentals provider). Until
then this module exposes the interface and returns a neutral score so
the Opportunity Score can already be computed end-to-end.
"""


def compute_valuation(pe: float | None = None, pb: float | None = None,
                       dividend_yield: float | None = None,
                       sector_avg_pe: float | None = None) -> dict:
    if pe is None or sector_avg_pe is None:
        return {"valuation": "No Data", "score": 50.0}

    # Cheaper relative to sector average -> higher score
    ratio = pe / sector_avg_pe if sector_avg_pe else 1.0
    score = max(0.0, min(100.0, (2 - ratio) * 50))

    if score >= 65:
        label = "Undervalued"
    elif score <= 35:
        label = "Overvalued"
    else:
        label = "Fair Value"

    return {
        "valuation": label,
        "score": round(score, 2),
        "pe": pe,
        "pb": pb,
        "dividend_yield": dividend_yield,
    }
