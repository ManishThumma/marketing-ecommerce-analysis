"""
Page 2 — Campaign Analytics
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from scipy import stats
from pipeline.load import get_connection

st.set_page_config(page_title="Campaigns", page_icon="📣", layout="wide")

@st.cache_data
def load():
    con = get_connection()
    cp     = con.execute("SELECT * FROM mart_campaign_performance").df()
    events = con.execute("SELECT * FROM events").df()
    con.close()
    events["timestamp"] = pd.to_datetime(events["timestamp"])
    return cp, events

cp, events = load()

st.title("📣 Campaign Analytics")
st.markdown("---")

# ── Sidebar filters ───────────────────────────────────────────
channels = ["All"] + sorted(cp["channel"].dropna().unique().tolist())
sel_channel = st.sidebar.selectbox("Channel", channels)
objectives = ["All"] + sorted(cp["objective"].dropna().unique().tolist())
sel_obj = st.sidebar.selectbox("Objective", objectives)

df = cp.copy()
if sel_channel != "All":
    df = df[df["channel"] == sel_channel]
if sel_obj != "All":
    df = df[df["objective"] == sel_obj]

# ── KPIs ─────────────────────────────────────────────────────
valid = df[df["net_revenue"].notna()]
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Campaigns",         f"{len(df)}")
k2.metric("Total Revenue",     f"${valid['net_revenue'].sum():,.0f}")
k3.metric("Avg Conversion",    f"{valid['conversion_rate'].mean()*100:.2f}%" if len(valid) else "—")
k4.metric("Avg Bounce Rate",   f"{valid['bounce_rate'].mean()*100:.2f}%" if len(valid) else "—")
k5.metric("Avg Duration",      f"{df['duration_days'].mean():.0f} days" if len(df) else "—")

st.markdown("---")

# ── Channel Revenue ───────────────────────────────────────────
col1, col2 = st.columns(2)

with col1:
    st.subheader("📊 Net Revenue by Channel")
    ch = (
        valid.groupby("channel")
        .agg(total_revenue=("net_revenue","sum"), campaigns=("campaign_id","count"))
        .sort_values("total_revenue", ascending=False).reset_index()
    )
    fig = px.bar(ch, x="channel", y="total_revenue", color="channel",
                 text_auto=".2s",
                 labels={"total_revenue":"Net Revenue ($)", "channel":"Channel"})
    fig.update_layout(showlegend=False, height=350, margin=dict(t=20))
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("🎯 Conversion Rate vs Bounce Rate")
    fig2 = px.scatter(valid, x="bounce_rate", y="conversion_rate",
                      color="channel", size="net_revenue",
                      hover_data=["campaign_id","objective","target_segment"],
                      labels={"bounce_rate":"Bounce Rate","conversion_rate":"Conversion Rate"})
    fig2.update_layout(height=350, margin=dict(t=20))
    st.plotly_chart(fig2, use_container_width=True)

# ── Objective comparison ──────────────────────────────────────
col3, col4 = st.columns(2)

with col3:
    st.subheader("🏷️ Performance by Objective")
    obj = (
        valid.groupby("objective")
        .agg(avg_revenue=("net_revenue","mean"), avg_conversion=("conversion_rate","mean"),
             avg_uplift=("expected_uplift","mean"), campaigns=("campaign_id","count"))
        .round(4).reset_index().sort_values("avg_revenue", ascending=False)
    )
    fig3 = px.bar(obj, x="objective", y="avg_revenue", color="objective",
                  labels={"avg_revenue":"Avg Net Revenue ($)", "objective":""})
    fig3.update_layout(showlegend=False, height=320, margin=dict(t=20))
    st.plotly_chart(fig3, use_container_width=True)

with col4:
    st.subheader("🎁 Revenue by Target Segment")
    seg = (
        valid.groupby("target_segment")["net_revenue"].sum()
        .sort_values(ascending=False).reset_index()
    )
    fig4 = px.pie(seg, names="target_segment", values="net_revenue",
                  color_discrete_sequence=px.colors.qualitative.Pastel, hole=0.4)
    fig4.update_layout(height=320, margin=dict(t=20))
    st.plotly_chart(fig4, use_container_width=True)

# ── A/B Test ─────────────────────────────────────────────────
st.markdown("---")
st.subheader("🧪 A/B Test — Experiment Group Analysis")

ab = (
    events.groupby("experiment_group")
    .agg(
        sessions=("session_id","nunique"),
        users=("customer_id","nunique"),
        purchases=("event_type", lambda x: (x=="purchase").sum()),
        bounces=("event_type",   lambda x: (x=="bounce").sum()),
        avg_session=("session_duration_sec","mean"),
    ).reset_index()
)
ab["conversion_rate"] = (ab["purchases"] / ab["sessions"]).round(4)
ab["bounce_rate"]     = (ab["bounces"]   / ab["sessions"]).round(4)

col5, col6 = st.columns(2)
with col5:
    fig5 = px.bar(ab, x="experiment_group", y="conversion_rate", color="experiment_group",
                  text_auto=".3f",
                  labels={"conversion_rate":"Conversion Rate","experiment_group":"Group"})
    fig5.update_layout(showlegend=False, height=320, margin=dict(t=20))
    st.plotly_chart(fig5, use_container_width=True)

with col6:
    fig6 = px.bar(ab, x="experiment_group", y="avg_session", color="experiment_group",
                  text_auto=".0f",
                  labels={"avg_session":"Avg Session (sec)","experiment_group":"Group"})
    fig6.update_layout(showlegend=False, height=320, margin=dict(t=20))
    st.plotly_chart(fig6, use_container_width=True)

# Chi-squared significance test
ctrl  = ab[ab["experiment_group"]=="Control"].iloc[0]
var_a = ab[ab["experiment_group"]=="Variant_A"].iloc[0]
ct = [
    [int(ctrl["purchases"]),  int(ctrl["sessions"]  - ctrl["purchases"])],
    [int(var_a["purchases"]), int(var_a["sessions"] - var_a["purchases"])],
]
chi2, p, _, _ = stats.chi2_contingency(ct)
sig = "✅ Statistically Significant (p < 0.05)" if p < 0.05 else "❌ Not Significant (p ≥ 0.05)"
st.info(f"**Control vs Variant_A Chi² Test** — χ²={chi2:.3f}, p={p:.4f} — {sig}")

# ── Campaign detail table ─────────────────────────────────────
st.markdown("---")
st.subheader("📋 Campaign Detail Table")
show_cols = ["campaign_id","channel","objective","target_segment","duration_days",
             "tx_count","net_revenue","conversion_rate","bounce_rate","revenue_per_visitor"]
show = valid[[c for c in show_cols if c in valid.columns]].sort_values("net_revenue", ascending=False)
st.dataframe(show.reset_index(drop=True), use_container_width=True)
