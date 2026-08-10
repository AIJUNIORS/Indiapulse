"""
fx.py -- v3.1 S2.5 FX handling for Global Markets.

Stores two series per Global Market index: local-currency close (as
fetched/cached directly) and an INR-converted close. Trend/Position/Cycle
are computed on the INR-converted series by default per the spec ("this is
what matters to an Indian investor comparing against domestic
opportunities"); local-currency Trend is kept as secondary context only.

Conversion path, in order:
  1. Direct {LOCAL_CCY}INR=X pair, if cached (preferred -- one hop)
  2. Bridge through USD/INR: {LOCAL_CCY}USD=X * INR=X (two hops)
Both paths are recorded in the output (`fx_method`) so it's visible which
one a given series actually used -- a bridged rate compounds two sources'
noise and is a meaningfully different confidence level than a direct quote.

Vietnam is intentionally excluded from CURRENCY_MAP -- its composite mixes
a USD-denominated US-listed ETF (VNM) with VND-denominated Hanoi-listed
stocks (EIB.VN, SSI.VN). That needs per-constituent conversion inside
composite_builder.py before a single blended-index FX rate even makes
sense here -- see composite_builder.py's CROSS_CURRENCY_COMPOSITES note.
"""

from typing import Optional

import pandas as pd

import price_cache

CURRENCY_MAP = {
    'Euro Stoxx 50': 'EUR',
    'Nikkei 225': 'JPY',
    'CSI 300': 'CNY',
    'Hang Seng': 'HKD',
    'Taiwan (TAIEX)': 'TWD',
    'South Korea (KOSPI)': 'KRW',
    'Indonesia (IDX)': 'IDR',
    'Thailand (SET)': 'THB',
    'Middle East (Tadawul)': 'SAR',
    'Brazil (Bovespa)': 'BRL',
    'Mexico (S&P/BMV IPC)': 'MXN',
    'Africa (FTSE/JSE Top 40)': 'ZAR',
    # Vietnam: see module docstring -- not eligible for single-rate conversion.
}


def direct_pair_symbol(currency: str) -> str:
    return f"{currency}INR=X"


def bridge_pair_symbol(currency: str) -> str:
    return f"{currency}USD=X"


def fx_symbols_needed() -> list[str]:
    """
    Every FX pair fx.py might need, for merging into the fetch batch upstream
    (data_fetch.symbols_for_resolved_sources()'s output + this list = the
    full symbol set price_cache.refresh_all() should pull). Includes both
    the direct and bridge pair for every currency -- cheap to fetch both,
    and having the bridge cached means a direct-pair outage doesn't block
    the whole category.
    """
    symbols = set()
    for currency in CURRENCY_MAP.values():
        symbols.add(direct_pair_symbol(currency))
        symbols.add(bridge_pair_symbol(currency))
    return sorted(symbols)


def convert_to_inr(local_close: pd.Series, currency: str) -> tuple[pd.Series, str]:
    """Returns (inr_series, method) where method is 'direct' or 'bridged-via-usd'."""
    direct_cache = price_cache.read_cache(direct_pair_symbol(currency))
    if direct_cache is not None and not direct_cache.empty:
        rate = direct_cache['close'].reindex(local_close.index).ffill()
        return local_close * rate, 'direct'

    usdinr_cache = price_cache.read_cache('INR=X')
    bridge_cache = price_cache.read_cache(bridge_pair_symbol(currency))
    if usdinr_cache is not None and bridge_cache is not None and not bridge_cache.empty:
        local_to_usd = bridge_cache['close'].reindex(local_close.index).ffill()
        usd_to_inr = usdinr_cache['close'].reindex(local_close.index).ffill()
        return local_close * local_to_usd * usd_to_inr, 'bridged-via-usd'

    raise ValueError(
        f"No FX path to INR for {currency} -- need either {direct_pair_symbol(currency)} "
        f"or both {bridge_pair_symbol(currency)} and INR=X cached. Run price_cache.refresh_all() "
        f"with fx_symbols_needed() included in the batch."
    )


def build_dual_series(category_name: str, local_close: pd.Series) -> dict:
    """
    Returns {'local': pd.Series, 'inr': pd.Series, 'fx_method': str, 'currency': str}.
    Raises KeyError if category_name isn't in CURRENCY_MAP (Vietnam, or a
    category outside Global Markets that shouldn't be calling this at all).
    """
    if category_name not in CURRENCY_MAP:
        raise KeyError(
            f"{category_name} has no registered currency in CURRENCY_MAP -- "
            f"not eligible for dual-series FX conversion (see module docstring re: Vietnam)"
        )
    currency = CURRENCY_MAP[category_name]
    inr_series, method = convert_to_inr(local_close, currency)
    return {'local': local_close, 'inr': inr_series, 'fx_method': method, 'currency': currency}


if __name__ == '__main__':
    import sys
    sys.path.insert(0, '.')
    from data_hierarchy import resolve_all

    resolved = resolve_all()
    global_markets = [r for r in resolved if r.group == 'global-markets']
    print(f"{len(global_markets)} Global Markets categories")
    print(f"FX symbols needed for fetch batch: {len(fx_symbols_needed())}")
    for sym in fx_symbols_needed():
        print(f"  {sym}")

    for r in global_markets:
        if r.name not in CURRENCY_MAP:
            print(f"  SKIP {r.name}: not in CURRENCY_MAP")
            continue
        cached = price_cache.read_cache(r.symbol) if r.symbol else None
        if cached is None:
            print(f"  NO DATA {r.name}: {r.symbol} not cached yet")
            continue
        try:
            dual = build_dual_series(r.name, cached['close'])
            print(f"  OK {r.name}: {dual['currency']} -> INR via {dual['fx_method']}")
        except Exception as e:
            print(f"  FAIL {r.name}: {e}")
