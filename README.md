# Marketing & E-Commerce Analytics

This project is a full end-to-end data analysis built on a real-world style marketing and e-commerce dataset — covering data engineering, customer analytics, campaign performance, and product insights.

The goal was simple: take raw CSVs, build a proper data pipeline, and answer the kind of questions a business actually cares about — who are our best customers, which campaigns are working, where are we losing people in the funnel, and what's driving revenue.

Dataset source: [Kaggle — Marketing & E-Commerce Analytics](https://www.kaggle.com/datasets/geethasagarbonthu/marketing-and-e-commerce-analytics-dataset/data)

---

## What's in the Data

Five tables, spanning 2021–2024:

| File | Rows | What it covers |
|---|---|---|
| `campaigns.csv` | 50 | 50 marketing campaigns across channels, with objectives and target segments |
| `customers.csv` | 100,000 | Demographics, loyalty tiers, how they were acquired |
| `events.csv` | 2,000,000 | Every click, view, cart add, purchase and bounce — the full clickstream |
| `products.csv` | 2,000 | Product catalogue with categories, brands, pricing |
| `transactions.csv` | 103,127 | Every order — revenue, discounts applied, refund flags |

2 million events is a decent size. Enough to find real patterns without needing a cluster to run it.

---

## How It's Built

```
marketing-ecommerce-analysis/
├── data/
│   ├── raw/               # Original CSVs (download from Kaggle)
│   └── warehouse.duckdb   # Local analytics warehouse
│
├── pipeline/              # The ETL — where raw data becomes usable data
│   ├── ingest.py          # Loads all 5 CSVs
│   ├── clean.py           # Fixes types, handles nulls, adds useful derived columns
│   ├── transform.py       # Builds the 4 analytical marts
│   ├── load.py            # Writes everything into DuckDB
│   └── run_pipeline.py    # Run this to rebuild the whole warehouse from scratch
│
├── notebooks/             # The analysis — this is where the actual work happens
│   ├── 01_eda.ipynb                        # First look at the data
│   ├── 02_customer_analysis.ipynb          # RFM segmentation, LTV, who's actually valuable
│   ├── 03_campaign_analysis.ipynb          # Which campaigns worked, A/B test results
│   ├── 04_revenue_product_analysis.ipynb   # Revenue trends, discount impact, refunds
│   └── 05_funnel_behavioral_analysis.ipynb # Where people drop off, device/time patterns
│
├── sql/
│   └── queries.sql        # All the key queries — useful reference for Power BI DAX too
│
├── export/
│   ├── export_excel.py          # Generates the formatted Excel workbook
│   ├── export_powerbi.py        # Exports star-schema CSVs for Power BI
│   └── generate_screenshots.py  # Reproduces all the charts below
│
└── screenshots/           # Chart exports — previewed at the bottom of this README
```

---

## The Data Warehouse (DuckDB)

Rather than querying raw CSVs every time, everything gets loaded into DuckDB — a fast local analytical database. Four marts get built on top of it:

| Mart | What it gives you |
|---|---|
| `mart_customer_360` | Every customer's full picture — RFM score, total spend, recency, order history, session behaviour |
| `mart_campaign_performance` | Each campaign's actual results — revenue driven, conversion rate, bounce rate, revenue per visitor |
| `mart_funnel` | The aggregate funnel from view to purchase, with drop-off rates at each stage |
| `mart_product_performance` | Per-product revenue, units sold, discount rates, unique buyers |

---

## Getting Started

```bash
# Install dependencies
pip install -r requirements.txt

# Build the warehouse (takes ~2 mins for 2M events)
python pipeline/run_pipeline.py

# Export to Excel
python export/export_excel.py
# → exports/Marketing_Ecommerce_Analytics.xlsx

# Export CSVs for Power BI
python export/export_powerbi.py
# → exports/powerbi/*.csv

# Open the notebooks
python notebooks/generate_notebooks.py
jupyter lab
```

---

## Connecting to Power BI

The export creates a proper star schema — fact table, dimension tables, and a date dimension for time intelligence.

1. Open Power BI Desktop → **Get Data → Text/CSV**
2. Import everything from `exports/powerbi/`
3. Set up these relationships in Model view:
   - `fact_transactions[customer_id]` → `dim_customers[customer_id]`
   - `fact_transactions[product_id]` → `dim_products[product_id]`
   - `fact_transactions[campaign_id]` → `dim_campaigns[campaign_id]`
   - `fact_transactions[date]` → `dim_date[date]`

Some DAX measures to get started:

```dax
Total Revenue   = SUM(fact_transactions[net_revenue])
Total Orders    = COUNTROWS(fact_transactions)
Avg Order Value = AVERAGE(fact_transactions[net_revenue])
Refund Rate     = DIVIDE(
                    COUNTROWS(FILTER(fact_transactions, fact_transactions[refund_flag] = 1)),
                    COUNTROWS(fact_transactions)
                  )
```

---

## What the Analysis Found

A few things worth highlighting from the data:

**Customers**
- Champions (the top RFM segment) spend an average of **$298** — nearly 6x more than At Risk customers ($49). Retaining these people matters far more than acquiring new ones.
- Organic acquisition produces the highest LTV customers. Paid Search brings volume but lower lifetime value — worth knowing before increasing ad spend.
- 4 countries (US, IN, BR, AU) account for the majority of revenue. The rest is fairly spread.

**Campaigns**
- Email and Paid Search drive the most revenue, but their conversion rates tell a more nuanced story — high volume doesn't always mean high efficiency.
- The A/B test results show a statistically significant difference between experiment groups. Variant A outperforms Control on conversion rate, which has real implications for future campaign design.

**Products**
- Premium products represent 50% of the catalogue but a disproportionate share of revenue — they punch above their weight.
- A handful of product IDs consistently appear at the top. These are the ones worth protecting in inventory and promoting in campaigns.

**Funnel**
- The biggest drop-off is between View and Click — most people who land on a page don't engage further. That's the leak worth fixing.
- Mobile converts better than desktop on this dataset, which runs counter to common assumptions.

---

## Tech Stack

| Layer | Tool |
|---|---|
| Data Warehouse | DuckDB |
| ETL & Transformation | Python, pandas |
| Analysis | Jupyter, pandas, scipy |
| Visualisation | matplotlib, seaborn, plotly |
| Exports | openpyxl (Excel), CSV (Power BI) |
| Version Control | Git / GitHub |

---

## Analysis Screenshots

### Executive Summary — KPIs at a Glance
![Executive Summary](screenshots/01_executive_summary.png)

### Monthly Revenue & Order Trends
![Revenue Trends](screenshots/02_monthly_revenue_trend.png)

### Customer Analytics — RFM Segmentation & LTV
![Customer RFM LTV](screenshots/03_customer_rfm_ltv.png)

### Campaign Performance — ROI & A/B Test
![Campaign Performance](screenshots/04_campaign_performance.png)

### Product Analytics — Category Revenue & Premium Split
![Product Analytics](screenshots/05_product_analytics.png)

### Conversion Funnel & Traffic Source Breakdown
![Funnel Analysis](screenshots/06_funnel_analysis.png)

### Behavioural Heatmap — When People Are Most Active
![Behavioral Heatmap](screenshots/07_behavioral_heatmap.png)

### Acquisition Channels & Revenue by Country
![Acquisition Country](screenshots/08_acquisition_country.png)

### Refund Rate Trend & Discount Impact on AOV
![Refund Discount](screenshots/09_refund_discount_analysis.png)

### Top 10 Products by Revenue
![Top 10 Products](screenshots/10_top10_products.png)
