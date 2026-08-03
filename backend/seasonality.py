"""
factors/seasonality.py -- v3.1 S3.4 Seasonality module.

Computed on whatever series the caller passes in -- per S2.6, that MUST be
the longest available series for the category (index-level history, even
when the display instrument is a younger ETF), not this module's concern to
enforce. This module trusts its input; data_hierarchy.py / the pipeline
orchestrator is responsible for choosing the right series before calling in.

Two outputs, mirroring the frontend's two mock functions exactly (same
signature shape, same graceful-degradation contract -- see
indiapulse-github-architecture-fixed-frontend doc S2):

  compute_monthly_stats(daily_close, month_idx, lookback, history_years)
      -> mean/median/positivePct/stdDev for one calendar month, across
         every historical occurrence of it within the lookback window.

  compute_annual_return(daily_close, lookback, history_years)
      -> average full calendar-year return over the lookback window.

Both auto-cap to whatever history actually exists -- NEVER return an
error/N/A state, same principle established in the frontend mock and
carried through every other factor module in this codebase. A category
with 1.1 years of history still returns real numbers computed from
whatever's there; it just does so with n=1 or n=2 observations, which the
stdDev handling below treats honestly (0, not a crash) rather than pretending
a spread exists where none can be measured.

Separately, compute_seasonality_score() produces the SINGLE raw_score
opportunity_score.py needs for the S4 Step-1 formula:
    "Seasonality | win rate/return blend | raw = (monthly win rate x 100),
     tapered per S3.4 sample-size rule"
"Tapered" isn't specified beyond "full confidence at >=3yr, linear taper
below" -- the spec doesn't say WHETHER the taper shrinks the score toward
zero or toward neutral. Shrinking toward zero would incorrectly punish a
category with only 2 years of data but a genuinely strong pattern as if it
were BAD, rather than merely uncertain. This module shrinks toward neutral
(50) instead -- a thin-sample category with an 80% win rate reads as
"probably favorable, low confidence" (score pulled toward 50, not toward 0).
This is a judgment call, not a spec requirement -- flagged the same way as
trend.py's slope_score constant: tunable, needs S6 backtest validation
before being treated as final.
"""

from typing import Optional, Union

import pandas as pd

MIN_HISTORY_FLOOR_YEARS = 3.0   # S3.4's own reference point -- matches the data hierarchy's 3yr floor (S2.1/S2.2)
Lookback = Union[int, str]      # int (years) or the literal 'Max'


def _monthly_return_series(daily_close: pd.Series) -> pd.Series:
    """Month-end close, %-change month over month -- the base series everything else slices from."""
    month_end = daily_close.resample('ME').last().dropna()   # 'M' deprecated/removed in current pandas -- use 'ME' (month-end)
    return month_end.pct_change().dropna() * 100


def _effective_years(requested: Lookback, history_years: float) -> float:
    req = history_years if requested == 'Max' else float(requested)
    return min(req, history_years)


def compute_monthly_stats(daily_close: pd.Series, month_idx: int, lookback: Lookback, history_years: float) -> dict:
    """
    month_idx: 0=Jan ... 11=Dec, matching the frontend's MONTHS array indexing.
    Returns the exact field shape the frontend's mock seasonStats() already
    produces: mean, median, positivePct, stdDev, n, effectiveYears, capped.
    """
    monthly_returns = _monthly_return_series(daily_close)
    same_month = monthly_returns[monthly_returns.index.month == (month_idx + 1)]  # pandas months are 1-indexed

    effective_years = _effective_years(lookback, history_years)
    requested_years = history_years if lookback == 'Max' else float(lookback)
    capped = requested_years > history_years

    # Take the most recent `effective_years` worth of observations for this calendar month.
    n_target = max(1, round(effective_years))
    observations = same_month.iloc[-n_target:] if len(same_month) >= n_target else same_month
    n = len(observations)

    if n == 0:
        # Genuinely zero observations of this calendar month exist yet (e.g. a category younger
        # than one full year). Still no N/A/error -- report a neutral, honestly-labeled zero-sample state.
        return {'mean': 0.0, 'median': 0.0, 'positivePct': None, 'stdDev': None,
                'n': 0, 'effectiveYears': round(effective_years, 1), 'capped': capped}

    mean = round(float(observations.mean()), 1)
    median = round(float(observations.median()), 1)
    positive_pct = round(float((observations > 0).sum()) / n * 100)
    std_dev = round(float(observations.std(ddof=1)), 1) if n >= 2 else 0.0

    return {
        'mean': mean, 'median': median, 'positivePct': positive_pct, 'stdDev': std_dev,
        'n': n, 'effectiveYears': round(effective_years, 1), 'capped': capped,
    }


