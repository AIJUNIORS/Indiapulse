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


def _inr_rate_series(index: pd.Index, currency: str) -> tuple[pd.Series, str]:
    """
    The shared rate lookup behind both convert_to_inr() (close-only) and
    convert_ohlc_to_inr() (full OHLC) -- factored out so both apply the
    EXACT same per-day rate rather than two independently-reindexed/ffilled
    copies that could silently drift apart on edge dates (a holiday gap
    filled slightly differently, etc.). Returns (rate_series, method).
    """
    direct_cache = price_cache.read_cache(direct_pair_symbol(currency))
    if direct_cache is not None and not direct_cache.empty:
        return direct_cache['close'].reindex(index).ffill(), 'direct'

    usdinr_cache = price_cache.read_cache('INR=X')
    bridge_cache = price_cache.read_cache(bridge_pair_symbol(currency))
    if usdinr_cache is not None and bridge_cache is not None and not bridge_cache.empty:
        local_to_usd = bridge_cache['close'].reindex(index).ffill()
        usd_to_inr = usdinr_cache['close'].reindex(index).ffill()
        return local_to_usd * usd_to_inr, 'bridged-via-usd'

    raise ValueError(
        f"No FX path to INR for {currency} -- need either {direct_pair_symbol(currency)} "
        f"or both {bridge_pair_symbol(currency)} and INR=X cached. Run price_cache.refresh_all() "
        f"with fx_symbols_needed() included in the batch."
    )


def convert_usd_to_inr(usd_close: pd.Series) -> pd.Series:
    """
    USD -> INR via the 'INR=X' series already cached for the broad-market
    USD/INR category (sources.py's own entry uses that exact symbol -- NOT
    direct_pair_symbol('USD') == 'USDINR=X', which is a different, uncached
    ticker convention). This is its own function rather than a CURRENCY_MAP
    entry because Vietnam's composite is a synthetic close-only series built
    entirely in composite_builder.py (build_vietnam_composite), not a single
    cached instrument with a 'high'/'low' -- convert_ohlc_to_inr() doesn't
    apply here, and going through build_dual_series()/CURRENCY_MAP would
    have incorrectly tried the 'USDINR=X' direct-pair symbol first.
    """
    usdinr_cache = price_cache.read_cache('INR=X')
    if usdinr_cache is None or usdinr_cache.empty:
        raise ValueError("No cached INR=X -- run price_cache.refresh_all() first")
    rate = usdinr_cache['close'].reindex(usd_close.index).ffill()
    return usd_close * rate


def convert_to_inr(local_close: pd.Series, currency: str) -> tuple[pd.Series, str]:
    """Returns (inr_series, method) where method is 'direct' or 'bridged-via-usd'."""
    rate, method = _inr_rate_series(local_close.index, currency)
    return local_close * rate, method


def convert_ohlc_to_inr(ohlc: pd.DataFrame, currency: str) -> tuple[pd.DataFrame, str]:
    """
    Converts every price column present ('open'/'high'/'low'/'close') using
    the SAME day's rate as convert_to_inr() would use for 'close' alone.
    This matters because ATR%/SMI (volatility.py, technicals.py) compute
    true-range from high/low against the prior close -- converting close
    to INR while leaving high/low in local currency would corrupt that
    range math (mixing two different currency scales in one subtraction).
    'volume' (share count, not a price) is left untouched.
    Returns (converted_df, method) -- same method convention as convert_to_inr().
    """
    if 'close' not in ohlc.columns:
        raise ValueError("convert_ohlc_to_inr() requires a 'close' column")
    rate, method = _inr_rate_series(ohlc.index, currency)
    converted = ohlc.copy()
    for col in ('open', 'high', 'low', 'close'):
        if col in converted.columns:
            converted[col] = converted[col] * rate
    return converted, method


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
