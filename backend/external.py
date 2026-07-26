#!/usr/bin/env python3
"""
IndiaPulse - External Source Connectors
Milestone 4 - Data Download Engine (placeholder)

Handles symbols whose backend/sources.py entry is
{"source": "EXTERNAL", "provider": "..."} -- data that isn't available
through Yahoo Finance at all (RBI G-Sec/SDL/corp-bond series, LME base
metals, NSE Debt segment, etc).

None of these providers are implemented yet. This module exists so the
download engine has one clean place to call and log from, instead of
guessing a Yahoo ticker or silently skipping with no explanation. Each
function below is a stub to be filled in during a future milestone.
"""

from __future__ import annotations

import pandas as pd

from backend.logger import get_logger

log = get_logger("external")

# Providers referenced by sources.py EXTERNAL entries, and their status.
SUPPORTED_PROVIDERS = {
    "RBI": "not_implemented",     # G-Sec buckets, SDL, corporate bond indices
    "NSE_DEBT": "not_implemented",  # NSE Debt segment series
    "LME": "not_implemented",     # London Metal Exchange (Nickel, Lead, ...)
}


def fetch_external(symbol: str, provider: str) -> pd.DataFrame | None:
    """Attempt to fetch data for an EXTERNAL-sourced symbol.

    Always returns None today -- every provider is a stub. Logs clearly
    so a download run's summary shows *why* the symbol was skipped
    (unimplemented external connector) rather than looking like a
    silent failure.
    """
    status = SUPPORTED_PROVIDERS.get(provider, "unknown_provider")
    log.info(
        "Skipping %s: external provider '%s' is %s (Milestone 5+)",
        symbol, provider, status,
    )
    return None
