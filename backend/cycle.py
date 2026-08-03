"""
factors/cycle.py -- v3.1 S3.3 Cycle (regime) module.

Base signals (spec, verbatim): "trend slope + position percentile +
drawdown-from-high + rate-of-change of volatility." All four already exist
as outputs of the other three factor modules -- this module doesn't
recompute anything from raw prices itself, it composes:
  - trend_result['raw_score']       (trend.py     -- alignment+slope blend, 0-100)
  - position_result['percentile']   (position.py  -- 0-100)
  - volatility_result['current_correction_pct']  (volatility.py -- this IS drawdown-from-high)
  - volatility_result['vol_roc_pct']             (volatility.py -- rate of change of vol)

Regime classification (v1 heuristic -- NOT specified in the methodology
doc beyond the four inputs above; this is a first-pass composite-score
formula, same honesty as trend.py's slope_score constant: "tunable;
S6 backtesting is what should actually calibrate this"):

    composite_score = 0.45*trend_raw + 0.35*position_pctile + 0.20*vol_modifier

  where vol_modifier inverts vol_roc_pct onto a 0-100 scale (falling vol ->
  higher modifier -> more supportive of a bullish-leaning regime; rising vol
  -> lower modifier). Trend gets the most weight (regime is fundamentally a
  trend-context question); Position next (distinguishes e.g. Distribution
  from Bear -- both have negative trend, but Distribution's position is
  still elevated from a recent bull run, Bear's isn't); vol_roc is the
  smallest weight, acting as a modifier rather than a primary driver.

  composite_score buckets into the same 7 phases as the S4 Step-1 raw-score
  table, using the table's own anchor values as band centers:
  Bear=0, Distribution=20, Recovery=40, Accumulation=55, Early Bull=70,
  Bull=85, Late Bull=95 -- thresholds sit at the midpoints between them.

Anti-whipsaw confirmation lag (spec pseudocode, ported directly):
    if raw_regime != confirmed_regime:
        pending_count = pending_count+1 if raw_regime==pending_regime else 1
        pending_regime = raw_regime
        if pending_count >= 3:
            confirmed_regime = raw_regime
    else:
        pending_count = 0
  confirmed_regime is what the frontend displays; raw_regime is stored
  alongside it for backtesting only (spec: check "regime persistence, avg
  weeks per labeled regime" -- if confirmed regimes average <4 weeks, the
  lag needs tightening, S6).

  Cold-start (first-ever observation for a category, no prior state):
  the pseudocode doesn't define this case explicitly. Reasonable reading:
  confirmed_regime = raw_regime immediately -- there's no prior confirmed
  regime to whipsaw against yet, so there's nothing to protect.

WHAT RAW_SCORE MEANS HERE, on purpose: raw_score returned by this module is
the continuous composite_score (0-100), NOT the confirmed_regime's fixed
S4 table value, and it is NOT lagged -- it updates every week same as
trend.py/position.py's raw_score. Only the LABEL (confirmed_regime) is
protected by the 3-week lag. This mirrors trend.py's own precedent (its
raw_score is a continuous blend, richer than the spec's illustrative
5-bucket table) and matches the spec's own framing that the lag exists to
stop the *label* from flickering ("this will visibly damage user trust in
the card"), not to smooth the numeric input to opportunity_score.py.

State persistence: this is the first factor module that needs memory
across runs. State lives in data/state/cycle_state.json, keyed
"group|name" -> {pending_regime, pending_count, confirmed_regime}. Callers
are expected to load_state() once per pipeline run, pass entries through
compute_cycle(), and save_state() once at the end -- not read/write per
category, to avoid partial-write races if the run is interrupted mid-way.
"""

import json
from pathlib import Path
from typing import Optional

CYCLE_LABELS = ['Bear', 'Distribution', 'Recovery', 'Accumulation', 'Early Bull', 'Bull', 'Late Bull']
CYCLE_ANCHORS = {'Bear': 0, 'Distribution': 20, 'Recovery': 40, 'Accumulation': 55,
                  'Early Bull': 70, 'Bull': 85, 'Late Bull': 95}   # S4 Step-1 fixed mapping, used downstream by opportunity_score.py off the LABEL, not derived from composite_score
CONFIRMATION_WEEKS = 3           # spec S3.3 -- 3 consecutive weekly agreements before the displayed label flips
VOL_ROC_CLAMP_PCT = 30.0         # vol_roc_pct beyond +-30% is treated as maximally supportive/unsupportive -- tunable, needs S6 calibration
DEFAULT_STATE_PATH = Path('data/state/cycle_state.json')

# Ordered thresholds (midpoints between consecutive CYCLE_ANCHORS values) for bucketing composite_score
_BUCKET_THRESHOLDS = [10, 30, 47.5, 62.5, 77.5, 90]   # 6 cut points -> 7 bands, matching CYCLE_LABELS order


def bucket_cycle(composite_score: float) -> str:
    for i, threshold in enumerate(_BUCKET_THRESHOLDS):
        if composite_score < threshold:
            return CYCLE_LABELS[i]
    return CYCLE_LABELS[-1]


