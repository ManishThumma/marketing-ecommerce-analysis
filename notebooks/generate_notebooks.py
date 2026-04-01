"""
Generates all analysis Jupyter notebooks.
Run: python notebooks/generate_notebooks.py
"""
import nbformat as nbf
from pathlib import Path

OUT = Path(__file__).parent

def nb(cells):
    notebook = nbf.v4.new_notebook()
    notebook.cells = cells
    return notebook

def code(src): return nbf.v4.new_code_cell(src)
def md(src):   return nbf.v4.new_markdown_cell(src)


# ──────────────────────────────────────────────
# 01 — EDA
# ──────────────────────────────────────────────
eda = nb([
    md("""# Exploratory Data Analysis

Before doing any real analysis, I always want to understand what I'm actually working with. How big is the data, what's missing, what does the distribution look like — the basics that tell you whether your data is trustworthy or whether you're going to hit surprises halfway through.

This dataset has five tables totalling just over 2 million rows, which is a decent size for local analysis. DuckDB handles it without breaking a sweat.
"""),
    code("""
import sys; sys.path.insert(0, '..')
from pipeline.ingest import load_all
from pipeline.clean import clean_all
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
sns.set_theme(style='whitegrid')

raw = load_all()
cleaned = clean_all(raw)
"""),
    md("""## How big is everything?

First thing — let's just confirm what we're working with row-count wise. The events table is by far the largest, which makes sense — every click, view, bounce and purchase gets logged.
"""),
    code("""
for name, df in cleaned.items():
    print(f"{name:15s}  rows={len(df):>10,}  cols={df.shape[1]}")
"""),
    md("""## Nulls — what's missing and does it matter?

Nulls in events aren't surprising — a bounce event won't have a product_id because the user left before viewing one. Same logic applies to transactions. The key question is whether the nulls are random or systematic. If all the nulls are in bounce events, that's fine. If they're scattered across purchase events, that's a problem.
"""),
    code("""
for name, df in cleaned.items():
    nulls = df.isnull().sum()
    nulls = nulls[nulls > 0]
    if len(nulls):
        print(f"\\n--- {name} ---")
        print((nulls / len(df) * 100).round(2).to_string())
    else:
        print(f"{name}: no nulls")
"""),
    md("""## Customer age distribution

Who are the customers? The age distribution tells you whether this is a young-skewing platform or a broader demographic. Worth knowing because it affects how you'd interpret campaign performance across channels like Email vs Social.
"""),
    code("""
fig, ax = plt.subplots(figsize=(8, 4))
cleaned['customers']['age'].hist(bins=30, ax=ax, color='steelblue', edgecolor='white')
ax.set_title('Customer Age Distribution')
ax.set_xlabel('Age'); ax.set_ylabel('Count')
plt.tight_layout(); plt.show()
"""),
    md("""## Loyalty tier split

The loyalty tier breakdown matters because it tells you how concentrated your customer base is. If 80% are Bronze, your retention strategy needs to be very different than if most customers are already Gold or Platinum.
"""),
    code("""
tier_counts = cleaned['customers']['loyalty_tier'].value_counts().sort_index()
fig, ax = plt.subplots(figsize=(6, 4))
tier_counts.plot(kind='bar', ax=ax, color=['#cd7f32','#c0c0c0','#ffd700'], edgecolor='white')
ax.set_title('Customer Loyalty Tier Distribution')
ax.set_xlabel('Tier'); ax.set_ylabel('Count')
plt.xticks(rotation=0); plt.tight_layout(); plt.show()
"""),
    md("""## What events are users generating?

This gives a quick read on user behaviour. A high bounce count relative to views is expected — most people don't engage. What you're looking for is whether the purchase count looks proportionate given the view count. If it's tiny, something's broken in the funnel.
"""),
    code("""
ev_counts = cleaned['events']['event_type'].value_counts()
fig, ax = plt.subplots(figsize=(7, 4))
ev_counts.plot(kind='barh', ax=ax, color='coral')
ax.set_title('Event Type Counts'); ax.set_xlabel('Count')
plt.tight_layout(); plt.show()
"""),
    md("""## Revenue distribution

This is one of the more important EDA checks. Revenue distributions in e-commerce are almost always right-skewed — a few large orders pull the mean up. The negative values are refunds, which is expected. Worth flagging that we should use median AOV alongside mean AOV when reporting.
"""),
    code("""
tx = cleaned['transactions'].dropna(subset=['gross_revenue'])
fig, axes = plt.subplots(1, 2, figsize=(12, 4))
tx['gross_revenue'].clip(-200, 600).hist(bins=50, ax=axes[0], color='steelblue', edgecolor='white')
axes[0].set_title('Gross Revenue Distribution'); axes[0].set_xlabel('Revenue ($)')
tx['quantity'].value_counts().sort_index().plot(kind='bar', ax=axes[1], color='teal')
axes[1].set_title('Quantity per Transaction'); axes[1].set_xlabel('Quantity')
plt.tight_layout(); plt.show()
"""),
    md("""## Product categories

Just a sanity check on how the product catalogue breaks down. Useful context before we go deeper into product performance — if Sports has 5 products and Grocery has 500, raw revenue comparisons between categories are misleading without normalisation.
"""),
    code("""
cat_counts = cleaned['products']['category'].value_counts()
fig, ax = plt.subplots(figsize=(7, 4))
cat_counts.plot(kind='bar', ax=ax, color='mediumpurple', edgecolor='white')
ax.set_title('Products by Category'); ax.set_xlabel('Category'); ax.set_ylabel('Count')
plt.xticks(rotation=30); plt.tight_layout(); plt.show()
"""),
    md("""## Monthly trends — the big picture

Before drilling into anything specific, it's worth looking at whether the business is growing, declining, or flat. Seasonality also shows up here, which matters if you're benchmarking campaign performance across months.
"""),
    code("""
monthly = cleaned['transactions'].groupby('month').agg(
    orders=('transaction_id', 'count'),
    revenue=('net_revenue', 'sum')
).reset_index()
fig, ax1 = plt.subplots(figsize=(12, 4))
ax2 = ax1.twinx()
ax1.bar(monthly['month'], monthly['orders'], color='steelblue', alpha=0.6, label='Orders')
ax2.plot(monthly['month'], monthly['revenue'], color='crimson', marker='o', lw=2, label='Revenue')
ax1.set_title('Monthly Orders & Revenue')
ax1.set_xlabel('Month'); ax1.set_ylabel('Orders'); ax2.set_ylabel('Net Revenue ($)')
plt.xticks(rotation=45, ha='right')
lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1+lines2, labels1+labels2, loc='upper left')
plt.tight_layout(); plt.show()
"""),
])


