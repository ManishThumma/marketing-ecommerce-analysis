"""
Generates all analysis Jupyter notebooks programmatically.
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
    md("# 01 — Exploratory Data Analysis\nOverview of all five tables: shape, dtypes, nulls, distributions."),
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
    md("## Dataset Sizes"),
    code("""
for name, df in cleaned.items():
    print(f"{name:15s}  rows={len(df):>10,}  cols={df.shape[1]}")
"""),
    md("## Null Analysis"),
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
    md("## Customer Age Distribution"),
    code("""
fig, ax = plt.subplots(figsize=(8, 4))
cleaned['customers']['age'].hist(bins=30, ax=ax, color='steelblue', edgecolor='white')
ax.set_title('Customer Age Distribution')
ax.set_xlabel('Age'); ax.set_ylabel('Count')
plt.tight_layout(); plt.show()
"""),
    md("## Loyalty Tier Distribution"),
    code("""
tier_counts = cleaned['customers']['loyalty_tier'].value_counts().sort_index()
fig, ax = plt.subplots(figsize=(6, 4))
tier_counts.plot(kind='bar', ax=ax, color=['#cd7f32','#c0c0c0','#ffd700'], edgecolor='white')
ax.set_title('Customer Loyalty Tier Distribution')
ax.set_xlabel('Tier'); ax.set_ylabel('Count')
plt.xticks(rotation=0); plt.tight_layout(); plt.show()
"""),
    md("## Event Type Breakdown"),
    code("""
ev_counts = cleaned['events']['event_type'].value_counts()
fig, ax = plt.subplots(figsize=(7, 4))
ev_counts.plot(kind='barh', ax=ax, color='coral')
ax.set_title('Event Type Counts'); ax.set_xlabel('Count')
plt.tight_layout(); plt.show()
"""),
    md("## Transaction Revenue Distribution"),
    code("""
tx = cleaned['transactions'].dropna(subset=['gross_revenue'])
fig, axes = plt.subplots(1, 2, figsize=(12, 4))
tx['gross_revenue'].clip(-200, 600).hist(bins=50, ax=axes[0], color='steelblue', edgecolor='white')
axes[0].set_title('Gross Revenue Distribution'); axes[0].set_xlabel('Revenue ($)')
tx['quantity'].value_counts().sort_index().plot(kind='bar', ax=axes[1], color='teal')
axes[1].set_title('Quantity per Transaction'); axes[1].set_xlabel('Quantity')
plt.tight_layout(); plt.show()
"""),
    md("## Product Category Distribution"),
    code("""
cat_counts = cleaned['products']['category'].value_counts()
fig, ax = plt.subplots(figsize=(7, 4))
cat_counts.plot(kind='bar', ax=ax, color='mediumpurple', edgecolor='white')
ax.set_title('Products by Category'); ax.set_xlabel('Category'); ax.set_ylabel('Count')
plt.xticks(rotation=30); plt.tight_layout(); plt.show()
"""),
    md("## Monthly Transaction Volume"),
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
    md("# 02 — Customer Analysis\nRFM segmentation, LTV, cohort retention, acquisition channel analysis."),
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
    md("## RFM Segment Distribution"),
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
    md("## Average LTV by RFM Segment"),
    code("""
ltv = c360[c360['rfm_segment'].notna()].groupby('rfm_segment')['total_revenue'].mean().sort_values(ascending=False)
fig, ax = plt.subplots(figsize=(8, 4))
ltv.plot(kind='bar', ax=ax, color='steelblue', edgecolor='white')
ax.set_title('Average LTV by RFM Segment'); ax.set_ylabel('Avg Revenue ($)')
plt.xticks(rotation=20); plt.tight_layout(); plt.show()
"""),
    md("## Loyalty Tier vs Revenue"),
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
    md("## Acquisition Channel Effectiveness"),
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
    md("## Customer Signup Trend"),
    code("""
customers['signup_month'] = pd.to_datetime(customers['signup_date']).dt.to_period('M').astype(str)
monthly_signups = customers.groupby(['signup_month','acquisition_channel'])['customer_id'].count().unstack(fill_value=0)
fig, ax = plt.subplots(figsize=(13, 5))
monthly_signups.plot(kind='area', ax=ax, alpha=0.7, stacked=True)
ax.set_title('Monthly Customer Signups by Acquisition Channel')
ax.set_xlabel('Month'); ax.set_ylabel('New Customers')
plt.xticks(rotation=45, ha='right'); plt.tight_layout(); plt.show()
"""),
    md("## Country Revenue Map (Top 10)"),
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
    md("# 03 — Campaign Analysis\nROI, channel performance, A/B testing, objective comparison."),
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
    md("## Campaign Revenue by Channel"),
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
    md("## Conversion Rate vs Bounce Rate by Channel"),
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
ax.set_title('Bounce Rate vs Conversion Rate (color = Revenue)')
plt.tight_layout(); plt.show()
"""),
    md("## Campaign Objective Performance"),
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
    md("## A/B Test Analysis — Experiment Groups"),
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

# Chi-squared test on Control vs Variant_A
control = ab[ab['experiment_group']=='Control'].iloc[0]
variant_a = ab[ab['experiment_group']=='Variant_A'].iloc[0]
ct = [[control['purchases'], control['sessions']-control['purchases']],
      [variant_a['purchases'], variant_a['sessions']-variant_a['purchases']]]
