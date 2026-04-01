"""
generate_screenshots.py — Generates publication-quality PNG chart screenshots.
Run: python export/generate_screenshots.py
Output: screenshots/*.png
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
from matplotlib.patches import FancyBboxPatch
from pipeline.load import get_connection

OUT = Path(__file__).parent.parent / "screenshots"
OUT.mkdir(exist_ok=True)

# ── Style ─────────────────────────────────────────────────────
DARK   = "#1F3864"
BLUE   = "#2E75B6"
LBLUE  = "#D6E4F0"
RED    = "#C00000"
GOLD   = "#F4B942"
GREEN  = "#2ECC71"
GREY   = "#F2F2F2"
WHITE  = "#FFFFFF"

plt.rcParams.update({
    "figure.facecolor": WHITE,
    "axes.facecolor":   GREY,
    "axes.edgecolor":   "#CCCCCC",
    "axes.labelcolor":  DARK,
    "axes.titlesize":   13,
    "axes.titlecolor":  DARK,
    "axes.titleweight": "bold",
    "xtick.color":      "#555555",
    "ytick.color":      "#555555",
    "text.color":       DARK,
    "font.family":      "DejaVu Sans",
    "grid.color":       "#DDDDDD",
    "grid.linestyle":   "--",
    "grid.linewidth":   0.6,
})

def save(fig, name):
    path = OUT / name
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor=WHITE)
    plt.close(fig)
    print(f"  ✓  {name}")

# ── Load ──────────────────────────────────────────────────────
print("Loading data...")
con = get_connection()
tx        = con.execute("SELECT * FROM transactions").df()
customers = con.execute("SELECT * FROM customers").df()
campaigns = con.execute("SELECT * FROM campaigns").df()
c360      = con.execute("SELECT * FROM mart_customer_360").df()
cp        = con.execute("SELECT * FROM mart_campaign_performance").df()
funnel    = con.execute("SELECT * FROM mart_funnel").df()
pp        = con.execute("SELECT * FROM mart_product_performance").df()
products  = con.execute("SELECT * FROM products").df()
events    = con.execute("SELECT * FROM events").df()
con.close()

tx["timestamp"]   = pd.to_datetime(tx["timestamp"])
tx["month"]       = tx["timestamp"].dt.to_period("M").astype(str)
events["timestamp"] = pd.to_datetime(events["timestamp"])
events["hour"]    = events["timestamp"].dt.hour
events["dow"]     = events["timestamp"].dt.day_name()

print("\nGenerating charts...")

# ═══════════════════════════════════════════════
# 01 — EXECUTIVE SUMMARY (KPI CARDS)
# ═══════════════════════════════════════════════
fig = plt.figure(figsize=(16, 7))
fig.patch.set_facecolor("#1a2744")
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, 16); ax.set_ylim(0, 7)
ax.axis("off")
ax.set_facecolor("#1a2744")

ax.text(8, 6.6, "Marketing & E-Commerce Analytics", fontsize=22, fontweight="bold",
        color=WHITE, ha="center", va="center")
ax.text(8, 6.15, "Executive Summary — Key Performance Indicators", fontsize=12,
        color="#AAC4E8", ha="center", va="center")

kpis = [
    ("Net Revenue",      f"${tx['net_revenue'].sum():,.0f}",                   BLUE,  "#D6E4F0"),
    ("Total Orders",     f"{len(tx):,}",                                        BLUE,  "#D6E4F0"),
    ("Unique Buyers",    f"{tx['customer_id'].nunique():,}",                    BLUE,  "#D6E4F0"),
    ("Avg Order Value",  f"${tx['net_revenue'].mean():,.2f}",                   GREEN, "#D5F5E3"),
    ("Refund Rate",      f"{tx['refund_flag'].mean()*100:.2f}%",                RED,   "#FADBD8"),
    ("Campaigns",        f"{len(campaigns)}",                                   GOLD,  "#FEF9E7"),
    ("Products",         f"{len(products):,}",                                  GOLD,  "#FEF9E7"),
    ("Total Customers",  f"{len(customers):,}",                                 GREEN, "#D5F5E3"),
    ("Champions (RFM)",  f"{(c360['rfm_segment']=='Champions').sum():,}",       GREEN, "#D5F5E3"),
    ("Avg Conversion",   f"{cp['conversion_rate'].mean()*100:.2f}%",            GOLD,  "#FEF9E7"),
    ("Premium Products", f"{int(products['is_premium'].sum()):,}",              BLUE,  "#D6E4F0"),
    ("Data Span",        "2021 – 2024",                                         BLUE,  "#D6E4F0"),
]

cols, rows = 4, 3
for i, (label, value, border_color, bg_color) in enumerate(kpis):
    col = i % cols
    row = rows - 1 - (i // cols)
    x = 0.25 + col * 3.88
    y = 0.35 + row * 1.85
    rect = FancyBboxPatch((x, y), 3.4, 1.5, boxstyle="round,pad=0.12",
                           linewidth=2.5, edgecolor=border_color, facecolor=bg_color)
    ax.add_patch(rect)
    ax.plot([x+0.15, x+3.25], [y+1.1, y+1.1], color=border_color, lw=2.5, alpha=0.6)
    ax.text(x + 1.7, y + 0.72, value, fontsize=16, fontweight="bold",
            color="#1a2744", ha="center", va="center")
    ax.text(x + 1.7, y + 0.28, label, fontsize=9.5, color="#555555",
            ha="center", va="center", fontstyle="italic")

save(fig, "01_executive_summary.png")

# ═══════════════════════════════════════════════
# 02 — MONTHLY REVENUE TREND
# ═══════════════════════════════════════════════
monthly = tx.groupby("month").agg(
    orders=("transaction_id", "count"),
    net_revenue=("net_revenue", "sum"),
    aov=("net_revenue", "mean")
).reset_index()

fig, axes = plt.subplots(1, 2, figsize=(16, 5))
fig.suptitle("Monthly Revenue & Order Trends", fontsize=16, fontweight="bold",
             color=DARK, y=1.01)

# Orders bar
ax1 = axes[0]
bars = ax1.bar(range(len(monthly)), monthly["orders"], color=BLUE, alpha=0.85, width=0.7)
ax1.set_xticks(range(len(monthly)))
ax1.set_xticklabels(monthly["month"], rotation=45, ha="right", fontsize=7)
ax1.set_title("Monthly Order Volume"); ax1.set_ylabel("Orders")
ax1.yaxis.grid(True); ax1.set_axisbelow(True)
for b in bars[::6]:
    ax1.text(b.get_x()+b.get_width()/2, b.get_height()+50,
             f'{b.get_height():,.0f}', ha='center', fontsize=7, color=DARK)

# Revenue line
ax2 = axes[1]
ax2.fill_between(range(len(monthly)), monthly["net_revenue"], alpha=0.2, color=RED)
ax2.plot(range(len(monthly)), monthly["net_revenue"], color=RED, lw=2.5, marker="o",
         markersize=4)
ax2.set_xticks(range(len(monthly)))
ax2.set_xticklabels(monthly["month"], rotation=45, ha="right", fontsize=7)
ax2.set_title("Monthly Net Revenue"); ax2.set_ylabel("Revenue ($)")
ax2.yaxis.grid(True); ax2.set_axisbelow(True)

fig.tight_layout()
save(fig, "02_monthly_revenue_trend.png")

# ═══════════════════════════════════════════════
# 03 — CUSTOMER ANALYSIS (RFM + LTV)
# ═══════════════════════════════════════════════
fig, axes = plt.subplots(1, 3, figsize=(18, 5))
fig.suptitle("Customer Analytics — RFM Segmentation & LTV", fontsize=16,
             fontweight="bold", color=DARK)

seg_colors = {"Champions": GREEN, "Loyal": BLUE, "Potential Loyalist": GOLD,
              "At Risk": "#E67E22", "Lost": RED}

# RFM count
seg = c360[c360["rfm_segment"].notna()]["rfm_segment"].value_counts()
seg_order = ["Champions","Loyal","Potential Loyalist","At Risk","Lost"]
seg = seg.reindex(seg_order).dropna()
ax = axes[0]
bars = ax.bar(seg.index, seg.values,
              color=[seg_colors[s] for s in seg.index], edgecolor="white", width=0.6)
ax.set_title("RFM Segment Distribution"); ax.set_ylabel("Customers")
ax.set_xticklabels(seg.index, rotation=20, ha="right")
ax.yaxis.grid(True); ax.set_axisbelow(True)
for b in bars:
    ax.text(b.get_x()+b.get_width()/2, b.get_height()+30,
            f'{b.get_height():,.0f}', ha='center', fontsize=9, fontweight="bold")

# Avg LTV by segment
ltv = c360[c360["rfm_segment"].notna()].groupby("rfm_segment")["total_revenue"].mean()
ltv = ltv.reindex(seg_order).dropna()
ax2 = axes[1]
bars2 = ax2.barh(ltv.index, ltv.values,
                 color=[seg_colors[s] for s in ltv.index], edgecolor="white", height=0.6)
ax2.set_title("Avg LTV by RFM Segment"); ax2.set_xlabel("Avg Revenue ($)")
ax2.xaxis.grid(True); ax2.set_axisbelow(True)
for b in bars2:
    ax2.text(b.get_width()+5, b.get_y()+b.get_height()/2,
             f'${b.get_width():,.0f}', va='center', fontsize=9)

# Tier breakdown
tier_rev = c360[c360["has_purchased"]].groupby("loyalty_tier")["total_revenue"].mean()
tier_colors = {"Bronze":"#cd7f32","Silver":"#999999","Gold":"#FFD700","Platinum":"#5DADE2"}
ax3 = axes[2]
bars3 = ax3.bar(tier_rev.index, tier_rev.values,
                color=[tier_colors.get(t, BLUE) for t in tier_rev.index],
                edgecolor="white", width=0.6)
ax3.set_title("Avg LTV by Loyalty Tier"); ax3.set_ylabel("Avg Revenue ($)")
ax3.set_xticklabels(tier_rev.index, rotation=0)
ax3.yaxis.grid(True); ax3.set_axisbelow(True)
for b in bars3:
    ax3.text(b.get_x()+b.get_width()/2, b.get_height()+2,
             f'${b.get_height():,.0f}', ha='center', fontsize=9, fontweight="bold")

fig.tight_layout()
save(fig, "03_customer_rfm_ltv.png")

# ═══════════════════════════════════════════════
# 04 — CAMPAIGN PERFORMANCE
# ═══════════════════════════════════════════════
valid_cp = cp[cp["net_revenue"].notna()].copy()

fig, axes = plt.subplots(1, 3, figsize=(18, 5))
fig.suptitle("Campaign Performance — ROI & Channel Analysis", fontsize=16,
             fontweight="bold", color=DARK)

# Revenue by channel
ch = valid_cp.groupby("channel")["net_revenue"].sum().sort_values(ascending=False)
ax = axes[0]
bars = ax.bar(ch.index, ch.values, color=BLUE, edgecolor="white", width=0.6)
ax.set_title("Net Revenue by Channel"); ax.set_ylabel("Revenue ($)")
ax.set_xticklabels(ch.index, rotation=30, ha="right")
ax.yaxis.grid(True); ax.set_axisbelow(True)
for b in bars:
    ax.text(b.get_x()+b.get_width()/2, b.get_height()+100,
            f'${b.get_height():,.0f}', ha='center', fontsize=8, fontweight="bold")

# Conversion vs bounce scatter
ax2 = axes[1]
sc = ax2.scatter(valid_cp["bounce_rate"], valid_cp["conversion_rate"],
                 c=valid_cp["net_revenue"], cmap="RdYlGn",
                 s=valid_cp["net_revenue"].fillna(0)/50+40, alpha=0.8, edgecolors="white")
plt.colorbar(sc, ax=ax2, label="Net Revenue ($)")
ax2.set_title("Conversion vs Bounce Rate"); ax2.set_xlabel("Bounce Rate")
ax2.set_ylabel("Conversion Rate")
ax2.xaxis.grid(True); ax2.yaxis.grid(True); ax2.set_axisbelow(True)

# A/B test
ab = events.groupby("experiment_group").agg(
    sessions=("session_id","nunique"),
    purchases=("event_type", lambda x: (x=="purchase").sum()),
).reset_index()
ab["conv"] = (ab["purchases"]/ab["sessions"]).round(4)
ax3 = axes[2]
ab_colors = [GREEN if i==ab["conv"].idxmax() else BLUE for i in ab.index]
bars3 = ax3.bar(ab["experiment_group"], ab["conv"]*100, color=ab_colors,
                edgecolor="white", width=0.6)
ax3.set_title("A/B Test — Conversion Rate"); ax3.set_ylabel("Conversion Rate (%)")
ax3.yaxis.grid(True); ax3.set_axisbelow(True)
ax3.set_xticklabels(ab["experiment_group"], rotation=15, ha="right")
for b in bars3:
    ax3.text(b.get_x()+b.get_width()/2, b.get_height()+0.01,
             f'{b.get_height():.2f}%', ha='center', fontsize=9, fontweight="bold")

fig.tight_layout()
save(fig, "04_campaign_performance.png")

# ═══════════════════════════════════════════════
# 05 — PRODUCT ANALYTICS
# ═══════════════════════════════════════════════
fig, axes = plt.subplots(1, 3, figsize=(18, 5))
fig.suptitle("Product Analytics — Revenue by Category & Premium Analysis",
             fontsize=16, fontweight="bold", color=DARK)

cat_rev = pp.groupby("category").agg(
    total_revenue=("total_revenue","sum"),
    units_sold=("units_sold","sum")
).sort_values("total_revenue", ascending=False).reset_index()

cat_palette = [BLUE, GOLD, GREEN, RED, "#9B59B6", "#1ABC9C", "#E67E22"]

# Category revenue
ax = axes[0]
bars = ax.bar(cat_rev["category"], cat_rev["total_revenue"],
              color=cat_palette[:len(cat_rev)], edgecolor="white", width=0.6)
ax.set_title("Revenue by Category"); ax.set_ylabel("Net Revenue ($)")
ax.set_xticklabels(cat_rev["category"], rotation=30, ha="right")
ax.yaxis.grid(True); ax.set_axisbelow(True)
for b in bars:
    ax.text(b.get_x()+b.get_width()/2, b.get_height()+500,
            f'${b.get_height():,.0f}', ha='center', fontsize=8, fontweight="bold")

# Units by category
ax2 = axes[1]
ax2.barh(cat_rev["category"][::-1], cat_rev["units_sold"][::-1],
         color=cat_palette[:len(cat_rev)], edgecolor="white", height=0.6)
ax2.set_title("Units Sold by Category"); ax2.set_xlabel("Units Sold")
ax2.xaxis.grid(True); ax2.set_axisbelow(True)

# Premium vs non-premium
prem = pp.groupby("is_premium").agg(
    total_revenue=("total_revenue","sum"),
    units=("units_sold","sum")
).reset_index()
prem["label"] = prem["is_premium"].map({True:"Premium", False:"Non-Premium"})
ax3 = axes[2]
wedges, texts, autotexts = ax3.pie(
    prem["total_revenue"], labels=prem["label"],
    colors=[GOLD, BLUE], autopct="%1.1f%%", startangle=90,
    wedgeprops=dict(edgecolor="white", linewidth=2)
)
for t in autotexts: t.set_fontweight("bold"); t.set_fontsize(11)
ax3.set_title("Revenue: Premium vs Non-Premium")

fig.tight_layout()
save(fig, "05_product_analytics.png")

# ═══════════════════════════════════════════════
# 06 — CONVERSION FUNNEL
# ═══════════════════════════════════════════════
fig, axes = plt.subplots(1, 2, figsize=(14, 5))
fig.suptitle("Conversion Funnel & Traffic Source Analysis",
             fontsize=16, fontweight="bold", color=DARK)

stages = ["view","click","add_to_cart","purchase"]
counts = events[events["event_type"].isin(stages)]["event_type"].value_counts()
funnel_counts = [counts.get(s, 0) for s in stages]
funnel_labels = ["View","Click","Add to Cart","Purchase"]
funnel_colors = [BLUE, GOLD, "#E67E22", GREEN]
pct = [f"{c/funnel_counts[0]*100:.1f}%" for c in funnel_counts]

ax = axes[0]
y_pos = [3, 2, 1, 0]
for i, (label, count, color, p) in enumerate(zip(funnel_labels, funnel_counts, funnel_colors, pct)):
    width = count / funnel_counts[0] * 10
    xstart = (10 - width) / 2
    rect = mpatches.FancyBboxPatch((xstart, y_pos[i]-0.35), width, 0.7,
                                    boxstyle="round,pad=0.05",
                                    facecolor=color, edgecolor="white", linewidth=2)
    ax.add_patch(rect)
    ax.text(5, y_pos[i], f"{label}  —  {count:,}  ({p})",
            ha="center", va="center", fontsize=11, fontweight="bold", color=WHITE)
ax.set_xlim(0, 10); ax.set_ylim(-0.6, 3.6)
ax.axis("off"); ax.set_facecolor(WHITE)
ax.set_title("Conversion Funnel (All Events)")

# Traffic source conversion
src = events.groupby("traffic_source").agg(
    views=("event_type",     lambda x: (x=="view").sum()),
    purchases=("event_type", lambda x: (x=="purchase").sum()),
).reset_index()
src["conv"] = (src["purchases"] / src["views"].replace(0,1) * 100).round(2)
src = src.sort_values("conv", ascending=True)

ax2 = axes[1]
bars = ax2.barh(src["traffic_source"], src["conv"],
                color=BLUE, edgecolor="white", height=0.6)
ax2.set_title("Conversion Rate by Traffic Source")
ax2.set_xlabel("Conversion Rate (%)")
ax2.xaxis.grid(True); ax2.set_axisbelow(True)
for b in bars:
    ax2.text(b.get_width()+0.01, b.get_y()+b.get_height()/2,
             f'{b.get_width():.2f}%', va='center', fontsize=9)

fig.tight_layout()
save(fig, "06_funnel_analysis.png")

# ═══════════════════════════════════════════════
# 07 — BEHAVIORAL HEATMAP
# ═══════════════════════════════════════════════
dow_order = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
pivot = events.groupby(["dow","hour"])["event_id"].count().unstack(fill_value=0)
pivot = pivot.reindex(dow_order)

fig, ax = plt.subplots(figsize=(16, 5))
fig.suptitle("Event Activity Heatmap — Day of Week × Hour of Day",
             fontsize=16, fontweight="bold", color=DARK)
im = ax.imshow(pivot.values, aspect="auto", cmap="YlOrRd")
ax.set_xticks(range(24)); ax.set_xticklabels(range(24))
ax.set_yticks(range(7)); ax.set_yticklabels(dow_order)
ax.set_xlabel("Hour of Day"); ax.set_ylabel("Day of Week")
plt.colorbar(im, ax=ax, label="Event Count")
ax.set_facecolor(WHITE)
fig.tight_layout()
save(fig, "07_behavioral_heatmap.png")

# ═══════════════════════════════════════════════
# 08 — ACQUISITION CHANNEL & COUNTRY
# ═══════════════════════════════════════════════
fig, axes = plt.subplots(1, 2, figsize=(15, 5))
fig.suptitle("Customer Acquisition — Channel LTV & Top Countries",
             fontsize=16, fontweight="bold", color=DARK)

acq = c360[c360["has_purchased"]].groupby("acquisition_channel")["total_revenue"].mean().sort_values(ascending=False)
ax = axes[0]
bars = ax.bar(acq.index, acq.values, color=BLUE, edgecolor="white", width=0.6)
ax.set_title("Avg LTV by Acquisition Channel"); ax.set_ylabel("Avg Revenue ($)")
ax.set_xticklabels(acq.index, rotation=30, ha="right")
ax.yaxis.grid(True); ax.set_axisbelow(True)
for b in bars:
    ax.text(b.get_x()+b.get_width()/2, b.get_height()+2,
            f'${b.get_height():,.0f}', ha='center', fontsize=9, fontweight="bold")

country_rev = c360[c360["has_purchased"]].groupby("country")["total_revenue"].sum().nlargest(10)
ax2 = axes[1]
bars2 = ax2.barh(country_rev.index[::-1], country_rev.values[::-1],
                 color=GOLD, edgecolor="white", height=0.6)
ax2.set_title("Top 10 Countries by Revenue"); ax2.set_xlabel("Total Revenue ($)")
ax2.xaxis.grid(True); ax2.set_axisbelow(True)
for b in bars2:
    ax2.text(b.get_width()+500, b.get_y()+b.get_height()/2,
             f'${b.get_width():,.0f}', va='center', fontsize=9)

fig.tight_layout()
save(fig, "08_acquisition_country.png")

# ═══════════════════════════════════════════════
# 09 — REFUND & DISCOUNT ANALYSIS
# ═══════════════════════════════════════════════
monthly_refund = tx.groupby("month")["refund_flag"].agg(["sum","count"])
monthly_refund["rate"] = monthly_refund["sum"] / monthly_refund["count"] * 100

tx["discounted"] = tx["discount_applied"] > 0
disc = tx.groupby("discounted")["net_revenue"].mean()

fig, axes = plt.subplots(1, 2, figsize=(14, 5))
fig.suptitle("Refund Rate Trend & Discount Impact",
             fontsize=16, fontweight="bold", color=DARK)

ax = axes[0]
ax.fill_between(range(len(monthly_refund)), monthly_refund["rate"], alpha=0.25, color=RED)
ax.plot(range(len(monthly_refund)), monthly_refund["rate"], color=RED, lw=2.5, marker="o", markersize=3)
ax.set_xticks(range(len(monthly_refund)))
ax.set_xticklabels(monthly_refund.index, rotation=45, ha="right", fontsize=7)
ax.set_title("Monthly Refund Rate"); ax.set_ylabel("Refund Rate (%)")
ax.yaxis.grid(True); ax.set_axisbelow(True)

ax2 = axes[1]
labels = ["No Discount", "Discounted"]
colors = [BLUE, GOLD]
bars2 = ax2.bar(labels, disc.values, color=colors, edgecolor="white", width=0.5)
ax2.set_title("Avg Order Value: Discounted vs Not"); ax2.set_ylabel("Avg Revenue ($)")
ax2.yaxis.grid(True); ax2.set_axisbelow(True)
for b in bars2:
    ax2.text(b.get_x()+b.get_width()/2, b.get_height()+0.3,
             f'${b.get_height():,.2f}', ha='center', fontsize=12, fontweight="bold")

fig.tight_layout()
save(fig, "09_refund_discount_analysis.png")

# ═══════════════════════════════════════════════
# 10 — TOP 10 PRODUCTS
# ═══════════════════════════════════════════════
top10 = (
    pp[pp["total_revenue"] > 0]
    .nlargest(10, "total_revenue")
    .reset_index(drop=True)
)
top10["label"] = "Product " + top10["product_id"].astype(str)

fig, ax = plt.subplots(figsize=(13, 6))
fig.suptitle("Top 10 Products by Net Revenue", fontsize=16, fontweight="bold", color=DARK)

gradient_colors = [plt.cm.Blues(0.9 - i*0.07) for i in range(10)]
bars = ax.barh(top10["label"][::-1], top10["total_revenue"][::-1],
               color=gradient_colors, edgecolor="white", height=0.7)
ax.set_xlabel("Net Revenue ($)")
ax.xaxis.grid(True); ax.set_axisbelow(True)

for i, b in enumerate(bars):
    row = top10.iloc[9-i]
    ax.text(b.get_width()+200, b.get_y()+b.get_height()/2,
            f'${b.get_width():,.0f}  |  {int(row["units_sold"])} units  |  {int(row["unique_buyers"])} buyers',
            va='center', fontsize=9)

ax.set_xlim(0, top10["total_revenue"].max() * 1.45)
fig.tight_layout()
save(fig, "10_top10_products.png")

print(f"\n✅  All 10 screenshots saved to: {OUT}")
print("   Files:", sorted([f.name for f in OUT.glob("*.png")]))
