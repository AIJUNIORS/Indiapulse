"""
factors/volatility.py -- v3.1 S3.5 Volatility module.

Method: ATR(14w) as % of price is the primary measure. Regime is NOT "is
ATR% high or low in absolute terms" -- it's the percentile of the current
ATR% within the category's OWN trailing 5Y history of that same measure
(spec: "realized volatility regime (percentile of trailing 52w vol vs. its
own 5Y history)"). A commodity and a low-vol equity ETF have structurally
different absolute ATR% levels; comparing each against its own history is
what makes "Elevated" mean the same thing across every category card.

Composite fallback (composite_builder.py's flagged limitation): composites
are close-only, so there's no real high/low for a true-range calculation.
When daily_close's DataFrame has no 'high'/'low' columns, this module falls
back to realized volatility (annualized rolling stdev of weekly returns) as
the ATR%-equivalent input to the same percentile-regime logic below. Every
output carries `method` ('atr' or 'realized_vol_proxy') so it's visible
which categories are running the proxy -- this is a materially different
confidence level, same principle as fx.py tagging 'direct' vs
'bridged-via-usd'.

Also computes max drawdown, current correction size, and recovery status
within the same window (spec: "max drawdown, recovery duration, current
correction size") -- these ride on the same price window Position (S3.2)
already established, so a category's Position and Volatility read are
always describing the same slice of history.

raw_score is NOT the percentile directly (unlike Position) -- S4 Step-1
maps the bucketed label to a fixed, INVERTED score (Low=100...High=10,
low vol = high score) before it enters the weighted sum.
"""

from typing import Optional

import numpy as np
import pandas as pd

VOL_LABELS = ['Low', 'Moderate', 'Elevated', 'High']          # ascending risk, matches frontend's VOLS enum order
RAW_SCORE_MAP = {'Low': 100, 'Moderate': 70, 'Elevated': 40, 'High': 10}  # S4 Step-1, inverted on purpose

ATR_PERIOD = 14                  # weeks -- Wilder-smoothed true range
VOL_PROXY_PERIOD = 14            # weeks -- rolling stdev window for the composite (close-only) fallback
VOL_ROC_LOOKBACK_WEEKS = 8       # trailing window for rate-of-change of volatility -- feeds cycle.py's regime signal
LOOKBACK_WEEKS = 260             # 5 years @ ~52.18 weeks/year -- same pinned window as position.py, for consistency
MIN_WEEKS_REQUIRED = ATR_PERIOD + 46  # need the ATR/proxy series itself to have run in for ~1yr before percentile-ranking it means anything


def bucket_volatility(percentile: float) -> str:
    """Percentile of current ATR%/proxy vs. its own trailing-window history -- NOT an absolute ATR% threshold."""
    if percentile >= 85:
        return 'High'
    if percentile >= 60:
        return 'Elevated'
    if percentile >= 30:
        return 'Moderate'
    return 'Low'


def _weekly_atr_pct(weekly: pd.DataFrame) -> pd.Series:
    """True Wilder-smoothed ATR(14w) as % of close -- requires real high/low (etf/benchmark/futures/fx resolutions)."""
    prev_close = weekly['close'].shift(1)
    tr = pd.concat([
        weekly['high'] - weekly['low'],
        (weekly['high'] - prev_close).abs(),
        (weekly['low'] - prev_close).abs(),
    ], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1 / ATR_PERIOD, adjust=False).mean()  # Wilder smoothing == EMA with alpha=1/period
    return (atr / weekly['close'] * 100).dropna()


def _weekly_realized_vol_proxy(weekly_close: pd.Series) -> pd.Series:
    """
    Composite (close-only) fallback: annualized rolling stdev of weekly
    returns, expressed as a %, standing in for ATR% -- see module docstring.
    """
    returns = weekly_close.pct_change()
    proxy = returns.rolling(VOL_PROXY_PERIOD).std() * np.sqrt(52) * 100
    return proxy.dropna()


