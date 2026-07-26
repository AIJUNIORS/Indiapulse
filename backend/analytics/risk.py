#!/usr/bin/env python3
"""
Risk Analytics

Combines volatility and drawdown signals into an overall risk score
(0-100, higher = riskier).
"""


def compute_risk(volatility_result: dict) -> dict:
    if volatility_result.get("volatility") == "Insufficient Data":
        return {"risk": "Insufficient Data", "score": 50.0}

    ann_vol = volatility_result.get("annualized_vol_pct", 20)
    dd = abs(volatility_result.get("max_drawdown_pct", -20))

    risk_score = min(100.0, (ann_vol * 1.5) + (dd * 0.5))

    if risk_score >= 65:
        label = "High Risk"
    elif risk_score <= 35:
        label = "Low Risk"
    else:
        label = "Moderate Risk"

    return {"risk": label, "score": round(risk_score, 2)}