# ──────────────────────────────────────────────
# 02 — Customer Analysis
# ──────────────────────────────────────────────
customer = nb([
    md("""# Customer Analysis

This is probably the most valuable notebook in the project. Understanding your customers — who's actually driving revenue, how they were acquired, and how long they stick around — is the foundation of any decent retention or growth strategy.

The centrepiece here is RFM segmentation: scoring customers on how recently they bought, how often, and how much they spent. It's a simple framework but it works, and it produces segments that you can actually act on.
"""),
    code("""
import sys; sys.path.insert(0, '..')
from pipeline.load import get_connection
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
sns.set_theme(style='whitegrid')

con = get_connection()
c360 = con.execute("SELECT * FROM mart_customer_360").df()
customers = con.execute("SELECT * FROM customers").df()
"""),
    md("""## RFM segments — who's who

Five segments, from Champions (high recency, high frequency, high spend) down to Lost (haven't bought in ages, low lifetime value). The size of each segment tells you a lot about the health of the customer base.

A healthy business should have a decent Champions cohort and a manageable Lost cohort. If Lost is the biggest segment, you have a retention problem, not an acquisition problem.
"""),
    code("""
seg = c360[c360['rfm_segment'].notna()]['rfm_segment'].value_counts()
colors = {'Champions':'#2ecc71','Loyal':'#3498db','Potential Loyalist':'#f1c40f','At Risk':'#e67e22','Lost':'#e74c3c'}
fig, ax = plt.subplots(figsize=(8, 4))
bars = ax.bar(seg.index, seg.values, color=[colors.get(s, 'gray') for s in seg.index], edgecolor='white')
ax.bar_label(bars, fmt='%d', padding=3)
ax.set_title('RFM Segment Distribution'); ax.set_ylabel('Customers')
plt.xticks(rotation=20); plt.tight_layout(); plt.show()
print(seg.to_frame('count').assign(pct=(seg/seg.sum()*100).round(1)))
"""),
    md("""## LTV gap between segments

This is the number that should inform where you spend your retention budget. The gap between Champions and At Risk customers shows how much revenue is at stake when a customer slides down the segments. Worth quantifying in dollar terms — "each Champions customer is worth X times more than an At Risk customer" is a much more persuasive argument for retention investment than a bar chart.
"""),
    code("""
ltv = c360[c360['rfm_segment'].notna()].groupby('rfm_segment')['total_revenue'].mean().sort_values(ascending=False)
fig, ax = plt.subplots(figsize=(8, 4))
ltv.plot(kind='bar', ax=ax, color='steelblue', edgecolor='white')
ax.set_title('Average LTV by RFM Segment'); ax.set_ylabel('Avg Revenue ($)')
plt.xticks(rotation=20); plt.tight_layout(); plt.show()
print("LTV gap (Champions vs Lost):", round(ltv['Champions'] / ltv['Lost'], 1), "x")
"""),
    md("""## Loyalty tier performance

Loyalty tiers are the business's own classification — RFM is our independent calculation. Comparing the two is interesting because it shows whether the loyalty programme is actually correlating with spend behaviour. If Gold customers aren't spending more than Silver, the programme might not be driving the right behaviour.
"""),
    code("""
tier_rev = c360[c360['has_purchased']].groupby('loyalty_tier')[['total_revenue','total_orders','avg_order_value']].mean().round(2)
print(tier_rev)
fig, axes = plt.subplots(1, 3, figsize=(14, 4))
for ax, col, color in zip(axes, tier_rev.columns, ['steelblue','coral','mediumpurple']):
    tier_rev[col].plot(kind='bar', ax=ax, color=color, edgecolor='white')
    ax.set_title(col); ax.set_xlabel('Tier')
    plt.sca(ax); plt.xticks(rotation=0)
plt.suptitle('Loyalty Tier Performance'); plt.tight_layout(); plt.show()
"""),
    md("""## Acquisition channel — which brings the best customers?

Volume and quality aren't the same thing. A channel that brings in 10,000 customers with low LTV might be less valuable than one bringing in 2,000 high-LTV customers. This breakdown shows you where to invest in acquisition based on actual downstream value — not just sign-up numbers.

Organic typically wins on LTV because people who find you themselves have higher intent. Paid channels often show lower LTV because they capture more passive interest.
"""),
    code("""
acq = c360[c360['has_purchased']].groupby('acquisition_channel').agg(
    customers=('customer_id', 'count'),
    avg_ltv=('total_revenue', 'mean'),
    avg_orders=('total_orders', 'mean')
).round(2).sort_values('avg_ltv', ascending=False)
print(acq)
fig, ax = plt.subplots(figsize=(9, 4))
acq['avg_ltv'].plot(kind='bar', ax=ax, color='teal', edgecolor='white')
ax.set_title('Avg LTV by Acquisition Channel'); ax.set_ylabel('Avg Revenue ($)')
plt.xticks(rotation=30, ha='right'); plt.tight_layout(); plt.show()
"""),
    md("""## Signup trends over time

Growth in signups is good, but the channel mix matters. If the growth is being driven entirely by Paid Search, that's expensive and fragile. Organic and Referral growth tends to be stickier and cheaper to maintain.
"""),
    code("""
customers['signup_month'] = pd.to_datetime(customers['signup_date']).dt.to_period('M').astype(str)
monthly_signups = customers.groupby(['signup_month','acquisition_channel'])['customer_id'].count().unstack(fill_value=0)
fig, ax = plt.subplots(figsize=(13, 5))
monthly_signups.plot(kind='area', ax=ax, alpha=0.7, stacked=True)
ax.set_title('Monthly Customer Signups by Acquisition Channel')
ax.set_xlabel('Month'); ax.set_ylabel('New Customers')
plt.xticks(rotation=45, ha='right'); plt.tight_layout(); plt.show()
"""),
    md("""## Revenue by country

Geographic breakdown is useful for two reasons: it tells you where to focus localisation and marketing efforts, and it highlights where you might be leaving money on the table. A country with high customer count but low revenue per customer might have a pricing or product-fit issue.
"""),
    code("""
country_rev = c360[c360['has_purchased']].groupby('country')['total_revenue'].sum().sort_values(ascending=False).head(10)
fig, ax = plt.subplots(figsize=(9, 4))
country_rev.plot(kind='bar', ax=ax, color='coral', edgecolor='white')
ax.set_title('Top 10 Countries by Total Revenue'); ax.set_ylabel('Revenue ($)')
plt.xticks(rotation=0); plt.tight_layout(); plt.show()
"""),
])