def compute_volatility(series: pd.DataFrame, lookback_weeks: int = LOOKBACK_WEEKS) -> dict:
    """
    series: DataFrame from composite_builder.get_category_series(resolved) --
    has 'close' always; 'high'/'low' present for etf/benchmark/futures/fx,
    absent for composite (triggers the realized-vol-proxy fallback).
    """
    weekly = series.resample('W-FRI').last().dropna(subset=['close'])

    has_ohlc = 'high' in weekly.columns and 'low' in weekly.columns and weekly['high'].notna().any()
    method = 'atr' if has_ohlc else 'realized_vol_proxy'
    vol_series = _weekly_atr_pct(weekly) if has_ohlc else _weekly_realized_vol_proxy(weekly['close'])

    if len(vol_series) < MIN_WEEKS_REQUIRED:
        return {
            'label': None, 'raw_score': None, 'percentile': None, 'method': method,
            'insufficient_history': True,
            'weeks_available': len(vol_series), 'weeks_required': MIN_WEEKS_REQUIRED,
        }

    since_inception = len(vol_series) < lookback_weeks
    vol_window = vol_series if since_inception else vol_series.iloc[-lookback_weeks:]
    current_vol = vol_window.iloc[-1]
    percentile = round(float((vol_window <= current_vol).sum()) / len(vol_window) * 100, 1)
    label = bucket_volatility(percentile)
    raw_score = RAW_SCORE_MAP[label]

    # Rate of change of volatility over the trailing window -- Cycle's 4th base signal (S3.3).
    # Positive = vol rising (fear building), negative = vol falling (calm returning).
    roc_lookback = min(VOL_ROC_LOOKBACK_WEEKS, len(vol_window) - 1)
    vol_n_ago = vol_window.iloc[-1 - roc_lookback]
    vol_roc_pct = round(float((current_vol - vol_n_ago) / vol_n_ago * 100), 2) if roc_lookback > 0 and vol_n_ago != 0 else 0.0

    # Drawdown / correction / recovery -- same price window convention as position.py
    price_window = weekly['close'].iloc[-lookback_weeks:] if len(weekly) >= lookback_weeks else weekly['close']
    running_peak = price_window.cummax()
    drawdown_pct = (price_window - running_peak) / running_peak * 100
    max_drawdown_pct = round(float(drawdown_pct.min()), 2)
    current_correction_pct = round(float(drawdown_pct.iloc[-1]), 2)

    trough_idx = drawdown_pct.idxmin()
    peak_before_trough = running_peak.loc[trough_idx]
    post_trough = price_window.loc[trough_idx:]
    recovered_mask = post_trough >= peak_before_trough
    if recovered_mask.any():
        recovery_date = post_trough[recovered_mask].index.min()
        recovery_weeks = int(post_trough.index.get_loc(recovery_date))
        still_in_drawdown = False
    else:
        recovery_weeks = None
        still_in_drawdown = True

    return {
        'label': label,
        'raw_score': raw_score,
        'percentile': percentile,
        'method': method,
        'insufficient_history': False,
        'weeks_available': len(vol_series),
        'window_weeks_used': len(vol_window),
        'since_inception': since_inception,
        'current_vol_pct': round(float(current_vol), 2),
        'vol_roc_pct': vol_roc_pct,
        'max_drawdown_pct': max_drawdown_pct,
        'current_correction_pct': current_correction_pct,
        'still_in_drawdown': still_in_drawdown,
        'recovery_weeks': recovery_weeks,   # None if the max-drawdown trough hasn't been recovered from yet
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
            result = compute_volatility(series)
            print(f"{r.group}/{r.name}: {result.get('label')} (pctile={result.get('percentile')}, "
                  f"method={result.get('method')}, maxDD={result.get('max_drawdown_pct')}%, "
                  f"weeks={result.get('weeks_available')})")
        except Exception as e:
            print(f"{r.group}/{r.name}: SKIP -- {e}")