chi2, p, _, _ = stats.chi2_contingency(ct)
print(f"\\nControl vs Variant_A — chi2={chi2:.3f}, p={p:.4f}")
print("Statistically significant" if p < 0.05 else "Not statistically significant")
"""),
    md("## Expected vs Actual Uplift"),
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
    md("# 04 — Revenue & Product Analysis\nRevenue trends, category performance, discount impact, refund analysis."),
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
    md("## Monthly Revenue & Order Trend"),
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
    md("## Discount Impact on Revenue"),
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
    md("## Refund Analysis"),
    code("""
refund_monthly = tx.groupby('month')['refund_flag'].agg(['sum','count'])
refund_monthly['refund_rate'] = (refund_monthly['sum'] / refund_monthly['count']).round(4)
fig, ax = plt.subplots(figsize=(13, 4))
ax.plot(refund_monthly.index, refund_monthly['refund_rate'], color='crimson', marker='o', lw=2)
ax.fill_between(refund_monthly.index, refund_monthly['refund_rate'], alpha=0.2, color='crimson')
ax.set_title('Monthly Refund Rate'); ax.set_ylabel('Refund Rate')
ax.set_xlabel('Month'); plt.xticks(rotation=45, ha='right'); plt.tight_layout(); plt.show()
"""),
    md("## Revenue by Product Category"),
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
    md("## Top 15 Products by Revenue"),
    code("""
top15 = pp.nlargest(15, 'total_revenue')
fig, ax = plt.subplots(figsize=(10, 5))
bars = ax.barh(top15['product_id'].astype(str), top15['total_revenue'], color='steelblue')
ax.set_title('Top 15 Products by Net Revenue'); ax.set_xlabel('Net Revenue ($)')
ax.set_ylabel('Product ID'); plt.tight_layout(); plt.show()
"""),
    md("## Premium vs Non-Premium Performance"),
    code("""
prem = pp.groupby('is_premium').agg(
    products=('product_id','count'),
    avg_price=('base_price','mean'),
    total_revenue=('total_revenue','sum'),
    units_sold=('units_sold','sum'),
).round(2)
print(prem)
"""),
])

# ──────────────────────────────────────────────
# 05 — Funnel & Behavioral Analysis
# ──────────────────────────────────────────────
funnel_nb = nb([
    md("# 05 — Funnel & Behavioral Analysis\nConversion funnel, device/traffic analysis, session behavior, hourly patterns."),
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
    md("## Conversion Funnel"),
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
print(funnel)
"""),
    md("## Funnel by Device Type"),
    code("""
funnel_stages = ['view','click','add_to_cart','purchase']
ev_dev = events[events['event_type'].isin(funnel_stages)]
dev_funnel = ev_dev.groupby(['device_type','event_type'])['event_id'].count().unstack(fill_value=0)
dev_funnel = dev_funnel[[s for s in funnel_stages if s in dev_funnel.columns]]
dev_funnel_pct = dev_funnel.div(dev_funnel['view'], axis=0).round(4)
print(dev_funnel_pct)
dev_funnel_pct.T.plot(kind='bar', figsize=(9, 5))
plt.title('Funnel Conversion by Device Type'); plt.ylabel('Rate (vs views)')
plt.xticks(rotation=30, ha='right'); plt.legend(title='Device'); plt.tight_layout(); plt.show()
"""),
    md("## Traffic Source Conversion Rate"),
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
    md("## Hourly Activity Heatmap (Day of Week vs Hour)"),
    code("""
dow_order = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
pivot = events.groupby(['day_of_week','hour'])['event_id'].count().unstack(fill_value=0)
pivot = pivot.reindex(dow_order)
fig, ax = plt.subplots(figsize=(14, 5))
sns.heatmap(pivot, ax=ax, cmap='YlOrRd', linewidths=0.3)
ax.set_title('Event Volume — Day of Week × Hour'); ax.set_xlabel('Hour'); ax.set_ylabel('')
plt.tight_layout(); plt.show()
"""),
    md("## Session Duration by Page Category"),
    code("""
sess = events.groupby('page_category')['session_duration_sec'].agg(['mean','median','count']).round(1).sort_values('mean', ascending=False)
print(sess)
fig, ax = plt.subplots(figsize=(8, 4))
ax.bar(sess.index, sess['mean'], color='steelblue', edgecolor='white', label='Mean')
ax.bar(sess.index, sess['median'], color='coral', edgecolor='white', alpha=0.7, label='Median')
ax.set_title('Session Duration by Page Category'); ax.set_ylabel('Seconds')
ax.legend(); plt.xticks(rotation=20); plt.tight_layout(); plt.show()
"""),
])

# ──────────────────────────────────────────────
# Write notebooks
# ──────────────────────────────────────────────
notebooks = [
    ("01_eda.ipynb", eda),
    ("02_customer_analysis.ipynb", customer),
    ("03_campaign_analysis.ipynb", campaign),
    ("04_revenue_product_analysis.ipynb", revenue),
    ("05_funnel_behavioral_analysis.ipynb", funnel_nb),
]

for fname, nb_obj in notebooks:
    path = OUT / fname
    with open(path, "w") as f:
        nbf.write(nb_obj, f)
    print(f"[notebooks] written: {path.name}")

print("\nAll notebooks generated. Run 'jupyter lab' to explore them.")
