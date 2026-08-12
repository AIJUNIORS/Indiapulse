"""
serializer.py -- v3.1 architecture doc S4/S7: writes the three JSON files
the frontend's boot() fetches -- data/computed.json, data/seasonality.json,
data/annual.json -- keyed exactly the way the frontend looks them up
(`COMPUTED_DATA[group]?.[name]`, `SEASONALITY_DATA[group]?.[name]?.[month]?.[lookback]`).

Two format details that matter and are easy to get wrong (see the earlier
review): seasonality.py's compute_monthly_stats() takes an integer
month_idx (0-11), but the frontend's seasonStats(group,name,month,...)
calls with the MONTH NAME string ('Jan'..'Dec') -- see the mockup's
`const month = MONTHS[monthIdx]` at its one call site. This module keys
seasonality.json by month name, not index, to match. Similarly,
compute_annual_return() returns a dict ({'meanAnnualReturn','n',
'effectiveYears','capped'}), but the frontend consumes annualReturn() as a
plain number (`const ann = annualReturn(...)`) -- this module unwraps to
just the scalar before writing annual.json.
"""

import json
from pathlib import Path
from typing import Optional

import pandas as pd

from seasonality import compute_monthly_stats, compute_annual_return

MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
LOOKBACKS = [1, 3, 5, 10, 20, 'Max']   # matches the frontend's LOOKBACKS array exactly, including the 'Max' literal

DATA_DIR = Path('data')


def _lookback_key(lb) -> str:
    """JSON object keys must be strings; the frontend's <select> values are already strings ('1','3',...,'Max')."""
    return str(lb)


def _data_status(trend_result: dict, position_result: dict, volatility_result: dict,
                  technicals: dict) -> Optional[dict]:
    """
    Surfaces a 'building history' progress readout for the frontend when
    ANY factor module is still below its own minimum-weeks bar, instead of
    silently discarding the weeks_available/weeks_required every module
    already computes (see trend.py/position.py/volatility.py/technicals.py
    -- this data existed all along, it just never left build_computed_entry()
    before). Returns None when every module cleared its floor -- category
    has full data, no banner needed.

    Reports the SLOWEST-clearing module (max weeks_required, since that's
    the actual bottleneck a category is waiting on -- e.g. Position clears
    at 8 weeks but Trend needs 45, so a category with 20 weeks cached is
    "building" against Trend's bar, not Position's) alongside the minimum
    weeks_available across modules that did report a number (a module that
    computed successfully doesn't cap the reported progress; only ones
    that are still insufficient do).
    """
    parts = [trend_result, position_result, volatility_result, technicals]
    insufficient = [p for p in parts if p.get('insufficient_history')]
    if not insufficient:
        return None
    weeks_available = min(p.get('weeks_available', 0) for p in insufficient)
    weeks_required = max(p.get('weeks_required', 0) for p in insufficient)
    return {
        'status': 'building',
        'weeksAvailable': weeks_available,
        'weeksRequired': weeks_required,
        'pctComplete': round(100 * weeks_available / weeks_required, 1) if weeks_required else 0.0,
    }


