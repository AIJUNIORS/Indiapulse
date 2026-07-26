#!/usr/bin/env python3
"""
IndiaPulse - Shared Utilities
"""

from pathlib import Path
import csv
import json


def read_universe_csv(filepath: Path) -> list[dict]:
    """Read a universe CSV file into a list of dict rows."""
    if not filepath.exists():
        return []
    with open(filepath, "r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_json(filepath: Path, data) -> None:
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


def read_json(filepath: Path, default=None):
    if not filepath.exists():
        return default
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def safe_symbol_filename(symbol: str) -> str:
    """Sanitize a symbol for use as a filename."""
    return "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in symbol)


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def normalize(value: float, min_value: float, max_value: float) -> float:
    """Normalize a value to a 0-100 scale given a min/max range."""
    if max_value == min_value:
        return 50.0
    score = (value - min_value) / (max_value - min_value) * 100
    return clamp(score)
