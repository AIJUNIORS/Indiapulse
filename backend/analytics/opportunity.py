#!/usr/bin/env python3
"""
Opportunity Scoring Engine (Phase 7)

Combines Seasonality (35%), Macro Cycle (30%), Momentum (20%), and
Valuation (15%) into a single 0-100 Opportunity Score, as agreed in
the IndiaPulse project blueprint.

Missing-data handling:
- Valuation is expected to be missing for every symbol today (no
  fundamentals provider yet -- see valuation.py). That's a *known,
  global* gap, not a symbol-specific problem, so rather than silently
  treating it as a neutral 50 (which quietly drags every score toward
  the middle), its 15% weight is redistributed proportionally across
  whichever components ARE available. This is the "proxy" fix: instead
  of assuming valuation, we size the pie by what we actually know.
- Seasonality, Momentum, and Macro Cycle are the real, symbol-specific,
  price-history-derived inputs. If any of *those* is missing (typically
  because a ticker has too little price history), there isn't enough
  real signal to responsibly produce a composite score at all -- so
  this returns score=None and rating="Insufficient Data" rather than
  fabricating a number that would silently tie with a dozen other
  unrelated symbols at some arbitrary value.
"""

from backend.config import OPPORTUNITY_WEIGHTS

# Which components are "always eventually available" vs which are
# treated as an acceptable, expected long-term gap (Phase 5+ only).
REQUIRED_COMPONENTS = ("seasonality", "macro_cycle", "momentum")
OPTIONAL_COMPONENTS = ("valuation",)


def compute_opportunity_score(seasonality_score: float | None, cycle_score: float | None,
                               momentum_score: float | None, valuation_score: float | None) -> dict:
    raw = {
        "seasonality": seasonality_score,
        "macro_cycle": cycle_score,
        "momentum": momentum_score,
        "valuation": valuation_score,
    }

    missing_required = [name for name in REQUIRED_COMPONENTS if raw[name] is None]
    if missing_required:
        return {
            "opportunity_score": None,
            "rating": "Insufficient Data",
            "data_sufficient": False,
            "missing_components": missing_required,
            "components": raw,
            "weights": OPPORTUNITY_WEIGHTS,
        }

    # Only optional components (valuation, today) may be missing past
    # this point. Redistribute their configured weight proportionally
    # across whichever components have a real value.
    available = {name: raw[name] for name in raw if raw[name] is not None}
    base_weights = {name: OPPORTUNITY_WEIGHTS[name] for name in available}
    weight_total = sum(base_weights.values())
    effective_weights = {name: w / weight_total for name, w in base_weights.items()}

    score = sum(available[name] * effective_weights[name] for name in available)
    score = round(min(100.0, max(0.0, score)), 2)

    if score >= 70:
        label = "High Opportunity"
    elif score <= 40:
        label = "Low Opportunity"
    else:
        label = "Moderate Opportunity"

    excluded = [name for name in OPTIONAL_COMPONENTS if raw[name] is None]

    return {
        "opportunity_score": score,
        "rating": label,
        "data_sufficient": True,
        "excluded_components": excluded,
        "components": raw,
        "weights": OPPORTUNITY_WEIGHTS,
        "effective_weights": {k: round(v, 4) for k, v in effective_weights.items()},
    }
