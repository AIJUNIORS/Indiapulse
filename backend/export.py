#!/usr/bin/env python3
"""
IndiaPulse - Export Engine

Writes computed analytics to json/ so the static frontend dashboards
can fetch() them directly (no backend server required for viewing).

Rows with insufficient underlying data (result["data_sufficient"] is
False -- see backend/analytics/opportunity.py) are never blended into
the ranked list or the average score. They're segregated into a
"coverage_gaps" list instead, so the frontend can show them in a
separate panel/footnote rather than as fake ties in the ranking.
"""

from datetime import datetime, timezone

from backend.config import JSON_DIR
from backend.utils import write_json


def _split_sufficient(results: list[dict]) -> tuple[list[dict], list[dict]]:
    sufficient = [r for r in results if r.get("data_sufficient")]
    gaps = [r for r in results if not r.get("data_sufficient")]
    return sufficient, gaps


def _coverage_gap_entry(r: dict) -> dict:
    """Minimal, honest record for a row we couldn't score -- symbol,
    category, and *why*, with no fabricated score attached."""
    missing = r.get("opportunity", {}).get("missing_components", [])
    reason_parts = []
    for label, block in (("trend", r.get("trend")), ("momentum", r.get("momentum")), ("seasonality", r.get("seasonality"))):
        if isinstance(block, dict) and block.get("data_sufficient") is False:
            rows_avail = block.get("rows_available")
            rows_req = block.get("rows_required") or block.get("years_required")
            if rows_avail is not None and rows_req is not None:
                reason_parts.append(f"{label}: {rows_avail}/{rows_req}")
            else:
                reason_parts.append(f"{label}: insufficient")
    return {
        "symbol": r["symbol"],
        "category": r.get("category", ""),
        "missing_components": missing,
        "reason": "; ".join(reason_parts) if reason_parts else "insufficient underlying data",
    }


def export_category(category: str, results: list[dict]) -> None:
    """Write one json/<category>.json file containing a list of symbol results."""
    sufficient, gaps = _split_sufficient(results)
    scores = [r["opportunity"]["opportunity_score"] for r in sufficient]
    payload = {
        "category": category,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(results),
        "scored_count": len(sufficient),
        "avg_opportunity_score": round(sum(scores) / len(scores), 2) if scores else None,
        "data": sorted(sufficient, key=lambda r: r["opportunity"]["opportunity_score"], reverse=True),
        "coverage_gaps": [_coverage_gap_entry(r) for r in gaps],
    }
    write_json(JSON_DIR / f"{category}.json", payload)


def export_opportunity_board(all_results: list[dict]) -> None:
    """Write the flagship opportunity.json ranking across every category."""
    sufficient, gaps = _split_sufficient(all_results)
    ranked = sorted(sufficient, key=lambda r: r["opportunity"]["opportunity_score"], reverse=True)
    scores = [r["opportunity"]["opportunity_score"] for r in ranked]

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(all_results),
        "scored_count": len(ranked),
        "avg_opportunity_score": round(sum(scores) / len(scores), 2) if scores else None,
        "ranking": [
            {
                "symbol": r["symbol"],
                "category": r.get("category", ""),
                "opportunity_score": r["opportunity"]["opportunity_score"],
                "rating": r["opportunity"]["rating"],
                "trend": r.get("trend", {}).get("trend"),
                "momentum": r.get("momentum", {}).get("momentum"),
                "seasonality": r.get("seasonality", {}).get("seasonality"),
                "excluded_components": r["opportunity"].get("excluded_components", []),
            }
            for r in ranked
        ],
        "coverage_gaps": [_coverage_gap_entry(r) for r in gaps],
    }
    write_json(JSON_DIR / "opportunity.json", payload)
