"""
test_price_cache.py -- exercises price_cache.update_symbol()'s incremental
logic (backfill -> incremental append -> up-to-date short-circuit -> overlap
de-dupe) using synthetic FetchResult objects, since this sandbox can't reach
Yahoo Finance. Monkeypatches data_fetch.fetch_symbol so no network call is
attempted. Run with: python3 test_price_cache.py
"""

import shutil
import sys
from datetime import date, timedelta

import pandas as pd

sys.path.insert(0, '.')
import data_fetch
import price_cache


def make_bars(start: date, n_days: int, base_price: float = 100.0) -> pd.DataFrame:
    dates = [start + timedelta(days=i) for i in range(n_days)]
    prices = [base_price + i * 0.5 for i in range(n_days)]
    df = pd.DataFrame({
        'open': prices, 'high': [p + 1 for p in prices], 'low': [p - 1 for p in prices],
        'close': prices, 'volume': [1000] * n_days,
    }, index=pd.Index(dates, name='date'))
    return df


def fake_fetch_factory(response_map):
    """Returns a stand-in for data_fetch.fetch_symbol that serves pre-built FetchResults."""
    def _fake(symbol, start=None, end=None):
        return response_map[symbol]
    return _fake


def run():
    # clean slate
    shutil.rmtree('data', ignore_errors=True)
    failures = []

    def check(label, cond):
        status = 'PASS' if cond else 'FAIL'
        print(f"  [{status}] {label}")
        if not cond:
            failures.append(label)

    print("Test 1: first-ever run (no cache) -> full backfill")
    backfill_bars = make_bars(date(2024, 1, 1), 10)
    price_cache.fetch_symbol = fake_fetch_factory({
        'TESTSYM': data_fetch.FetchResult('TESTSYM', True, backfill_bars, 10,
                                           backfill_bars.index.min(), backfill_bars.index.max())
    })
    result = price_cache.update_symbol('TESTSYM', today=date(2024, 1, 10))
    check("status is 'updated'", result['status'] == 'updated')
    check("10 rows added", result['rows_added'] == 10)
    check("10 total rows", result['total_rows'] == 10)
    cached = price_cache.read_cache('TESTSYM')
    check("cache has 10 rows on disk", len(cached) == 10)
    check("cache index starts 2024-01-01", cached.index.min() == date(2024, 1, 1))

    print("\nTest 2: incremental run -> only fetches the gap, appends")
    new_bars = make_bars(date(2024, 1, 11), 3, base_price=105.0)
    price_cache.fetch_symbol = fake_fetch_factory({
        'TESTSYM': data_fetch.FetchResult('TESTSYM', True, new_bars, 3,
                                           new_bars.index.min(), new_bars.index.max())
    })
    result = price_cache.update_symbol('TESTSYM', today=date(2024, 1, 13))
    check("status is 'updated'", result['status'] == 'updated')
    check("3 rows added", result['rows_added'] == 3)
    check("13 total rows", result['total_rows'] == 13)
    cached = price_cache.read_cache('TESTSYM')
    check("cache now has 13 rows", len(cached) == 13)
    check("cache index now ends 2024-01-13", cached.index.max() == date(2024, 1, 13))

    print("\nTest 3: same-day re-run -> short-circuits to 'up-to-date', no fetch call")
    def _should_not_be_called(*a, **k):
        raise AssertionError("fetch_symbol should NOT be called when already up-to-date")
    price_cache.fetch_symbol = _should_not_be_called
    result = price_cache.update_symbol('TESTSYM', today=date(2024, 1, 13))
    check("status is 'up-to-date'", result['status'] == 'up-to-date')
    check("0 rows added", result['rows_added'] == 0)

    print("\nTest 4: overlapping bar (provider revised a recent close) -> de-dupe keeps newest")
    revised_bar = make_bars(date(2024, 1, 13), 1, base_price=999.0)  # same date, different price
    price_cache.fetch_symbol = fake_fetch_factory({
        'TESTSYM': data_fetch.FetchResult('TESTSYM', True, revised_bar, 1,
                                           revised_bar.index.min(), revised_bar.index.max())
    })
    result = price_cache.update_symbol('TESTSYM', today=date(2024, 1, 14))
    cached = price_cache.read_cache('TESTSYM')
    check("still 13 rows (overlap de-duped, not appended as new)", len(cached) == 13)
    check("2024-01-13 close was overwritten with the revised value", cached.loc[date(2024, 1, 13), 'close'] == 999.0)

    print("\nTest 5: fetch failure -> reported, cache untouched")
    price_cache.fetch_symbol = fake_fetch_factory({
        'TESTSYM': data_fetch.FetchResult('TESTSYM', False, None, 0, None, None, error='rate limited')
    })
    result = price_cache.update_symbol('TESTSYM', today=date(2024, 1, 20))
    check("status is 'fetch-failed'", result['status'] == 'fetch-failed')
    check("error message preserved", result['error'] == 'rate limited')
    cached = price_cache.read_cache('TESTSYM')
    check("cache untouched at 13 rows after a failed fetch", len(cached) == 13)

    print("\nTest 6: filesystem-unsafe symbol names round-trip correctly")
    for sym in ['^CRSLDX', 'INR=X', 'HG=F']:
        bars = make_bars(date(2024, 1, 1), 5)
        price_cache.fetch_symbol = fake_fetch_factory({
            sym: data_fetch.FetchResult(sym, True, bars, 5, bars.index.min(), bars.index.max())
        })
        price_cache.update_symbol(sym, today=date(2024, 1, 5))
        check(f"round-trips through cache: {sym}", price_cache.read_cache(sym) is not None)

    print(f"\n{'='*50}")
    if failures:
        print(f"{len(failures)} FAILED: {failures}")
        sys.exit(1)
    else:
        print("ALL TESTS PASSED")

    shutil.rmtree('data', ignore_errors=True)


if __name__ == '__main__':
    run()
