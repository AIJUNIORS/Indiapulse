#!/usr/bin/env python3
"""
IndiaPulse - Main Pipeline Orchestrator

Universe -> Download -> Indicators -> Analytics -> Scores -> Dashboard(json)

Run with:  python -m backend.main [--download] [--incremental]
"""

import argparse

import pandas as pd

from backend.config import HISTORICAL_DIR
from backend.logger import get_logger
from backend.download import download_universe, load_universe
from backend.analytics.summary import summarize_symbol
from backend.analytics.breadth import compute_breadth
from backend.analytics.cycle import compute_cycle
from backend.export import export_category, export_opportunity_board
from backend.macro import download_macro_universe, get_cycle_inputs
from backend.utils import safe_symbol_filename

log = get_logger("main")

CATEGORY_MAP = {
    "Broad Market": "broad_market",
    "Sector": "sectors",
    "Industry": "industries",
    "Theme": "themes",
    "Factor": "factors",
    "Fixed Income": "fixed_income",
    "Commodity": "commodities",
}


def _load_history(symbol: str) -> pd.DataFrame | None:
    path = HISTORICAL_DIR / f"{safe_symbol_filename(symbol)}.csv"
    if not path.exists():
        return None
    try:
        df = pd.read_csv(path, index_col=0, parse_dates=True)
        return df
    except Exception as exc:  # noqa: BLE001
        log.warning("Failed to read history for %s: %s", symbol, exc)
        return None


def run_pipeline(incremental: bool = False, do_download: bool = False) -> None:
    if do_download:
        log.info("Running download stage (incremental=%s)...", incremental)
        download_universe(incremental=incremental)
        download_macro_universe(incremental=incremental)

    universe = load_universe()
    log.info("Computing analytics for %d symbols...", len(universe))

    # Macro cycle inputs, derived from whatever macro series have been
    # downloaded so far (see backend/macro.py). Falls back to a neutral
    # 0.0/0.0/"hold" reading per-field, with a log line, for any series
    # not yet populated (most need the RBI/MOSPI/GSTN connectors from
    # backend/external.py, which aren't implemented yet).
    macro_inputs = get_cycle_inputs()
    cycle_result = compute_cycle(
        growth_trend=macro_inputs["growth_trend"],
        inflation_trend=macro_inputs["inflation_trend"],
        rate_direction=macro_inputs["rate_direction"],
    )

    by_category: dict[str, list[dict]] = {}
    all_results: list[dict] = []

    for row in universe:
        symbol = row["Symbol"]
        category = row.get("Category", "Uncategorized")
        df = _load_history(symbol)
        if df is None or df.empty:
            log.info("No historical data for %s yet; skipping analytics", symbol)
            continue

        result = summarize_symbol(symbol, df, category=category, macro_cycle_result=cycle_result)
        json_key = CATEGORY_MAP.get(category, category.lower().replace(" ", "_"))
        by_category.setdefault(json_key, []).append(result)
        all_results.append(result)

    for json_key, results in by_category.items():
        export_category(json_key, results)
        trend_scores = [r["trend"]["score"] for r in results if r.get("trend", {}).get("score") is not None]
        if trend_scores:
            breadth = compute_breadth(trend_scores)
            log.info("%s breadth: %s (%.1f%%)", json_key, breadth["breadth"], breadth["score"])

    export_opportunity_board(all_results)
    log.info("Pipeline complete. Exported %d category files + opportunity board.", len(by_category))


def main():
    parser = argparse.ArgumentParser(description="IndiaPulse pipeline orchestrator")
    parser.add_argument("--download", action="store_true", help="Download historical data before computing analytics")
    parser.add_argument("--incremental", action="store_true", help="Use incremental (update-only) download mode")
    args = parser.parse_args()

    run_pipeline(incremental=args.incremental, do_download=args.download)


if __name__ == "__main__":
    main()
