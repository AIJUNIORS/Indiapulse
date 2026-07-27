#!/usr/bin/env python3
"""
Ticker discovery for the 6 symbols still mapped to None in sources.py:
NIFTYPOWER, TOURISM, LOWBETA, GROWTH, GSEC10Y, GSEC813.

Report-only -- does NOT write into sources.py. These were left unmapped
on purpose ("do NOT guess a ticker") after earlier blind guesses caused
duplicate/wrong mappings, so any candidate here needs a human look
before landing in the map.

Two kinds of candidates tested per symbol:
  - INDEX/ETF ticker guesses (same pattern as verify_proxy_tickers.py)
  - For symbols where no confirmed index/ETF is likely to exist, a
    CUSTOM equal-weight basket of real constituent stocks, matching
    the pattern already used elsewhere in sources.py (e.g.
    NIFTYCONSTRUCTION, NIFTYHOTELS, NIFTYSHIPPING, MOBILITY).

Run where yfinance has real Yahoo access:
    python scripts/discover_tickers.py
"""
import yfinance as yf

MIN_ROWS = 250

INDEX_ETF_CANDIDATES = {
    "NIFTYPOWER": ["NIFTY_POWER.NS", "NIFTYPOWER.NS", "PSUBNKBEES.NS"],
    "GROWTH": ["NIFTYGS15.NS", "GROWTHSECT.NS"],
    "LOWBETA": ["NIFTYLOWVOL30.NS", "LOWBETA.NS"],
    "GSEC10Y": ["0P0001CGJ2.BO", "GSEC10YEAR.NS"],
    "GSEC813": ["0P0001CGJ3.BO"],
    "TOURISM": ["THOMASCOOK.NS"],
}

CUSTOM_BASKET_CANDIDATES = {
    "NIFTYPOWER": ["NTPC.NS", "POWERGRID.NS", "TATAPOWER.NS", "ADANIPOWER.NS"],
    "TOURISM": ["THOMASCOOK.NS", "IRCTC.NS", "EASEMYTRIP.NS"],
    "GROWTH": None,
    "LOWBETA": None,
    "GSEC10Y": None,
    "GSEC813": None,
}


def test_ticker(t, period="2y"):
    try:
        hist = yf.Ticker(t).history(period=period)
        if hist.empty:
            return "EMPTY"
        return f"OK ({len(hist)} rows)" if len(hist) >= MIN_ROWS else f"THIN ({len(hist)} rows)"
    except Exception as e:
        return f"FAIL ({e})"


if __name__ == "__main__":
    for symbol, tickers in INDEX_ETF_CANDIDATES.items():
        print(f"\n{symbol} -- index/ETF candidates:")
        for t in tickers:
            print(f"  {t:24s} {test_ticker(t)}")

        basket = CUSTOM_BASKET_CANDIDATES.get(symbol)
        if basket:
            print(f"{symbol} -- CUSTOM basket candidates (equal_weight fallback):")
            for t in basket:
                print(f"  {t:24s} {test_ticker(t)}")
        elif symbol in ("GROWTH", "LOWBETA", "GSEC10Y", "GSEC813"):
            print(f"  (no basket attempted -- {symbol} is a factor/bond, not a sector; needs human judgment)")
