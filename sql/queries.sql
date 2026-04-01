-- ============================================================
-- MARKETING & E-COMMERCE ANALYTICS — KEY SQL QUERIES
-- Warehouse: DuckDB (data/warehouse.duckdb)
-- ============================================================


-- ─────────────────────────────────────────────
-- 1. REVENUE OVERVIEW
-- ─────────────────────────────────────────────

-- Monthly revenue trend
SELECT
    month,
    COUNT(transaction_id)          AS orders,
    SUM(net_revenue)               AS net_revenue,
    SUM(gross_revenue)             AS gross_revenue,
    ROUND(AVG(net_revenue), 2)     AS aov,
    SUM(CAST(refund_flag AS INT))  AS refunds
FROM transactions
GROUP BY month
ORDER BY month;


-- Revenue by channel (campaign channel attribution)
SELECT
    c.channel,
    COUNT(DISTINCT t.transaction_id)  AS orders,
    COUNT(DISTINCT t.customer_id)     AS unique_customers,
    ROUND(SUM(t.net_revenue), 2)      AS net_revenue,
    ROUND(AVG(t.net_revenue), 2)      AS avg_order_value,
    SUM(CAST(t.refund_flag AS INT))   AS refunds
FROM transactions t
JOIN campaigns c ON t.campaign_id = c.campaign_id
WHERE t.campaign_id != 0
GROUP BY c.channel
ORDER BY net_revenue DESC;


-- ─────────────────────────────────────────────
-- 2. CAMPAIGN PERFORMANCE
-- ─────────────────────────────────────────────

-- Top 10 campaigns by net revenue
SELECT
    c.campaign_id,
    c.channel,
    c.objective,
    c.target_segment,
    c.duration_days,
    cp.tx_count                      AS orders,
    ROUND(cp.net_revenue, 2)         AS net_revenue,
    ROUND(cp.conversion_rate, 4)     AS conversion_rate,
    ROUND(cp.bounce_rate, 4)         AS bounce_rate,
    ROUND(cp.revenue_per_visitor, 2) AS revenue_per_visitor
FROM mart_campaign_performance cp
JOIN campaigns c ON cp.campaign_id = c.campaign_id
WHERE cp.net_revenue IS NOT NULL
ORDER BY cp.net_revenue DESC
LIMIT 10;


-- Campaign objective comparison
SELECT
    objective,
    COUNT(*)                             AS campaigns,
    ROUND(AVG(net_revenue), 2)           AS avg_net_revenue,
    ROUND(AVG(conversion_rate), 4)       AS avg_conversion_rate,
    ROUND(AVG(expected_uplift), 4)       AS avg_expected_uplift,
    ROUND(AVG(duration_days), 1)         AS avg_duration_days
FROM mart_campaign_performance
GROUP BY objective
ORDER BY avg_net_revenue DESC;


-- A/B Test experiment group comparison
SELECT
    experiment_group,
    COUNT(DISTINCT session_id)                             AS sessions,
    COUNT(DISTINCT customer_id)                            AS unique_users,
    SUM(CASE WHEN event_type = 'purchase' THEN 1 ELSE 0 END) AS purchases,
    SUM(CASE WHEN event_type = 'bounce'   THEN 1 ELSE 0 END) AS bounces,
    ROUND(
        SUM(CASE WHEN event_type = 'purchase' THEN 1 ELSE 0 END) * 1.0
        / COUNT(DISTINCT session_id), 4
    ) AS conversion_rate,
    ROUND(AVG(session_duration_sec), 1) AS avg_session_sec
FROM events
GROUP BY experiment_group
ORDER BY conversion_rate DESC;


-- ─────────────────────────────────────────────
-- 3. CUSTOMER ANALYTICS
-- ─────────────────────────────────────────────

-- Customer count and revenue by loyalty tier
SELECT
    loyalty_tier,
    COUNT(*)                            AS customers,
    SUM(CASE WHEN has_purchased THEN 1 ELSE 0 END) AS buyers,
    ROUND(AVG(total_revenue), 2)        AS avg_ltv,
    ROUND(AVG(total_orders), 2)         AS avg_orders,
    ROUND(AVG(avg_order_value), 2)      AS avg_aov,
    ROUND(AVG(recency_days), 1)         AS avg_recency_days
FROM mart_customer_360
GROUP BY loyalty_tier
ORDER BY loyalty_tier;


-- RFM segment distribution
SELECT
    rfm_segment,
    COUNT(*)                          AS customers,
    ROUND(AVG(total_revenue), 2)      AS avg_revenue,
    ROUND(AVG(total_orders), 2)       AS avg_orders,
    ROUND(AVG(recency_days), 1)       AS avg_recency_days
FROM mart_customer_360
WHERE rfm_segment IS NOT NULL
GROUP BY rfm_segment
ORDER BY avg_revenue DESC;


-- New customer acquisition by month and channel
SELECT
    STRFTIME(signup_date, '%Y-%m')    AS signup_month,
    acquisition_channel,
    COUNT(*)                          AS new_customers
FROM customers
GROUP BY signup_month, acquisition_channel
ORDER BY signup_month, new_customers DESC;


