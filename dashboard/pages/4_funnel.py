"""
Page 4 — Funnel & Behavioral Analysis
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pipeline.load import get_connection

st.set_page_config(page_title="Funnel & Behavior", page_icon="🔽", layout="wide")

@st.cache_data
def load():
    con = get_connection()
    events = con.execute("SELECT * FROM events").df()
    funnel = con.execute("SELECT * FROM mart_funnel").df()
    con.close()
    events["timestamp"]   = pd.to_datetime(events["timestamp"])
    events["hour"]        = events["timestamp"].dt.hour
    events["day_of_week"] = events["timestamp"].dt.day_name()
    events["month"]       = events["timestamp"].dt.to_period("M").astype(str)
    return events, funnel

events, funnel = load()

st.title("🔽 Funnel & Behavioral Analysis")
st.markdown("---")

# ── Sidebar ───────────────────────────────────────────────────
devices = ["All"] + sorted(events["device_type"].dropna().unique().tolist())
sel_device = st.sidebar.selectbox("Device Type", devices)
sources = ["All"] + sorted(events["traffic_source"].dropna().unique().tolist())
sel_source = st.sidebar.selectbox("Traffic Source", sources)

ev = events.copy()
if sel_device != "All":
    ev = ev[ev["device_type"] == sel_device]
if sel_source != "All":
    ev = ev[ev["traffic_source"] == sel_source]

# ── KPIs ─────────────────────────────────────────────────────
total_sessions  = ev["session_id"].nunique()
purchases_count = (ev["event_type"] == "purchase").sum()
bounce_count    = (ev["event_type"] == "bounce").sum()
avg_session     = ev["session_duration_sec"].mean()
conv_rate       = purchases_count / total_sessions if total_sessions else 0
bounce_rate     = bounce_count / len(ev) if len(ev) else 0

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Total Sessions",    f"{total_sessions:,}")
k2.metric("Purchases",         f"{purchases_count:,}")
k3.metric("Conversion Rate",   f"{conv_rate*100:.2f}%")
k4.metric("Bounce Rate",       f"{bounce_rate*100:.2f}%")
k5.metric("Avg Session (sec)", f"{avg_session:.1f}")

st.markdown("---")

# ── Funnel chart ──────────────────────────────────────────────
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("🔽 Conversion Funnel")
    stages = ["view", "click", "add_to_cart", "purchase"]
    counts = ev[ev["event_type"].isin(stages)]["event_type"].value_counts()
    funnel_data = pd.DataFrame({
        "stage": stages,
        "count": [counts.get(s, 0) for s in stages],
    })
    funnel_data["pct_of_top"] = (funnel_data["count"] / funnel_data["count"].iloc[0] * 100).round(1)

    fig = go.Figure(go.Funnel(
        y=funnel_data["stage"],
        x=funnel_data["count"],
        textinfo="value+percent initial",
        marker=dict(color=["#3498db","#2ecc71","#f1c40f","#e74c3c"]),
    ))
    fig.update_layout(height=380, margin=dict(t=20))
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("📱 Funnel by Device Type")
    dev_funnel = (
        ev[ev["event_type"].isin(stages)]
        .groupby(["device_type","event_type"])["event_id"].count()
        .unstack(fill_value=0)
    )
    dev_funnel = dev_funnel[[s for s in stages if s in dev_funnel.columns]]
    dev_norm = dev_funnel.div(dev_funnel["view"], axis=0).round(4).reset_index()
    dev_melt = dev_norm.melt(id_vars="device_type", var_name="stage", value_name="rate")
    fig2 = px.bar(dev_melt, x="stage", y="rate", color="device_type", barmode="group",
                  labels={"rate":"Rate vs Views","stage":"Stage"},
                  category_orders={"stage": stages})
    fig2.update_layout(height=380, margin=dict(t=20), legend=dict(orientation="h"))
    st.plotly_chart(fig2, use_container_width=True)

# ── Traffic source ────────────────────────────────────────────
col3, col4 = st.columns(2)

with col3:
    st.subheader("🌐 Conversion Rate by Traffic Source")
    src = (
        ev.groupby("traffic_source").agg(
            views=("event_type",    lambda x: (x=="view").sum()),
            purchases=("event_type",lambda x: (x=="purchase").sum()),
            bounces=("event_type",  lambda x: (x=="bounce").sum()),
        ).reset_index()
    )
    src["conversion_rate"] = (src["purchases"] / src["views"].replace(0,1)).round(4)
    src["bounce_rate"]     = (src["bounces"]   / (src["views"] + src["bounces"]).replace(0,1)).round(4)
    src = src.sort_values("conversion_rate", ascending=False)
    fig3 = px.bar(src, x="traffic_source", y="conversion_rate",
                  color="conversion_rate", color_continuous_scale="Teal",
                  text_auto=".3f",
                  labels={"conversion_rate":"Conversion Rate","traffic_source":"Source"})
    fig3.update_layout(showlegend=False, height=320, margin=dict(t=20), coloraxis_showscale=False)
    st.plotly_chart(fig3, use_container_width=True)

with col4:
    st.subheader("📄 Session Duration by Page Category")
    page = (
        ev.groupby("page_category")["session_duration_sec"]
        .agg(["mean","median"]).round(1).reset_index()
        .sort_values("mean", ascending=False)
    )
    fig4 = go.Figure()
    fig4.add_bar(x=page["page_category"], y=page["mean"],   name="Mean",   marker_color="steelblue")
    fig4.add_bar(x=page["page_category"], y=page["median"], name="Median", marker_color="coral")
    fig4.update_layout(barmode="group", height=320, margin=dict(t=20),
                       yaxis_title="Seconds", legend=dict(orientation="h"))
    st.plotly_chart(fig4, use_container_width=True)

# ── Heatmap ───────────────────────────────────────────────────
st.markdown("---")
st.subheader("🕐 Event Activity Heatmap — Day of Week × Hour")
dow_order = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
pivot = (
    ev.groupby(["day_of_week","hour"])["event_id"].count()
    .unstack(fill_value=0)
    .reindex(dow_order)
)
fig5 = px.imshow(pivot, color_continuous_scale="YlOrRd",
                 labels=dict(x="Hour of Day", y="Day of Week", color="Events"),
                 aspect="auto")
fig5.update_layout(height=360, margin=dict(t=20))
st.plotly_chart(fig5, use_container_width=True)

# ── Experiment group ──────────────────────────────────────────
st.markdown("---")
st.subheader("🧪 Experiment Group — Conversion & Bounce")
ab = (
    ev.groupby("experiment_group").agg(
        sessions=("session_id","nunique"),
        purchases=("event_type", lambda x: (x=="purchase").sum()),
        bounces=("event_type",   lambda x: (x=="bounce").sum()),
        avg_session=("session_duration_sec","mean"),
    ).reset_index()
)
ab["conversion_rate"] = (ab["purchases"] / ab["sessions"]).round(4)
ab["bounce_rate"]     = (ab["bounces"]   / ab["sessions"]).round(4)

col5, col6 = st.columns(2)
with col5:
    fig6 = px.bar(ab, x="experiment_group", y="conversion_rate", color="experiment_group",
                  text_auto=".3f",
                  labels={"conversion_rate":"Conversion Rate","experiment_group":"Group"})
    fig6.update_layout(showlegend=False, height=300, margin=dict(t=20))
    st.plotly_chart(fig6, use_container_width=True)
with col6:
    fig7 = px.bar(ab, x="experiment_group", y="avg_session", color="experiment_group",
                  text_auto=".0f",
                  labels={"avg_session":"Avg Session (sec)","experiment_group":"Group"})
    fig7.update_layout(showlegend=False, height=300, margin=dict(t=20))
    st.plotly_chart(fig7, use_container_width=True)
