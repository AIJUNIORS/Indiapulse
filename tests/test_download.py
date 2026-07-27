"""Tests for backend/download.py -- mocks _download_with_retry,
build_equal_weight_index, and fetch_external directly (no real network
or filesystem beyond tmp_path), covering the three source-type branches
in download_symbol() and the incremental/merge logic.
"""
from unittest.mock import patch

import pandas as pd
import pytest

import backend.download as download


def _ohlcv(rows=3):
    idx = pd.date_range("2024-01-01", periods=rows, freq="D")
    return pd.DataFrame(
        {"Open": [1] * rows, "High": [1] * rows, "Low": [1] * rows,
         "Close": [1] * rows, "Volume": [1] * rows},
        index=idx,
    )


@pytest.fixture
def historical_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(download, "HISTORICAL_DIR", tmp_path)
    return tmp_path


def test_validate_dataframe_requires_ohlcv_columns():
    bad = pd.DataFrame({"Close": [1, 2, 3]})
    assert download.validate_dataframe(bad, "TEST") is False


def test_validate_dataframe_rejects_all_nan_close():
    df = _ohlcv()
    df["Close"] = None
    assert download.validate_dataframe(df, "TEST") is False


def test_validate_dataframe_accepts_good_data():
    assert download.validate_dataframe(_ohlcv(), "TEST") is True


def test_download_symbol_routes_index_source_to_download_with_retry(historical_dir):
    row = {"Symbol": "NIFTY50", "AssetClass": "Equity"}
    with patch("backend.download.get_source", return_value={"source": "INDEX", "ticker": "^NSEI"}), \
         patch("backend.download._download_with_retry", return_value=_ohlcv()) as mock_dl, \
         patch("backend.download.build_equal_weight_index") as mock_custom, \
         patch("backend.download.fetch_external") as mock_ext:
        result = download.download_symbol(row)
    assert result is True
    mock_dl.assert_called_once()
    mock_custom.assert_not_called()
    mock_ext.assert_not_called()


def test_download_symbol_routes_custom_source_to_equal_weight_builder(historical_dir):
    row = {"Symbol": "NIFTYPOWER", "AssetClass": "Equity"}
    entry = {"source": "CUSTOM", "symbols": ["NTPC.NS", "POWERGRID.NS"], "method": "equal_weight"}
    with patch("backend.download.get_source", return_value=entry), \
         patch("backend.download.build_equal_weight_index", return_value=_ohlcv()) as mock_custom, \
         patch("backend.download._download_with_retry") as mock_dl:
        result = download.download_symbol(row)
    assert result is True
    mock_custom.assert_called_once()
    mock_dl.assert_not_called()


def test_download_symbol_routes_external_source_to_fetch_external(historical_dir):
    row = {"Symbol": "CORPBOND", "AssetClass": "FixedIncome"}
    entry = {"source": "EXTERNAL", "provider": "RBI"}
    with patch("backend.download.get_source", return_value=entry), \
         patch("backend.download.fetch_external", return_value=_ohlcv()) as mock_ext:
        result = download.download_symbol(row)
    assert result is True
    mock_ext.assert_called_once_with("CORPBOND", "RBI")


def test_download_symbol_returns_false_when_no_source_mapping(historical_dir):
    row = {"Symbol": "UNKNOWN", "AssetClass": "Equity"}
    with patch("backend.download.get_source", return_value=None):
        assert download.download_symbol(row) is False


def test_download_symbol_returns_false_for_index_with_missing_ticker(historical_dir):
    row = {"Symbol": "GROWTH", "AssetClass": "Equity"}
    entry = {"source": "ETF", "ticker": None}
    with patch("backend.download.get_source", return_value=entry):
        assert download.download_symbol(row) is False


def test_download_symbol_returns_false_when_provider_not_implemented(historical_dir):
    row = {"Symbol": "SDL", "AssetClass": "SomeUnsupportedClass"}
    with patch("backend.download.get_provider_for_asset_class", return_value="not_implemented"):
        assert download.download_symbol(row) is False


def test_download_symbol_returns_false_on_failed_validation(historical_dir):
    row = {"Symbol": "NIFTY50", "AssetClass": "Equity"}
    bad_df = pd.DataFrame({"Close": [None, None]})  # missing OHLCV cols entirely
    with patch("backend.download.get_source", return_value={"source": "INDEX", "ticker": "^NSEI"}), \
         patch("backend.download._download_with_retry", return_value=bad_df):
        assert download.download_symbol(row) is False


def test_download_symbol_writes_csv_to_historical_dir(historical_dir):
    row = {"Symbol": "NIFTY50", "AssetClass": "Equity"}
    with patch("backend.download.get_source", return_value={"source": "INDEX", "ticker": "^NSEI"}), \
         patch("backend.download._download_with_retry", return_value=_ohlcv()), \
         patch("backend.download.time.sleep"):
        download.download_symbol(row)
    assert (historical_dir / "NIFTY50.csv").exists()


def test_load_universe_dedupes_across_files(tmp_path, monkeypatch):
    monkeypatch.setattr(download, "UNIVERSE_DIR", tmp_path)
    (tmp_path / "broad_market.csv").write_text("Symbol,AssetClass,Active\nNIFTY50,Equity,True\n")
    (tmp_path / "sectors.csv").write_text("Symbol,AssetClass,Active\nNIFTY50,Equity,True\nNIFTYBANK,Equity,True\n")
    monkeypatch.setattr(download, "UNIVERSE_FILES", ["broad_market.csv", "sectors.csv"])
    universe = download.load_universe()
    symbols = [r["Symbol"] for r in universe]
    assert symbols.count("NIFTY50") == 1
    assert "NIFTYBANK" in symbols


def test_load_universe_skips_inactive_rows(tmp_path, monkeypatch):
    monkeypatch.setattr(download, "UNIVERSE_DIR", tmp_path)
    (tmp_path / "broad_market.csv").write_text("Symbol,AssetClass,Active\nDEAD,Equity,False\nALIVE,Equity,True\n")
    monkeypatch.setattr(download, "UNIVERSE_FILES", ["broad_market.csv"])
    symbols = [r["Symbol"] for r in download.load_universe()]
    assert "DEAD" not in symbols
    assert "ALIVE" in symbols
