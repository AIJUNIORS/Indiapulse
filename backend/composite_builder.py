"""
composite_builder.py -- v3.1 S2.4 Market Leader Composite construction, plus
get_category_series(), the single entry point downstream factor modules use
regardless of whether a category resolved to an ETF, benchmark, futures/FX,
or composite.

Construction method: equal-weight at each rebalance, units-based (not
weight-drift-formula-based -- tracking unit counts avoids compounding
rounding error and is easier to verify). Rebalanced on every calendar-quarter
transition (v3.1 S2.4: "quarterly, calendar quarter-end").

Composite history is bounded by the SHORTEST-listed constituent, not the
longest -- a composite can only be computed over dates where every
constituent has a price. This is why some composites in sources.py show
deep history (24.1y for Financial Services) despite no single ETF existing
that long: the underlying stocks (HDFCBANK, ICICIBANK, etc.) have been
listed that long, even though no ETF wrapper did.

Corporate actions: each constituent's cached series already comes from
data_fetch.py with auto_adjust=True (split/dividend-adjusted per symbol).
This module combines already-adjusted series -- it does not re-adjust.

KNOWN LIMITATION -- cross-currency composites: this module assumes every
constituent is priced in the same currency. That held for every composite
in the registry except Vietnam (VNM is a USD-denominated US-listed ETF;
EIB.HM/SSI.HM are VND-denominated Hanoi-listed stocks) -- Vietnam now
routes through build_vietnam_composite() below instead, which converts the
VND constituents to USD (VNM's own currency) before combining, via the
same VNDUSD=X bridge-pair convention fx.py already uses for Global Markets
INR conversion. Any FUTURE composite that mixes currencies would need the
same treatment; build_composite() still guards against being called
directly on a registered cross-currency name (CROSS_CURRENCY_COMPOSITES)
so a new one can't silently produce a wrong blended series before someone
writes its conversion path.

KNOWN LIMITATION -- composites are close-only. A synthetic index level has
no real high/low/volume, so ATR-style volatility measures can't be computed
on composite-sourced categories the same way as ETF/index-sourced ones.
Volatility module has a close-based fallback (realized stdev of returns)
for resolution == 'composite'.
"""

from datetime import timedelta
from typing import Optional

import pandas as pd

import price_cache
import fx
from data_hierarchy import ResolvedSource

CROSS_CURRENCY_COMPOSITES = {'Vietnam'}  # see module docstring -- Vietnam now has a conversion path (build_vietnam_composite); a NEW name added here still blocks build_composite() until it gets one too
VIETNAM_VND_CONSTITUENTS = {'EIB.HM', 'SSI.HM'}  # VNM is already USD-denominated and needs no conversion


def build_composite(constituent_prices: dict[str, pd.Series], category_name: str = '') -> pd.DataFrame:
    """
    constituent_prices: {symbol: pd.Series of close prices, indexed by date}.
    Returns a single-column DataFrame ('close') -- a synthetic composite
    index level, base 100 at the first common date, equal-weighted,
    rebalanced at every calendar-quarter transition.
    """
    if category_name in CROSS_CURRENCY_COMPOSITES:
        raise ValueError(
            f"{category_name} mixes currencies across constituents -- convert each "
            f"constituent to a common currency via fx.py before calling build_composite()"
        )
    if len(constituent_prices) < 2:
        raise ValueError("build_composite() needs at least 2 constituents")

    # Intersection: only dates where every constituent has a price
    common_index = None
    for s in constituent_prices.values():
        idx = s.dropna().index
        common_index = idx if common_index is None else common_index.intersection(idx)
    common_index = common_index.sort_values()

    if len(common_index) < 2:
        raise ValueError("insufficient overlapping history across constituents -- check for a symbol with a short or broken cache")

    prices = pd.DataFrame({sym: s.reindex(common_index) for sym, s in constituent_prices.items()})
    n = len(prices.columns)
    quarters = pd.PeriodIndex(prices.index, freq='Q')

    portfolio_value = pd.Series(index=prices.index, dtype=float)
    units = pd.Series(0.0, index=prices.columns)
    value = 100.0
    prev_quarter = None

    for i, dt in enumerate(prices.index):
        row = prices.loc[dt]
        q = quarters[i]
        if i == 0 or q != prev_quarter:
            # Rebalance: split current portfolio value equally across constituents,
            # buy units at today's price. i==0 seeds the initial equal-weight position.
            alloc = value / n
            units = alloc / row
        value = float((units * row).sum())
        portfolio_value.loc[dt] = value
        prev_quarter = q

    return pd.DataFrame({'close': portfolio_value})


