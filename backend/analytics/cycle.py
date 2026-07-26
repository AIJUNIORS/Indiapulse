#!/usr/bin/env python3
"""
Macro Cycle Analytics

Classifies the current macro cycle stage using CPI trend, IIP/GDP
growth trend, and the monetary policy stance (repo rate direction).
Stages: Recovery -> Expansion -> Peak -> Slowdown -> Recession -> Recovery
"""

CYCLE_STAGES = ["Recovery", "Expansion", "Peak", "Slowdown", "Recession"]

# Which sectors/asset classes tend to be favoured in each stage
STAGE_PREFERENCES = {
    "Recovery": ["NIFTYAUTO", "NIFTYREALTY", "NIFTYBANK", "SILVER"],
    "Expansion": ["NIFTYIT", "NIFTYCAPITALMARKET", "NIFTYINFRA"],
    "Peak": ["NIFTYENERGY", "NIFTYMETAL", "GOLD"],
    "Slowdown": ["NIFTYFMCG", "NIFTYPHARMA", "GSEC10Y"],
    "Recession": ["GOLD", "GSEC10Y", "NIFTYFMCG"],
}


def compute_cycle(growth_trend: float, inflation_trend: float, rate_direction: str) -> dict:
    """
    growth_trend: recent growth momentum, positive = accelerating (e.g. IIP/GDP YoY delta)
    inflation_trend: recent CPI momentum, positive = accelerating inflation
    rate_direction: "hiking" | "cutting" | "hold"
    """
    if growth_trend > 0 and inflation_trend <= 0:
        stage = "Recovery"
    elif growth_trend > 0 and inflation_trend > 0 and rate_direction != "cutting":
        stage = "Expansion"
    elif growth_trend <= 0 and inflation_trend > 0:
        stage = "Peak"
    elif growth_trend < 0 and rate_direction == "cutting":
        stage = "Slowdown"
    else:
        stage = "Recession"

    stage_score_map = {"Recovery": 80, "Expansion": 90, "Peak": 55, "Slowdown": 35, "Recession": 15}

    return {
        "cycle_stage": stage,
        "score": stage_score_map[stage],
        "preferred_segments": STAGE_PREFERENCES[stage],
    }