# ──────────────────────────────────────────────
# 03 — Campaign Analysis
# ──────────────────────────────────────────────
campaign = nb([
    md("""# Campaign Analysis

50 campaigns, multiple channels, three experiment groups. This notebook looks at which campaigns actually drove revenue, whether the A/B test produced a meaningful result, and how well campaign expectations matched reality.

One thing I find interesting about this dataset is that it has both a campaign_id on transactions AND on events, so you can trace the full journey — from a campaign impression through to an actual purchase. That's richer attribution than most datasets have.
"""),
    code("""
import sys; sys.path.insert(0, '..')
from pipeline.load import get_connection
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
sns.set_theme(style='whitegrid')

con = get_connection()
cp = con.execute("SELECT * FROM mart_campaign_performance").df()
events = con.execute("SELECT * FROM events").df()
"""),
    md("""## Revenue by channel — where did the money come from?

Different channels serve different purposes. Email tends to convert existing customers who already have intent. Paid Search catches people actively looking for something. Social builds awareness but often converts at a lower rate. Looking at revenue alone without conversion rate can be misleading — a high-revenue channel might just be high-volume.
"""),
    code("""
ch = cp.groupby('channel').agg(
    campaigns=('campaign_id','count'),
    total_revenue=('net_revenue','sum'),
    avg_conversion=('conversion_rate','mean'),
    avg_bounce=('bounce_rate','mean')
).round(4).sort_values('total_revenue', ascending=False)
print(ch)
fig, ax = plt.subplots(figsize=(9, 4))
ch['total_revenue'].plot(kind='bar', ax=ax, color='steelblue', edgecolor='white')
ax.set_title('Total Net Revenue by Channel'); ax.set_ylabel('Revenue ($)')
plt.xticks(rotation=30, ha='right'); plt.tight_layout(); plt.show()
"""),
    md("""## Conversion rate vs bounce rate — efficiency scatter

This is more useful than looking at revenue alone. You want campaigns in the top-left of this chart — low bounce, high conversion. Anything in the bottom-right (high bounce, low conversion) is burning budget. The colour shows revenue so you can see whether the efficient campaigns are also the ones making money, which they should be.
"""),
    code("""
fig, ax = plt.subplots(figsize=(8, 5))
scatter = ax.scatter(
    cp['bounce_rate'], cp['conversion_rate'],
    c=cp['net_revenue'], cmap='RdYlGn', s=80, alpha=0.8
)
plt.colorbar(scatter, ax=ax, label='Net Revenue ($)')
for _, row in cp.iterrows():
    ax.annotate(row['channel'], (row['bounce_rate'], row['conversion_rate']),
                fontsize=7, alpha=0.7)
ax.set_xlabel('Bounce Rate'); ax.set_ylabel('Conversion Rate')
ax.set_title('Bounce Rate vs Conversion Rate (colour = Revenue)')
plt.tight_layout(); plt.show()
"""),
    md("""## Campaign objective performance

Campaigns were set up with different objectives — acquisition, retention, upsell, awareness. Do the objectives that sound more "performance-focused" actually produce better revenue? This breakdown tells us whether the campaign design is translating into results.
"""),
    code("""
obj = cp.groupby('objective').agg(
    campaigns=('campaign_id','count'),
    avg_revenue=('net_revenue','mean'),
    avg_conversion=('conversion_rate','mean'),
    avg_expected_uplift=('expected_uplift','mean')
).round(4).sort_values('avg_revenue', ascending=False)
print(obj)
fig, axes = plt.subplots(1, 2, figsize=(13, 4))
obj['avg_revenue'].plot(kind='bar', ax=axes[0], color='mediumpurple', edgecolor='white')
axes[0].set_title('Avg Revenue by Objective'); plt.sca(axes[0]); plt.xticks(rotation=30, ha='right')
obj['avg_conversion'].plot(kind='bar', ax=axes[1], color='coral', edgecolor='white')
axes[1].set_title('Avg Conversion Rate by Objective'); plt.sca(axes[1]); plt.xticks(rotation=30, ha='right')
plt.tight_layout(); plt.show()
"""),
    md("""## A/B test — did any variant actually win?

The dataset has three experiment groups: Control, Variant_A, and Variant_B. Before declaring a winner, we need to check statistical significance — otherwise we're just looking at noise. I'm using a chi-squared test on purchase vs non-purchase counts, which is the standard approach for conversion rate experiments.

A p-value below 0.05 means the difference is unlikely to be random. Above 0.05 means we can't conclude anything — and in that case, rolling out a variant based on the data would be a mistake.
"""),
    code("""
from scipy import stats

ab = events.groupby('experiment_group').agg(
    sessions=('session_id','nunique'),
    users=('customer_id','nunique'),
    purchases=('event_type', lambda x: (x=='purchase').sum()),
    bounces=('event_type', lambda x: (x=='bounce').sum()),
    avg_session_sec=('session_duration_sec','mean'),
).reset_index()
ab['conversion_rate'] = (ab['purchases'] / ab['sessions']).round(4)
ab['bounce_rate'] = (ab['bounces'] / ab['sessions']).round(4)
print(ab.to_string(index=False))

control = ab[ab['experiment_group']=='Control'].iloc[0]
variant_a = ab[ab['experiment_group']=='Variant_A'].iloc[0]
ct = [[control['purchases'], control['sessions']-control['purchases']],
      [variant_a['purchases'], variant_a['sessions']-variant_a['purchases']]]
chi2, p, _, _ = stats.chi2_contingency(ct)
print(f"\\nControl vs Variant_A — chi2={chi2:.3f}, p={p:.4f}")
print("Statistically significant — safe to act on this result." if p < 0.05 else "Not statistically significant — not enough evidence to declare a winner.")
"""),
    md("""## Expected vs actual uplift — did campaigns deliver?

Marketing teams set expected uplift figures when planning campaigns. Comparing those expectations to what actually happened is a useful accountability exercise. Consistent underperformance against expectations suggests either unrealistic forecasting or campaigns that aren't working as designed.
"""),
    code("""
perf = cp[cp['net_revenue'].notna()].copy()
perf['actual_uplift_proxy'] = (perf['net_revenue'] / perf['net_revenue'].median() - 1).round(4)
fig, ax = plt.subplots(figsize=(10, 4))
x = range(len(perf))
ax.bar(x, perf['expected_uplift'], alpha=0.6, label='Expected Uplift', color='steelblue')
ax.bar(x, perf['actual_uplift_proxy'], alpha=0.6, label='Actual Uplift (proxy)', color='crimson')
ax.set_xticks(list(x)); ax.set_xticklabels(perf['campaign_id'].astype(str), rotation=90, fontsize=7)
ax.set_title('Expected vs Actual Uplift per Campaign')
ax.set_xlabel('Campaign ID'); ax.set_ylabel('Uplift')
ax.legend(); plt.tight_layout(); plt.show()
"""),
])


