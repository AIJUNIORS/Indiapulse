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