def compute_annual_return(daily_close: pd.Series, lookback: Lookback, history_years: float) -> dict:
    """Average full calendar-year return over the lookback window, same capping rule as compute_monthly_stats."""
    year_end = daily_close.resample('YE').last().dropna()   # 'Y' deprecated/removed in current pandas -- use 'YE' (year-end)
    annual_returns = year_end.pct_change().dropna() * 100

    effective_years = _effective_years(lookback, history_years)
    requested_years = history_years if lookback == 'Max' else float(lookback)
    capped = requested_years > history_years

    n_target = max(1, round(effective_years))
    observations = annual_returns.iloc[-n_target:] if len(annual_returns) >= n_target else annual_returns
    n = len(observations)

    mean = round(float(observations.mean()), 1) if n > 0 else 0.0
    return {'meanAnnualReturn': mean, 'n': n, 'effectiveYears': round(effective_years, 1), 'capped': capped}


def compute_seasonality_score(daily_close: pd.Series, current_month_idx: int, history_years: float) -> dict:
    """
    The single raw_score opportunity_score.py consumes -- win-rate based,
    tapered toward neutral (50) below the 3yr floor. See module docstring
    for why neutral-taper, not zero-taper.
    """
    stats = compute_monthly_stats(daily_close, current_month_idx, 'Max', history_years)

    if stats['n'] == 0 or stats['positivePct'] is None:
        return {'raw_score': 50.0, 'win_rate_pct': None, 'sample_years': stats['effectiveYears'], 'confidence_taper': 0.0}

    win_rate = stats['positivePct']
    taper = min(1.0, stats['effectiveYears'] / MIN_HISTORY_FLOOR_YEARS)
    raw_score = round(50 + (win_rate - 50) * taper, 1)

    return {
        'raw_score': raw_score,
        'win_rate_pct': win_rate,
        'sample_years': stats['effectiveYears'],   # S2.6: surface this everywhere the score is shown, distinct from the instrument's own history_years
        'confidence_taper': round(taper, 2),
    }


if __name__ == '__main__':
    import sys
    sys.path.insert(0, '.')
    import price_cache
    from data_hierarchy import resolve_all
    from composite_builder import get_category_series
    from datetime import date

    resolved = [r for r in resolve_all() if r.resolution != 'unresolved'][:5]  # smoke-test a handful
    current_month = date.today().month - 1  # 0-indexed

    for r in resolved:
        try:
            series = get_category_series(r)
            monthly = compute_monthly_stats(series['close'], current_month, 'Max', r.history_years)
            annual = compute_annual_return(series['close'], 5, r.history_years)
            score = compute_seasonality_score(series['close'], current_month, r.history_years)
            print(f"{r.group}/{r.name}: month_mean={monthly['mean']}% (n={monthly['n']}, {monthly['effectiveYears']}y), "
                  f"5y_annual_avg={annual['meanAnnualReturn']}%, seasonality_score={score['raw_score']} "
                  f"(taper={score['confidence_taper']})")
        except Exception as e:
            print(f"{r.group}/{r.name}: SKIP -- {e}")
