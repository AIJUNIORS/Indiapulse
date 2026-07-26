#!/usr/bin/env python3
"""
IndiaPulse - Provider Registry & Symbol Mapping
Milestone 4 - Data Download Engine (v3 - structured source registry)

Maps each asset class / category to a download provider, and maps our
internal universe symbols to a typed *source descriptor* instead of a
bare ticker string. This lets the download engine (backend/download.py)
decide *how* to fetch a symbol without embedding special cases:

    {"source": "INDEX",    "ticker": "^NSEI"}
    {"source": "ETF",      "ticker": "PHARMABEES.NS"}
    {"source": "FUTURE",   "ticker": "GC=F"}
    {"source": "CUSTOM",   "method": "equal_weight", "symbols": [...]}
    {"source": "EXTERNAL", "provider": "LME"}
    None                                   # not sourced yet -- skip cleanly

Priority order used while building this map (never bridge unrelated
sectors as a proxy -- build a custom index instead):

    Official Yahoo Index -> Official Yahoo ETF -> IndiaPulse Custom
    Index -> External Source -> Manual (None)

CHANGELOG (this revision, superseding the v2 flat YFINANCE_SYMBOL_MAP):
- Replaced bare ticker strings with typed descriptors so download.py,
  custom_index.py and external.py can each own their slice of the
  pipeline instead of the downloader guessing from ticker shape.
- NIFTYMEGA250 and HIGHBETA removed entirely (also removed from the
  universe CSVs) -- no reliable benchmark exists for either; HIGHBETA
  is better computed dynamically from constituent beta, not sourced.
- 8 Industries that were silently duplicating an unrelated category
  (Telecom->Media, Logistics/Shipping->same dup, Aviation/Hotels->dup,
  Construction->Infra, Renewable/Power->Energy, Cable->Metal) now
  resolve to real IndiaPulse Custom Indices (top-3 market leaders,
  equal weighted) built by backend/custom_index.py, per the "never use
  unrelated proxies" rule. NIFTYPOWER has no distinct custom index
  defined yet and is intentionally left unmapped (None) rather than
  re-pointed at Energy.
- MOBILITY promoted from a dup of EV to its own Custom Index (auto
  OEMs), since it's a distinct concept (transportation demand, not
  EV-adoption specifically).
- Verified ETF fallbacks (via scripts/verify_proxy_tickers.py) swapped
  in wherever the matching Yahoo index returns real but too-thin
  history for backtesting: Healthcare/Hospital -> PHARMABEES.NS,
  NIFTYSMALLCAP50 -> SMALLCAP.NS, NIFTYSMALLCAP250 -> HDFCSML250.NS,
  Digital/Internet -> TNIDETF.NS, Manufacturing -> MAKEINDIA.NS,
  ESG -> ESG.NS, Dividend/Dividend50 -> DIVOPPBEES.NS,
  Alpha50 -> ALPL30IETF.NS, Quality30 -> QUAL30IETF.NS,
  Momentum30 -> MOM30IETF.NS, LowVol30 -> LOWVOLIETF.NS,
  EqualWeight -> EQUAL50.NS. Theme "Defence" now uses its own ETF
  (GROWWDEFNC.NS) rather than duplicating the Industry Defence index.
- Removed the "^INR10Y" fixed-income proxies (that ticker is the US
  10-Year Treasury, not an Indian G-Sec series). GSEC10Y/GSEC813/
  CORPBOND are unmapped (None) pending a real NSE G-Sec/corp-bond
  ticker; SDL is routed to the External source (RBI/NSE Debt, not
  yet implemented -- see backend/external.py).
- NICKEL and LEAD routed to the External source (LME) instead of a
  guessed/nonexistent Yahoo futures ticker.
- GROWTH and LOWBETA left unmapped (None): no confirmed distinct
  ticker exists yet for either ("Nifty Growth Sectors 15" and a truly
  distinct low-beta index respectively) -- do not guess.
"""

