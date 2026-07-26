#!/usr/bin/env python3
"""
IndiaPulse - Incremental Update Runner

Meant to be scheduled (Phase 9 - Automation) to refresh only new data
since the last run, recompute analytics, and re-export json.
"""

from backend.logger import get_logger
from backend.download import download_universe

log = get_logger("update")


def run_incremental_update() -> None:
    log.info("Starting incremental update...")
    results = download_universe(incremental=True)
    log.info(
        "Incremental update finished: %d success / %d failed / %d skipped",
        len(results["success"]), len(results["failed"]), len(results["skipped"]),
    )

    # Recompute analytics after refreshing data.
    from backend.main import run_pipeline
    run_pipeline(incremental=True)


if __name__ == "__main__":
    run_incremental_update()
