"""
factors/technicals.py -- supplementary card-display technicals: rsi, smi,
atrPct, trendPct, pivotDist. These are display-only fields consumed
directly by the frontend's existing bucketing (rsiInterp/smiInterp/
pivotInterp) -- none of them feed opportunity_score.py's S4 formula (that's
Trend/Position/Cycle/Volatility/Seasonality's job). They exist here because
nothing else in the pipeline computes them.

Weekly cadence throughout, matching every other factor module -- Position,
Trend, Cycle, Volatility are all weekly, and these cards sit right next to
them, so mixing a daily-cadence RSI in would silently talk about a
different timeframe.

Composite (close-only) fallback: RSI and trendPct only need close, so they
work identically for composite-sourced categories. SMI and pivotDist need a
real high/low for a faithful reading; when absent (resolution=='composite')
both fall back to a close-as-proxy method (same honesty pattern as
volatility.py's 'atr' vs 'realized_vol_proxy' -- every output carries
`method` so it's visible which categories are running the proxy).
"""

from typing import Optional

import numpy as np
import pandas as pd

RSI_PERIOD = 14          # weeks
SMI_PERIOD = 14          # weeks, %K lookback
SMI_EMA1 = 3             # first smoothing EMA
SMI_EMA2 = 3             # second smoothing EMA
TREND_PCT_FAST_WEEKS = 18
TREND_PCT_SLOW_WEEKS = 40
PIVOT_LOOKBACK_WEEKS = 52   # prior calendar year, approximated as trailing 52 weeks
MIN_WEEKS_REQUIRED = max(RSI_PERIOD, SMI_PERIOD + SMI_EMA1 + SMI_EMA2, TREND_PCT_SLOW_WEEKS, PIVOT_LOOKBACK_WEEKS) + 5


def _weekly_rsi(weekly_close: pd.Series, period: int = RSI_PERIOD) -> pd.Series:
    """Wilder-smoothed RSI, same smoothing convention as volatility.py's ATR (EMA with alpha=1/period)."""
    delta = weekly_close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(100).where(avg_loss != 0, 100)  # zero avg_loss -> no down weeks -> RSI 100, not NaN


def _weekly_smi(weekly: pd.DataFrame, has_ohlc: bool) -> tuple[pd.Series, str]:
    """
    Stochastic Momentum Index (14,3,3): double-EMA-smoothed distance of close
    from the midpoint of the high/low range, normalized by half the range.
    Close-only fallback substitutes rolling max/min of CLOSE for high/low --
    a materially different (compressed) reading, hence the returned method tag.
    """
    if has_ohlc:
        hh = weekly['high'].rolling(SMI_PERIOD).max()
        ll = weekly['low'].rolling(SMI_PERIOD).min()
        method = 'smi'
    else:
        hh = weekly['close'].rolling(SMI_PERIOD).max()
        ll = weekly['close'].rolling(SMI_PERIOD).min()
        method = 'smi_close_proxy'

    mid = (hh + ll) / 2
    diff = weekly['close'] - mid
    rng = hh - ll

    diff_smoothed = diff.ewm(span=SMI_EMA1, adjust=False).mean().ewm(span=SMI_EMA2, adjust=False).mean()
    rng_smoothed = rng.ewm(span=SMI_EMA1, adjust=False).mean().ewm(span=SMI_EMA2, adjust=False).mean()

    smi = (200 * diff_smoothed / rng_smoothed.replace(0, np.nan)).fillna(0)
    return smi, method


def _trend_pct(weekly_close: pd.Series) -> float:
    """% of price vs the 18w/40w MA stack -- average distance from each, not the same measure as trend.py's 10/30/40w EMA stack."""
    ema_fast = weekly_close.ewm(span=TREND_PCT_FAST_WEEKS, adjust=False).mean().iloc[-1]
    ema_slow = weekly_close.ewm(span=TREND_PCT_SLOW_WEEKS, adjust=False).mean().iloc[-1]
    price = weekly_close.iloc[-1]
    pct_fast = (price - ema_fast) / ema_fast * 100
    pct_slow = (price - ema_slow) / ema_slow * 100
    return round(float((pct_fast + pct_slow) / 2), 1)