def _vol_modifier(vol_roc_pct: float) -> float:
    """Falling vol (negative ROC) -> higher modifier (more bullish-supportive); rising vol -> lower."""
    clamped = max(-VOL_ROC_CLAMP_PCT, min(VOL_ROC_CLAMP_PCT, vol_roc_pct))
    return 50 - clamped * (50 / VOL_ROC_CLAMP_PCT)


def compute_raw_regime(trend_result: dict, position_result: dict, volatility_result: dict) -> Optional[dict]:
    """
    Composes the three upstream factor results into this week's raw regime
    + composite_score. Returns None if any upstream module reported
    insufficient_history -- Cycle can't be meaningfully computed on a
    category none of its three inputs could compute on.
    """
    if trend_result.get('insufficient_history') or position_result.get('insufficient_history') or volatility_result.get('insufficient_history'):
        return None

    trend_raw = trend_result['raw_score']
    position_pctile = position_result['percentile']
    vol_roc_pct = volatility_result['vol_roc_pct']

    composite_score = round(
        0.45 * trend_raw + 0.35 * position_pctile + 0.20 * _vol_modifier(vol_roc_pct), 1
    )
    raw_regime = bucket_cycle(composite_score)

    return {
        'raw_regime': raw_regime,
        'composite_score': composite_score,
        'inputs': {
            'trend_raw_score': trend_raw,
            'position_percentile': position_pctile,
            'drawdown_from_high_pct': volatility_result['current_correction_pct'],
            'vol_roc_pct': vol_roc_pct,
        },
    }


def load_state(path: Path = DEFAULT_STATE_PATH) -> dict:
    if not path.exists():
        return {}
    with open(path) as f:
        return json.load(f)


def save_state(state: dict, path: Path = DEFAULT_STATE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w') as f:
        json.dump(state, f, indent=2, sort_keys=True)


def apply_confirmation(entry: Optional[dict], raw_regime: str) -> dict:
    """
    Ports the spec's pseudocode exactly. `entry` is the prior state for this
    one category (None on cold-start -- first observation ever).
    """
    if entry is None:
        # Cold-start: nothing to whipsaw against yet, confirm immediately.
        return {'pending_regime': raw_regime, 'pending_count': 0, 'confirmed_regime': raw_regime}

    pending_regime = entry['pending_regime']
    pending_count = entry['pending_count']
    confirmed_regime = entry['confirmed_regime']

    if raw_regime != confirmed_regime:
        pending_count = pending_count + 1 if raw_regime == pending_regime else 1
        pending_regime = raw_regime
        if pending_count >= CONFIRMATION_WEEKS:
            confirmed_regime = raw_regime
    else:
        pending_count = 0
        pending_regime = confirmed_regime  # clarity only -- spec's pseudocode leaves this stale; doesn't affect confirmed_regime, verified by simulation

    return {'pending_regime': pending_regime, 'pending_count': pending_count, 'confirmed_regime': confirmed_regime}


def compute_cycle(group: str, name: str, trend_result: dict, position_result: dict,
                   volatility_result: dict, state: dict) -> dict:
    """
    `state` is the FULL loaded state dict (all categories) -- this function
    reads/updates only this category's key in it and returns the per-category
    result; the caller is responsible for save_state(state) once, after
    looping over every category (see module docstring re: partial-write races).
    """
    key = f"{group}|{name}"
    raw = compute_raw_regime(trend_result, position_result, volatility_result)

    if raw is None:
        return {
            'label': None, 'raw_regime': None, 'raw_score': None,
            'insufficient_history': True,
        }

    prior_entry = state.get(key)
    updated_entry = apply_confirmation(prior_entry, raw['raw_regime'])
    state[key] = updated_entry  # mutates the passed-in state dict in place

    return {
        'label': updated_entry['confirmed_regime'],     # what the frontend displays
        'raw_score': raw['composite_score'],            # continuous, unlagged -- see module docstring
        'raw_regime': raw['raw_regime'],                 # this week's unconfirmed signal, stored for S6 backtesting only
        'pending_regime': updated_entry['pending_regime'],
        'pending_count': updated_entry['pending_count'],
        'weeks_until_confirm': max(0, CONFIRMATION_WEEKS - updated_entry['pending_count']) if updated_entry['pending_regime'] != updated_entry['confirmed_regime'] else 0,
        'insufficient_history': False,
        'inputs': raw['inputs'],
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

    resolved = [r for r in resolve_all() if r.resolution != 'unresolved'][:5]  # smoke-test a handful
    state = load_state()  # loaded once for the whole run, per module docstring

    for r in resolved:
        try:
            series = get_category_series(r)
            trend_result = compute_trend(series['close'])
            position_result = compute_position(series['close'])
            volatility_result = compute_volatility(series)
            result = compute_cycle(r.group, r.name, trend_result, position_result, volatility_result, state)
            if result['insufficient_history']:
                print(f"{r.group}/{r.name}: insufficient history")
            else:
                print(f"{r.group}/{r.name}: {result['label']} "
                      f"(raw={result['raw_regime']}, score={result['raw_score']}, "
                      f"pending {result['pending_count']}/{CONFIRMATION_WEEKS} -> {result['pending_regime']})")
        except Exception as e:
            print(f"{r.group}/{r.name}: SKIP -- {e}")

    save_state(state)  # once, at the end -- see module docstring
