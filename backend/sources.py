#!/usr/bin/env python3
"""
IndiaPulse - Provider Registry & Symbol Mapping
Milestone 3 - Backend Foundation (v2 - reconciled against 112 live NSE
indices on dhan.co/all-nse-indices, discover_tickers.py output pending)

Maps each asset class / category to a data provider, and maps our
internal universe symbols to the ticker format each provider expects.
Currently "yfinance" is the only implemented provider; "manual" is a
placeholder for macro series that need to be sourced from RBI/MOSPI/GSTN
APIs or manual CSV upload (Phase 5+).

CHANGELOG (this revision):
- MNC: NIFTY_MNC.NS (404) -> ^CNXMNC (confirmed live, deep CNX-legacy
  history, same family as ^CNXAUTO/^CNXFMCG/^CNXMETAL etc.)
- NIFTYLARGEMIDCAP250: was wrongly proxied to ^CNX200 (duplicate of
  NIFTY200) -> corrected to NIFTY_LARGEMID250.NS, confirmed real ticker
  on Yahoo (was misclassified THIN by a period=2y test; real depth
  unconfirmed until discover_tickers.py re-checks with period="max")
- NIFTYRETAIL: fixed typo "NIFTIY_INDIA_RETAIL.NS" -> "NIFTY_INDIA_RETAIL.NS"
- ESG: fixed "NIFTY100ESG.NS" -> "NIFTY100_ESG.NS"
- VALUE20: "NIFTY50VALUE20.NS" (404) -> "NV20.NS" (confirmed OK, 499 rows)
- Removed all "^INR10Y" fixed-income proxies. That ticker is the US
  10-Year Treasury, not an Indian G-Sec series -- it was silently
  feeding US rates into GSEC10Y/GSEC813/SDL/CORPBOND. Set to None
  pending discover_tickers.py against the real NSE G-Sec bucket names
  (Nifty 4-8 Yr G-Sec / 11-15 Yr / 15 Yr Plus / Composite G-Sec).
- Fixed 8 categories that were silently duplicating another category's
  ticker due to copy-paste (not distinct data, and in 2 cases actively
  wrong): NIFTYTELECOM, NIFTYCONSTRUCTION, NIFTYPOWER, NIFTYRENEWABLE,
  NIFTYHOTELS, NIFTYSHIPPING, TOURISM, MOBILITY, GROWTH. Each now
  points at its own confirmed-real NSE index name (per dhan.co live
  list) with ticker=None pending discovery, instead of quietly
  re-fetching a neighboring category's data under a different label.
- Swapped 6 factor/theme indices that only return 1 row on Yahoo
  (real index, but too new/thin for backtesting) for the ETF that
  tracks them, confirmed via your own verify_proxy_tickers.py run
  (ALPHA50, QUALITY30, MOMENTUM30, LOWVOL30, DIVIDEND, DIVIDEND50,
  EQUALWEIGHT). Per "index if not ETF" -- these fall back to ETF.
- Added 3 new categories to reach the 108-index target, reconciled
  against dhan.co's live NSE index list: NIFTYIPO, NIFTYMIDCAPSELECT,
  NIFTYFINSERVICE2550. Tickers unconfirmed (None) pending discovery.
- Every ticker=None entry is intentional: better to skip cleanly in
  the downloader than to silently pull wrong/duplicate data. Run
  discover_tickers.py and fill these in from its output.
"""

# ---------------------------------------------------------------------
# Provider registry: which downloader handles which AssetClass
# ---------------------------------------------------------------------

