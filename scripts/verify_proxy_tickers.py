#!/usr/bin/env python3
"""
Verify candidate Yahoo tickers for symbols currently mapped to a proxy in
backend/sources.py. NSE publishes a real, distinct index for each of these
(Insurance, NBFC, Power, Telecommunications, LargeMidcap 250, Total Market)
but the exact Yahoo ticker string can't be confirmed without live Yahoo
access, which this sandbox doesn't have.

Run this where yfinance already works (your GCP VM / local machine):

    python scripts/verify_proxy_tickers.py

For each symbol it tries several candidate tickers and reports which one
actually returns data. Replace the proxy in backend/sources.py with the
first candidate that prints OK.
"""
import yfinance as yf

CANDIDATES = {
    "NIFTYINSURANCE (currently proxied to NIFTY_FIN_SERVICE.NS)": [
        "NIFTY_INSURANCE.NS", "NIFTYINSU.NS", "NIFTY_INSU.NS",
    ],
    "NIFTYNBFC (currently proxied to NIFTY_FIN_SERVICE.NS)": [
        "NIFTY_NBFC.NS", "NIFTYNBFC.NS", "NIFTY_MIDSML_FINSERVICE.NS",
    ],
    "NIFTYPOWER (currently proxied to NIFTY_ENERGY.NS)": [
        "NIFTY_POWER.NS", "NIFTYPOWER.NS",
    ],
    "NIFTYTELECOM (currently proxied to NIFTY_MEDIA.NS)": [
        "NIFTY_TELECOM.NS", "NIFTYTELECOM.NS", "NIFTY_INDIA_TELECOM.NS",
    ],
    "NIFTYLARGEMIDCAP250 (currently proxied to ^CNX200)": [
        "NIFTY_LARGEMIDCAP_250.NS", "NIFTYLARGEMID250.NS",
    ],
    "NIFTYTOTALMARKET (currently proxied to ^CRSLDX)": [
        "NIFTY_TOTAL_MKT.NS", "NIFTYTOTALMKT.NS",
    ],
    "NIFTYHOSPITAL (currently proxied to NIFTY_HEALTHCARE.NS)": [
        "NIFTY500_HEALTHCARE.NS", "NIFTY500HEALTHCARE.NS",
    ],
}

if __name__ == "__main__":
    for label, tickers in CANDIDATES.items():
        print(f"\n{label}")
        for t in tickers:
            try:
                hist = yf.Ticker(t).history(period="5d")
                status = f"OK ({len(hist)} rows)" if not hist.empty else "EMPTY"
            except Exception as e:
                status = f"FAIL ({e})"
            print(f"  {t:32s} {status}")
