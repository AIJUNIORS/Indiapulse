"""Tests for backend/external.py -- filesystem-based (manual CSV drop-in),
no network calls, so these use tmp_path and monkeypatch MANUAL_DIR directly.
"""
import pandas as pd
import pytest

import backend.external as external


@pytest.fixture
def manual_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(external, "MANUAL_DIR", tmp_path)
    return tmp_path


def test_returns_none_when_no_manual_csv_and_unknown_provider(manual_dir):
    assert external.fetch_external("CPI", "MOSPI") is None


def test_loads_valid_manual_csv(manual_dir):
    path = manual_dir / "CPI.csv"
    df = pd.DataFrame(
        {"Close": [100.0, 101.5, 103.0]},
        index=pd.date_range("2024-01-01", periods=3, freq="MS"),
    )
    df.index.name = "Date"
    df.to_csv(path)

    out = external.fetch_external("CPI", "MOSPI")
    assert out is not None
    assert len(out) == 3
    assert "Close" in out.columns


def test_manual_csv_missing_close_column_returns_none(manual_dir):
    path = manual_dir / "CPI.csv"
    pd.DataFrame({"NotClose": [1, 2, 3]}, index=pd.date_range("2024-01-01", periods=3)).to_csv(path)
    assert external.fetch_external("CPI", "MOSPI") is None


def test_manual_csv_all_nan_close_returns_none(manual_dir):
    path = manual_dir / "CPI.csv"
    pd.DataFrame(
        {"Close": [None, None, None]},
        index=pd.date_range("2024-01-01", periods=3),
    ).to_csv(path)
    assert external.fetch_external("CPI", "MOSPI") is None


def test_manual_csv_fills_missing_ohlv_columns(manual_dir):
    path = manual_dir / "GDP.csv"
    df = pd.DataFrame({"Close": [200.0, 205.0]}, index=pd.date_range("2024-01-01", periods=2))
    df.to_csv(path)

    out = external.fetch_external("GDP", "MOSPI")
    assert out is not None
    for col in ("Open", "High", "Low"):
        assert col in out.columns
        assert (out[col] == out["Close"]).all()
    assert "Volume" in out.columns
    assert (out["Volume"] == 0).all()


def test_unsupported_provider_still_checks_manual_dir_first(manual_dir):
    # Even for a provider not in SUPPORTED_PROVIDERS at all, a manual
    # CSV should still be picked up -- the manual drop-in path doesn't
    # depend on the provider name being recognized.
    path = manual_dir / "WEIRD.csv"
    pd.DataFrame({"Close": [1.0, 2.0]}, index=pd.date_range("2024-01-01", periods=2)).to_csv(path)
    out = external.fetch_external("WEIRD", "SomeUnknownProvider")
    assert out is not None
