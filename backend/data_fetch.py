"""
data_fetch.py -- pulls raw daily OHLCV for a resolved instrument.

Consumes the ticker symbols that data_hierarchy.resolve_all() decided to use
(and, for composites, every constituent). Writes nothing itself -- returns
FetchResult objects that price_cache.py persists. This module's only job is
"get bars for a symbol reliably or fail loudly," nothing else.

Provider: yfinance (unofficial Yahoo Finance data). Matches the ticker
conventions already in sources.py -- .NS suffix for NSE equities/ETFs,
^ prefix for indices, =F for futures, =X for FX pairs.

Network reality: yfinance is unofficial and best-effort. Expect intermittent
failures, especially on thinly-traded NSE ETFs. This module retries with
backoff and reports per-symbol success/failure rather than failing an entire
batch on one bad ticker -- deciding whether a partial batch is good enough to
deploy is quality_guard.py's job, not this module's.

NOTE ON THIS ENVIRONMENT: built and syntax/logic-tested here, but this sandbox
can't reach Yahoo Finance (only PyPI/GitHub domains are network-reachable) --
so the live fetch path is unverified against a real response until it runs
inside the GitHub Actions runner, which has open internet. The incremental
caching logic in price_cache.py IS tested here, with synthetic data standing
in for fetch_symbol()'s output -- see test_price_cache.py.
"""

import logging
import re
import time
from dataclasses import dataclass
from datetime import date
from typing import Optional

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
BACKOFF_SECONDS = 2.0          # linear backoff: 2s, 4s, 6s between retries on the same symbol
REQUEST_PAUSE_SECONDS = 0.5    # pause between symbols regardless of outcome -- avoid batch rate-limiting


@dataclass
class FetchResult:
    symbol: str
    ok: bool
    bars: Optional[pd.DataFrame]   # columns: open, high, low, close, volume; index: date (no intraday timestamp)
    rows: int
    first_date: Optional[date]
    last_date: Optional[date]
    error: Optional[str] = None



# Bare (no-dot) composite constituents that are NOT NSE stocks and must not
# get '.NS' appended -- e.g. VNM is the US-listed VanEck Vietnam ETF (NYSE
# Arca), quoted as plain 'VNM' on Yahoo. Without this exemption,
# to_yf_symbol() below silently mis-requests 'VNM.NS' (empty/wrong
# instrument) since VNM has no dot and doesn't match the ^/=F/=X patterns.
# Add to this set, don't touch the suffix logic below, whenever a composite
# constituent is deliberately non-NSE.
NON_NSE_BARE_SYMBOLS = {'VNM'}


def to_yf_symbol(raw_symbol: str, default_exchange_suffix: str = '.NS') -> str:
    """
    sources.py stores composite constituents as bare NSE codes (e.g. 'SBIN',
    'M&M') since that's the natural label for display/weighting -- but
    yfinance needs the exchange suffix. Indices (^...), futures (...=F), and
    FX (...=X) are already in yfinance's own format and pass through as-is.
    A small explicit exemption list (NON_NSE_BARE_SYMBOLS) covers bare
    non-NSE tickers like VNM that would otherwise be misdetected as NSE
    stocks just because they contain no dot.
    """
    if raw_symbol.startswith('^') or raw_symbol.endswith('=F') or raw_symbol.endswith('=X'):
        return raw_symbol
    if raw_symbol in NON_NSE_BARE_SYMBOLS:
        return raw_symbol
    if '.' in raw_symbol:  # already has an exchange suffix (e.g. NIFTYBEES.NS, ^SET.BK)
        return raw_symbol
    return f"{raw_symbol}{default_exchange_suffix}"



# Some symbols throw on a full 'period=max' pull even though the ticker and
# its history are genuinely valid (confirmed by checking Yahoo's own web UI
# for these exact symbols) -- yfinance's max-period metadata resolution is
# what's actually broken, not the data. Two known error signatures so far:
#   1. Ambiguous-DST timestamps on very long histories (e.g. ^BVSP pre-2000)
#   2. "Period 'max' is invalid, must be one of: 1d, 5d" on certain NSE
#      strategy-index quotes (e.g. NIFTY_LARGEMID250.NS, NIFTY_MICROCAP250.NS)
#      -- Yahoo's web UI serves full history for these, but the max-range API
#      call yfinance uses to resolve valid periods fails for this quoteType.
# Retrying once with a bounded start date works around both. This is a
# workaround, not a confirmed root cause for case 2 -- verify with
# tools/find_tickers.py's bounded_history_check() if it recurs on new
# symbols, and widen the signature list below if a new error message shows
# up for the same underlying pattern.
FULL_HISTORY_FALLBACK_START = date(2000, 1, 1)
_FULL_HISTORY_ERROR_SIGNATURES = (
    'cannot infer dst', 'ambiguous',              # case 1
    "period 'max' is invalid",                     # case 2
)


