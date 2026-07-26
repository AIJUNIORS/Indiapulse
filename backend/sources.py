#!/usr/bin/env python3
"""
IndiaPulse - Provider Registry & Symbol Mapping
Milestone 3 - Backend Foundation

Maps each asset class / category to a data provider, and maps our
internal universe symbols to the ticker format each provider expects.
Currently "yfinance" is the only implemented provider; "manual" is a
placeholder for macro series that need to be sourced from RBI/MOSPI/GSTN
APIs or manual CSV upload (Phase 5+).
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
# ---------------------------------------------------------------------

YFINANCE_SYMBOL_MAP = {
    # Broad Market
    "NIFTY50": "^NSEI",
    "NIFTYNEXT50": "^NSMIDCP",
    "NIFTY100": "^CNX100",
    "NIFTY200": "^CNX200",
    "NIFTY500": "^CRSLDX",
    "NIFTYLARGEMIDCAP250": "^CNX200",  # proxy
    "NIFTYTOTALMARKET": "^CRSLDX",  # proxy
    "NIFTYMIDCAP50": "^NSEMDCP50",
    "NIFTYMIDCAP100": "NIFTY_MIDCAP_100.NS",
    "NIFTYMIDCAP150": "NIFTYMIDCAP150.NS",
    "NIFTYSMALLCAP50": "NIFTYSMLCAP50.NS",
    "NIFTYSMALLCAP100": "^CNXSC",
    "NIFTYSMALLCAP250": "NIFTYSMLCAP250.NS",
    "NIFTYMICROCAP250": "NIFTY_MICROCAP250.NS",
    "NIFTYMEGA250": "NIFTY_MEGA_CAP_250.NS",

    # Sectors
    "NIFTYAUTO": "^CNXAUTO",
    "NIFTYBANK": "^NSEBANK",
    "NIFTYFINSERVICE": "NIFTY_FIN_SERVICE.NS",
    "NIFTYFMCG": "^CNXFMCG",
    "NIFTYHEALTHCARE": "NIFTY_HEALTHCARE.NS",
    "NIFTYIT": "^CNXIT",
    "NIFTYMEDIA": "^CNXMEDIA",
    "NIFTYMETAL": "^CNXMETAL",
    "NIFTYPHARMA": "^CNXPHARMA",
    "NIFTYPSUBANK": "^CNXPSUBANK",
    "NIFTYPRIVATEBANK": "NIFTY_PVT_BANK.NS",
    "NIFTYREALTY": "^CNXREALTY",
    "NIFTYCONSUMERDURABLES": "NIFTY_CONSR_DURBL.NS",
    "NIFTYOILGAS": "NIFTY_OIL_AND_GAS.NS",
    "NIFTYENERGY": "^CNXENERGY",
    "NIFTYINFRA": "^CNXINFRA",
    "NIFTYCOMMODITIES": "^CNXCMDT",
    "NIFTYSERVICES": "^CNXSERVICE",
    "NIFTYCONSUMPTION": "^CNXCONSUM",
    "NIFTYPSE": "^CNXPSE",

    # Industries
    "NIFTYCHEMICAL": "NIFTY_CHEMICALS.NS",
    "NIFTYCAPITALMARKET": "NIFTY_CAPITAL_MKT.NS",
    "NIFTYTELECOM": "NIFTY_MEDIA.NS",  # proxy until telecom index verified
    "NIFTYLOGISTICS": "NIFTY_LOGISTICS.NS",
    "NIFTYAVIATION": "NIFTY_AVIATION.NS",
    "NIFTYCEMENT": "NIFTY_INDIA_MFG.NS",  # proxy
    "NIFTYCONSTRUCTION": "NIFTY_INFRA.NS",  # proxy
    "NIFTYDEFENCE": "NIFTY_IND_DEFENCE.NS",
    "NIFTYRETAIL": "NIFTIY_INDIA_RETAIL.NS",
    "NIFTYTEXTILE": "NIFTY_INDIA_MFG.NS",  # proxy
    "NIFTYSUGAR": "NIFTY_INDIA_MFG.NS",  # proxy
    "NIFTYFERTILIZER": "NIFTY_INDIA_MFG.NS",  # proxy
    "NIFTYAUTOCOMP": "^CNXAUTO",  # proxy
    "NIFTYPOWER": "NIFTY_ENERGY.NS",  # proxy
    "NIFTYHOSPITAL": "NIFTY_HEALTHCARE.NS",  # proxy
    "NIFTYINSURANCE": "NIFTY_FIN_SERVICE.NS",  # proxy
    "NIFTYNBFC": "NIFTY_FIN_SERVICE.NS",  # proxy
    "NIFTYINTERNET": "NIFTY_IND_DIGITAL.NS",  # closer match than Media; same ticker as DIGITAL theme
    "NIFTYRENEWABLE": "NIFTY_ENERGY.NS",  # proxy
    "NIFTYCABLE": "^CNXMETAL",  # proxy
    "NIFTYELECTRICAL": "NIFTY_INDIA_MFG.NS",  # proxy
    "NIFTYPACKAGING": "NIFTY_INDIA_MFG.NS",  # proxy
    "NIFTYENGINEERING": "NIFTY_INDIA_MFG.NS",  # proxy
    "NIFTYHOTELS": "NIFTY_AVIATION.NS",  # proxy (tourism-linked)
    "NIFTYSHIPPING": "NIFTY_LOGISTICS.NS",  # proxy

    # Themes
    "MANUFACTURING": "NIFTY_INDIA_MFG.NS",
    "DEFENCE": "NIFTY_IND_DEFENCE.NS",
    "EV": "NIFTY_EV.NS",
    "DIGITAL": "NIFTY_IND_DIGITAL.NS",
    "CPSE": "NIFTY_CPSE.NS",
    "PSU": "^CNXPSE",
    "RURAL": "NIFTY_RURAL.NS",
    "HOUSING": "NIFTY_HOUSING.NS",
    "TOURISM": "NIFTY_AVIATION.NS",  # proxy
    "ESG": "NIFTY100ESG.NS",
    "INFRA": "^CNXINFRA",
    "MNC": "NIFTY_MNC.NS",
    "CONSUMPTION": "^CNXCONSUM",
    "MOBILITY": "NIFTY_EV.NS",  # proxy
    "DIVIDEND": "NIFTY_DIV_OPPS_50.NS",

    # Factors
    "ALPHA50": "NIFTYALPHA50.NS",
    "QUALITY30": "NIFTY200QUALTY30.NS",
    "VALUE20": "NIFTY50VALUE20.NS",
    "MOMENTUM30": "NIFTY200MOMENTM30.NS",
    "LOWVOL30": "NIFTY100LOWVOL30.NS",
    "HIGHBETA": "NIFTYHIGHBETA50.NS",
    "LOWBETA": "NIFTYLOWVOL50.NS",  # proxy
    "EQUALWEIGHT": "NIFTY50EQL.NS",
    "DIVIDEND50": "NIFTY_DIV_OPPS_50.NS",
    "GROWTH": "NIFTY200QUALTY30.NS",  # proxy

    # Fixed Income (best-effort proxies; refine with bond ETFs)
    "GSEC10Y": "^INR10Y",
    "GSEC813": "^INR10Y",  # proxy
    "SDL": "^INR10Y",  # proxy
    "BHARATBOND2030": "BHARATBOND2030.NS",  # proxy - may need ETF ticker
    "BHARATBOND2031": "BHARATBOND2031.NS",
    "CORPBOND": "^INR10Y",  # proxy
    "LIQUID": "LIQUIDBEES.NS",
    "MONEYMARKET": "LIQUIDBEES.NS",  # proxy

    # Commodities
    "GOLD": "GC=F",
    "SILVER": "SI=F",
    "COPPER": "HG=F",
    "ALUMINIUM": "ALI=F",
    "ZINC": "ZNC=F",
    "NICKEL": "NICKEL=F",
    "LEAD": "LEAD=F",
    "BRENT": "BZ=F",
    "WTI": "CL=F",
    "NATGAS": "NG=F",
    "COAL": "MTF=F",
    "STEEL": "HRC=F",
}


def get_provider_for_asset_class(asset_class: str) -> str:
    """Return the provider name registered for a given AssetClass."""
    entry = PROVIDERS.get(asset_class)
    return entry["provider"] if entry else "unknown"


def get_yfinance_ticker(symbol: str) -> str | None:
    """Return the Yahoo Finance ticker for an internal universe symbol."""
    return YFINANCE_SYMBOL_MAP.get(symbol)
