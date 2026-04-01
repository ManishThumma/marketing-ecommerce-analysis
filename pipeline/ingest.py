"""
ingest.py — Load raw CSVs into DataFrames with basic validation.
"""
import pandas as pd
from pathlib import Path

RAW_DIR = Path(__file__).parent.parent / "data" / "raw"


def load_all() -> dict[str, pd.DataFrame]:
    files = {
        "campaigns": "campaigns.csv",
        "customers": "customers.csv",
        "events": "events.csv",
        "products": "products.csv",
        "transactions": "transactions.csv",
    }
    frames = {}
    for name, fname in files.items():
        path = RAW_DIR / fname
        df = pd.read_csv(path)
        print(f"[ingest] {name}: {len(df):,} rows, {df.shape[1]} cols")
        frames[name] = df
    return frames


if __name__ == "__main__":
    data = load_all()
    for name, df in data.items():
        print(f"\n--- {name} ---")
        print(df.dtypes)
        print(df.isnull().sum())
