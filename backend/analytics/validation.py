#!/usr/bin/env python3
"""
Analytics Validation

Sanity checks applied to computed analytics before they are persisted
or exposed to the frontend, catching obviously broken outputs.
"""


def validate_score(name: str, value: float, low: float = 0.0, high: float = 100.0) -> bool:
    if value is None:
        return False
    try:
        v = float(value)
    except (TypeError, ValueError):
        return False
    return low <= v <= high


def validate_symbol_result(result: dict) -> list[str]:
    """Return a list of validation error strings (empty = valid)."""
    errors = []
    for section in ("trend", "momentum", "volatility", "risk", "seasonality", "opportunity"):
        block = result.get(section)
        if block is None:
            errors.append(f"Missing section: {section}")
            continue
        score = block.get("score") if isinstance(block, dict) else None
        if score is not None and not validate_score(section, score):
            errors.append(f"Invalid score in {section}: {score}")
    return errors
