"""
check_tickers.py -- standalone local sanity check for every ticker touched
by the recent sources.py / data_fetch.py fixes.

Run this on a machine with real internet access (this sandbox has none --
see data_fetch.py's module docstring). It does NOT touch the rest of the
pipeline, the cache, or quality_guard -- it's a pure "does yfinance return
something sane for this exact symbol" check, so you can confirm each fix
before pushing and burning an Actions run on it.

Usage:
    pip install yfinance pandas
    python check_tickers.py            # checks every symbol below
    python check_tickers.py TMPV.NS    # check just one symbol

What it reports per symbol:
    - whether yfinance returned any rows at all
    - first/last date in the returned history (so you can eyeball whether
      "24.1 years" or "newly listed" claims actually hold up)
    - row count
    - the specific DST-ambiguous error, if it's the Brazil-style failure
    - anything else, printed as-is so you're not guessing at causes
"""

import sys
from datetime import date

import yfinance as yf


# Every symbol touched by the recent fix, grouped by what's being checked.
# Add to this dict as new candidates come up -- it's meant to be a running
# scratchpad, not a one-shot list.
CHECKS = {
    "NIFTY strategy indices (were '^X', now 'X.NS')": [
        "NIFTY_LARGEMID250.NS",
        "NIFTY_MICROCAP250.NS",
        "NIFTY200MOMENTM30.NS",   # fixed: no underscore, 'MOMENTM' not 'MOMENTUM'
        "MOMOMENTUM.NS",          # ETF proxy fallback -- need its actual history_years
    ],
    "Vietnam composite (was '.HM', now '.VN'; VNM bare, no suffix)": [
        "VNM",
        "EIB.VN",
        "SSI.VN",
    ],
    "Amara Raja rename (AMARAJABAT -> ARE&M, Oct 2023)": [
        "ARE&M.NS",
    ],
    "EV Ecosystem: TMPV vs TATAMOTORS -- confirm ticker + how much history TMPV actually has": [
        "TMPV.NS",
        "TATAMOTORS.NS",   # kept for comparison -- see note below
        "M&M.NS",
        "BAJAJ-AUTO.NS",
        "EXIDEIND.NS",
    ],
    "Brazil DST-ambiguous full-history pull": [
        "^BVSP",
    ],
    "Mutual-fund NAV fallbacks for LargeMidcap 250 / Microcap 250 -- ASSIGNMENT UNCONFIRMED, see identify_fund() output below": [
        "0P0001NQZ5.BO",   # assumed LargeMidcap 250, per the order given -- NOT verified
        "0P0001R64W.BO",   # assumed Microcap 250, per the order given -- NOT verified
    ],
}


def identify_fund(symbol: str) -> None:
    """
    0P-prefixed symbols are Yahoo's internal mutual-fund identifiers -- the
    symbol string itself carries no readable meaning, unlike 'TATAMOTORS.NS'.
    This prints whatever name/category fields Yahoo has for it so you can
    confirm which real-world fund it actually is before trusting the
    LargeMidcap-vs-Microcap assignment made in sources.py.
    """
    print(f"\n--- identify: {symbol} ---")
    try:
        info = yf.Ticker(symbol).get_info()
    except Exception as e:
        print(f"  Could not fetch info: {e}")
        return
    for field in ("longName", "shortName", "category", "fundFamily", "legalType"):
        if info.get(field):
            print(f"  {field}: {info[field]}")
    if not any(info.get(f) for f in ("longName", "shortName")):
        print("  No name fields returned -- info dict may be empty/blocked; "
              "check manually in a browser at the Yahoo URL for this symbol.")


def check_symbol(symbol: str) -> None:
    print(f"\n--- {symbol} ---")
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="max", auto_adjust=True, actions=False)
    except Exception as e:
        msg = str(e)
        if ("ambiguous" in msg.lower() or "cannot infer dst" in msg.lower()
                or "period 'max' is invalid" in msg.lower()):
            print(f"  FULL-HISTORY-PULL ERROR (matches data_fetch.py's fallback trigger): {msg}")
            print("  Retrying bounded from 2000-01-01 -- this is the SAME retry data_fetch.py")
            print("  actually performs in production, so this result tells us whether that")
            print("  fix genuinely works, not just whether period='max' happens to fail.")
            try:
                df2 = ticker.history(start="2000-01-01", auto_adjust=True, actions=False)
                if df2.empty:
                    print("  -> still empty after bounding start date.")
                else:
                    print(f"  -> bounded pull worked: {len(df2)} rows, "
                          f"{df2.index.min().date()} to {df2.index.max().date()}")
            except Exception as e2:
                print(f"  -> bounded retry also failed: {e2}")
        else:
            print(f"  EXCEPTION: {msg}")
        return

    if df.empty:
        print("  EMPTY -- delisted, wrong ticker, or no data in range.")
        return

    first, last = df.index.min().date(), df.index.max().date()
    years = (last - first).days / 365.25
    print(f"  OK: {len(df)} rows, {first} to {last} (~{years:.1f} years of history)")
    if years < 3:
        print(f"  NOTE: under the 3yr floor -- can't be used as etf/benchmark tier, "
              f"composite-only per resolve_source()'s MIN_HISTORY_YEARS rule.")


def main() -> None:
    if len(sys.argv) > 1:
        for sym in sys.argv[1:]:
            check_symbol(sym)
        return

    for label, symbols in CHECKS.items():
        print(f"\n{'=' * 70}\n{label}\n{'=' * 70}")
        for sym in symbols:
            check_symbol(sym)

    print(f"\n{'=' * 70}\nFund identification (0P... symbols)\n{'=' * 70}")
    for sym in ("0P0001NQZ5.BO", "0P0001R64W.BO"):
        identify_fund(sym)

    print(f"\n{'=' * 70}")
    print("Run finished. Things to eyeball in the output above:")
    print("  1. Did all three NIFTY_*.NS symbols return real rows? If any is")
    print("     EMPTY, that specific '.NS' guess was wrong -- needs a different")
    print("     symbol format, not necessarily a composite fallback.")
    print("  2. Does TMPV.NS actually exist and how many years of history does")
    print("     it have? If it's brand new (a few months), decide whether a")
    print("     sub-3yr composite constituent is acceptable here or whether")
    print("     TATAMOTORS should stay until TMPV clears more history.")
    print("  3. Did ^BVSP hit the DST-ambiguous error, and did the bounded")
    print("     2000-01-01 retry actually fix it?")
    print("  4. Do the identify_fund() names above actually confirm")
    print("     0P0001NQZ5.BO = LargeMidcap 250 and 0P0001R64W.BO = Microcap 250?")
    print("     If they're swapped or something else entirely, fix the")
    print("     assignment in sources.py before trusting either -- that")
    print("     assignment was a guess based on the order given, not verified.")


if __name__ == "__main__":
    main()
