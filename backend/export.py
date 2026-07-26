#!/usr/bin/env python3
"""
IndiaPulse - Export Engine

Writes computed analytics to json/ so the static frontend dashboards
can fetch() them directly (no backend server required for viewing).
"""

from datetime import datetime, timezone

from backend.config import JSON_DIR
from backend.utils import write_json


def export_category(category: str, results: list[dict]) -> None:
    """Write one json/<category>.json file containing a list of symbol results."""
    payload = {
        "category": category,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(results),
        "data": sorted(results, key=lambda r: r.get("opportunity", {}).get("opportunity_score", 0), reverse=True),
    }
    write_json(JSON_DIR / f"{category}.json", payload)


def export_opportunity_board(all_results: list[dict]) -> None:
    """Write the flagship opportunity.json ranking across every category."""
    ranked = sorted(
        all_results,
        key=lambda r: r.get("opportunity", {}).get("opportunity_score", 0),
        reverse=True,
    )
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(ranked),
        "ranking": [
            {
                "symbol": r["symbol"],
                "category": r.get("category", ""),
                "opportunity_score": r.get("opportunity", {}).get("opportunity_score"),
                "rating": r.get("opportunity", {}).get("rating"),
                "trend": r.get("trend", {}).get("trend"),
                "momentum": r.get("momentum", {}).get("momentum"),
                "seasonality": r.get("seasonality", {}).get("seasonality"),
            }
            for r in ranked
        ],
    }
    write_json(JSON_DIR / "opportunity.json", payload)
