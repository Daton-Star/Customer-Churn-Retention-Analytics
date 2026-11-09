-- =====================================================================
-- Phase 2a: Table validation (DuckDB)
-- Views over /data/stage1/*.csv are created by run_sql.py before this runs.
-- Each block is one named check; results are saved to results/validation_*.csv
-- =====================================================================

-- name: v01_row_counts
-- Row count per table (compare with data_quality_report.csv and file line counts)
SELECT 'orders' AS tbl, COUNT(*) AS n_rows FROM orders
UNION ALL SELECT 'user_churn_features', COUNT(*) FROM user_churn_features
UNION ALL SELECT 'daily_kpis', COUNT(*) FROM daily_kpis
UNION ALL SELECT 'brand_monthly_funnel', COUNT(*) FROM brand_monthly_funnel
UNION ALL SELECT 'category_monthly_funnel', COUNT(*) FROM category_monthly_funnel
UNION ALL SELECT 'hour_dow_activity', COUNT(*) FROM hour_dow_activity
UNION ALL SELECT 'session_summary', COUNT(*) FROM session_summary
UNION ALL SELECT 'cohort_retention_visitors', COUNT(*) FROM cohort_retention_visitors
UNION ALL SELECT 'cohort_retention_buyers', COUNT(*) FROM cohort_retention_buyers
UNION ALL SELECT 'products', COUNT(*) FROM products;

-- name: v02_primary_keys
-- Primary-key uniqueness: n_rows must equal n_distinct for every table
SELECT 'orders.order_id' AS key, COUNT(*) AS n_rows, COUNT(DISTINCT order_id) AS n_distinct FROM orders
UNION ALL SELECT 'user_churn_features.user_id', COUNT(*), COUNT(DISTINCT user_id) FROM user_churn_features
UNION ALL SELECT 'daily_kpis.date', COUNT(*), COUNT(DISTINCT date) FROM daily_kpis
UNION ALL SELECT 'brand_monthly_funnel.(month,brand)', COUNT(*), COUNT(DISTINCT (month, brand)) FROM brand_monthly_funnel
UNION ALL SELECT 'category_monthly_funnel.(month,category_id)', COUNT(*), COUNT(DISTINCT (month, category_id)) FROM category_monthly_funnel
UNION ALL SELECT 'hour_dow_activity.(dow,hour)', COUNT(*), COUNT(DISTINCT (day_of_week_0_sun, hour_utc)) FROM hour_dow_activity
UNION ALL SELECT 'session_summary.(month,bucket)', COUNT(*), COUNT(DISTINCT (month, events_bucket)) FROM session_summary
UNION ALL SELECT 'products.product_id', COUNT(*), COUNT(DISTINCT product_id) FROM products;

-- name: v03_nulls
-- Nulls in key and measure columns
SELECT 'orders' AS tbl,
       COUNT(*) FILTER (WHERE order_id IS NULL OR user_id IS NULL OR order_ts IS NULL) AS null_keys,
       COUNT(*) FILTER (WHERE order_value IS NULL) AS null_measure
FROM orders
UNION ALL SELECT 'user_churn_features',
       COUNT(*) FILTER (WHERE user_id IS NULL OR churned IS NULL),
       COUNT(*) FILTER (WHERE total_spend IS NULL)
FROM user_churn_features
UNION ALL SELECT 'products',
       COUNT(*) FILTER (WHERE product_id IS NULL OR category_id IS NULL),
       COUNT(*) FILTER (WHERE median_price IS NULL)
FROM products
UNION ALL SELECT 'products.category_code (expected mostly null)',
       COUNT(*) FILTER (WHERE category_code IS NULL), NULL
FROM products
UNION ALL SELECT 'user_churn_features.avg_days_between_orders (null = single order)',
       COUNT(*) FILTER (WHERE avg_days_between_orders IS NULL),
       COUNT(*) FILTER (WHERE n_orders = 1)
FROM user_churn_features;

-- name: v04_ranges
-- Value ranges: dates within Oct-2019..Feb-2020, no negative money or counts
SELECT 'orders.order_ts' AS col, MIN(order_ts)::VARCHAR AS min_val, MAX(order_ts)::VARCHAR AS max_val FROM orders
UNION ALL SELECT 'orders.order_value', MIN(order_value)::VARCHAR, MAX(order_value)::VARCHAR FROM orders
UNION ALL SELECT 'orders.items', MIN(items)::VARCHAR, MAX(items)::VARCHAR FROM orders
UNION ALL SELECT 'ucf.first_order_ts', MIN(first_order_ts)::VARCHAR, MAX(first_order_ts)::VARCHAR FROM user_churn_features
UNION ALL SELECT 'ucf.last_order_ts', MIN(last_order_ts)::VARCHAR, MAX(last_order_ts)::VARCHAR FROM user_churn_features
UNION ALL SELECT 'ucf.total_spend', MIN(total_spend)::VARCHAR, MAX(total_spend)::VARCHAR FROM user_churn_features
UNION ALL SELECT 'ucf.recency_days', MIN(recency_days)::VARCHAR, MAX(recency_days)::VARCHAR FROM user_churn_features
UNION ALL SELECT 'ucf.churned', MIN(churned)::VARCHAR, MAX(churned)::VARCHAR FROM user_churn_features
UNION ALL SELECT 'daily_kpis.date', MIN(date)::VARCHAR, MAX(date)::VARCHAR FROM daily_kpis
UNION ALL SELECT 'products.median_price', MIN(median_price)::VARCHAR, MAX(median_price)::VARCHAR FROM products
UNION ALL SELECT 'hour_dow.hour_utc', MIN(hour_utc)::VARCHAR, MAX(hour_utc)::VARCHAR FROM hour_dow_activity;

-- name: v05_cross_table_consistency
-- Reconcile tables against each other
WITH o AS (SELECT SUM(order_value) rev, COUNT(*) n FROM orders),
     d AS (SELECT SUM(revenue) rev, SUM(buyers) buyer_days FROM daily_kpis),
     s AS (SELECT SUM(sessions_with_purchase) n FROM session_summary)
SELECT 'revenue: orders vs daily_kpis' AS check_name, ROUND(o.rev, 2) AS a, ROUND(d.rev, 2) AS b, ROUND(o.rev - d.rev, 2) AS diff FROM o, d
UNION ALL SELECT 'orders vs session_summary purchase sessions', o.n, s.n, o.n - s.n FROM o, s;

-- name: v06_churn_label_check
-- Re-derive the churn label from orders.csv and compare with user_churn_features.churned
WITH future AS (
    SELECT user_id, COUNT(*) AS jf_orders, SUM(order_value) AS jf_spend
    FROM orders WHERE order_ts >= '2020-01-01' GROUP BY user_id
)
SELECT COUNT(*) AS cohort_users,
       COUNT(*) FILTER (WHERE u.churned = (f.user_id IS NULL)::INT) AS label_matches,
       COUNT(*) FILTER (WHERE COALESCE(f.jf_orders, 0) = u.future_orders) AS future_orders_match,
       COUNT(*) FILTER (WHERE ABS(COALESCE(f.jf_spend, 0) - u.future_spend) < 0.01) AS future_spend_match,
       (SELECT COUNT(DISTINCT user_id) FROM orders WHERE order_ts < '2020-01-01') AS oct_dec_buyers_in_orders
FROM user_churn_features u LEFT JOIN future f USING (user_id);
