"""
scoring/opportunity_score.py -- v3.1 S4 Opportunity Score.

The real fix the architecture doc flags: today the frontend sets
`opportunity = structure` (Opportunity Score = Market Structure Score only).
This module produces the actual blend: structure + business + seasonality,
still landing in the same `opportunity` slot the frontend already knows how
to render (stanceFor()'s >=80/>=60/>=40 thresholds), so no frontend change.

Weighting (v1 -- the source docs describe *what* feeds the blend, not the
exact split; same tunable-pending-S6-backtest framing as every weighted
constant elsewhere in this codebase):

    opportunity = 0.60*structure + 0.20*business + 0.20*seasonality

Structure gets the majority weight -- it's the richest input (itself
already a 4-way blend of Trend/Position/Cycle/Volatility) and the one
available for every category. Business and seasonality get equal, smaller
weights as context layers on top.

Missing-component handling: business_score.py correctly returns None for
categories outside the curated calendar's scope (Broad Market, Market Cap,
Strategy, Global Markets, Innovation, Logistics -- not a data gap). Rather
than silently scoring a "0" for business in that case (which would drag
every out-of-scope category's opportunity down for no real reason),
weights are redistributed proportionally across whichever components ARE
available for that category. A category with no business coverage still
gets a fully-formed opportunity score from structure+seasonality alone,
just as the frontend's existing '--' fallback already treats "out of
scope" as a clean non-event rather than a penalty.

flag=='context'/'currency' categories (India VIX, USD/INR, etc.) get
opportunity=None outright, exactly matching the frontend's current
`flag==='context' ? null : structure` line -- these aren't investable
categories, there's nothing to score.
"""

from typing import Optional

WEIGHTS = {'structure': 0.60, 'business': 0.20, 'seasonality': 0.20}


def compute_opportunity(structure_score: Optional[float], business_fundamental: Optional[int],
                          seasonality_raw_score: Optional[float], flag: Optional[str] = None) -> Optional[float]:
    """
    structure_score: 0-100, from structure_score.compute_structure()['score'].
    business_fundamental: 1-5 stars, from business_score.compute_effective_business_score()
        (None if out of curated scope) -- rescaled to 0-100 here (1->0, 5->100)
        so it sits on the same scale as the other two inputs before blending.
    seasonality_raw_score: 0-100, from seasonality.compute_seasonality_score()['raw_score'].
    flag: category's context/currency flag, if any -- context/currency instruments
        aren't scored at all, matching the frontend's existing null-out logic.
    """
    if flag in ('context', 'currency'):
        return None
    if structure_score is None:
        return None  # can't score a category whose technical stack is insufficient-history

    components = {'structure': structure_score}
    if business_fundamental is not None:
        components['business'] = (business_fundamental - 1) / 4 * 100  # 1-5 -> 0-100
    if seasonality_raw_score is not None:
        components['seasonality'] = seasonality_raw_score

    total_weight = sum(WEIGHTS[k] for k in components)
    blended = sum(WEIGHTS[k] * v for k, v in components.items()) / total_weight
    return round(max(0.0, min(100.0, blended)), 1)


if __name__ == '__main__':
    # structure-only (out-of-scope business, no seasonality edge case)
    print("Full inputs:", compute_opportunity(72.5, 4, 61.0))
    print("No business coverage:", compute_opportunity(72.5, None, 61.0))
    print("Context flag:", compute_opportunity(72.5, 4, 61.0, flag='context'))
    print("Insufficient structure:", compute_opportunity(None, 4, 61.0))