def build_computed_entry(technicals: dict, structure: dict, business: Optional[dict],
                          trend_result: dict, cycle_result: dict, volatility_result: dict,
                          position_result: dict, opportunity: Optional[float],
                          arrow: Optional[tuple] = None, accel: Optional[tuple] = None,
                          exhaustion: Optional[tuple] = None) -> dict:
    """
    One category's entry in computed.json -- field names match CATEGORIES'
    numeric inputs exactly (structure, fundamental, contra, trend, cycle,
    vol, opportunity, rsi, smi, atrPct, trendPct, pivotDist, posPct, arrow,
    accel, exhaustion). Label fields (rsiInterp, structLabel, posInterp,
    etc.) are NOT included -- those stay frontend-side bucketing logic per
    the architecture doc's own split table, computed off these raw numbers,
    unchanged. arrow/accel/exhaustion ARE serialized as their [label, css_class]
    tuples directly -- momentum_signals.py already returns them pre-bucketed
    in that exact 2-element shape, same as the frontend's own ARROWS/ACCEL/
    EXH_LEVELS arrays, so no extra bucketing step is needed on either side.

    dataStatus is new: {'status':'building','weeksAvailable':N,'weeksRequired':M,
    'pctComplete':P} when a category is still accumulating history below one or
    more modules' floors, None once every module has cleared its bar. Lets the
    frontend distinguish "actively building, N/M weeks in" from a genuine fetch
    failure or a category that will never have this data (context/currency flags) --
    previously both rendered as the exact same blank 'Insufficient History'.
    """
    return {
        'structure': structure.get('score'),
        'fundamental': business['fundamental'] if business else None,
        'contra': business['contra'] if business else None,
        'trend': trend_result.get('label'),
        'cycle': cycle_result.get('label'),
        'vol': volatility_result.get('label'),
        'opportunity': opportunity,
        'rsi': technicals.get('rsi'),
        'smi': technicals.get('smi'),
        'atrPct': technicals.get('atrPct'),
        'trendPct': technicals.get('trendPct'),
        'pivotDist': technicals.get('pivotDist'),
        'posPct': position_result.get('percentile'),
        'arrow': list(arrow) if arrow else None,
        'accel': list(accel) if accel else None,
        'exhaustion': list(exhaustion) if exhaustion else None,
        'dataStatus': _data_status(trend_result, position_result, volatility_result, technicals),
    }


def build_seasonality_grid(daily_close: pd.Series, history_years: float) -> dict:
    """{month_name: {lookback_str: stats_dict}} -- full 12 x 6 grid, per the
    frontend's computedSeasonState()/monthReturnRank() which rank the
    CURRENT month against all 11 others, so every month must be present,
    not just the current one."""
    grid = {}
    for month_idx, month_name in enumerate(MONTHS):
        grid[month_name] = {
            _lookback_key(lb): compute_monthly_stats(daily_close, month_idx, lb, history_years)
            for lb in LOOKBACKS
        }
    return grid


def null_seasonality_grid() -> dict:
    """
    Same 12 x 6 shape as build_seasonality_grid(), but every cell is the
    honest zero-observation stats dict compute_monthly_stats() itself
    returns when n==0 (mean/median 0.0, positivePct/stdDev None, n=0).
    For use when a category has NO price series to compute on at all --
    e.g. pipeline.py's except block, when get_category_series() raised
    before any real computation happened.

    quality_guard.check_seasonality_grid_shape() only validates SHAPE
    (12 months, 6 lookbacks each), not cell contents, so without this the
    only alternative was omitting the category's seasonality.json entry
    entirely -- which check_seasonality_grid_shape flags as a blocking
    issue and aborts the ENTIRE deploy (all groups), not just this one
    category. Null-filling with the correct shape here lets one broken
    category degrade gracefully (as computed.json's dataStatus already
    does) instead of taking every other category down with it.
    """
    zero_cell = {'mean': 0.0, 'median': 0.0, 'positivePct': None, 'stdDev': None,
                 'n': 0, 'effectiveYears': 0.0, 'capped': False}
    return {month_name: {_lookback_key(lb): dict(zero_cell) for lb in LOOKBACKS} for month_name in MONTHS}


def null_annual_grid() -> dict:
    """Same reasoning as null_seasonality_grid() -- matching shape for annual.json
    ({lookback_str: 0.0}), so a category that crashed before computing anything
    still passes quality_guard's shape checks instead of blocking every other
    category's deploy."""
    return {_lookback_key(lb): 0.0 for lb in LOOKBACKS}


def build_annual_grid(daily_close: pd.Series, history_years: float) -> dict:
    """{lookback_str: meanAnnualReturn} -- unwrapped scalar, see module docstring."""
    return {
        _lookback_key(lb): compute_annual_return(daily_close, lb, history_years)['meanAnnualReturn']
        for lb in LOOKBACKS
    }


def _nested_set(store: dict, group: str, name: str, value) -> None:
    store.setdefault(group, {})[name] = value


def write_json_files(computed: dict, seasonality: dict, annual: dict, out_dir: Path = DATA_DIR) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for filename, payload in (('computed.json', computed), ('seasonality.json', seasonality), ('annual.json', annual)):
        with open(out_dir / filename, 'w') as f:
            json.dump(payload, f, indent=2, sort_keys=True)
