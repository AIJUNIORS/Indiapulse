"""
factors/position.py -- v3.1 S3.2 Position module.

Method: percentile rank of the current price within a fixed rolling window
-- 5 years, or since-inception if the category has less than 5 years of
history (spec: "Lookback window: fixed rolling 5 years, or since-inception
if <5Y of data exists. This must be pinned globally -- do not let it float
per-category, or quartile outputs become incomparable across cards.").

Weekly cadence, matching trend.py -- Position is compared against Trend in
the Cycle module (S3.3) and shown alongside it throughout the frontend, so
both need to be computed on the same resampled series or the two numbers
would be silently talking about different timeframes.

raw_score is the percentile itself, unmodified -- the S4 Step-1 mapping
table says so explicitly ("Position | percentile | raw = percentile
directly (0-100)"), unlike Trend/Cycle/Volatility which need a categorical
-> numeric lookup first. Position is the one factor where the raw score
and the human-facing number are the same value.

Percentile definition: (count of in-window closes <= current close) /
(window length) * 100. Current close is included in its own window, so a
brand-new all-time-high always reads exactly 100, not slightly under it.
"""

from typing import Optional

import pandas as pd

POSITION_LABELS = ['Near ATL', 'Lower Quartile', 'Middle', 'Upper Quartile', 'Near ATH']
LOOKBACK_WEEKS = 260          # 5 years @ ~52.18 weeks/year, rounded down -- the pinned global window
MIN_WEEKS_REQUIRED = 8        # below this, "percentile within window" isn't a meaningful statement


def bucket_position(percentile: float) -> str:
    """
    Mirrors the frontend's existing posInterp thresholds exactly (posPct>=90
    'Near ATH' / >=65 'Upper Quartile' / >=35 'Middle' / >=15 'Lower Quartile'
    / else 'Near ATL') -- the frontend keeps its own copy of this bucketing
    per the architecture doc ("stays in frontend unchanged"), but the backend
    module labels independently too, on the same thresholds, so the two never
    silently drift apart if one gets edited without the other.
    """
    if percentile >= 90:
        return 'Near ATH'
    if percentile >= 65:
        return 'Upper Quartile'
    if percentile >= 35:
        return 'Middle'
    if percentile >= 15:
        return 'Lower Quartile'
    return 'Near ATL'


def compute_position(daily_close: pd.Series, lookback_weeks: int = LOOKBACK_WEEKS) -> dict:
    """
    daily_close: pd.Series of close prices, indexed by date (from
    composite_builder.get_category_series(resolved)['close']).
    """
    weekly = daily_close.resample('W-FRI').last().dropna()

    if len(weekly) < MIN_WEEKS_REQUIRED:
        return {
            'label': None, 'raw_score': None, 'percentile': None,
            'insufficient_history': True,
            'weeks_available': len(weekly), 'weeks_required': MIN_WEEKS_REQUIRED,
        }

    since_inception = len(weekly) < lookback_weeks
    window = weekly if since_inception else weekly.iloc[-lookback_weeks:]

    current = window.iloc[-1]
    percentile = round(float((window <= current).sum()) / len(window) * 100, 1)
    label = bucket_position(percentile)

    return {
        'label': label,
        'raw_score': percentile,        # S4 Step-1: Position raw score IS the percentile, unmodified
        'percentile': percentile,
        'insufficient_history': False,
        'weeks_available': len(weekly),
        'window_weeks_used': len(window),
        'window_years_used': round(len(window) / 52.1775, 1),
        'since_inception': since_inception,   # True if <5Y history -- window fell back per spec, not a full 5Y read
        'price': round(float(current), 2),
        'window_high': round(float(window.max()), 2),
        'window_low': round(float(window.min()), 2),
    }


if __name__ == '__main__':
    import sys
    sys.path.insert(0, '.')
    import price_cache
    from data_hierarchy import resolve_all
    from composite_builder import get_category_series

    resolved = [r for r in resolve_all() if r.resolution != 'unresolved'][:5]  # smoke-test a handful
    for r in resolved:
        try:
            series = get_category_series(r)
            result = compute_position(series['close'])
            window_note = 'since-inception' if result.get('since_inception') else f"{result.get('window_years_used')}y window"
            print(f"{r.group}/{r.name}: {result.get('label')} (pctile={result.get('percentile')}, {window_note}, "
                  f"weeks={result.get('weeks_available')})")
        except Exception as e:
            print(f"{r.group}/{r.name}: SKIP -- {e}")
