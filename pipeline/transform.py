"""
transform.py — Feature engineering and analytical mart creation.
"""
import pandas as pd
import numpy as np


def build_customer_360(customers, transactions, events) -> pd.DataFrame:
    """Customer-level aggregated mart with RFM and behavioral features."""
    # Transaction aggregates
    tx_agg = (
        transactions[~transactions["refund_flag"]]
        .groupby("customer_id")
        .agg(
            total_orders=("transaction_id", "count"),
            total_revenue=("net_revenue", "sum"),
            avg_order_value=("net_revenue", "mean"),
            total_quantity=("quantity", "sum"),
            first_purchase=("timestamp", "min"),
            last_purchase=("timestamp", "max"),
            refund_count=("refund_flag", lambda x: transactions.loc[x.index, "refund_flag"].sum()),
            discount_used_count=("discount_applied", lambda x: (x > 0).sum()),
        )
        .reset_index()
    )

    # Recency (days since last purchase from dataset max date)
    max_date = transactions["timestamp"].max()
    tx_agg["recency_days"] = (max_date - tx_agg["last_purchase"]).dt.days
    tx_agg["customer_lifetime_days"] = (tx_agg["last_purchase"] - tx_agg["first_purchase"]).dt.days

    # RFM scoring (1–5, 5 = best)
    tx_agg["r_score"] = pd.qcut(tx_agg["recency_days"].rank(method="first"), 5, labels=[5,4,3,2,1]).astype(int)
    tx_agg["f_score"] = pd.qcut(tx_agg["total_orders"].rank(method="first"), 5, labels=[1,2,3,4,5]).astype(int)
    tx_agg["m_score"] = pd.qcut(tx_agg["total_revenue"].rank(method="first"), 5, labels=[1,2,3,4,5]).astype(int)
    tx_agg["rfm_score"] = tx_agg["r_score"] + tx_agg["f_score"] + tx_agg["m_score"]

    def rfm_segment(score):
        if score >= 13:
            return "Champions"
        elif score >= 10:
            return "Loyal"
        elif score >= 7:
            return "Potential Loyalist"
        elif score >= 5:
            return "At Risk"
        else:
            return "Lost"

    tx_agg["rfm_segment"] = tx_agg["rfm_score"].apply(rfm_segment)

    # Event aggregates
    event_agg = (
        events.groupby("customer_id")
        .agg(
            total_events=("event_id", "count"),
            total_sessions=("session_id", "nunique"),
            purchase_events=("event_type", lambda x: (x == "purchase").sum()),
            bounce_events=("event_type", lambda x: (x == "bounce").sum()),
            avg_session_duration=("session_duration_sec", "mean"),
            devices_used=("device_type", "nunique"),
        )
        .reset_index()
    )
    event_agg["conversion_rate"] = (
        event_agg["purchase_events"] / event_agg["total_sessions"]
    ).round(4)

    # Merge everything
    c360 = customers.merge(tx_agg, on="customer_id", how="left")
    c360 = c360.merge(event_agg, on="customer_id", how="left")
    c360["has_purchased"] = c360["total_orders"].notna() & (c360["total_orders"] > 0)
    c360["total_orders"] = c360["total_orders"].fillna(0).astype(int)
    c360["total_revenue"] = c360["total_revenue"].fillna(0)

    print(f"[transform] customer_360: {len(c360):,} rows")
    return c360


def build_campaign_performance(campaigns, transactions, events) -> pd.DataFrame:
    """Campaign-level performance mart."""
    tx_perf = (
        transactions.groupby("campaign_id")
        .agg(
            tx_count=("transaction_id", "count"),
            gross_revenue=("gross_revenue", "sum"),
            net_revenue=("net_revenue", "sum"),
            refunds=("refund_flag", "sum"),
            avg_discount=("discount_applied", "mean"),
            unique_customers=("customer_id", "nunique"),
        )
        .reset_index()
    )

    event_perf = (
        events.groupby("campaign_id")
        .agg(
            impressions=("event_id", "count"),
            unique_visitors=("customer_id", "nunique"),
            purchases=("event_type", lambda x: (x == "purchase").sum()),
            bounces=("event_type", lambda x: (x == "bounce").sum()),
            add_to_carts=("event_type", lambda x: (x == "add_to_cart").sum()),
            avg_session_sec=("session_duration_sec", "mean"),
        )
        .reset_index()
    )
    event_perf["bounce_rate"] = (event_perf["bounces"] / event_perf["impressions"]).round(4)
    event_perf["click_to_cart_rate"] = (event_perf["add_to_carts"] / event_perf["impressions"]).round(4)
    event_perf["conversion_rate"] = (event_perf["purchases"] / event_perf["unique_visitors"]).round(4)

    perf = campaigns.merge(tx_perf, on="campaign_id", how="left")
    perf = perf.merge(event_perf, on="campaign_id", how="left")
    perf["roi"] = ((perf["net_revenue"] - perf["net_revenue"].median()) / perf["net_revenue"].median()).round(4)
    # After merge, unique_visitors may be suffixed; use the one from event_perf
    uv_col = "unique_visitors_y" if "unique_visitors_y" in perf.columns else "unique_visitors"
    perf["revenue_per_visitor"] = (perf["net_revenue"] / perf[uv_col]).round(2)

    print(f"[transform] campaign_performance: {len(perf):,} rows")
    return perf


def build_funnel(events) -> pd.DataFrame:
    """Session-level funnel: view → click → add_to_cart → purchase."""
    funnel_order = ["view", "click", "add_to_cart", "purchase"]
    counts = events[events["event_type"].isin(funnel_order)]["event_type"].value_counts()
    funnel = pd.DataFrame({
        "stage": funnel_order,
        "count": [counts.get(s, 0) for s in funnel_order],
    })
    funnel["drop_off_rate"] = (1 - funnel["count"] / funnel["count"].shift(1)).round(4)
    funnel["conversion_from_top"] = (funnel["count"] / funnel["count"].iloc[0]).round(4)
    print(f"[transform] funnel built")
    return funnel


def build_product_performance(products, transactions) -> pd.DataFrame:
    """Product-level revenue and sales mart."""
    tx = transactions[~transactions["refund_flag"]].copy()
    prod_agg = (
        tx.groupby("product_id")
        .agg(
            units_sold=("quantity", "sum"),
            total_revenue=("net_revenue", "sum"),
            avg_revenue_per_tx=("net_revenue", "mean"),
            order_count=("transaction_id", "count"),
            unique_buyers=("customer_id", "nunique"),
            discount_rate=("discount_applied", "mean"),
        )
        .reset_index()
    )
    prod_perf = products.merge(prod_agg, on="product_id", how="left")
    prod_perf["units_sold"] = prod_perf["units_sold"].fillna(0)
    prod_perf["total_revenue"] = prod_perf["total_revenue"].fillna(0)
    print(f"[transform] product_performance: {len(prod_perf):,} rows")
    return prod_perf


def build_all(cleaned: dict) -> dict:
    marts = {
        "customer_360": build_customer_360(
            cleaned["customers"], cleaned["transactions"], cleaned["events"]
        ),
        "campaign_performance": build_campaign_performance(
            cleaned["campaigns"], cleaned["transactions"], cleaned["events"]
        ),
        "funnel": build_funnel(cleaned["events"]),
        "product_performance": build_product_performance(
            cleaned["products"], cleaned["transactions"]
        ),
    }
    return marts
