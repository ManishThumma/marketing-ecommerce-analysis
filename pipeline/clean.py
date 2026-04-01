"""
clean.py — Data cleaning and type casting for all tables.
"""
import pandas as pd


def clean_campaigns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["start_date"] = pd.to_datetime(df["start_date"])
    df["end_date"] = pd.to_datetime(df["end_date"])
    df["duration_days"] = (df["end_date"] - df["start_date"]).dt.days
    df["channel"] = df["channel"].str.strip()
    df["objective"] = df["objective"].str.strip()
    df["target_segment"] = df["target_segment"].str.strip()
    return df


def clean_customers(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["signup_date"] = pd.to_datetime(df["signup_date"])
    df["age"] = pd.to_numeric(df["age"], errors="coerce")
    df["country"] = df["country"].str.strip().str.upper()
    df["gender"] = df["gender"].str.strip()
    df["loyalty_tier"] = pd.Categorical(
        df["loyalty_tier"], categories=["Bronze", "Silver", "Gold", "Platinum"], ordered=True
    )
    df["acquisition_channel"] = df["acquisition_channel"].str.strip()
    return df


def clean_events(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["product_id"] = pd.to_numeric(df["product_id"], errors="coerce").astype("Int64")
    df["campaign_id"] = df["campaign_id"].fillna(0).astype(int)
    df["event_type"] = df["event_type"].str.strip()
    df["device_type"] = df["device_type"].str.strip()
    df["traffic_source"] = df["traffic_source"].str.strip()
    df["page_category"] = df["page_category"].str.strip()
    df["experiment_group"] = df["experiment_group"].str.strip()
    df["date"] = df["timestamp"].dt.date
    df["hour"] = df["timestamp"].dt.hour
    df["day_of_week"] = df["timestamp"].dt.day_name()
    return df


def clean_products(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["launch_date"] = pd.to_datetime(df["launch_date"])
    df["base_price"] = pd.to_numeric(df["base_price"], errors="coerce")
    df["is_premium"] = df["is_premium"].astype(bool)
    df["category"] = df["category"].str.strip()
    df["brand"] = df["brand"].str.strip()
    return df


def clean_transactions(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["product_id"] = pd.to_numeric(df["product_id"], errors="coerce").astype("Int64")
    df["campaign_id"] = df["campaign_id"].fillna(0).astype(int)
    df["discount_applied"] = pd.to_numeric(df["discount_applied"], errors="coerce").fillna(0)
    df["gross_revenue"] = pd.to_numeric(df["gross_revenue"], errors="coerce")
    df["refund_flag"] = df["refund_flag"].astype(bool)
    df["date"] = df["timestamp"].dt.date
    df["month"] = df["timestamp"].dt.to_period("M").astype(str)
    df["year"] = df["timestamp"].dt.year
    df["net_revenue"] = df["gross_revenue"].where(~df["refund_flag"], 0)
    return df


def clean_all(frames: dict) -> dict:
    cleaners = {
        "campaigns": clean_campaigns,
        "customers": clean_customers,
        "events": clean_events,
        "products": clean_products,
        "transactions": clean_transactions,
    }
    cleaned = {}
    for name, fn in cleaners.items():
        cleaned[name] = fn(frames[name])
        null_counts = cleaned[name].isnull().sum()
        nulls = null_counts[null_counts > 0].to_dict()
        print(f"[clean] {name}: {len(cleaned[name]):,} rows | nulls: {nulls}")
    return cleaned
