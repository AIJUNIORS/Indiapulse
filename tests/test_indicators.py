"""
Minimal smoke tests for the indicator layer.
Run with: pytest tests/
"""

import numpy as np
import pandas as pd

from backend.indicators.moving_average import sma, ema
from backend.indicators.rsi import rsi
from backend.indicators.macd import macd
from backend.indicators.atr import atr
from backend.indicators.returns import simple_returns, rate_of_change


def _sample_series(n=300):
    np.random.seed(0)
    return pd.Series(100 + np.cumsum(np.random.randn(n)))


def test_sma_length_matches_input():
    s = _sample_series()
    result = sma(s, 20)
    assert len(result) == len(s)
    assert result.iloc[-1] == pytest_approx(s.tail(20).mean())


def pytest_approx(value, tol=1e-6):
    class _Approx:
        def __eq__(self, other):
            return abs(other - value) < tol
    return _Approx()


def test_rsi_bounded_between_0_and_100():
    s = _sample_series()
    r = rsi(s, 14).dropna()
    assert (r >= 0).all() and (r <= 100).all()


def test_macd_returns_three_columns():
    s = _sample_series()
    result = macd(s)
    assert set(result.columns) == {"MACD", "Signal", "Histogram"}


def test_atr_non_negative():
    s = _sample_series()
    high = s + 1
    low = s - 1
    result = atr(high, low, s, 14).dropna()
    assert (result >= 0).all()


def test_rate_of_change_zero_when_flat():
    s = pd.Series([100.0] * 50)
    roc = rate_of_change(s, 21).dropna()
    assert (roc.abs() < 1e-9).all()
