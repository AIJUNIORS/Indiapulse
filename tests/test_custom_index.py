"""Tests for backend/custom_index.py -- mocks yfinance, no real network."""
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from backend.custom_index import build_equal_weight_index


def _fake_ohlcv(closes: list[float]) -> pd.DataFrame:
    idx = pd.date_range("2024-01-01", periods=len(closes), freq="D")
    return pd.DataFrame({
        "Open": closes, "High": closes, "Low": closes,
        "Close": closes, "Volume": [1000] * len(closes),
    }, index=idx)


def test_equal_weight_composite_is_base_100_at_start():
    frames = {
        "A.NS": _fake_ohlcv([100, 110, 120]),
        "B.NS": _fake_ohlcv([50, 55, 60]),
    }
    with patch("yfinance.download", side_effect=lambda sym, **kw: frames[sym]):
        out = build_equal_weight_index(["A.NS", "B.NS"], period="1y", interval="1d")
    assert out is not None
    assert out["Close"].iloc[0] == pytest.approx(100.0, abs=0.01)


def test_equal_weight_composite_reflects_average_return():
    # A doubles, B stays flat -> equal-weight composite should be
    # roughly the midpoint return, not either extreme.
    frames = {
        "A.NS": _fake_ohlcv([100, 200]),
        "B.NS": _fake_ohlcv([100, 100]),
    }
    with patch("yfinance.download", side_effect=lambda sym, **kw: frames[sym]):
        out = build_equal_weight_index(["A.NS", "B.NS"], period="1y", interval="1d")
    final = out["Close"].iloc[-1]
    assert 140 < final < 160  # (100 + 200)/2 -> 150


def test_returns_none_if_fewer_than_two_constituents_have_data():
    frames = {"A.NS": _fake_ohlcv([100, 110])}

    def fake_download(sym, **kw):
        if sym == "A.NS":
            return frames["A.NS"]
        return pd.DataFrame()  # empty -- e.g. delisted constituent

    with patch("yfinance.download", side_effect=fake_download):
        out = build_equal_weight_index(["A.NS", "B.NS"], period="1y", interval="1d")
    assert out is None


def test_returns_none_if_all_constituents_fail():
    with patch("yfinance.download", side_effect=lambda sym, **kw: pd.DataFrame()):
        out = build_equal_weight_index(["A.NS", "B.NS"], period="1y", interval="1d")
    assert out is None


def test_handles_multiindex_columns_from_yfinance():
    # yfinance sometimes returns MultiIndex columns (ticker, field) --
    # confirm the flattening logic in build_equal_weight_index works.
    closes = [100, 105]
    idx = pd.date_range("2024-01-01", periods=2, freq="D")
    df = pd.DataFrame(
        {"Open": closes, "High": closes, "Low": closes, "Close": closes, "Volume": [1, 1]},
        index=idx,
    )
    df.columns = pd.MultiIndex.from_product([df.columns, ["A.NS"]])
    frames = {"A.NS": df, "B.NS": _fake_ohlcv([50, 52])}

    with patch("yfinance.download", side_effect=lambda sym, **kw: frames[sym]):
        out = build_equal_weight_index(["A.NS", "B.NS"], period="1y", interval="1d")
    assert out is not None
    assert not out["Close"].isna().all()


def test_output_has_required_ohlcv_columns():
    frames = {"A.NS": _fake_ohlcv([100, 102, 104]), "B.NS": _fake_ohlcv([50, 51, 52])}
    with patch("yfinance.download", side_effect=lambda sym, **kw: frames[sym]):
        out = build_equal_weight_index(["A.NS", "B.NS"], period="1y", interval="1d")
    assert set(["Open", "High", "Low", "Close", "Volume"]).issubset(out.columns)
    assert not out["Close"].isna().any()
