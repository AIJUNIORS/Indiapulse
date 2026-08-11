"""
find_tickers.py -- use yfinance's own Search (Yahoo's autocomplete/search
API) to find the real ticker for a name, instead of guessing suffix
patterns. Run this for anything check_tickers.py reports as EMPTY, 404, or
a weird period/metadata error -- those are exactly the cases where another
guessed '.NS'/'.BO'/etc suffix is more likely to be wrong again than right.

Usage:
    pip install yfinance
    python find_tickers.py
"""

import yfinance as yf

QUERIES = [
    "Nifty LargeMidcap 250",
    "Nifty Microcap 250",
    "Nifty200 Momentum 30",
]


def search(query: str) -> None:
    print(f"\n--- '{query}' ---")
    try:
        results = yf.Search(query, max_results=8).quotes
    except Exception as e:
        print(f"  Search failed: {e}")
        return

    if not results:
        print("  No results.")
        return

    for r in results:
        print(f"  {r.get('symbol', '?'):25} {r.get('shortname', r.get('longname', '?'))!r:45} "
              f"exch={r.get('exchange', '?')} type={r.get('quoteType', '?')}")


def bounded_history_check(symbol: str) -> None:
    """For symbols that failed with 'Period max is invalid' rather than a
    clean 404 -- try an explicit bounded start/end instead of period='max',
    in case the symbol IS valid but yfinance's max-period metadata lookup
    is what's actually broken."""
    print(f"\n--- bounded-range check: {symbol} ---")
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(start="2023-01-01", end="2026-08-10", auto_adjust=True, actions=False)
        if df.empty:
            print("  Still empty with explicit bounded range.")
        else:
            print(f"  OK with bounded range: {len(df)} rows, "
                  f"{df.index.min().date()} to {df.index.max().date()}")
    except Exception as e:
        print(f"  Still fails: {e}")


if __name__ == "__main__":
    for q in QUERIES:
        search(q)

    for sym in ["NIFTY_LARGEMID250.NS", "NIFTY_MICROCAP250.NS"]:
        bounded_history_check(sym)
