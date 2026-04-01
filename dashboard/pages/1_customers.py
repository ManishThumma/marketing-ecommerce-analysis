"""
Page 1 — Customer Analytics
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pipeline.load import get_connection

st.set_page_config(page_title="Customers", page_icon="👥", layout="wide")

@st.cache_data
def load():
    con = get_connection()
    c360      = con.execute("SELECT * FROM mart_customer_360").df()
    customers = con.execute("SELECT * FROM customers").df()
    con.close()
    customers["signup_date"]  = pd.to_datetime(customers["signup_date"])
    customers["signup_month"] = customers["signup_date"].dt.to_period("M").astype(str)
    return c360, customers

c360, customers = load()

st.title("👥 Customer Analytics")
st.markdown("---")

# ── Sidebar filters ──────────────────────────────────────────
countries = ["All"] + sorted(c360["country"].dropna().unique().tolist())
sel_country = st.sidebar.selectbox("Country", countries)
tiers = ["All"] + sorted(c360["loyalty_tier"].dropna().unique().tolist())
sel_tier = st.sidebar.selectbox("Loyalty Tier", tiers)

df = c360.copy()
if sel_country != "All":
    df = df[df["country"] == sel_country]
if sel_tier != "All":
    df = df[df["loyalty_tier"] == sel_tier]

buyers = df[df["has_purchased"]]

# ── KPIs ─────────────────────────────────────────────────────
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Total Customers",  f"{len(df):,}")
k2.metric("Total Buyers",     f"{int(df['has_purchased'].sum()):,}")
k3.metric("Avg LTV",          f"${buyers['total_revenue'].mean():,.2f}" if len(buyers) else "—")
k4.metric("Avg Orders",       f"{buyers['total_orders'].mean():.1f}" if len(buyers) else "—")
k5.metric("Avg AOV",          f"${buyers['avg_order_value'].mean():,.2f}" if len(buyers) else "—")

st.markdown("---")

# ── RFM Segments ─────────────────────────────────────────────
col1, col2 = st.columns(2)

with col1:
    st.subheader("🎯 RFM Segment Distribution")
    seg = df[df["rfm_segment"].notna()]["rfm_segment"].value_counts().reset_index()
    seg.columns = ["segment", "count"]
    color_map = {
        "Champions": "#2ecc71", "Loyal": "#3498db",
        "Potential Loyalist": "#f1c40f", "At Risk": "#e67e22", "Lost": "#e74c3c"
    }
    fig = px.bar(seg, x="segment", y="count", color="segment",
                 color_discrete_map=color_map,
                 labels={"count": "Customers", "segment": ""})
    fig.update_layout(showlegend=False, height=350, margin=dict(t=20))
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("💰 Avg LTV by RFM Segment")
    ltv_seg = (
        df[df["rfm_segment"].notna()]
        .groupby("rfm_segment")["total_revenue"].mean()
        .sort_values(ascending=False).reset_index()
    )
    ltv_seg.columns = ["segment", "avg_ltv"]
    fig2 = px.bar(ltv_seg, x="segment", y="avg_ltv", color="segment",
                  color_discrete_map=color_map,
                  labels={"avg_ltv": "Avg Revenue ($)", "segment": ""})
    fig2.update_layout(showlegend=False, height=350, margin=dict(t=20))
    st.plotly_chart(fig2, use_container_width=True)

# ── Acquisition channel ───────────────────────────────────────
col3, col4 = st.columns(2)

with col3:
    st.subheader("📣 Acquisition Channel — LTV")
    acq = (
        buyers.groupby("acquisition_channel")
        .agg(customers=("customer_id","count"), avg_ltv=("total_revenue","mean"))
        .sort_values("avg_ltv", ascending=False).reset_index()
    )
    fig3 = px.bar(acq, x="acquisition_channel", y="avg_ltv",
                  color="avg_ltv", color_continuous_scale="teal",
                  labels={"avg_ltv": "Avg LTV ($)", "acquisition_channel": "Channel"})
    fig3.update_layout(height=320, margin=dict(t=20), coloraxis_showscale=False)
    st.plotly_chart(fig3, use_container_width=True)

with col4:
    st.subheader("📅 Monthly New Signups by Channel")
    cust_filt = customers.copy()
    if sel_country != "All":
        cust_filt = cust_filt[cust_filt["country"] == sel_country]
    monthly = (
        cust_filt.groupby(["signup_month","acquisition_channel"])["customer_id"]
        .count().unstack(fill_value=0).reset_index()
        .melt(id_vars="signup_month", var_name="channel", value_name="signups")
    )
    fig4 = px.area(monthly, x="signup_month", y="signups", color="channel",
                   labels={"signup_month": "Month", "signups": "New Customers"})
    fig4.update_layout(height=320, margin=dict(t=20), legend=dict(orientation="h"))
    st.plotly_chart(fig4, use_container_width=True)

# ── Loyalty tier breakdown ────────────────────────────────────
st.subheader("🏅 Loyalty Tier Performance")
tier_perf = (
    buyers.groupby("loyalty_tier")
    .agg(
        customers=("customer_id","count"),
        avg_ltv=("total_revenue","mean"),
        avg_orders=("total_orders","mean"),
        avg_aov=("avg_order_value","mean"),
        avg_recency=("recency_days","mean"),
    ).round(2).reset_index()
)
st.dataframe(tier_perf, use_container_width=True)

col5, col6 = st.columns(2)
with col5:
    fig5 = px.bar(tier_perf, x="loyalty_tier", y="avg_ltv",
                  color="loyalty_tier",
                  color_discrete_map={"Bronze":"#cd7f32","Silver":"#c0c0c0","Gold":"#ffd700","Platinum":"#a0ced9"},
                  labels={"avg_ltv":"Avg LTV ($)", "loyalty_tier":"Tier"})
    fig5.update_layout(showlegend=False, height=300, margin=dict(t=20))
    st.plotly_chart(fig5, use_container_width=True)

with col6:
    fig6 = px.scatter(buyers.sample(min(3000, len(buyers))), x="recency_days", y="total_revenue",
                      color="rfm_segment", color_discrete_map=color_map,
                      opacity=0.5, size_max=6,
                      labels={"recency_days":"Recency (days)", "total_revenue":"Total Revenue ($)"})
    fig6.update_layout(height=300, margin=dict(t=20), legend=dict(orientation="h", y=-0.3))
    st.subheader("Recency vs Revenue (sample)")
    st.plotly_chart(fig6, use_container_width=True)