def fetch_symbol(symbol: str, start: Optional[date] = None, end: Optional[date] = None) -> FetchResult:
    """
    Fetch daily OHLCV for one symbol. `start=None` pulls full available
    history (initial backfill). A real `start` (last cached date + 1) is
    what incremental runs pass -- see price_cache.update_symbol().
    """
    yf_symbol = to_yf_symbol(symbol)
    last_error = None
    effective_start = start
    full_history_fallback_tried = False

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            ticker = yf.Ticker(yf_symbol)
            df = ticker.history(
                start=effective_start.isoformat() if effective_start else None,
                end=end.isoformat() if end else None,
                period='max' if effective_start is None else None,
                auto_adjust=True,   # split/dividend-adjusted close -- makes a single instrument's
                                     # series usable for return calculations without a separate
                                     # corporate-action step. Composites still need their own
                                     # adjustment across constituents -- that's composite_builder.py.
                actions=False,
            )
            if df.empty:
                # yfinance doesn't always raise here -- for some quoteTypes
                # (seen on NSE strategy-index quotes) it just logs a warning
                # internally ("Period 'max' is invalid...") and hands back an
                # empty frame with no exception at all. So this can't be
                # caught in the except block below -- it needs its own
                # bounded-range retry, same fallback, different trigger.
                if not full_history_fallback_tried and (effective_start is None or effective_start < FULL_HISTORY_FALLBACK_START):
                    effective_start = FULL_HISTORY_FALLBACK_START
                    full_history_fallback_tried = True
                    logger.warning(f"[{yf_symbol}] empty response on full-history pull (no exception raised -- "
                                    f"likely a period='max' incompatibility for this quoteType); "
                                    f"retrying from {FULL_HISTORY_FALLBACK_START.isoformat()}")
                    continue
                return FetchResult(
                    symbol=symbol, ok=False, bars=None, rows=0, first_date=None, last_date=None,
                    error=f"empty response for {yf_symbol} -- delisted, wrong ticker, or no data in range "
                          f"(bounded-range retry also empty)" if full_history_fallback_tried else
                          f"empty response for {yf_symbol} -- delisted, wrong ticker, or no data in range",
                )

            df = df.rename(columns=str.lower)[['open', 'high', 'low', 'close', 'volume']]
            # Keep a real DatetimeIndex (normalized to midnight, no intraday
            # component) rather than degrading to a plain object Index of
            # datetime.date -- resample()/PeriodIndex() downstream (trend.py,
            # position.py, volatility.py, seasonality.py, composite_builder.py's
            # quarterly rebalance) all require an actual DatetimeIndex and raise
            # "Only valid with DatetimeIndex..." on anything less.
            df.index = pd.to_datetime(df.index).normalize()
            if df.index.tz is not None:
                df.index = df.index.tz_localize(None)
            df.index.name = 'date'

            return FetchResult(
                symbol=symbol, ok=True, bars=df, rows=len(df),
                first_date=df.index.min(), last_date=df.index.max(),
            )
        except Exception as e:
            last_error = str(e)
            logger.warning(f"[{yf_symbol}] attempt {attempt}/{MAX_RETRIES} failed: {last_error}")
            is_full_history_issue = any(sig in last_error.lower() for sig in _FULL_HISTORY_ERROR_SIGNATURES)
            if is_full_history_issue and not full_history_fallback_tried and (effective_start is None or effective_start < FULL_HISTORY_FALLBACK_START):
                # Same request will fail identically on plain retry -- jump
                # straight to the bounded start instead of burning the
                # remaining MAX_RETRIES attempts on an unwinnable call.
                effective_start = FULL_HISTORY_FALLBACK_START
                full_history_fallback_tried = True
                logger.warning(f"[{yf_symbol}] full-history pull failed ({last_error}); retrying from {FULL_HISTORY_FALLBACK_START.isoformat()}")
                continue
            if attempt < MAX_RETRIES:
                time.sleep(BACKOFF_SECONDS * attempt)
        finally:
            time.sleep(REQUEST_PAUSE_SECONDS)

    return FetchResult(symbol=symbol, ok=False, bars=None, rows=0,
                        first_date=None, last_date=None, error=last_error)


def fetch_batch(symbols: list[str], start: Optional[date] = None, end: Optional[date] = None) -> dict[str, FetchResult]:
    """
    Sequential, not yf.download() bulk mode -- bulk mode silently drops bad
    tickers from the combined result in some yfinance versions, which makes
    per-symbol failure attribution hard. At ~70 categories x ~1-2 symbols
    each (composite constituents included), sequential fetch with the pause
    above comfortably fits inside a single Actions job's time budget.
    """
    results = {}
    for sym in symbols:
        results[sym] = fetch_symbol(sym, start=start, end=end)
        status = 'ok' if results[sym].ok else f"FAILED: {results[sym].error}"
        logger.info(f"[{sym}] {status} ({results[sym].rows} rows)")
    return results


def symbols_for_resolved_sources(resolved) -> list[str]:
    """
    Flatten a list of ResolvedSource (from data_hierarchy.resolve_all()) into
    the unique set of tickers that need fetching -- one symbol for
    etf/benchmark/futures/fx resolutions, every constituent for composites.
    De-duplicated, so a stock appearing in two different composites is only
    fetched once.
    """
    symbols = set()
    for r in resolved:
        if r.symbol:
            symbols.add(r.symbol)
        if r.constituents:
            symbols.update(r.constituents)
    return sorted(symbols)


if __name__ == '__main__':
    import sys
    sys.path.insert(0, '.')
    from data_hierarchy import resolve_all

    logging.basicConfig(level=logging.INFO, format='%(message)s')
    resolved = resolve_all()
    symbols = symbols_for_resolved_sources(resolved)
    print(f"{len(symbols)} unique symbols to fetch across {len(resolved)} categories")

    results = fetch_batch(symbols)
    ok = sum(1 for r in results.values() if r.ok)
    print(f"{ok}/{len(symbols)} fetched successfully")
    for sym, r in results.items():
        if not r.ok:
            print(f"  FAILED: {sym} -- {r.error}")
