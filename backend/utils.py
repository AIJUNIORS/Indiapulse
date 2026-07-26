"""
Utility Functions
"""

from pathlib import Path
import pandas as pd


def ensure_directory(path):
    Path(path).mkdir(parents=True, exist_ok=True)


def read_csv(path):
    return pd.read_csv(path)


def save_csv(df, path):
    df.to_csv(path, index=False)
