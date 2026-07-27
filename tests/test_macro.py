"""Tests for backend/macro.py -- pure logic (trend/direction calculations)
and filesystem-based series loading, mocked/monkeypatched, no network.
"""
import pandas as pd
import pytest

import backend.macro as macro


@pytest.fixture
def historical_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(macro, "HISTORICAL_DIR", tmp_path)
    return tmp_path


def _write_series(dir_, symbol, closes):
    path = dir_ / f"{symbol}.csv"
    df = pd.DataFrame({"Close": closes}, index=pd.date_range("2024-01-01", periods=len(closes), freq="MS"))
    df.to_csv(path)


def test_pct_change_basic():
    df = pd.DataFrame({"Close": [100.0, 110.0]})
    assert macro._pct_change(df) == pytest.approx(10.0)


def test_pct_change_needs_two_points():
    assert macro._pct_change(pd.DataFrame({"Close": [100.0]})) is None


def test_pct_change_handles_zero_prior():
    assert macro._pct_change(pd.DataFrame({"Close": [0.0, 5.0]})) is None


def test_get_growth_trend_falls_back_to_neutral_when_no_data(historical_dir):
    change, src = macro.get_growth_trend()
    assert change == 0.0
    assert src is None


def test_get_growth_trend_uses_first_available_symbol_in_priority_order(historical_dir):
    # GDP is first in GROWTH_SYMBOLS -- should win over IIP even if
    # IIP also has data.
    _write_series(historical_dir, "GDP", [100, 105])
    _write_series(historical_dir, "IIP", [50, 40])
    change, src = macro.get_growth_trend()
    assert src == "GDP"
    assert change == pytest.approx(5.0)


def test_get_growth_trend_skips_to_next_symbol_if_first_missing(historical_dir):
    _write_series(historical_dir, "PMI_MFG", [50, 55])
    change, src = macro.get_growth_trend()
    assert src == "PMI_MFG"
    assert change == pytest.approx(10.0)


def test_get_rate_direction_hiking(historical_dir):
    _write_series(historical_dir, "REPO_RATE", [6.0, 6.25])
    assert macro.get_rate_direction() == "hiking"


def test_get_rate_direction_cutting(historical_dir):
    _write_series(historical_dir, "REPO_RATE", [6.25, 6.0])
    assert macro.get_rate_direction() == "cutting"


def test_get_rate_direction_hold_when_unchanged(historical_dir):
    _write_series(historical_dir, "REPO_RATE", [6.0, 6.0])
    assert macro.get_rate_direction() == "hold"


def test_get_rate_direction_defaults_to_hold_when_no_data(historical_dir):
    assert macro.get_rate_direction() == "hold"


def test_get_cycle_inputs_bundles_all_fields(historical_dir):
    _write_series(historical_dir, "GDP", [100, 103])
    _write_series(historical_dir, "CPI", [110, 112])
    _write_series(historical_dir, "REPO_RATE", [6.5, 6.5])
    inputs = macro.get_cycle_inputs()
    assert set(inputs) == {
        "growth_trend", "inflation_trend", "rate_direction",
        "growth_source", "inflation_source",
    }
    assert inputs["growth_source"] == "GDP"
    assert inputs["inflation_source"] == "CPI"
    assert inputs["rate_direction"] == "hold"
