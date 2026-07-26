"""
IndiaPulse
Market Data Download Engine
"""

from pathlib import Path
from datetime import datetime
import pandas as pd
import yfinance as yf
from tqdm import tqdm

from backend.config import CONFIG
from backend.sources import get_provider


# ----------------------------------------------------------
# Directories
# ----------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent

UNIVERSE_DIR = PROJECT_ROOT / "data" / "universe"
RAW_DIR = PROJECT_ROOT / "data" / "raw"

RAW_DIR.mkdir(parents=True, exist_ok=True)


# ----------------------------------------------------------
# Read all universe CSV files
# ----------------------------------------------------------

def load_universe():

    csv_files = sorted(UNIVERSE_DIR.glob("*.csv"))

    frames = []

    for file in csv_files:

        df = pd.read_csv(file)

        frames.append(df)

    universe = pd.concat(frames, ignore_index=True)

    universe = universe.drop_duplicates(subset="Symbol")

    return universe


# ----------------------------------------------------------
# Yahoo Finance Symbol Mapping
# ----------------------------------------------------------

def yahoo_symbol(symbol):

    """
    Convert IndiaPulse symbols
    into Yahoo Finance symbols.
    """

    return f"{symbol}.NS"


# ----------------------------------------------------------
# Download one symbol
# ----------------------------------------------------------

def download_symbol(symbol):

    yahoo = yahoo_symbol(symbol)

    try:

        df = yf.download(
            yahoo,
            period="10y",
            interval="1d",
            progress=False,
            auto_adjust=False
        )

        if df.empty:

            print(f"⚠ No data : {symbol}")

            return False

        df.reset_index(inplace=True)

        filename = RAW_DIR / f"{symbol}.csv"

        df.to_csv(filename, index=False)

        return True

    except Exception as e:

        print(f"✖ {symbol}: {e}")

        return False


# ----------------------------------------------------------
# Download all
# ----------------------------------------------------------

def download_all():

    universe = load_universe()

    print(f"\nUniverse Size : {len(universe)} symbols\n")

    success = 0

    failed = 0

    for _, row in tqdm(universe.iterrows(), total=len(universe)):

        symbol = row["Symbol"]

        asset = row["AssetClass"]

        provider = get_provider(asset)

        if provider != "yfinance":

            continue

        ok = download_symbol(symbol)

        if ok:

            success += 1

        else:

            failed += 1

    print("\n================================")

    print(f"Downloaded : {success}")

    print(f"Failed     : {failed}")

    print("================================")


# ----------------------------------------------------------
# Main
# ----------------------------------------------------------

if __name__ == "__main__":

    start = datetime.now()

    print("\nIndiaPulse Download Engine")

    download_all()

    end = datetime.now()

    print(f"\nCompleted in {end-start}")