# ---------------------------------------------------------------------
# Provider registry: which downloader handles which AssetClass
# ---------------------------------------------------------------------

PROVIDERS = {
    "Equity": {
        "provider": "yfinance",
        "description": "NSE indices, ETFs & equities via Yahoo Finance",
    },
    "Bond": {
        "provider": "yfinance",
        "description": "Bond / fixed-income proxies via Yahoo Finance (best-effort)",
    },
    "Commodity": {
        "provider": "yfinance",
        "description": "Commodity futures/spot proxies via Yahoo Finance",
    },
    "Macro": {
        "provider": "manual",
        "description": "Macro series sourced manually / future RBI-MOSPI-GSTN connectors",
    },
}


# ---------------------------------------------------------------------
# Source registry: internal Symbol -> typed source descriptor
#
# source values:
#   "INDEX"    -> official Yahoo index ticker (^ prefix or NSE index .NS)
#   "ETF"      -> Yahoo-tradable ETF used as a proxy (longer/cleaner history)
#   "FUTURE"   -> Yahoo futures/spot ticker (commodities)
#   "CUSTOM"   -> IndiaPulse-built equal-weight index from constituent
#                 stocks (see backend/custom_index.py)
#   "EXTERNAL" -> not on Yahoo; needs a future RBI / NSE Debt / LME
#                 connector (see backend/external.py). Always ticker-less.
#   None       -> intentionally unmapped. The downloader must skip this
#                 symbol with a clear log line, never guess or reuse a
#                 neighboring category's data.
# ---------------------------------------------------------------------

