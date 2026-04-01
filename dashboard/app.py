"""
Main Streamlit entry point — Overview / KPI page.
Run: streamlit run dashboard/app.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pipeline.load import get_connection

st.set_page_config(
    page_title="Marketing & E-Commerce Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Shared data loader (cached) ──────────────────────────────
@st.cache_data
def load_data():
    con = get_connection()
    tx       = con.execute("SELECT * FROM transactions").df()
    c360     = con.execute("SELECT * FROM mart_customer_360").df()
    cp       = con.execute("SELECT * FROM mart_campaign_performance").df()
    events   = con.execute("SELECT * FROM events").df()
    products = con.execute("SELECT * FROM products").df()
    pp       = con.execute("SELECT * FROM mart_product_performance").df()
    con.close()

    tx["timestamp"] = pd.to_datetime(tx["timestamp"])
    tx["month"]     = tx["timestamp"].dt.to_period("M").astype(str)
    events["timestamp"] = pd.to_datetime(events["timestamp"])
    return tx, c360, cp, events, products, pp

tx, c360, cp, events, products, pp = load_data()

# ── Sidebar filters ──────────────────────────────────────────
st.sidebar.title("📊 Analytics Dashboard")
st.sidebar.markdown("---")

years = sorted(tx["timestamp"].dt.year.unique())
sel_years = st.sidebar.multiselect("Filter by Year", years, default=years)

tx_f  = tx[tx["timestamp"].dt.year.isin(sel_years)]
ev_f  = events[events["timestamp"].dt.year.isin(sel_years)]

st.sidebar.markdown("---")
st.sidebar.markdown("**Pages**")
st.sidebar.page_link("app.py",                         label="🏠 Overview")
st.sidebar.page_link("pages/1_customers.py",           label="👥 Customers")
st.sidebar.page_link("pages/2_campaigns.py",           label="📣 Campaigns")
st.sidebar.page_link("pages/3_products.py",            label="🛍️ Products")
st.sidebar.page_link("pages/4_funnel.py",              label="🔽 Funnel & Behavior")

# ── Page header ─────────────────────────────────────────────
st.title("🏠 Business Overview")
st.caption("Marketing & E-Commerce Analytics — full DA/BA/DE project")
st.markdown("---")

# ── KPI Cards ───────────────────────────────────────────────
total_revenue  = tx_f["net_revenue"].sum()
total_orders   = len(tx_f)
unique_buyers  = tx_f["customer_id"].nunique()
aov            = tx_f["net_revenue"].mean()
refund_rate    = tx_f["refund_flag"].mean() * 100
total_events   = len(ev_f)

k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("💰 Net Revenue",    f"${total_revenue:,.0f}")
k2.metric("📦 Total Orders",   f"{total_orders:,}")
k3.metric("👤 Unique Buyers",  f"{unique_buyers:,}")
k4.metric("🛒 Avg Order Value",f"${aov:,.2f}")
k5.metric("↩️ Refund Rate",    f"{refund_rate:.2f}%")
k6.metric("🖱️ Total Events",   f"{total_events:,}")

st.markdown("---")

# ── Monthly Revenue Trend ────────────────────────────────────
monthly = (
    tx_f.groupby("month")
    .agg(orders=("transaction_id","count"), net_revenue=("net_revenue","sum"))
    .reset_index()
)

col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("📈 Monthly Revenue & Orders")
    fig = go.Figure()
    fig.add_bar(x=monthly["month"], y=monthly["orders"],
                name="Orders", marker_color="steelblue", opacity=0.6, yaxis="y")
    fig.add_scatter(x=monthly["month"], y=monthly["net_revenue"],
                    name="Net Revenue", line=dict(color="crimson", width=2),
                    mode="lines+markers", yaxis="y2")
    fig.update_layout(
        yaxis=dict(title="Orders"),
        yaxis2=dict(title="Net Revenue ($)", overlaying="y", side="right"),
        legend=dict(orientation="h"),
        height=380, margin=dict(t=20, b=40),
    )
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("📊 Revenue by Channel")
    ch_rev = (
        tx_f[tx_f["campaign_id"] != 0]
        .merge(cp[["campaign_id","channel"]].drop_duplicates(), on="campaign_id", how="left")
        .groupby("channel")["net_revenue"].sum()
        .sort_values(ascending=False)
        .reset_index()
    )
    fig2 = px.pie(ch_rev, names="channel", values="net_revenue",
                  color_discrete_sequence=px.colors.qualitative.Set2,
                  hole=0.4)
    fig2.update_layout(height=380, margin=dict(t=20))
    st.plotly_chart(fig2, use_container_width=True)

# ── Country & Loyalty ────────────────────────────────────────
col3, col4 = st.columns(2)

with col3:
    st.subheader("🌍 Revenue by Country (Top 10)")
    country_rev = (
        c360[c360["has_purchased"]]
        .groupby("country")["total_revenue"].sum()
        .nlargest(10).reset_index()
    )
    fig3 = px.bar(country_rev, x="country", y="total_revenue",
                  color="total_revenue", color_continuous_scale="Blues",
                  labels={"total_revenue": "Revenue ($)"})
    fig3.update_layout(height=320, margin=dict(t=20), coloraxis_showscale=False)
    st.plotly_chart(fig3, use_container_width=True)

with col4:
    st.subheader("🏅 Revenue by Loyalty Tier")
    tier_rev = (
        c360[c360["has_purchased"]]
        .groupby("loyalty_tier")["total_revenue"].sum()
        .reset_index()
        .sort_values("total_revenue", ascending=False)
    )
    colors_map = {"Bronze": "#cd7f32", "Silver": "#c0c0c0", "Gold": "#ffd700", "Platinum": "#a0ced9"}
    fig4 = px.bar(tier_rev, x="loyalty_tier", y="total_revenue",
                  color="loyalty_tier", color_discrete_map=colors_map,
                  labels={"total_revenue": "Revenue ($)", "loyalty_tier": "Tier"})
    fig4.update_layout(height=320, margin=dict(t=20), showlegend=False)
    st.plotly_chart(fig4, use_container_width=True)

# ── Recent Transactions Table ────────────────────────────────
st.subheader("🧾 Recent Transactions (last 20)")
cols = ["transaction_id","timestamp","customer_id","product_id","quantity","discount_applied","gross_revenue","net_revenue","refund_flag"]
st.dataframe(
    tx_f[cols].sort_values("timestamp", ascending=False).head(20).reset_index(drop=True),
    use_container_width=True, height=280,
)
