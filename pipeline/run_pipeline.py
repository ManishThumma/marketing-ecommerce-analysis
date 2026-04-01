"""
run_pipeline.py — Orchestrates the full ETL pipeline.
Run: python pipeline/run_pipeline.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.ingest import load_all
from pipeline.clean import clean_all
from pipeline.transform import build_all
from pipeline.load import load_to_duckdb


def run():
    print("=" * 50)
    print("MARKETING E-COMMERCE ETL PIPELINE")
    print("=" * 50)

    print("\n[1/4] INGESTING RAW DATA...")
    raw = load_all()

    print("\n[2/4] CLEANING DATA...")
    cleaned = clean_all(raw)

    print("\n[3/4] BUILDING ANALYTICAL MARTS...")
    marts = build_all(cleaned)

    print("\n[4/4] LOADING TO DUCKDB WAREHOUSE...")
    db_path = load_to_duckdb(cleaned, marts)

    print("\n" + "=" * 50)
    print("PIPELINE COMPLETE")
    print(f"Warehouse: {db_path}")
    print("Tables: campaigns, customers, events, products, transactions")
    print("Marts:  mart_customer_360, mart_campaign_performance, mart_funnel, mart_product_performance")
    print("=" * 50)


if __name__ == "__main__":
    run()