SOURCE_REGISTRY = {
    # ---- Broad Market (14; NIFTYMEGA250 removed) ----
    "NIFTY50": {"source": "INDEX", "ticker": "^NSEI"},
    "NIFTYNEXT50": {"source": "INDEX", "ticker": "^NSMIDCP"},
    "NIFTY100": {"source": "INDEX", "ticker": "^CNX100"},
    "NIFTY200": {"source": "INDEX", "ticker": "^CNX200"},
    "NIFTY500": {"source": "INDEX", "ticker": "^CRSLDX"},
    "NIFTYLARGEMIDCAP250": {"source": "INDEX", "ticker": "NIFTY_LARGEMID250.NS"},
    "NIFTYTOTALMARKET": {"source": "INDEX", "ticker": "^CRSLDX"},  # intentional dup: no distinct total-market ticker
    "NIFTYMIDCAP50": {"source": "INDEX", "ticker": "^NSEMDCP50"},
    "NIFTYMIDCAP100": {"source": "INDEX", "ticker": "NIFTY_MIDCAP_100.NS"},
    "NIFTYMIDCAP150": {"source": "INDEX", "ticker": "NIFTYMIDCAP150.NS"},
    "NIFTYSMALLCAP50": {"source": "ETF", "ticker": "SMALLCAP.NS"},  # index THIN; ETF confirmed 497 rows
    "NIFTYSMALLCAP100": {"source": "INDEX", "ticker": "^CNXSC"},
    "NIFTYSMALLCAP250": {"source": "ETF", "ticker": "HDFCSML250.NS"},
    "NIFTYMICROCAP250": {"source": "INDEX", "ticker": "NIFTY_MICROCAP250.NS"},

    # ---- Sectors (20) ----
    "NIFTYAUTO": {"source": "INDEX", "ticker": "^CNXAUTO"},
    "NIFTYBANK": {"source": "INDEX", "ticker": "^NSEBANK"},
    "NIFTYFINSERVICE": {"source": "INDEX", "ticker": "NIFTY_FIN_SERVICE.NS"},
    "NIFTYFMCG": {"source": "INDEX", "ticker": "^CNXFMCG"},
    "NIFTYHEALTHCARE": {"source": "ETF", "ticker": "PHARMABEES.NS"},  # index THIN; ETF confirmed 499 rows
    "NIFTYIT": {"source": "INDEX", "ticker": "^CNXIT"},
    "NIFTYMEDIA": {"source": "INDEX", "ticker": "^CNXMEDIA"},
    "NIFTYMETAL": {"source": "INDEX", "ticker": "^CNXMETAL"},
    "NIFTYPHARMA": {"source": "INDEX", "ticker": "^CNXPHARMA"},
    "NIFTYPSUBANK": {"source": "INDEX", "ticker": "^CNXPSUBANK"},
    "NIFTYPRIVATEBANK": {"source": "INDEX", "ticker": "NIFTY_PVT_BANK.NS"},
    "NIFTYREALTY": {"source": "INDEX", "ticker": "^CNXREALTY"},
    "NIFTYCONSUMERDURABLES": {"source": "ETF", "ticker": "CONSUMBEES.NS"},  # index THIN; ETF confirmed 493 rows
    "NIFTYOILGAS": {"source": "INDEX", "ticker": "NIFTY_OIL_AND_GAS.NS"},
    "NIFTYENERGY": {"source": "INDEX", "ticker": "^CNXENERGY"},
    "NIFTYINFRA": {"source": "INDEX", "ticker": "^CNXINFRA"},
    "NIFTYCOMMODITIES": {"source": "INDEX", "ticker": "^CNXCMDT"},
    "NIFTYSERVICES": {"source": "INDEX", "ticker": "^CNXSERVICE"},
    "NIFTYCONSUMPTION": {"source": "INDEX", "ticker": "^CNXCONSUM"},
    "NIFTYPSE": {"source": "INDEX", "ticker": "^CNXPSE"},

    # ---- Industries (25) ----
    "NIFTYCHEMICAL": {"source": "INDEX", "ticker": "NIFTY_CHEMICALS.NS"},
    "NIFTYCAPITALMARKET": {"source": "INDEX", "ticker": "NIFTY_CAPITAL_MKT.NS"},
    "NIFTYTELECOM": {
        "source": "CUSTOM", "method": "equal_weight",
        "symbols": ["BHARTIARTL.NS", "INDUSTOWER.NS", "TATACOMM.NS"],
    },
    "NIFTYLOGISTICS": {
        "source": "CUSTOM", "method": "equal_weight",
        "symbols": ["CONCOR.NS", "DELHIVERY.NS", "BLUEDART.NS"],
    },
    "NIFTYAVIATION": {
        "source": "CUSTOM", "method": "equal_weight",
        "symbols": ["INDIGO.NS", "GMRAIRPORT.NS", "SPICEJET.NS"],
    },
    "NIFTYCEMENT": {"source": "INDEX", "ticker": "NIFTY_INDIA_MFG.NS"},  # intentional generic proxy: no distinct Cement index
    "NIFTYCONSTRUCTION": {
        "source": "CUSTOM", "method": "equal_weight",
        "symbols": ["LT.NS", "NCC.NS", "RVNL.NS"],
    },
    "NIFTYDEFENCE": {"source": "INDEX", "ticker": "NIFTY_IND_DEFENCE.NS"},
    "NIFTYRETAIL": {"source": "INDEX", "ticker": "NIFTY_INDIA_RETAIL.NS"},
    "NIFTYTEXTILE": {"source": "INDEX", "ticker": "NIFTY_INDIA_MFG.NS"},  # intentional generic proxy
    "NIFTYSUGAR": {"source": "INDEX", "ticker": "NIFTY_INDIA_MFG.NS"},  # intentional generic proxy
    "NIFTYFERTILIZER": {"source": "INDEX", "ticker": "NIFTY_INDIA_MFG.NS"},  # intentional generic proxy
    "NIFTYAUTOCOMP": {"source": "INDEX", "ticker": "^CNXAUTO"},  # intentional dup: no separate Auto Components index
    "NIFTYPOWER": None,  # no distinct index/custom basket defined yet; do NOT reuse Energy
    "NIFTYHOSPITAL": {"source": "ETF", "ticker": "PHARMABEES.NS"},  # intentional dup: no separate Hospital index
    "NIFTYINSURANCE": {"source": "INDEX", "ticker": "NIFTY_FIN_SERVICE.NS"},  # intentional dup: no separate Insurance index
    "NIFTYNBFC": {"source": "INDEX", "ticker": "NIFTY_FIN_SERVICE.NS"},  # intentional dup: no separate NBFC index
    "NIFTYINTERNET": {"source": "ETF", "ticker": "TNIDETF.NS"},  # same underlying theme as DIGITAL
    "NIFTYRENEWABLE": {
        "source": "CUSTOM", "method": "equal_weight",
        "symbols": ["SUZLON.NS", "WAAREE.NS", "INOXWIND.NS"],
    },
    "NIFTYCABLE": {
        "source": "CUSTOM", "method": "equal_weight",
        "symbols": ["POLYCAB.NS", "KEI.NS", "RRKABEL.NS"],
    },
    "NIFTYELECTRICAL": {"source": "INDEX", "ticker": "NIFTY_INDIA_MFG.NS"},  # intentional generic proxy
    "NIFTYPACKAGING": {"source": "INDEX", "ticker": "NIFTY_INDIA_MFG.NS"},  # intentional generic proxy
    "NIFTYENGINEERING": {"source": "INDEX", "ticker": "NIFTY_INDIA_MFG.NS"},  # intentional generic proxy
    "NIFTYHOTELS": {
        "source": "CUSTOM", "method": "equal_weight",
        "symbols": ["INDHOTEL.NS", "EIHOTEL.NS", "CHALET.NS"],
    },
    "NIFTYSHIPPING": {
        "source": "CUSTOM", "method": "equal_weight",
        "symbols": ["SCI.NS", "GESHIP.NS", "COCHINSHIP.NS"],
    },

    # ---- Themes (15) ----
    "MANUFACTURING": {"source": "ETF", "ticker": "MAKEINDIA.NS"},
    "DEFENCE": {"source": "ETF", "ticker": "GROWWDEFNC.NS"},  # own ETF, decoupled from Industry Defence index
    "EV": {"source": "INDEX", "ticker": "NIFTY_EV.NS"},
    "DIGITAL": {"source": "ETF", "ticker": "TNIDETF.NS"},
    "CPSE": {"source": "INDEX", "ticker": "NIFTY_CPSE.NS"},
    "PSU": {"source": "INDEX", "ticker": "^CNXPSE"},  # intentional dup with NIFTYPSE
    "RURAL": {"source": "INDEX", "ticker": "NIFTY_RURAL.NS"},
    "HOUSING": {"source": "INDEX", "ticker": "NIFTY_HOUSING.NS"},
    "TOURISM": None,  # no confirmed distinct index/custom basket yet; do NOT reuse Aviation/Hotels
    "ESG": {"source": "ETF", "ticker": "ESG.NS"},
    "INFRA": {"source": "INDEX", "ticker": "^CNXINFRA"},  # intentional dup with NIFTYINFRA
    "MNC": {"source": "INDEX", "ticker": "^CNXMNC"},
    "CONSUMPTION": {"source": "INDEX", "ticker": "^CNXCONSUM"},  # intentional dup with NIFTYCONSUMPTION
    "MOBILITY": {
        "source": "CUSTOM", "method": "equal_weight",
        "symbols": ["TATAMOTORS.NS", "M&M.NS", "TVSMOTOR.NS"],
    },
    "DIVIDEND": {"source": "ETF", "ticker": "DIVOPPBEES.NS"},

    # ---- Factors (9; HIGHBETA removed) ----
    "ALPHA50": {"source": "ETF", "ticker": "ALPL30IETF.NS"},  # ETF fallback, confirmed 493 rows
    "QUALITY30": {"source": "ETF", "ticker": "QUAL30IETF.NS"},  # ETF fallback, confirmed 493 rows
    "VALUE20": {"source": "INDEX", "ticker": "NV20.NS"},  # confirmed OK, 499 rows
    "MOMENTUM30": {"source": "ETF", "ticker": "MOM30IETF.NS"},  # ETF fallback, confirmed 493 rows
    "LOWVOL30": {"source": "ETF", "ticker": "LOWVOLIETF.NS"},  # ETF fallback, confirmed 493 rows
    "LOWBETA": None,  # unclear if distinct from LOWVOL30; do not guess a ticker
    "EQUALWEIGHT": {"source": "ETF", "ticker": "EQUAL50.NS"},  # confirmed 299 rows; alt SBINEQWETF.NS (344 rows)
    "DIVIDEND50": {"source": "ETF", "ticker": "DIVOPPBEES.NS"},  # intentional dup with DIVIDEND theme
    "GROWTH": None,  # real index is "Nifty Growth Sectors 15"; ticker unconfirmed

    # ---- Fixed Income (8) ----
    "GSEC10Y": None,  # needs a real NSE G-Sec bucket ticker; ^INR10Y (US Treasury) removed
    "GSEC813": None,  # closest real bucket: "Nifty 4-8 Yr G-Sec"; ticker unconfirmed
    "SDL": {"source": "EXTERNAL", "provider": "RBI"},  # distinct index family from G-Sec entirely
    "BHARATBOND2030": {"source": "ETF", "ticker": None},  # needs the fund's ISIN-based ticker, not the generic name
    "BHARATBOND2031": {"source": "ETF", "ticker": None},  # same issue
    "CORPBOND": {"source": "EXTERNAL", "provider": "RBI"},
    "LIQUID": {"source": "ETF", "ticker": "LIQUIDBEES.NS"},
    "MONEYMARKET": {"source": "ETF", "ticker": "LIQUIDBEES.NS"},  # intentional dup: no separate money-market ETF

    # ---- Commodities (12) ----
    "GOLD": {"source": "FUTURE", "ticker": "GC=F"},
    "SILVER": {"source": "FUTURE", "ticker": "SI=F"},
    "COPPER": {"source": "FUTURE", "ticker": "HG=F"},
    "ALUMINIUM": {"source": "FUTURE", "ticker": "ALI=F"},
    "ZINC": {"source": "FUTURE", "ticker": "ZNC=F"},
    "NICKEL": {"source": "EXTERNAL", "provider": "LME"},
    "LEAD": {"source": "EXTERNAL", "provider": "LME"},
    "BRENT": {"source": "FUTURE", "ticker": "BZ=F"},
    "WTI": {"source": "FUTURE", "ticker": "CL=F"},
    "NATGAS": {"source": "FUTURE", "ticker": "NG=F"},
    "COAL": {"source": "FUTURE", "ticker": "MTF=F"},
    "STEEL": {"source": "FUTURE", "ticker": "HRC=F"},
}


# ---------------------------------------------------------------------
# Public accessors
# ---------------------------------------------------------------------

def get_provider_for_asset_class(asset_class: str) -> str:
    """Return the provider name registered for a given AssetClass."""
    entry = PROVIDERS.get(asset_class)
    return entry["provider"] if entry else "unknown"


def get_source(symbol: str) -> dict | None:
    """Return the source descriptor for an internal universe symbol.

    May return None -- callers (the downloader) must handle this by
    skipping the symbol with a log line, not by crashing or silently
    substituting another symbol's data.
    """
    return SOURCE_REGISTRY.get(symbol)


def get_yfinance_ticker(symbol: str) -> str | None:
    """Back-compat helper: return a plain Yahoo ticker if this symbol's
    source is INDEX/ETF/FUTURE and has a real ticker. Returns None for
    CUSTOM, EXTERNAL, or unmapped symbols -- those need get_source()
    and the appropriate handler (custom_index.py / external.py).
    """
    entry = get_source(symbol)
    if not entry:
        return None
    if entry.get("source") in ("INDEX", "ETF", "FUTURE"):
        return entry.get("ticker")
    return None
