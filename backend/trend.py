"""
factors/trend.py -- v3.1 S3.1 Trend module.

Method: multi-timeframe weekly EMA stack (10w/30w/40w) + slope of the 30w
EMA. Weekly cadence is primary per spec ("similar in spirit to the
CONTRA/MTRSIE architecture already built... applied at weekly cadence for
investing rather than trading horizon"); daily is only used elsewhere for
the "latest tactical" overlay (that's the daily-refresh workflow's job, not
this module's -- this module always resamples to weekly).

Scoring (raw_score, 0-100), transparent and testable in two parts:
  1. Stack alignment (70% weight) -- price vs EMA10w vs EMA30w vs EMA40w,
     three pairwise comparisons, each +1/-1 -> normalized to 0-100.
     This is the dominant signal: a fully-aligned bullish stack
     (price > 10w > 30w > 40w) scores 100 on this component regardless of
     how fast it's moving.
  2. Slope of the 30w EMA over the trailing 10 weeks (30% weight) --
     acts as a tiebreaker/momentum adjustment within a given alignment,
     so two categories with the same stack ordering but different velocity
     don't score identically.

Bucketing anchors match the methodology's Step-1 raw-score mapping table
(Strong Bear=0, Bear=25, Sideways=50, Bull=75, Strong Bull=100) --
raw_score is split into five equal 20-point bands.
"""

from typing import Optional

import pandas as pd

TREND_LABELS = ['Strong Bear', 'Bear', 'Sideways', 'Bull', 'Strong Bull']
MIN_WEEKS_REQUIRED = 45  # 40w EMA + buffer for the slope lookback to be meaningful


def bucket_trend(raw_score: float) -> str:
    idx = min(4, max(0, int(raw_score // 20)))
    return TREND_LABELS[idx]


def compute_trend(daily_close: pd.Series, slope_lookback_weeks: int = 10) -> dict:
    """
    daily_close: pd.Series of close prices, indexed by date (from
    composite_builder.get_category_series(resolved)['close']).
    """
    weekly = daily_close.resample('W-FRI').last().dropna()

    if len(weekly) < MIN_WEEKS_REQUIRED:
        return {
            'label': None, 'raw_score': None, 'insufficient_history': True,
            'weeks_available': len(weekly), 'weeks_required': MIN_WEEKS_REQUIRED,
        }

    ema10 = weekly.ewm(span=10, adjust=False).mean()
    ema30 = weekly.ewm(span=30, adjust=False).mean()
    ema40 = weekly.ewm(span=40, adjust=False).mean()

    price = weekly.iloc[-1]
    e10, e30, e40 = ema10.iloc[-1], ema30.iloc[-1], ema40.iloc[-1]

    alignment = 0
    alignment += 1 if price > e10 else -1
    alignment += 1 if e10 > e30 else -1
    alignment += 1 if e30 > e40 else -1
    alignment_score = (alignment + 3) / 6 * 100  # -3..3 -> 0..100

    lookback = min(slope_lookback_weeks, len(ema30) - 1)
    if lookback > 0 and ema30.iloc[-1 - lookback] != 0:
        slope_pct = (ema30.iloc[-1] - ema30.iloc[-1 - lookback]) / ema30.iloc[-1 - lookback] * 100
    else:
        slope_pct = 0.0
    # 5 score-points per 1% slope over the lookback window, clamped to [0,100] --
    # tunable constant; §6 backtesting is what should actually calibrate this.
    slope_score = max(0.0, min(100.0, 50 + slope_pct * 5))

    raw_score = round(0.7 * alignment_score + 0.3 * slope_score, 1)
    label = bucket_trend(raw_score)

    return {
        'label': label,
        'raw_score': raw_score,
        'insufficient_history': False,
        'weeks_available': len(weekly),
        'price': round(float(price), 2),
        'ema10w': round(float(e10), 2),
        'ema30w': round(float(e30), 2),
        'ema40w': round(float(e40), 2),
        'alignment': alignment,          # -3..3, raw pairwise-comparison count, useful for debugging/backtest
        'slope_pct_10w': round(slope_pct, 2),
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
            result = compute_trend(series['close'])
            print(f"{r.group}/{r.name}: {result.get('label')} (score={result.get('raw_score')}, "
                  f"weeks={result.get('weeks_available')})")
        except Exception as e:
            print(f"{r.group}/{r.name}: SKIP -- {e}")
