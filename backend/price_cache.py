"""
price_cache.py -- persists data_fetch.py results to data/cache/raw/*.parquet
and does incremental (not full-refetch) updates on every scheduled run.

Design: each Actions run restores the previous run's data/cache/ (via an
Actions cache action or artifact -- it's generated output, not committed to
main per the architecture doc S1/S8). This module doesn't care whether that
restore happened or not -- it reads whatever's on disk, fetches only what's
missing since the last cached date, and writes back. First-ever run (nothing
cached) transparently falls back to a full backfill per symbol.

Why incremental matters here specifically: yfinance's full-history pull for
~90 symbols (70 categories, several multi-constituent composites) is the
slow, rate-limit-risking path. A daily run only needs 1-2 new bars per
symbol -- incremental fetch is what keeps the daily workflow fast and
polite to the (unofficial, rate-limit-sensitive) provider.
"""

import re
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd

from data_fetch import FetchResult, fetch_symbol

CACHE_DIR = Path('data/cache/raw')


def _cache_path(symbol: str) -> Path:
    """Sanitize a ticker into a filesystem-safe filename: ^CRSLDX -> _CRSLDX.parquet, INR=X -> INR_X.parquet"""
    safe = re.sub(r'[^A-Za-z0-9.]', '_', symbol)
    return CACHE_DIR / f"{safe}.parquet"


def read_cache(symbol: str) -> Optional[pd.DataFrame]:
    path = _cache_path(symbol)
    if not path.exists():
        return None
    return pd.read_parquet(path)


def write_cache(symbol: str, df: pd.DataFrame) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    df.sort_index().to_parquet(_cache_path(symbol))


def update_symbol(symbol: str, today: Optional[date] = None) -> dict:
    """
    Incremental fetch for one symbol: read what's cached, fetch only the
    gap, append, de-dupe (keeping the newer row on overlap -- covers the
    case where yfinance revises a recent bar, e.g. post-close adjustments),
    write back. Falls back to a full backfill if nothing's cached yet.

    `today` is injectable for testing; defaults to the real current date.
    """
    today = today or date.today()
    existing = read_cache(symbol)
    start = None

    if existing is not None and len(existing) > 0:
        last_date = existing.index.max()
        start = last_date + timedelta(days=1)
        if start > today:
            return {'symbol': symbol, 'status': 'up-to-date', 'rows_added': 0, 'total_rows': len(existing)}

    result: FetchResult = fetch_symbol(symbol, start=start)

    if not result.ok:
        return {
            'symbol': symbol, 'status': 'fetch-failed', 'error': result.error,
            'rows_added': 0, 'total_rows': len(existing) if existing is not None else 0,
        }

    if existing is not None:
        combined = pd.concat([existing, result.bars])
        combined = combined[~combined.index.duplicated(keep='last')].sort_index()
    else:
        combined = result.bars

    write_cache(symbol, combined)
    prior_rows = len(existing) if existing is not None else 0
    return {'symbol': symbol, 'status': 'updated', 'rows_added': len(combined) - prior_rows, 'total_rows': len(combined)}


def refresh_all(symbols: list[str]) -> list[dict]:
    return [update_symbol(s) for s in symbols]


def summarize(results: list[dict]) -> str:
    updated = [r for r in results if r['status'] == 'updated']
    uptodate = [r for r in results if r['status'] == 'up-to-date']
    failed = [r for r in results if r['status'] == 'fetch-failed']
    lines = [
        f"{len(updated)} updated, {len(uptodate)} already current, {len(failed)} failed "
        f"(of {len(results)} total)",
    ]
    if failed:
        lines.append("Failures (pipeline.py's quality_guard.py decides if this blocks deploy):")
        lines.extend(f"  {r['symbol']}: {r['error']}" for r in failed)
    return '\n'.join(lines)


if __name__ == '__main__':
    import sys
    sys.path.insert(0, '.')
    from data_hierarchy import resolve_all
    from data_fetch import symbols_for_resolved_sources
    import fx
    from composite_builder import vietnam_fx_symbols_needed

    resolved = resolve_all()
    # fx.fx_symbols_needed() and vietnam_fx_symbols_needed() were previously
    # never actually merged in here despite fx.py's own docstring assuming
    # they would be -- Global Markets INR conversion and the Vietnam
    # composite fix both silently depended on FX pairs that this script
    # never fetched. Fixed: merge all three symbol sources into one batch.
    symbols = sorted(set(symbols_for_resolved_sources(resolved))
                      | set(fx.fx_symbols_needed())
                      | set(vietnam_fx_symbols_needed()))
    print(f"Refreshing cache for {len(symbols)} symbols...")

    summary = refresh_all(symbols)
    print(summarize(summary))
