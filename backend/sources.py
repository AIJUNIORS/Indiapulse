"""
IndiaPulse
Data Source Registry
"""

# ---------------------------------------------------------------------
# Supported Data Providers
# ---------------------------------------------------------------------

PROVIDERS = {
    "Equity": "yfinance",
    "Commodity": "yfinance",
    "Bond": "yfinance",
    "FX": "yfinance",
    "Macro": "manual"
}

# ---------------------------------------------------------------------
# Provider Details
# ---------------------------------------------------------------------

SOURCE_DETAILS = {
    "yfinance": {
        "name": "Yahoo Finance",
        "history": True,
        "intraday": True
    },
    "manual": {
        "name": "Manual / Government Source",
        "history": False,
        "intraday": False
    }
}

# ---------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------

def get_provider(asset_class: str) -> str:
    """Return the download provider for an asset class."""
    return PROVIDERS.get(asset_class, "unknown")