def _pivot_distance(weekly: pd.DataFrame, has_ohlc: bool) -> tuple[Optional[float], str]:
    """
    Classic floor pivot ((H+L+C)/3) of the prior ~52-week period, % distance
    of current price from it. Close-only fallback uses the close series' own
    rolling max/min as H/L stand-ins (not true intraday range) -- flagged via
    method, same pattern as SMI above.
    """
    if len(weekly) < PIVOT_LOOKBACK_WEEKS + 1:
        return None, 'insufficient_history'

    prior_window = weekly.iloc[-PIVOT_LOOKBACK_WEEKS - 1:-1]  # the ~52w preceding the current bar
    if has_ohlc:
        h = prior_window['high'].max()
        l = prior_window['low'].min()
        method = 'pivot'
    else:
        h = prior_window['close'].max()
        l = prior_window['close'].min()
        method = 'pivot_close_proxy'
    c = prior_window['close'].iloc[-1]
    pivot = (h + l + c) / 3
    if pivot == 0:
        return None, method
    price = weekly['close'].iloc[-1]
    return round(float((price - pivot) / pivot * 100), 1), method


def compute_technicals(series: pd.DataFrame) -> dict:
    """
    series: DataFrame from composite_builder.get_category_series(resolved) --
    same input shape volatility.py takes. Returns rsi, smi, atrPct (aliased
    from a fresh ATR%/proxy calc kept local to this module so technicals.py
    doesn't have to import volatility.py's internals), trendPct, pivotDist --
    each with an 'insufficient_history' escape hatch, same convention as
    every other factor module.
    """
    weekly = series.resample('W-FRI').last().dropna(subset=['close'])
    has_ohlc = 'high' in weekly.columns and 'low' in weekly.columns and weekly['high'].notna().any()

    if len(weekly) < MIN_WEEKS_REQUIRED:
        return {
            'rsi': None, 'smi': None, 'atrPct': None, 'trendPct': None, 'pivotDist': None,
            'smi_method': None, 'pivot_method': None,
            'insufficient_history': True, 'weeks_available': len(weekly), 'weeks_required': MIN_WEEKS_REQUIRED,
        }

    rsi = round(float(_weekly_rsi(weekly['close']).iloc[-1]), 1)
    smi_series, smi_method = _weekly_smi(weekly, has_ohlc)
    smi = round(float(smi_series.iloc[-1]), 1)

    if has_ohlc:
        prev_close = weekly['close'].shift(1)
        tr = pd.concat([
            weekly['high'] - weekly['low'],
            (weekly['high'] - prev_close).abs(),
            (weekly['low'] - prev_close).abs(),
        ], axis=1).max(axis=1)
        atr_pct = float((tr.ewm(alpha=1 / 14, adjust=False).mean() / weekly['close'] * 100).iloc[-1])
    else:
        atr_pct = float((weekly['close'].pct_change().rolling(14).std() * np.sqrt(52) * 100).iloc[-1])

    trend_pct = _trend_pct(weekly['close'])
    pivot_dist, pivot_method = _pivot_distance(weekly, has_ohlc)

    return {
        'rsi': rsi,
        'smi': smi,
        'atrPct': round(atr_pct, 1) if not np.isnan(atr_pct) else None,
        'trendPct': trend_pct,
        'pivotDist': pivot_dist,
        'smi_method': smi_method,
        'pivot_method': pivot_method,
        'insufficient_history': False,
        'weeks_available': len(weekly),
    }


if __name__ == '__main__':
    import sys
    sys.path.insert(0, '.')
    import price_cache
    from data_hierarchy import resolve_all
    from composite_builder import get_category_series

    resolved = [r for r in resolve_all() if r.resolution != 'unresolved'][:5]
    for r in resolved:
        try:
            series = get_category_series(r)
            result = compute_technicals(series)
            print(f"{r.group}/{r.name}: rsi={result.get('rsi')} smi={result.get('smi')} "
                  f"atrPct={result.get('atrPct')} trendPct={result.get('trendPct')} "
                  f"pivotDist={result.get('pivotDist')} ({result.get('pivot_method')})")
        except Exception as e:
            print(f"{r.group}/{r.name}: SKIP -- {e}")
