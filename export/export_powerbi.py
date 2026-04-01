"""
export_powerbi.py — Exports clean CSVs optimised for Power BI import.
Run: python export/export_powerbi.py

Output: exports/powerbi/*.csv
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from pipeline.load import get_connection

OUT_DIR = Path(__file__).parent.parent / "exports" / "powerbi"
OUT_DIR.mkdir(parents=True, exist_ok=True)

print("Loading data from DuckDB...")
con = get_connection()

tx        = con.execute("SELECT * FROM transactions").df()
customers = con.execute("SELECT * FROM customers").df()
campaigns = con.execute("SELECT * FROM campaigns").df()
products  = con.execute("SELECT * FROM products").df()
c360      = con.execute("SELECT * FROM mart_customer_360").df()
cp        = con.execute("SELECT * FROM mart_campaign_performance").df()
funnel    = con.execute("SELECT * FROM mart_funnel").df()
pp        = con.execute("SELECT * FROM mart_product_performance").df()
con.close()

# ── Derived columns ───────────────────────────────────────────
tx["timestamp"] = pd.to_datetime(tx["timestamp"])
tx["date"]      = tx["timestamp"].dt.date.astype(str)
tx["month"]     = tx["timestamp"].dt.to_period("M").astype(str)
tx["year"]      = tx["timestamp"].dt.year
tx["quarter"]   = tx["timestamp"].dt.to_period("Q").astype(str)

customers["signup_date"]  = pd.to_datetime(customers["signup_date"]).dt.date.astype(str)

campaigns["start_date"] = pd.to_datetime(campaigns["start_date"]).dt.date.astype(str)
campaigns["end_date"]   = pd.to_datetime(campaigns["end_date"]).dt.date.astype(str)

products["launch_date"] = pd.to_datetime(products["launch_date"]).dt.date.astype(str)

# Clean up c360 for Power BI
c360_pb = c360[[
    "customer_id","country","age","gender","loyalty_tier","acquisition_channel",
    "signup_date","total_orders","total_revenue","avg_order_value","recency_days",
    "rfm_score","rfm_segment","has_purchased","r_score","f_score","m_score",
]].copy()
c360_pb["signup_date"] = pd.to_datetime(c360_pb["signup_date"]).dt.date.astype(str)
c360_pb["has_purchased"] = c360_pb["has_purchased"].astype(int)

# Campaign performance
cp_pb = cp[[c for c in [
    "campaign_id","channel","objective","target_segment","duration_days",
    "tx_count","net_revenue","gross_revenue","refunds","unique_customers",
    "impressions","unique_visitors","purchases","bounces","add_to_carts",
    "avg_session_sec","bounce_rate","conversion_rate","revenue_per_visitor",
    "expected_uplift","roi"
] if c in cp.columns]].copy()

# Product performance
pp_pb = pp.merge(
    products[["product_id","category","brand","base_price","is_premium"]],
    on="product_id", how="left"
)

# Date dimension (for Power BI time intelligence)
date_range = pd.date_range(
    start=pd.to_datetime(tx["timestamp"]).min().date(),
    end=pd.to_datetime(tx["timestamp"]).max().date(),
    freq="D"
)
date_dim = pd.DataFrame({
    "date":        date_range.strftime("%Y-%m-%d"),
    "year":        date_range.year,
    "quarter":     date_range.to_period("Q").astype(str),
    "month":       date_range.to_period("M").astype(str),
    "month_num":   date_range.month,
    "month_name":  date_range.strftime("%B"),
    "week":        date_range.isocalendar().week.values,
    "day_of_week": date_range.day_name(),
    "is_weekend":  (date_range.dayofweek >= 5).astype(int),
})

# ── Export ────────────────────────────────────────────────────
exports = {
    "fact_transactions":      tx[["transaction_id","date","month","quarter","year",
                                   "customer_id","product_id","campaign_id","quantity",
                                   "discount_applied","gross_revenue","net_revenue","refund_flag"]],
    "dim_customers":          customers,
    "dim_campaigns":          campaigns,
    "dim_products":           products,
    "dim_date":               date_dim,
    "mart_customer_360":      c360_pb,
    "mart_campaign_perf":     cp_pb,
    "mart_funnel":            funnel,
    "mart_product_perf":      pp_pb[[c for c in [
        "product_id","category","brand","base_price","is_premium",
        "units_sold","total_revenue","avg_revenue_per_tx","unique_buyers","discount_rate"
    ] if c in pp_pb.columns]],
}

for name, df in exports.items():
    path = OUT_DIR / f"{name}.csv"
    df.to_csv(path, index=False)
    print(f"  {name}.csv  →  {len(df):,} rows")

print(f"\n✅ Power BI CSVs saved to: {OUT_DIR}")
print("""
─────────────────────────────────────────────
POWER BI IMPORT GUIDE
─────────────────────────────────────────────
1. Open Power BI Desktop
2. Home → Get Data → Text/CSV
3. Import all CSVs from exports/powerbi/
4. Suggested relationships:
   fact_transactions[customer_id]  → dim_customers[customer_id]
   fact_transactions[product_id]   → dim_products[product_id]
   fact_transactions[campaign_id]  → dim_campaigns[campaign_id]
   fact_transactions[date]         → dim_date[date]
   mart_customer_360[customer_id]  → dim_customers[customer_id]
   mart_campaign_perf[campaign_id] → dim_campaigns[campaign_id]

5. Key DAX measures to create:
   Total Revenue   = SUM(fact_transactions[net_revenue])
   Total Orders    = COUNTROWS(fact_transactions)
   Avg Order Value = AVERAGE(fact_transactions[net_revenue])
   Refund Rate     = DIVIDE(COUNTROWS(FILTER(fact_transactions, fact_transactions[refund_flag]=1)), COUNTROWS(fact_transactions))
   Conversion Rate = DIVIDE([Total Orders], DISTINCTCOUNT(fact_transactions[customer_id]))
─────────────────────────────────────────────
""")
