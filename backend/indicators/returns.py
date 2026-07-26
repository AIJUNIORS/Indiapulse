#!/usr/bin/env python3
"""Return calculations: simple returns, log returns, rate of change."""

import numpy as np
import pandas as pd


def simple_returns(close: pd.Series) -> pd.Series:
    return close.pct_change()


def log_returns(close: pd.Series) -> pd.Series:
    return np.log(close / close.shift(1))


def rate_of_change(close: pd.Series, period: int = 21) -> pd.Series:
    """Percentage change over `period` bars (a momentum indicator)."""
    return (close / close.shift(period) - 1) * 100


def monthly_returns(close: pd.Series) -> pd.Series:
    """Resample a daily close series to month-end returns (for seasonality)."""
    monthly_close = close.resample("ME").last()
    return monthly_close.pct_change() * 100