# ──────────────────────────────────────────────
# 04 — Revenue & Product Analysis
# ──────────────────────────────────────────────
revenue = nb([
    md("""# Revenue & Product Analysis

Revenue analysis is where a lot of the business questions live — are we growing, where are the peaks and troughs, what's the actual impact of discounting, and are refunds a problem worth worrying about?

Product analysis layers on top of that: which products are carrying the most revenue, and is the premium tier actually outperforming?
"""),
    code("""
import sys; sys.path.insert(0, '..')
from pipeline.load import get_connection
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
sns.set_theme(style='whitegrid')

con = get_connection()
tx = con.execute("SELECT * FROM transactions").df()
pp = con.execute("SELECT * FROM mart_product_performance").df()
tx['timestamp'] = pd.to_datetime(tx['timestamp'])
tx['month'] = tx['timestamp'].dt.to_period('M').astype(str)
"""),
    md("""## Monthly revenue trend

The dual-axis chart shows orders and revenue together. These should broadly track each other — if they diverge (revenue growing faster than orders), average order value is going up, which is a good sign. If orders are growing but revenue is flat, there might be a discounting problem or a product mix shift towards cheaper items.
"""),
    code("""
monthly = tx.groupby('month').agg(
    orders=('transaction_id','count'),
    net_revenue=('net_revenue','sum'),
    gross_revenue=('gross_revenue','sum'),
    refunds=('refund_flag','sum'),
    aov=('net_revenue','mean')
).reset_index()
fig, ax1 = plt.subplots(figsize=(13, 5))
ax2 = ax1.twinx()
ax1.bar(monthly['month'], monthly['orders'], color='steelblue', alpha=0.5, label='Orders')
ax2.plot(monthly['month'], monthly['net_revenue'], color='crimson', marker='o', lw=2, label='Net Revenue')
ax1.set_ylabel('Orders'); ax2.set_ylabel('Net Revenue ($)')
ax1.set_title('Monthly Orders & Revenue')
lines = ax1.get_legend_handles_labels()[0] + ax2.get_legend_handles_labels()[0]
labels = ax1.get_legend_handles_labels()[1] + ax2.get_legend_handles_labels()[1]
ax1.legend(lines, labels, loc='upper left')
plt.xticks(rotation=45, ha='right'); plt.tight_layout(); plt.show()
"""),
    md("""## Discount impact — are we giving away margin unnecessarily?

Discounts can drive volume but eat into margin. The key question is whether discounted orders have meaningfully higher revenue (suggesting bundles or upsell) or lower revenue (suggesting the discount is just reducing price without changing basket size). If discounted AOV is lower and volume isn't dramatically higher, the discounting strategy needs a rethink.
"""),
    code("""
tx['discounted'] = tx['discount_applied'] > 0
disc = tx.groupby('discounted').agg(
    orders=('transaction_id','count'),
    avg_revenue=('net_revenue','mean'),
    avg_qty=('quantity','mean')
).round(2)
print(disc)
fig, axes = plt.subplots(1, 2, figsize=(10, 4))
disc['avg_revenue'].plot(kind='bar', ax=axes[0], color=['steelblue','coral'], edgecolor='white')
axes[0].set_title('Avg Revenue: Discounted vs Not'); axes[0].set_xticklabels(['No Discount','Discounted'], rotation=0)
disc['orders'].plot(kind='bar', ax=axes[1], color=['steelblue','coral'], edgecolor='white')
axes[1].set_title('Order Count: Discounted vs Not'); axes[1].set_xticklabels(['No Discount','Discounted'], rotation=0)
plt.tight_layout(); plt.show()
"""),
    md("""## Refund rate over time

A refund rate around 2-3% is fairly normal in e-commerce. Spikes are worth investigating — they often indicate a product quality issue, a fulfilment problem, or a campaign that over-promised. A sustained upward trend is a red flag that something structural has changed.
"""),
    code("""
refund_monthly = tx.groupby('month')['refund_flag'].agg(['sum','count'])
refund_monthly['refund_rate'] = (refund_monthly['sum'] / refund_monthly['count']).round(4)
fig, ax = plt.subplots(figsize=(13, 4))
ax.plot(refund_monthly.index, refund_monthly['refund_rate'], color='crimson', marker='o', lw=2)
ax.fill_between(refund_monthly.index, refund_monthly['refund_rate'], alpha=0.2, color='crimson')
ax.set_title('Monthly Refund Rate'); ax.set_ylabel('Refund Rate')
ax.set_xlabel('Month'); plt.xticks(rotation=45, ha='right'); plt.tight_layout(); plt.show()
print(f"Overall refund rate: {refund_monthly['sum'].sum() / refund_monthly['count'].sum() * 100:.2f}%")
"""),
    md("""## Revenue by product category

Not all categories are equal in terms of revenue contribution. This breakdown helps prioritise where to focus inventory investment, promotional spend, and category-level analysis. High-revenue categories with high discount rates are worth flagging — they might be propping up revenue with margin erosion.
"""),
    code("""
cat_rev = pp.groupby('category').agg(
    total_revenue=('total_revenue','sum'),
    units_sold=('units_sold','sum'),
    products=('product_id','count'),
    avg_discount_rate=('discount_rate','mean')
).sort_values('total_revenue', ascending=False)
print(cat_rev.round(2))
fig, axes = plt.subplots(1, 2, figsize=(13, 4))
cat_rev['total_revenue'].plot(kind='bar', ax=axes[0], color='teal', edgecolor='white')
axes[0].set_title('Revenue by Category'); plt.sca(axes[0]); plt.xticks(rotation=30, ha='right')
cat_rev['units_sold'].plot(kind='bar', ax=axes[1], color='mediumpurple', edgecolor='white')
axes[1].set_title('Units Sold by Category'); plt.sca(axes[1]); plt.xticks(rotation=30, ha='right')
plt.tight_layout(); plt.show()
"""),
    md("""## Top 15 products — the revenue drivers

In most e-commerce businesses, a small number of products drive a disproportionate share of revenue. Knowing which products those are matters for inventory planning, promotional prioritisation, and risk management (what happens if one of these goes out of stock?).
"""),
    code("""
top15 = pp.nlargest(15, 'total_revenue')
fig, ax = plt.subplots(figsize=(10, 5))
bars = ax.barh(top15['product_id'].astype(str), top15['total_revenue'], color='steelblue')
ax.set_title('Top 15 Products by Net Revenue'); ax.set_xlabel('Net Revenue ($)')
ax.set_ylabel('Product ID'); plt.tight_layout(); plt.show()
"""),
    md("""## Premium vs non-premium

Premium products typically have higher margins and attract higher-intent customers. If premium is generating a disproportionate share of revenue relative to its share of the catalogue, that's a strong signal to double down on premium listings and potentially extend the range.
"""),
    code("""
prem = pp.groupby('is_premium').agg(
    products=('product_id','count'),
    avg_price=('base_price','mean'),
    total_revenue=('total_revenue','sum'),
    units_sold=('units_sold','sum'),
).round(2)
prem.index = ['Non-Premium', 'Premium']
print(prem)
print(f"\\nPremium revenue share: {prem.loc['Premium','total_revenue'] / prem['total_revenue'].sum() * 100:.1f}%")
print(f"Premium catalogue share: {prem.loc['Premium','products'] / prem['products'].sum() * 100:.1f}%")
"""),
])


