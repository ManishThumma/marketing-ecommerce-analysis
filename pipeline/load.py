"""
load.py — Load cleaned DataFrames and marts into DuckDB warehouse.
"""
import duckdb
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "warehouse.duckdb"


def load_to_duckdb(cleaned: dict, marts: dict):
    con = duckdb.connect(str(DB_PATH))

    # Raw/cleaned tables
    for name, df in cleaned.items():
        con.execute(f"DROP TABLE IF EXISTS {name}")
        con.execute(f"CREATE TABLE {name} AS SELECT * FROM df")
        print(f"[load] {name} → {con.execute(f'SELECT COUNT(*) FROM {name}').fetchone()[0]:,} rows")

    # Analytical marts
    for name, df in marts.items():
        con.execute(f"DROP TABLE IF EXISTS mart_{name}")
        con.execute(f"CREATE TABLE mart_{name} AS SELECT * FROM df")
        print(f"[load] mart_{name} → {con.execute(f'SELECT COUNT(*) FROM mart_{name}').fetchone()[0]:,} rows")

    con.close()
    print(f"\n[load] DuckDB warehouse saved to: {DB_PATH}")
    return str(DB_PATH)


def get_connection():
    return duckdb.connect(str(DB_PATH))