def vietnam_fx_symbols_needed() -> list[str]:
    """
    The one extra FX pair Vietnam needs that fx.py's own fx_symbols_needed()
    won't fetch -- VND isn't in fx.py's CURRENCY_MAP (Vietnam is intentionally
    excluded there, see fx.py's module docstring), so its VNDUSD=X bridge
    pair is never included in that batch. Callers building the fetch batch
    (price_cache.py's __main__) need to merge this in alongside
    fx.fx_symbols_needed(), or build_vietnam_composite() below will raise
    on a cache miss instead of silently using stale/wrong data.
    """
    return [fx.bridge_pair_symbol('VND')]


def _convert_vnd_constituent_to_usd(local_close: pd.Series) -> pd.Series:
    """
    VND -> USD via VNDUSD=X -- the same 'local currency to a base' bridge
    pair fx.py already fetches for Global Markets INR conversion (fx.py's
    bridge_pair_symbol(currency) convention), just consumed one hop short
    of INR here since USD (not INR) is the common currency Vietnam's
    constituents need to share before combining.
    """
    bridge_symbol = fx.bridge_pair_symbol('VND')
    bridge_cache = price_cache.read_cache(bridge_symbol)
    if bridge_cache is None or bridge_cache.empty:
        raise ValueError(
            f"No cached {bridge_symbol} -- run price_cache.refresh_all() with "
            f"vietnam_fx_symbols_needed() included in the batch"
        )
    rate = bridge_cache['close'].reindex(local_close.index).ffill()
    return local_close * rate


def build_vietnam_composite(constituent_prices: dict[str, pd.Series]) -> pd.DataFrame:
    """
    Vietnam's dedicated composite path -- converts the VND-denominated
    constituents (EIB.HM, SSI.HM) to USD before combining with the
    already-USD-denominated VNM, then defers to build_composite()'s normal
    equal-weight/quarterly-rebalance logic on the now-currency-unified
    series. This IS the fix the module docstring previously flagged as
    "not implemented here."

    Resulting composite is USD-denominated (VNM's own currency), not INR --
    if Vietnam needs INR-denominated display consistent with other Global
    Markets categories, run fx.build_dual_series() on this composite's
    'close' output afterward. That needs 'Vietnam': 'USD' added to fx.py's
    CURRENCY_MAP first (a separate, small change -- not applied here, since
    it's a fx.py edit, not a composite_builder.py one).
    """
    converted = {
        symbol: (_convert_vnd_constituent_to_usd(close) if symbol in VIETNAM_VND_CONSTITUENTS else close)
        for symbol, close in constituent_prices.items()
    }
    # category_name='' deliberately does NOT match CROSS_CURRENCY_COMPOSITES --
    # currencies are already unified above, so build_composite()'s guard correctly
    # doesn't apply to this already-converted input.
    return build_composite(converted, category_name='')


def get_category_series(resolved: ResolvedSource) -> pd.DataFrame:
    """
    The single entry point factor modules should call: 'give me this
    category's price series, however it was sourced.' Returns a DataFrame
    with at least a 'close' column; 'open'/'high'/'low'/'volume' are present
    for etf/benchmark/futures/fx resolutions (real OHLCV from cache) and
    absent for composite resolutions (synthetic, close-only -- see module
    docstring's volatility-module limitation note).
    """
    if resolved.resolution in ('etf', 'benchmark', 'futures', 'fx'):
        cached = price_cache.read_cache(resolved.symbol)
        if cached is None:
            raise ValueError(f"No cached data for {resolved.symbol} ({resolved.group}/{resolved.name}) "
                              f"-- run price_cache.refresh_all() first")
        return cached

    if resolved.resolution == 'composite':
        missing = [c for c in resolved.constituents if price_cache.read_cache(c) is None]
        if missing:
            raise ValueError(f"Missing cached data for composite constituents {missing} "
                              f"({resolved.group}/{resolved.name}) -- run price_cache.refresh_all() first")
        constituent_prices = {c: price_cache.read_cache(c)['close'] for c in resolved.constituents}
        if resolved.name in CROSS_CURRENCY_COMPOSITES:
            return build_vietnam_composite(constituent_prices)   # currency-unify before combining -- see module docstring
        return build_composite(constituent_prices, category_name=resolved.name)

    raise ValueError(f"Cannot build a series for resolution={resolved.resolution} "
                      f"({resolved.group}/{resolved.name}) -- check data_hierarchy.resolve_source() output first")


if __name__ == '__main__':
    import sys
    sys.path.insert(0, '.')
    from data_hierarchy import resolve_all

    resolved = resolve_all()
    composites = [r for r in resolved if r.resolution == 'composite']
    print(f"{len(composites)} composite categories to build")
    for r in composites:
        try:
            series = get_category_series(r)
            span_years = (series.index.max() - series.index.min()).days / 365.25
            print(f"  OK  {r.group}/{r.name}: {len(series)} rows, {span_years:.1f}y span")
        except Exception as e:
            print(f"  FAIL {r.group}/{r.name}: {e}")
