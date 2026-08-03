"""
factors/structure_score.py -- the 'structure' field the frontend renders
directly (structLabel bucketing, drives stanceFor() alongside opportunity).
Architecture doc describes it as "Technical-only composite (Trend+Position+
Cycle+Volatility, percentile-blended)" but no module actually produced it --
this is that module.

Weighting (v1, NOT spec'd beyond "percentile-blended" -- same honesty as
cycle.py's composite_score weights and trend.py's slope_score constant:
tunable, needs S6 backtest validation before being treated as final):

    structure = 0.30*trend_raw + 0.25*position_raw + 0.25*cycle_raw + 0.20*volatility_raw

Equal-ish weighting on purpose -- unlike cycle.py (which deliberately
weights trend heaviest because regime IS fundamentally a trend question),
structure is meant to be a general "how healthy does this category's
technical picture look" read, so no single input dominates. Cycle's
raw_score here is its continuous composite_score (0-100, unlagged) per
cycle.py's own module docstring -- not the confirmed_regime label.

All four inputs are already 0-100 scores from their own modules, so this
is a straight weighted average, not a re-percentiled blend -- "percentile-
blended" in the architecture doc is read here as "each input is already a
percentile-like 0-100 score," not as an instruction to re-rank across
categories (that would need every category's score computed first, which
would make this module a whole-universe batch step rather than a
per-category one; not what any of the other factor modules do).
"""

from typing import Optional

WEIGHTS = {'trend': 0.30, 'position': 0.25, 'cycle': 0.25, 'volatility': 0.20}


def compute_structure(trend_result: dict, position_result: dict,
                       cycle_result: dict, volatility_result: dict) -> dict:
    """
    Returns None-safe dict with 'score' (0-100, rounded 1dp) or
    insufficient_history=True if any input couldn't be computed --
    structure can't be meaningfully read off a partial stack, same
    precedent as cycle.py's own upstream-insufficiency check.
    """
    if (trend_result.get('insufficient_history') or position_result.get('insufficient_history')
            or cycle_result.get('insufficient_history') or volatility_result.get('insufficient_history')):
        return {'score': None, 'insufficient_history': True}

    score = round(
        WEIGHTS['trend'] * trend_result['raw_score']
        + WEIGHTS['position'] * position_result['raw_score']
        + WEIGHTS['cycle'] * cycle_result['raw_score']
        + WEIGHTS['volatility'] * volatility_result['raw_score'],
        1,
    )
    return {
        'score': max(0.0, min(100.0, score)),
        'insufficient_history': False,
        'inputs': {
            'trend_raw_score': trend_result['raw_score'],
            'position_raw_score': position_result['raw_score'],
            'cycle_raw_score': cycle_result['raw_score'],
            'volatility_raw_score': volatility_result['raw_score'],
        },
    }


if __name__ == '__main__':
    import sys
    sys.path.insert(0, '.')
    import price_cache
    from data_hierarchy import resolve_all
    from composite_builder import get_category_series
    from trend import compute_trend
    from position import compute_position
    from volatility import compute_volatility
    from cycle import compute_cycle, load_state, save_state

    resolved = [r for r in resolve_all() if r.resolution != 'unresolved'][:5]
    state = load_state()
    for r in resolved:
        try:
            series = get_category_series(r)
            trend_result = compute_trend(series['close'])
            position_result = compute_position(series['close'])
            volatility_result = compute_volatility(series)
            cycle_result = compute_cycle(r.group, r.name, trend_result, position_result, volatility_result, state)
            result = compute_structure(trend_result, position_result, cycle_result, volatility_result)
            print(f"{r.group}/{r.name}: structure={result.get('score')}")
        except Exception as e:
            print(f"{r.group}/{r.name}: SKIP -- {e}")
    save_state(state)