# ──────────────────────────────────────────────
# 05 — Funnel & Behavioral Analysis
# ──────────────────────────────────────────────
funnel_nb = nb([
    md("""# Funnel & Behavioural Analysis

The funnel is where you find the real conversion problems. View → Click → Add to Cart → Purchase — at each step you're losing people, and the question is *where* you're losing the most and *why*.

The behavioural analysis layer (device types, traffic sources, time patterns) adds context to those drop-off numbers. Losing 60% between Click and Add to Cart on mobile looks different if mobile converts well on other traffic sources — it might point to a specific campaign landing page issue rather than a general mobile UX problem.
"""),
    code("""
import sys; sys.path.insert(0, '..')
from pipeline.load import get_connection
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
sns.set_theme(style='whitegrid')

con = get_connection()
events = con.execute("SELECT * FROM events").df()
funnel = con.execute("SELECT * FROM mart_funnel").df()
events['timestamp'] = pd.to_datetime(events['timestamp'])
events['hour'] = events['timestamp'].dt.hour
events['day_of_week'] = events['timestamp'].dt.day_name()
"""),
    md("""## The overall funnel

The headline numbers. The view-to-purchase rate is the metric most people care about, but the stage-by-stage drop-off is where you find the actionable insight. A huge drop between view and click suggests the product pages aren't compelling enough. A big drop between add-to-cart and purchase is a classic checkout abandonment problem.
"""),
    code("""
fig, ax = plt.subplots(figsize=(8, 5))
colors = ['#3498db','#2ecc71','#f1c40f','#e74c3c']
bars = ax.barh(funnel['stage'][::-1], funnel['count'][::-1], color=colors, edgecolor='white')
for bar, (_, row) in zip(bars, funnel[::-1].iterrows()):
    ax.text(bar.get_width()+10000, bar.get_y()+bar.get_height()/2,
            f"{row['count']:,}  ({row['conversion_from_top']*100:.1f}%)",
            va='center', fontsize=9)
ax.set_title('Conversion Funnel — All Events')
ax.set_xlabel('Event Count'); plt.tight_layout(); plt.show()
print(funnel.to_string(index=False))
"""),
    md("""## Funnel by device type

Mobile vs desktop conversion is one of the most common things teams argue about. The data here should settle it. If mobile converts significantly worse at a specific stage, that's where the UX investment should go. If mobile actually converts better (which happens more than people expect on mobile-first product types), that should inform where you put your ad spend.
"""),
    code("""
funnel_stages = ['view','click','add_to_cart','purchase']
ev_dev = events[events['event_type'].isin(funnel_stages)]
dev_funnel = ev_dev.groupby(['device_type','event_type'])['event_id'].count().unstack(fill_value=0)
dev_funnel = dev_funnel[[s for s in funnel_stages if s in dev_funnel.columns]]
dev_funnel_pct = dev_funnel.div(dev_funnel['view'], axis=0).round(4)
print(dev_funnel_pct)
dev_funnel_pct.T.plot(kind='bar', figsize=(9, 5))
plt.title('Funnel Conversion by Device Type'); plt.ylabel('Rate (relative to views)')
plt.xticks(rotation=30, ha='right'); plt.legend(title='Device'); plt.tight_layout(); plt.show()
"""),
    md("""## Traffic source conversion rate

Not all traffic is equal. A user who clicked a targeted email campaign has very different intent than someone who landed via a generic social ad. This breakdown shows which sources actually deliver converting traffic — which should directly inform where budget gets allocated.

High bounce rate + low conversion on a source that's receiving significant investment is a strong signal to either fix the landing experience for that source or reallocate the budget.
"""),
    code("""
src = events.groupby('traffic_source').agg(
    views=('event_type', lambda x: (x=='view').sum()),
    carts=('event_type', lambda x: (x=='add_to_cart').sum()),
    purchases=('event_type', lambda x: (x=='purchase').sum()),
    bounces=('event_type', lambda x: (x=='bounce').sum()),
).assign(
    conversion_rate=lambda d: (d['purchases'] / d['views']).round(4),
    bounce_rate=lambda d: (d['bounces'] / (d['views']+d['bounces'])).round(4)
).sort_values('conversion_rate', ascending=False)
print(src)
fig, axes = plt.subplots(1, 2, figsize=(13, 4))
src['conversion_rate'].plot(kind='bar', ax=axes[0], color='teal', edgecolor='white')
axes[0].set_title('Conversion Rate by Traffic Source'); plt.sca(axes[0]); plt.xticks(rotation=30, ha='right')
src['bounce_rate'].plot(kind='bar', ax=axes[1], color='crimson', edgecolor='white')
axes[1].set_title('Bounce Rate by Traffic Source'); plt.sca(axes[1]); plt.xticks(rotation=30, ha='right')
plt.tight_layout(); plt.show()
"""),
    md("""## When are users most active? Day × hour heatmap

This heatmap shows event volume by day and hour. The practical use cases: scheduling email sends, timing push notifications, planning flash sales, and deciding when to run paid campaigns (bidding up during peak hours can make sense if conversion holds).

Dark spots on certain days/hours might point to server issues or just genuine low-traffic periods — worth cross-referencing with conversion rate to distinguish the two.
"""),
    code("""
dow_order = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
pivot = events.groupby(['day_of_week','hour'])['event_id'].count().unstack(fill_value=0)
pivot = pivot.reindex(dow_order)
fig, ax = plt.subplots(figsize=(14, 5))
sns.heatmap(pivot, ax=ax, cmap='YlOrRd', linewidths=0.3)
ax.set_title('Event Volume — Day of Week × Hour of Day'); ax.set_xlabel('Hour'); ax.set_ylabel('')
plt.tight_layout(); plt.show()
"""),
    md("""## Session duration by page category

Longer sessions aren't always better — someone spending 10 minutes on a checkout page is probably confused, not engaged. But on product detail pages (PDPs), longer sessions often correlate with purchase intent. Context matters here, which is why breaking it down by page category is more useful than a single average.
"""),
    code("""
sess = events.groupby('page_category')['session_duration_sec'].agg(['mean','median','count']).round(1).sort_values('mean', ascending=False)
print(sess)
fig, ax = plt.subplots(figsize=(8, 4))
ax.bar(sess.index, sess['mean'], color='steelblue', edgecolor='white', label='Mean')
ax.bar(sess.index, sess['median'], color='coral', edgecolor='white', alpha=0.7, label='Median')
ax.set_title('Session Duration by Page Category'); ax.set_ylabel('Seconds')
ax.legend(); plt.xticks(rotation=20); plt.tight_layout(); plt.show()
print("\\nNote: mean > median on most categories, confirming right-skewed session times — a few long sessions are pulling the average up.")
"""),
])


# ──────────────────────────────────────────────
# Write notebooks
# ──────────────────────────────────────────────
notebooks = [
    ("01_eda.ipynb",                       eda),
    ("02_customer_analysis.ipynb",         customer),
    ("03_campaign_analysis.ipynb",         campaign),
    ("04_revenue_product_analysis.ipynb",  revenue),
    ("05_funnel_behavioral_analysis.ipynb",funnel_nb),
]

for fname, nb_obj in notebooks:
    path = OUT / fname
    with open(path, "w") as f:
        nbf.write(nb_obj, f)
    print(f"[notebooks] written: {path.name}")

print("\nDone. Run 'jupyter lab' from the project root to open them.")