-- Country-level customer and revenue breakdown
SELECT
    c.country,
    COUNT(DISTINCT c.customer_id)          AS customers,
    ROUND(SUM(m.total_revenue), 2)         AS total_revenue,
    ROUND(AVG(m.total_revenue), 2)         AS avg_ltv,
    ROUND(AVG(m.total_orders), 2)          AS avg_orders
FROM customers c
JOIN mart_customer_360 m ON c.customer_id = m.customer_id
WHERE m.has_purchased = true
GROUP BY c.country
ORDER BY total_revenue DESC;


-- ─────────────────────────────────────────────
-- 4. PRODUCT ANALYTICS
-- ─────────────────────────────────────────────

-- Top 10 products by revenue
SELECT
    p.product_id,
    p.category,
    p.brand,
    ROUND(p.base_price, 2)               AS base_price,
    p.is_premium,
    pp.units_sold,
    ROUND(pp.total_revenue, 2)           AS total_revenue,
    ROUND(pp.avg_revenue_per_tx, 2)      AS avg_revenue_per_tx,
    pp.unique_buyers
FROM mart_product_performance pp
JOIN products p ON pp.product_id = p.product_id
WHERE pp.total_revenue IS NOT NULL
ORDER BY pp.total_revenue DESC
LIMIT 10;


-- Revenue by product category
SELECT
    category,
    COUNT(*)                              AS products,
    ROUND(SUM(total_revenue), 2)          AS total_revenue,
    ROUND(AVG(total_revenue), 2)          AS avg_revenue,
    SUM(CAST(units_sold AS INT))          AS total_units,
    ROUND(AVG(discount_rate), 4)          AS avg_discount_rate
FROM mart_product_performance
GROUP BY category
ORDER BY total_revenue DESC;


-- Premium vs non-premium performance
SELECT
    is_premium,
    COUNT(*)                             AS products,
    ROUND(AVG(base_price), 2)            AS avg_base_price,
    ROUND(SUM(total_revenue), 2)         AS total_revenue,
    SUM(CAST(units_sold AS INT))         AS total_units,
    ROUND(AVG(avg_revenue_per_tx), 2)    AS avg_revenue_per_tx
FROM mart_product_performance
GROUP BY is_premium
ORDER BY is_premium DESC;


-- ─────────────────────────────────────────────
-- 5. FUNNEL ANALYSIS
-- ─────────────────────────────────────────────

-- Overall funnel stages
SELECT * FROM mart_funnel;


-- Funnel by device type
SELECT
    device_type,
    SUM(CASE WHEN event_type = 'view'         THEN 1 ELSE 0 END) AS views,
    SUM(CASE WHEN event_type = 'click'        THEN 1 ELSE 0 END) AS clicks,
    SUM(CASE WHEN event_type = 'add_to_cart'  THEN 1 ELSE 0 END) AS add_to_carts,
    SUM(CASE WHEN event_type = 'purchase'     THEN 1 ELSE 0 END) AS purchases,
    ROUND(
        SUM(CASE WHEN event_type = 'purchase' THEN 1 ELSE 0 END) * 1.0
        / NULLIF(SUM(CASE WHEN event_type = 'view' THEN 1 ELSE 0 END), 0), 4
    ) AS view_to_purchase_rate
FROM events
WHERE device_type IS NOT NULL
GROUP BY device_type
ORDER BY view_to_purchase_rate DESC;


-- Funnel by traffic source
SELECT
    traffic_source,
    SUM(CASE WHEN event_type = 'view'         THEN 1 ELSE 0 END) AS views,
    SUM(CASE WHEN event_type = 'add_to_cart'  THEN 1 ELSE 0 END) AS add_to_carts,
    SUM(CASE WHEN event_type = 'purchase'     THEN 1 ELSE 0 END) AS purchases,
    ROUND(
        SUM(CASE WHEN event_type = 'purchase' THEN 1 ELSE 0 END) * 1.0
        / NULLIF(SUM(CASE WHEN event_type = 'view' THEN 1 ELSE 0 END), 0), 4
    ) AS conversion_rate
FROM events
GROUP BY traffic_source
ORDER BY conversion_rate DESC;


-- ─────────────────────────────────────────────
-- 6. COHORT RETENTION (monthly)
-- ─────────────────────────────────────────────

WITH cohorts AS (
    SELECT
        customer_id,
        DATE_TRUNC('month', signup_date) AS cohort_month
    FROM customers
),
purchases AS (
    SELECT
        t.customer_id,
        DATE_TRUNC('month', t.timestamp)   AS purchase_month
    FROM transactions t
    WHERE NOT t.refund_flag
),
combined AS (
    SELECT
        c.cohort_month,
        p.purchase_month,
        DATEDIFF('month', c.cohort_month, p.purchase_month) AS months_since_signup,
        COUNT(DISTINCT c.customer_id) AS customers
    FROM cohorts c
    JOIN purchases p ON c.customer_id = p.customer_id
    GROUP BY c.cohort_month, p.purchase_month, months_since_signup
)
SELECT
    STRFTIME(cohort_month, '%Y-%m') AS cohort,
    months_since_signup,
    customers
FROM combined
WHERE months_since_signup BETWEEN 0 AND 11
ORDER BY cohort, months_since_signup;
