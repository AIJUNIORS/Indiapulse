"""
test_factors.py -- synthetic-data tests for every factor/scoring module,
same style as test_price_cache.py (plain script, check() helper, no
pytest dependency). Run with: python3 test_factors.py

Covers what price_cache's own tests don't: correctness/shape of trend,
position, volatility (both ATR and close-only proxy paths), cycle
(cold-start + confirmation lag), seasonality, technicals (both OHLC and
close-only SMI/pivot proxy paths), structure_score, business_score, and
opportunity_score. Does NOT hit yfinance or price_cache -- everything here
is constructed pd.Series/DataFrame input, so it runs anywhere, no network.
"""

import sys
sys.path.insert(0, '.')

import numpy as np
import pandas as pd

from trend import compute_trend
from position import compute_position
from volatility import compute_volatility
from cycle import compute_cycle, apply_confirmation
from seasonality import compute_monthly_stats, compute_annual_return, compute_seasonality_score
from technicals import compute_technicals
from structure_score import compute_structure
from business_score import compute_effective_business_score
from opportunity_score import compute_opportunity

failures = []


def check(label, cond):
    status = 'PASS' if cond else 'FAIL'
    print(f"  [{status}] {label}")
    if not cond:
        failures.append(label)


def make_ohlc(n_days=1500, base=100.0, drift=0.03, seed=0):
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range('2020-01-01', periods=n_days)
    close = base + np.cumsum(rng.standard_normal(n_days) * 0.5 + drift)
    high = close + rng.random(n_days) * 1.5
    low = close - rng.random(n_days) * 1.5
    return pd.DataFrame({'close': close, 'high': high, 'low': low}, index=dates)


