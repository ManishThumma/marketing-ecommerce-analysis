# Marketing & E-Commerce Analytics

A full **Data Analytics / Business Analytics / Data Engineering** project built on the [Marketing & E-Commerce Analytics Dataset](https://www.kaggle.com/datasets/geethasagarbonthu/marketing-and-e-commerce-analytics-dataset/data).

---

## Dataset

| File | Rows | Description |
|---|---|---|
| `campaigns.csv` | 50 | Channel, objective, target segment, expected uplift |
| `customers.csv` | 100,000 | Demographics, loyalty tier, acquisition channel |
| `events.csv` | 2,000,000 | Clickstream — views, clicks, carts, purchases, bounces |
| `products.csv` | 2,000 | Category, brand, price, premium flag |
| `transactions.csv` | 103,127 | Revenue, discounts, refunds |

---

## Project Structure

```
marketing-ecommerce-analysis/
├── data/
│   ├── raw/               # Original CSVs
│   └── warehouse.duckdb   # DuckDB local warehouse (generated)
│
├── pipeline/              # DATA ENGINEERING
│   ├── ingest.py          # Load raw CSVs
│   ├── clean.py           # Type casting, null handling, derived columns
│   ├── transform.py       # Build analytical marts (Customer 360, Campaign Performance, Funnel, Products)
│   ├── load.py            # Persist to DuckDB
│   └── run_pipeline.py    # Orchestrator — run everything end-to-end
│
├── notebooks/             # JUPYTER ANALYSIS
│   ├── 01_eda.ipynb                       # Exploratory Data Analysis
│   ├── 02_customer_analysis.ipynb         # RFM segmentation, LTV, cohort analysis
│   ├── 03_campaign_analysis.ipynb         # Campaign ROI, A/B testing
│   ├── 04_revenue_product_analysis.ipynb  # Revenue trends, discount & refund analysis
│   └── 05_funnel_behavioral_analysis.ipynb # Funnel, device, session heatmaps
│
├── sql/
│   └── queries.sql        # Key analytical SQL queries (DuckDB dialect)
│
├── dashboard/             # STREAMLIT DASHBOARD
│   ├── app.py             # Home — KPI overview
│   └── pages/
│       ├── 1_customers.py     # RFM, LTV, acquisition, loyalty
│       ├── 2_campaigns.py     # ROI, A/B test, channel comparison
│       ├── 3_products.py      # Category, premium vs non-premium, top products
│       └── 4_funnel.py        # Funnel, heatmap, traffic source, experiment groups
│
└── requirements.txt
```

---

## Analytical Marts (DuckDB)

| Mart | Description |
|---|---|
| `mart_customer_360` | Per-customer: RFM scores, LTV, recency, order history, session behavior |
| `mart_campaign_performance` | Per-campaign: revenue, conversion rate, bounce rate, revenue per visitor |
| `mart_funnel` | Aggregate funnel: view → click → add_to_cart → purchase with drop-off rates |
| `mart_product_performance` | Per-product: units sold, revenue, discount rate, unique buyers |

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the ETL pipeline (generates DuckDB warehouse)
python pipeline/run_pipeline.py

# 3. Launch the Streamlit dashboard
streamlit run dashboard/app.py

# 4. (Optional) Generate Jupyter notebooks
python notebooks/generate_notebooks.py
jupyter lab
```

---

## Key Insights Covered

- **Revenue trends** — monthly orders, AOV, refund rates
- **Customer segmentation** — RFM (Champions → Lost), loyalty tier, LTV by acquisition channel
- **Campaign ROI** — revenue per channel, conversion vs bounce, expected vs actual uplift
- **A/B Testing** — chi-squared significance test across experiment groups
- **Conversion funnel** — view → purchase drop-off by device and traffic source
- **Behavioral patterns** — hourly/daily heatmaps, session duration by page category
- **Product analysis** — top products, category revenue, premium vs non-premium

---

## Tech Stack

| Layer | Tool |
|---|---|
| Data Warehouse | DuckDB |
| ETL / Transformation | Python (pandas) |
| Analysis | Jupyter, pandas, scipy |
| Visualization | Plotly, matplotlib, seaborn |
| Dashboard | Streamlit |
| Version Control | Git / GitHub |