PROVIDERS = {
    "Equity": {
        "provider": "yfinance",
        "description": "NSE indices & equities via Yahoo Finance",
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
# Symbol map: internal Symbol -> provider-specific ticker
# Indices use Yahoo's ^ prefix; stocks would use the .NS suffix (not
# used yet since Milestone 2 universe is index-level only).
#
# ticker = None means: no confirmed working Yahoo ticker yet. The
# downloader should skip these cleanly (log + continue), not attempt
# a fetch. Do NOT fill these in by guessing -- run discover_tickers.py
# and confirm real row count with period="max" first.
# ---------------------------------------------------------------------

YFINANCE_SYMBOL_MAP = {
    # ---- Broad Market (15) ----
    "NIFTY50": "^NSEI",
    "NIFTYNEXT50": "^NSMIDCP",
    "NIFTY100": "^CNX100",
    "NIFTY200": "^CNX200",
    "NIFTY500": "^CRSLDX",
    "NIFTYLARGEMIDCAP250": "NIFTY_LARGEMID250.NS",  # FIXED: was dup of NIFTY200
    "NIFTYTOTALMARKET": "^CRSLDX",  # intentional dup: no separate Yahoo total-market ticker
    "NIFTYMIDCAP50": "^NSEMDCP50",
    "NIFTYMIDCAP100": "NIFTY_MIDCAP_100.NS",
    "NIFTYMIDCAP150": "NIFTYMIDCAP150.NS",
    "NIFTYSMALLCAP50": "SMALLCAP.NS",  # ETF fallback (index ticker THIN, ETF confirmed 497 rows)
    "NIFTYSMALLCAP100": "^CNXSC",  # TODO: recheck with period=max, currently THIN
    "NIFTYSMALLCAP250": "NIFTYSMLCAP250.NS",
    "NIFTYMICROCAP250": "NIFTY_MICROCAP250.NS",  # TODO: THIN, no ETF fallback found yet
    "NIFTYMEGA250": None,  # TODO: no working Yahoo ticker found (tried 3 variants, all 404)

    # ---- Sectors (20) ----
    "NIFTYAUTO": "^CNXAUTO",
    "NIFTYBANK": "^NSEBANK",
    "NIFTYFINSERVICE": "NIFTY_FIN_SERVICE.NS",
    "NIFTYFMCG": "^CNXFMCG",
    "NIFTYHEALTHCARE": "NIFTY_HEALTHCARE.NS",  # TODO: THIN, ETF fallback HEALTHY.NS is OK (499 rows)
    "NIFTYIT": "^CNXIT",
    "NIFTYMEDIA": "^CNXMEDIA",
    "NIFTYMETAL": "^CNXMETAL",
    "NIFTYPHARMA": "^CNXPHARMA",
    "NIFTYPSUBANK": "^CNXPSUBANK",
    "NIFTYPRIVATEBANK": "NIFTY_PVT_BANK.NS",
    "NIFTYREALTY": "^CNXREALTY",
    "NIFTYCONSUMERDURABLES": "CONSUMBEES.NS",  # ETF fallback (index THIN, ETF confirmed 493 rows)
    "NIFTYOILGAS": "NIFTY_OIL_AND_GAS.NS",  # TODO: THIN
    "NIFTYENERGY": "^CNXENERGY",
    "NIFTYINFRA": "^CNXINFRA",
    "NIFTYCOMMODITIES": "^CNXCMDT",
    "NIFTYSERVICES": "^CNXSERVICE",
    "NIFTYCONSUMPTION": "^CNXCONSUM",
    "NIFTYPSE": "^CNXPSE",

    # ---- Industries (25) ----
    "NIFTYCHEMICAL": "NIFTY_CHEMICALS.NS",  # TODO: THIN, no ETF found
    "NIFTYCAPITALMARKET": "NIFTY_CAPITAL_MKT.NS",  # real name confirmed "Nifty Capital Markets"; TODO recheck THIN
    "NIFTYTELECOM": None,  # FIXED: was wrongly dup of Media. Real: "Nifty Mid Small IT & Telecom". TODO ticker
    "NIFTYLOGISTICS": None,  # FIXED: 404. Real name: "Nifty Transportation & Logistics". TODO ticker
    "NIFTYAVIATION": None,  # TODO: 404, no working alternative found yet
    "NIFTYCEMENT": "NIFTY_INDIA_MFG.NS",  # intentional generic proxy: no distinct Cement index on NSE
    "NIFTYCONSTRUCTION": None,  # FIXED: was wrongly dup of Infra. No distinct index confirmed. TODO
    "NIFTYDEFENCE": "NIFTY_IND_DEFENCE.NS",  # real name confirmed "Nifty India Defence"; TODO recheck THIN
    "NIFTYRETAIL": "NIFTY_INDIA_RETAIL.NS",  # FIXED: typo "NIFTIY_..." -> "NIFTY_..."; still 404, TODO
    "NIFTYTEXTILE": "NIFTY_INDIA_MFG.NS",  # intentional generic proxy: no distinct index on NSE
    "NIFTYSUGAR": "NIFTY_INDIA_MFG.NS",  # intentional generic proxy
    "NIFTYFERTILIZER": "NIFTY_INDIA_MFG.NS",  # intentional generic proxy
    "NIFTYAUTOCOMP": "^CNXAUTO",  # intentional dup: no separate Auto Components index on Yahoo
    "NIFTYPOWER": None,  # FIXED: was wrongly dup of Energy. No distinct NSE index; consider BSE POWER instead
    "NIFTYHOSPITAL": "NIFTY_HEALTHCARE.NS",  # intentional dup: no separate Hospital index
    "NIFTYINSURANCE": "NIFTY_FIN_SERVICE.NS",  # intentional dup: no separate Insurance index on Yahoo
    "NIFTYNBFC": "NIFTY_FIN_SERVICE.NS",  # intentional dup: no separate NBFC index on Yahoo
    "NIFTYINTERNET": "NIFTY_IND_DIGITAL.NS",  # intentional dup with DIGITAL theme (same underlying index)
    "NIFTYRENEWABLE": None,  # FIXED: was wrongly dup of Energy. No distinct index confirmed. TODO
    "NIFTYCABLE": "^CNXMETAL",  # REVIEW: unclear this is the right proxy for "Cable" -- verify intent
    "NIFTYELECTRICAL": "NIFTY_INDIA_MFG.NS",  # intentional generic proxy
    "NIFTYPACKAGING": "NIFTY_INDIA_MFG.NS",  # intentional generic proxy
    "NIFTYENGINEERING": "NIFTY_INDIA_MFG.NS",  # intentional generic proxy
    "NIFTYHOTELS": None,  # FIXED: was wrongly dup of Aviation. Likely folds into Tourism. TODO
    "NIFTYSHIPPING": None,  # FIXED: was wrongly dup of Logistics. Same real index as NIFTYLOGISTICS

    # ---- Themes (15) ----
    "MANUFACTURING": "NIFTY_INDIA_MFG.NS",  # real name confirmed "Nifty India Manufacturing"
    "DEFENCE": "NIFTY_IND_DEFENCE.NS",  # intentional dup with NIFTYDEFENCE (same real index)
    "EV": "NIFTY_EV.NS",  # real name confirmed "Nifty EV and New Age Auto"; TODO recheck THIN
    "DIGITAL": "NIFTY_IND_DIGITAL.NS",  # real name confirmed "Nifty India Digital"
    "CPSE": "NIFTY_CPSE.NS",  # real name confirmed "Nifty CPSE"; TODO recheck THIN
    "PSU": "^CNXPSE",  # intentional dup with NIFTYPSE
    "RURAL": "NIFTY_RURAL.NS",  # real name confirmed "Nifty Rural"; TODO recheck THIN
    "HOUSING": "NIFTY_HOUSING.NS",  # real name confirmed "Nifty Housing"; TODO recheck THIN
    "TOURISM": None,  # FIXED: was wrongly dup of Aviation. Real: "Nifty India Tourism". TODO ticker
    "ESG": "NIFTY100_ESG.NS",  # FIXED: was "NIFTY100ESG.NS" (missing underscore); still THIN, TODO
    "INFRA": "^CNXINFRA",  # intentional dup with NIFTYINFRA
    "MNC": "^CNXMNC",  # FIXED: was NIFTY_MNC.NS (404) -> confirmed live on Yahoo, deep history
    "CONSUMPTION": "^CNXCONSUM",  # intentional dup with NIFTYCONSUMPTION
    "MOBILITY": None,  # FIXED: was wrongly dup of EV. Real: "Nifty Mobility" (distinct). TODO ticker
    "DIVIDEND": "DIVOPPBEES.NS",  # ETF fallback (index 404, ETF confirmed 493 rows)

    # ---- Factors (10) ----
    "ALPHA50": "ALPL30IETF.NS",  # ETF fallback (NIFTYALPHA50.NS is real but THIN; ETF confirmed 493 rows)
    "QUALITY30": "QUAL30IETF.NS",  # ETF fallback (confirmed 493 rows)
    "VALUE20": "NV20.NS",  # FIXED: "NIFTY50VALUE20.NS" 404'd -> confirmed OK, 499 rows
    "MOMENTUM30": "MOM30IETF.NS",  # ETF fallback (confirmed 493 rows)
    "LOWVOL30": "LOWVOLIETF.NS",  # ETF fallback (confirmed 493 rows)
    "HIGHBETA": None,  # TODO: 404, no ETF fallback found (tried 2 variants)
    "LOWBETA": None,  # TODO: 404, may just duplicate LOWVOL30's concept -- review whether distinct
    "EQUALWEIGHT": "EQUAL50.NS",  # ETF fallback (confirmed 299 rows; SBINEQWETF.NS alt, 344 rows)
    "DIVIDEND50": "DIVOPPBEES.NS",  # intentional dup with DIVIDEND: same real index
    "GROWTH": None,  # FIXED: was wrongly dup of QUALITY30. Real: "Nifty Growth Sectors 15". TODO ticker

    # ---- Fixed Income (8) ----
    # All four "*.NS G-Sec proxies" below were pointed at ^INR10Y, which
    # is the US 10-Year Treasury -- a real correctness bug, not just a
    # thin-data issue. Set to None until discover_tickers.py confirms
    # tickers for NSE's actual G-Sec bucket family: Nifty 4-8 Yr G-Sec /
    # Nifty 11-15 Yr G-Sec / Nifty 15 Yr Plus G-Sec / Nifty Composite G-Sec.
    "GSEC10Y": None,  # was ^INR10Y (WRONG: US Treasury). TODO: map to a real NSE G-Sec bucket
    "GSEC813": None,  # was ^INR10Y (WRONG). Closest real bucket: "Nifty 4-8 Yr G-Sec". TODO
    "SDL": None,  # was ^INR10Y (WRONG). SDL is a distinct index family from G-Sec entirely. TODO
    "BHARATBOND2030": "BHARATBOND2030.NS",  # TODO: 404, likely needs the actual fund's ISIN-based ticker
    "BHARATBOND2031": "BHARATBOND2031.NS",  # TODO: 404, same issue
    "CORPBOND": None,  # was ^INR10Y (WRONG). TODO: needs a real corporate bond index/ETF ticker
    "LIQUID": "LIQUIDBEES.NS",
    "MONEYMARKET": "LIQUIDBEES.NS",  # intentional dup: no separate money-market index ETF confirmed

    # ---- Commodities (12) ----
    "GOLD": "GC=F",
    "SILVER": "SI=F",
    "COPPER": "HG=F",
    "ALUMINIUM": "ALI=F",
    "ZINC": "ZNC=F",
    "NICKEL": None,  # TODO: Yahoo doesn't carry this future under NICKEL=F or any variant tried
    "LEAD": None,  # TODO: same issue as Nickel
    "BRENT": "BZ=F",
    "WTI": "CL=F",
    "NATGAS": "NG=F",
    "COAL": "MTF=F",
    "STEEL": "HRC=F",

    # ---- New: added to reach 108-index target ----
    # Reconciled against dhan.co/all-nse-indices (112 live-quoted NSE
    # indices) -- each of these is a real, distinct, currently-traded
    # index that wasn't already covered above. Tickers unconfirmed.
    "NIFTYIPO": None,  # "Nifty IPO" -- distinct theme, no overlap with existing categories
    "NIFTYMIDCAPSELECT": None,  # "Nifty Midcap Select" -- distinct from Midcap50/100/150
    "NIFTYFINSERVICE2550": None,  # "Nifty Financial Services 25/50" -- distinct from NIFTYFINSERVICE
}


def get_provider_for_asset_class(asset_class: str) -> str:
    """Return the provider name registered for a given AssetClass."""
    entry = PROVIDERS.get(asset_class)
    return entry["provider"] if entry else "unknown"


def get_yfinance_ticker(symbol: str) -> str | None:
    """Return the Yahoo Finance ticker for an internal universe symbol.

    May return None -- callers (the downloader) must handle this by
    skipping the symbol with a log line, not by crashing or silently
    substituting another ticker.
    """
    return YFINANCE_SYMBOL_MAP.get(symbol)