def run():
    print("Test 1: trend.py -- insufficient vs sufficient history")
    short = make_ohlc(n_days=20)
    result = compute_trend(short['close'])
    check("insufficient_history True on <45 weeks", result['insufficient_history'] is True)

    trending_up = make_ohlc(n_days=1500, drift=0.15, seed=1)
    result = compute_trend(trending_up['close'])
    check("sufficient history computes a label", result['label'] is not None)
    check("raw_score in [0,100]", 0 <= result['raw_score'] <= 100)
    check("strong uptrend scores in upper half", result['raw_score'] > 50)

    print("\nTest 2: position.py -- percentile bounds and since-inception flag")
    df = make_ohlc(n_days=700, drift=0.2, seed=2)  # ~2.8y, genuinely under the 5y pinned window
    result = compute_position(df['close'])
    check("percentile is a valid 0-100 value", 0 <= result['percentile'] <= 100)
    check("since_inception True for <5y data", result['since_inception'] is True)

    print("\nTest 3: volatility.py -- ATR path vs close-only proxy path")
    df = make_ohlc(n_days=1500, seed=3)
    atr_result = compute_volatility(df)  # has high/low
    check("ATR path used when OHLC present", atr_result['method'] == 'atr')
    check("label is a valid VOL_LABEL", atr_result['label'] in ('Low', 'Moderate', 'Elevated', 'High'))

    close_only = df[['close']]
    proxy_result = compute_volatility(close_only)
    check("proxy path used when high/low absent", proxy_result['method'] == 'realized_vol_proxy')
    check("vol_roc_pct present in both paths", 'vol_roc_pct' in atr_result and 'vol_roc_pct' in proxy_result)

    print("\nTest 4: cycle.py -- cold start confirms immediately, whipsaw needs 3 weeks")
    cold = apply_confirmation(None, 'Bull')
    check("cold-start confirms immediately", cold['confirmed_regime'] == 'Bull')

    entry = cold
    for _ in range(2):  # 2 consecutive 'Bear' readings -- not enough to flip yet
        entry = apply_confirmation(entry, 'Bear')
    check("regime does NOT flip after only 2 agreements", entry['confirmed_regime'] == 'Bull')
    entry = apply_confirmation(entry, 'Bear')  # 3rd agreement
    check("regime flips on the 3rd consecutive agreement", entry['confirmed_regime'] == 'Bear')

    trend_r = compute_trend(trending_up['close'])
    position_r = compute_position(trending_up['close'])
    vol_r = compute_volatility(trending_up)
    cycle_result = compute_cycle('test', 'Synthetic', trend_r, position_r, vol_r, {})
    check("cycle produces a valid label on cold start", cycle_result['label'] in
          ('Bear', 'Distribution', 'Recovery', 'Accumulation', 'Early Bull', 'Bull', 'Late Bull'))

    print("\nTest 5: seasonality.py -- zero-observation month doesn't crash, neutral-tapers correctly")
    daily = trending_up['close']
    stats = compute_monthly_stats(daily, 5, 'Max', 4.0)
    check("n >= 0, no crash", stats['n'] >= 0)
    annual = compute_annual_return(daily, 3, 4.0)
    check("annual return dict has expected keys", set(annual) == {'meanAnnualReturn', 'n', 'effectiveYears', 'capped'})
    score = compute_seasonality_score(daily, 5, 1.5)  # <3yr -> taper should pull toward 50
    check("taper < 1.0 for <3yr history", score['confidence_taper'] < 1.0)
    check("raw_score pulled toward neutral, not left at raw win rate", abs(score['raw_score'] - 50) <= abs((score['win_rate_pct'] or 50) - 50))

    print("\nTest 6: technicals.py -- OHLC vs close-only fallback methods differ")
    tech_ohlc = compute_technicals(df)
    tech_close_only = compute_technicals(close_only)
    check("SMI uses real method when OHLC present", tech_ohlc['smi_method'] == 'smi')
    check("SMI falls back to close proxy without OHLC", tech_close_only['smi_method'] == 'smi_close_proxy')
    check("RSI is in [0,100] in both paths", 0 <= tech_ohlc['rsi'] <= 100 and 0 <= tech_close_only['rsi'] <= 100)

    print("\nTest 7: structure_score.py -- insufficient upstream propagates, full inputs blend correctly")
    insufficient = compute_structure({'insufficient_history': True}, position_r, cycle_result, vol_r)
    check("propagates insufficient_history", insufficient['insufficient_history'] is True)
    full = compute_structure(
        {'raw_score': 80, 'insufficient_history': False},
        {'raw_score': 60, 'insufficient_history': False},
        {'raw_score': 70, 'insufficient_history': False},
        {'raw_score': 50, 'insufficient_history': False},
    )
    expected = round(0.30 * 80 + 0.25 * 60 + 0.25 * 70 + 0.20 * 50, 1)
    check(f"weighted blend matches expected ({expected})", full['score'] == expected)

    print("\nTest 8: business_score.py -- state mapping, out-of-scope returns None")
    calendar = {'Test Cat': {'states': ['Peak'] * 12, 'confidence': 'high', 'why': ['x'] * 12}}
    result = compute_effective_business_score('Test Cat', 0, calendar)
    check("Peak + high confidence -> 5 stars", result['fundamental'] == 5)
    check("contra is inverse (6 - fundamental)", result['contra'] == 1)
    check("out-of-scope category returns None", compute_effective_business_score('Nope', 0, calendar) is None)

    print("\nTest 9: opportunity_score.py -- weight redistribution when a component is missing")
    full_score = compute_opportunity(80.0, 5, 60.0)
    partial_score = compute_opportunity(80.0, None, 60.0)  # no business coverage
    check("full-input score is a valid 0-100 value", 0 <= full_score <= 100)
    check("partial-input score redistributes weight, doesn't just drop to 0 for missing piece",
          partial_score is not None and 0 <= partial_score <= 100)
    check("context flag forces None", compute_opportunity(80.0, 5, 60.0, flag='context') is None)
    check("insufficient structure forces None", compute_opportunity(None, 5, 60.0) is None)

    print(f"\n{'='*50}")
    if failures:
        print(f"{len(failures)} FAILED: {failures}")
        sys.exit(1)
    print("ALL TESTS PASSED")


if __name__ == '__main__':
    run()
