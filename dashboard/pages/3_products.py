"""
Page 3 — Product Analytics
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
import pandas as pd
import plotly.express as px
from pipeline.load import get_connection

st.set_page_config(page_title="Products", page_icon="🛍️", layout="wide")

@st.cache_data
def load():
    con = get_connection()
    pp = con.execute("SELECT * FROM mart_product_performance").df()
    tx = con.execute("SELECT * FROM transactions").df()
    con.close()
    tx["timestamp"] = pd.to_datetime(tx["timestamp"])
    tx["month"] = tx["timestamp"].dt.to_period("M").astype(str)
    return pp, tx

pp, tx = load()

st.title("🛍️ Product Analytics")
st.markdown("---")

# ── Sidebar filters ───────────────────────────────────────────
categories = ["All"] + sorted(pp["category"].dropna().unique().tolist())
sel_cat = st.sidebar.selectbox("Category", categories)
premium_opt = st.sidebar.radio("Product Type", ["All", "Premium Only", "Non-Premium Only"])

df = pp.copy()
if sel_cat != "All":
    df = df[df["category"] == sel_cat]
if premium_opt == "Premium Only":
    df = df[df["is_premium"] == True]
elif premium_opt == "Non-Premium Only":
    df = df[df["is_premium"] == False]

sold = df[df["total_revenue"] > 0]

# ── KPIs ─────────────────────────────────────────────────────
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Total Products",    f"{len(df):,}")
k2.metric("Products Sold",     f"{len(sold):,}")
k3.metric("Total Revenue",     f"${sold['total_revenue'].sum():,.0f}" if len(sold) else "—")
k4.metric("Total Units",       f"{int(sold['units_sold'].sum()):,}" if len(sold) else "—")
k5.metric("Avg Price",         f"${df['base_price'].mean():,.2f}" if len(df) else "—")

st.markdown("---")

# ── Category revenue ──────────────────────────────────────────
col1, col2 = st.columns(2)

with col1:
    st.subheader("📦 Revenue by Category")
    cat = (
        sold.groupby("category")
        .agg(total_revenue=("total_revenue","sum"), units_sold=("units_sold","sum"),
             products=("product_id","count"))
        .sort_values("total_revenue", ascending=False).reset_index()
    )
    fig = px.bar(cat, x="category", y="total_revenue", color="category",
                 text_auto=".2s",
                 labels={"total_revenue":"Net Revenue ($)", "category":""})
    fig.update_layout(showlegend=False, height=360, margin=dict(t=20))
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("📊 Units Sold by Category")
    fig2 = px.pie(cat, names="category", values="units_sold",
                  color_discrete_sequence=px.colors.qualitative.Pastel, hole=0.35)
    fig2.update_layout(height=360, margin=dict(t=20))
    st.plotly_chart(fig2, use_container_width=True)

# ── Premium analysis ──────────────────────────────────────────
col3, col4 = st.columns(2)

with col3:
    st.subheader("⭐ Premium vs Non-Premium")
    prem = (
        sold.groupby("is_premium")
        .agg(total_revenue=("total_revenue","sum"), units=("units_sold","sum"),
             avg_price=("base_price","mean"), products=("product_id","count"))
        .round(2).reset_index()
    )
    prem["label"] = prem["is_premium"].map({True: "Premium", False: "Non-Premium"})
    fig3 = px.bar(prem, x="label", y="total_revenue", color="label",
                  text_auto=".2s",
                  color_discrete_map={"Premium":"#ffd700","Non-Premium":"#95a5a6"},
                  labels={"total_revenue":"Net Revenue ($)", "label":""})
    fig3.update_layout(showlegend=False, height=320, margin=dict(t=20))
    st.plotly_chart(fig3, use_container_width=True)

with col4:
    st.subheader("💲 Price vs Revenue")
    sample = sold.sample(min(500, len(sold)))
    fig4 = px.scatter(sample, x="base_price", y="total_revenue",
                      color="category", size="units_sold",
                      hover_data=["product_id","brand"],
                      labels={"base_price":"Base Price ($)","total_revenue":"Revenue ($)"})
    fig4.update_layout(height=320, margin=dict(t=20))
    st.plotly_chart(fig4, use_container_width=True)

# ── Top 20 products ───────────────────────────────────────────
st.markdown("---")
st.subheader("🏆 Top 20 Products by Revenue")
top20 = sold.nlargest(20, "total_revenue")[
    ["product_id","category","brand","base_price","is_premium",
     "units_sold","total_revenue","unique_buyers","discount_rate"]
].round(3)
st.dataframe(top20.reset_index(drop=True), use_container_width=True)

# ── Monthly revenue for top categories ───────────────────────
st.subheader("📅 Monthly Revenue Trend — Top 4 Categories")
top_cats = cat.nlargest(4, "total_revenue")["category"].tolist()
tx_cat = tx.merge(pp[["product_id","category"]], on="product_id", how="left")
tx_cat = tx_cat[tx_cat["category"].isin(top_cats) & ~tx_cat["refund_flag"]]
monthly_cat = (
    tx_cat.groupby(["month","category"])["net_revenue"]
    .sum().reset_index()
)
fig5 = px.line(monthly_cat, x="month", y="net_revenue", color="category",
               markers=True,
               labels={"net_revenue":"Net Revenue ($)", "month":"Month"})
fig5.update_layout(height=380, margin=dict(t=20), legend=dict(orientation="h"))
st.plotly_chart(fig5, use_container_width=True)
