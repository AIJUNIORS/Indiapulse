"""Structural tests for backend/sources.py -- no network calls.

These check the shape of SOURCE_REGISTRY itself: every entry has a
valid source type, CUSTOM entries have real constituent lists, and
only the known/accepted unmapped symbols are None. This is meant to
catch the exact class of bug this project already hit twice
(typo'd tickers, wrong-index duplicates, silently-empty CUSTOM
baskets) without needing live Yahoo access.
"""
from backend.sources import (
    SOURCE_REGISTRY,
    get_source,
    get_yfinance_ticker,
    get_provider_for_asset_class,
)

VALID_SOURCE_TYPES = {"INDEX", "ETF", "FUTURE", "CUSTOM", "EXTERNAL", "FX"}

# Confirmed via discover_tickers.py / verify_proxy_tickers.py to have no
# real ticker available. Any None NOT in this set is a regression.
ACCEPTED_UNMAPPED = {"GROWTH", "LOWBETA", "GSEC813"}


def test_every_entry_has_valid_source_type_or_is_accepted_none():
    for symbol, entry in SOURCE_REGISTRY.items():
        if entry is None:
            assert symbol in ACCEPTED_UNMAPPED, (
                f"{symbol} is unmapped (None) but not in the accepted list -- "
                f"either it's a new regression or ACCEPTED_UNMAPPED needs updating"
            )
            continue
        assert entry.get("source") in VALID_SOURCE_TYPES, (
            f"{symbol} has unknown source type: {entry.get('source')}"
        )


def test_custom_entries_have_at_least_two_symbols():
    for symbol, entry in SOURCE_REGISTRY.items():
        if entry and entry.get("source") == "CUSTOM":
            symbols = entry.get("symbols") or []
            assert len(symbols) >= 2, (
                f"{symbol} is CUSTOM but has fewer than 2 constituents "
                f"(a 1-stock basket isn't a meaningful index proxy)"
            )
            assert entry.get("method") == "equal_weight", (
                f"{symbol} CUSTOM entry missing/unexpected 'method'"
            )


def test_index_and_etf_entries_have_nonempty_ticker():
    # BHARATBOND2030/2031 are ETF-sourced but genuinely still need the
    # fund's ISIN-based ticker (not the generic bond name) -- open item,
    # same status as GROWTH/LOWBETA/GSEC813, not a regression.
    accepted_missing_ticker = {"BHARATBOND2030", "BHARATBOND2031"}
    for symbol, entry in SOURCE_REGISTRY.items():
        if entry and entry.get("source") in ("INDEX", "ETF", "FUTURE", "FX"):
            ticker = entry.get("ticker")
            if symbol in accepted_missing_ticker:
                continue
            assert ticker, f"{symbol} is {entry['source']} but has no ticker set"
            assert isinstance(ticker, str) and len(ticker) > 0


def test_external_entries_have_provider():
    for symbol, entry in SOURCE_REGISTRY.items():
        if entry and entry.get("source") == "EXTERNAL":
            assert entry.get("provider"), f"{symbol} is EXTERNAL but has no provider set"


def test_get_source_returns_none_for_unknown_symbol():
    assert get_source("NOT_A_REAL_SYMBOL_XYZ") is None


def test_get_yfinance_ticker_only_for_ticker_backed_sources():
    # NIFTY50 is INDEX-backed -- should return a ticker
    assert get_yfinance_ticker("NIFTY50") is not None
    # NIFTYPOWER is CUSTOM-backed -- must NOT return a plain ticker,
    # since callers use this specifically to decide "do I need
    # custom_index.py instead of a direct yfinance call"
    assert get_yfinance_ticker("NIFTYPOWER") is None


def test_no_duplicate_tickers_across_unrelated_categories():
    """Catch the exact bug class this project hit before: two
    genuinely different symbols silently sharing one ticker without
    an explicit '# intentional dup' comment nearby is a regression,
    not a design choice. This test can't read comments, so it only
    flags NEW duplicates beyond a known-intentional allowlist --
    update the allowlist deliberately, don't silence this test.
    """
    intentional_dup_tickers = {
        "^CNXAUTO", "^CNXCONSUM", "^CNXINFRA", "^CNXPSE", "^CRSLDX",
        "NIFTY_FIN_SERVICE.NS", "NIFTY_INDIA_MFG.NS", "PHARMABEES.NS",
        "TNIDETF.NS", "DIVOPPBEES.NS", "^CNXMNC", "LIQUIDBEES.NS",
    }
    seen: dict[str, list[str]] = {}
    for symbol, entry in SOURCE_REGISTRY.items():
        if entry and entry.get("source") in ("INDEX", "ETF", "FUTURE", "FX"):
            t = entry.get("ticker")
            if t:
                seen.setdefault(t, []).append(symbol)

    unexpected_dups = {
        t: syms for t, syms in seen.items()
        if len(syms) > 1 and t not in intentional_dup_tickers
    }
    assert not unexpected_dups, f"Unreviewed duplicate tickers found: {unexpected_dups}"


def test_get_provider_for_asset_class_unknown_defaults_safely():
    assert get_provider_for_asset_class("NotARealAssetClass") == "unknown"
