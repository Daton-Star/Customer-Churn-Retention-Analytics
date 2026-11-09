-- =====================================================================
-- Phase 2b: 15 business SQL queries (DuckDB)
-- Project: Customer Churn & Retention Analytics for E-Commerce
-- Data: Stage 1 outputs (REES46 cosmetics shop, Oct 2019 - Feb 2020)
-- Money is in the dataset's own currency units (unspecified).
-- Run: python run_sql.py 01_business_queries.sql  -> results/<name>.csv
-- =====================================================================


-- name: q01_monthly_kpis_mom
-- Business question: How are revenue, orders and buyers trending month to month?
-- Technique: CTE + LAG window for month-over-month growth.
WITH monthly AS (
    SELECT DATE_TRUNC('month', order_ts)::DATE AS month,
           COUNT(*)                            AS orders,
           COUNT(DISTINCT user_id)             AS buyers,
           SUM(order_value)                    AS revenue
    FROM orders
    GROUP BY 1
)
SELECT month,
       orders,
       buyers,
       ROUND(revenue, 2)                                                    AS revenue,
       ROUND(revenue / orders, 2)                                           AS aov,
       ROUND(orders * 1.0 / buyers, 3)                                      AS orders_per_buyer,
       ROUND(100.0 * (revenue / LAG(revenue) OVER w - 1), 2)                AS revenue_mom_pct,
       ROUND(100.0 * (orders  * 1.0 / LAG(orders) OVER w - 1), 2)           AS orders_mom_pct,
       ROUND(100.0 * (buyers  * 1.0 / LAG(buyers) OVER w - 1), 2)           AS buyers_mom_pct
FROM monthly
WINDOW w AS (ORDER BY month)
ORDER BY month;


-- name: q02_cumulative_revenue
-- Business question: How does revenue accumulate, and where are the spikes?
-- Technique: running total (SUM OVER ... ROWS UNBOUNDED PRECEDING) + 7-day moving average.
SELECT date,
       ROUND(revenue, 2)                                                                  AS revenue,
       buyers,
       ROUND(AVG(revenue) OVER (ORDER BY date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW), 2) AS revenue_7d_avg,
       ROUND(SUM(revenue) OVER (ORDER BY date ROWS UNBOUNDED PRECEDING), 2)               AS cumulative_revenue,
       ROUND(100.0 * SUM(revenue) OVER (ORDER BY date ROWS UNBOUNDED PRECEDING)
             / SUM(revenue) OVER (), 2)                                                   AS cumulative_pct
FROM daily_kpis
ORDER BY date;


-- name: q03_new_vs_returning_buyers
-- Business question: Each month, how many buyers are new vs returning, and what is the repeat rate?
-- Technique: CTE with MIN() OVER (PARTITION BY user) to find each buyer's first order month.
-- Caveat: October "new" buyers are left-censored (they may have bought before Oct 2019).
WITH buyer_months AS (
    SELECT user_id,
           DATE_TRUNC('month', order_ts)::DATE                                   AS month,
           MIN(DATE_TRUNC('month', order_ts)::DATE) OVER (PARTITION BY user_id)  AS first_month
    FROM orders
),
per_month AS (
    SELECT DISTINCT user_id, month, first_month FROM buyer_months
)
SELECT month,
       COUNT(*)                                        AS buyers,
       COUNT(*) FILTER (WHERE month = first_month)     AS new_buyers,
       COUNT(*) FILTER (WHERE month > first_month)     AS returning_buyers,
       ROUND(100.0 * COUNT(*) FILTER (WHERE month > first_month) / COUNT(*), 2) AS returning_share_pct
FROM per_month
GROUP BY month
ORDER BY month;


-- name: q04_interpurchase_gaps
-- Business question: How long do customers wait between orders? (input to the churn window in Phase 3)
-- Technique: LAG over each user's orders to get the gap to the previous order.
WITH ordered AS (
    SELECT user_id, order_ts,
           LAG(order_ts) OVER (PARTITION BY user_id ORDER BY order_ts) AS prev_ts,
           ROW_NUMBER()  OVER (PARTITION BY user_id ORDER BY order_ts) AS order_seq
    FROM orders
),
gaps AS (
    SELECT user_id, order_seq,
           DATE_DIFF('second', prev_ts, order_ts) / 86400.0 AS gap_days
    FROM ordered
    WHERE prev_ts IS NOT NULL
)
SELECT COUNT(*)                                     AS repeat_gaps,
       COUNT(DISTINCT user_id)                      AS repeat_buyers,
       ROUND(AVG(gap_days), 1)                      AS mean_gap_days,
       ROUND(QUANTILE_CONT(gap_days, 0.25), 1)      AS p25_gap_days,
       ROUND(MEDIAN(gap_days), 1)                   AS median_gap_days,
       ROUND(QUANTILE_CONT(gap_days, 0.75), 1)      AS p75_gap_days,
       ROUND(QUANTILE_CONT(gap_days, 0.90), 1)      AS p90_gap_days,
       ROUND(100.0 * AVG((gap_days <= 60)::INT), 2) AS pct_gaps_within_60d,
       ROUND(100.0 * AVG((gap_days <= 30)::INT), 2) AS pct_gaps_within_30d
FROM gaps;


-- name: q05_rfm_scores_vs_churn
-- Business question: Do RFM scores built on Oct-Dec behaviour separate churners from stayers?
-- Technique: NTILE(5) for R, F, M scores; JOIN orders -> user_churn_features for the churn label.
-- Snapshot date = 2020-01-01 (end of observation window). F uses a rank-based NTILE because
-- most users have 1 order; ties are broken by spend, then user_id, so scores are balanced and reproducible.
WITH obs AS (
    SELECT user_id,
           DATE_DIFF('day', MAX(order_ts), TIMESTAMP '2020-01-01') AS recency_days,
           COUNT(*)                                                AS frequency,
           SUM(order_value)                                        AS monetary
    FROM orders
    WHERE order_ts < '2020-01-01'
    GROUP BY user_id
),
scored AS (
    SELECT o.*,
           NTILE(5) OVER (ORDER BY recency_days DESC, user_id) AS r_score,   -- 5 = most recent
           NTILE(5) OVER (ORDER BY frequency, monetary, user_id) AS f_score,   -- 5 = most orders
           NTILE(5) OVER (ORDER BY monetary, user_id)  AS m_score    -- 5 = highest spend
    FROM obs o
)
SELECT s.r_score + s.f_score + s.m_score           AS rfm_total,
       COUNT(*)                                    AS buyers,
       ROUND(SUM(s.monetary), 2)                   AS oct_dec_revenue,
       ROUND(100.0 * AVG(u.churned), 2)            AS churn_rate_pct,
       ROUND(AVG(u.future_spend), 2)               AS avg_jan_feb_spend
FROM scored s
JOIN user_churn_features u USING (user_id)
GROUP BY 1
ORDER BY 1;


-- name: q06_top_brands_rank
-- Business question: Which brands drive revenue, and is the ranking stable month to month?
-- Technique: RANK() overall and per month (PARTITION BY month); brand "unknown" = missing brand.
-- Share is computed over ALL brands before the top-15 filter.
WITH brand_month AS (
    SELECT brand, month, revenue,
           RANK() OVER (PARTITION BY month ORDER BY revenue DESC) AS month_rank
    FROM brand_monthly_funnel
),
brand_total AS (
    SELECT brand,
           SUM(revenue)                                        AS revenue,
           SUM(SUM(revenue)) OVER ()                           AS all_brand_revenue,
           RANK() OVER (ORDER BY SUM(revenue) DESC)            AS overall_rank
    FROM brand_monthly_funnel
    GROUP BY brand
)
SELECT t.overall_rank,
       t.brand,
       ROUND(t.revenue, 2)                                                   AS revenue,
       ROUND(100.0 * t.revenue / t.all_brand_revenue, 2)                     AS revenue_share_pct,
       MIN(m.month_rank)                                                     AS best_month_rank,
       MAX(m.month_rank)                                                     AS worst_month_rank
FROM brand_total t
JOIN brand_month m USING (brand)
WHERE t.overall_rank <= 15
GROUP BY t.overall_rank, t.brand, t.revenue, t.all_brand_revenue
ORDER BY t.overall_rank;


-- name: q07_brand_conversion
-- Business question: Which brands convert browsers into buyers, and which leak at the cart?
-- Technique: aggregate funnel ratios with a minimum-traffic filter; RANK on conversion.
WITH b AS (
    SELECT brand,
           SUM(views) AS views, SUM(carts) AS carts, SUM(removes) AS removes,
           SUM(purchase_items) AS purchase_items, SUM(revenue) AS revenue
    FROM brand_monthly_funnel
    GROUP BY brand
    HAVING SUM(views) >= 50000          -- only brands with meaningful traffic
)
SELECT brand,
       views,
       ROUND(100.0 * carts / views, 2)                    AS view_to_cart_pct,
       ROUND(100.0 * purchase_items / carts, 2)           AS cart_to_purchase_pct,
       ROUND(100.0 * purchase_items / views, 2)           AS view_to_purchase_pct,
       ROUND(100.0 * removes / carts, 2)                  AS cart_remove_pct,
       ROUND(revenue / views, 3)                          AS revenue_per_view,
       RANK() OVER (ORDER BY purchase_items * 1.0 / views DESC) AS conversion_rank
FROM b
ORDER BY conversion_rank;


-- name: q08_category_conversion_with_products
-- Business question: Which categories convert well, and what do they contain?
-- Technique: JOIN category funnel <-> products (product count, median price, dominant brand).
-- category_code is mostly missing, so categories are identified by category_id + top brand.
WITH cat_funnel AS (
    SELECT category_id,
           SUM(views) AS views, SUM(carts) AS carts,
           SUM(purchase_items) AS purchase_items, SUM(revenue) AS revenue
    FROM category_monthly_funnel
    GROUP BY category_id
),
cat_products AS (
    SELECT category_id,
           COUNT(*)                         AS n_products,
           ROUND(MEDIAN(median_price), 2)   AS median_product_price,
           MAX(category_code)               AS category_code
    FROM products
    GROUP BY category_id
),
cat_top_brand AS (
    SELECT category_id, brand,
           ROW_NUMBER() OVER (PARTITION BY category_id ORDER BY SUM(revenue) DESC) AS rn
    FROM products
    WHERE brand <> 'unknown'
    GROUP BY category_id, brand
)
SELECT f.category_id,
       p.category_code,
       tb.brand                                           AS top_named_brand,
       p.n_products,
       p.median_product_price,
       ROUND(f.revenue, 2)                                AS revenue,
       RANK() OVER (ORDER BY f.revenue DESC)              AS revenue_rank,
       ROUND(100.0 * f.carts / f.views, 2)                AS view_to_cart_pct,
       ROUND(100.0 * f.purchase_items / f.carts, 2)       AS cart_to_purchase_pct,
       ROUND(100.0 * f.purchase_items / f.views, 2)       AS view_to_purchase_pct
FROM cat_funnel f
LEFT JOIN cat_products  p  USING (category_id)
LEFT JOIN cat_top_brand tb ON tb.category_id = f.category_id AND tb.rn = 1
QUALIFY revenue_rank <= 15
ORDER BY revenue_rank;


-- name: q09_cart_abandonment_trend
-- Business question: Is cart abandonment getting better or worse month to month?
-- Technique: two CTEs (session-level and event-level) joined on month; LAG for the change.
WITH sess AS (
    SELECT month::DATE AS month,
           SUM(sessions_with_cart)        AS cart_sessions,
           SUM(abandoned_cart_sessions)   AS abandoned_sessions,
           SUM(sessions_with_purchase)    AS purchase_sessions,
           SUM(sessions)                  AS sessions
    FROM session_summary
    GROUP BY 1
),
evt AS (
    SELECT DATE_TRUNC('month', date)::DATE AS month,
           SUM(carts) AS carts, SUM(removes) AS removes, SUM(purchase_items) AS purchase_items
    FROM daily_kpis
    GROUP BY 1
)
SELECT s.month,
       s.cart_sessions,
       ROUND(100.0 * s.abandoned_sessions / s.cart_sessions, 2)            AS cart_abandonment_pct,
       ROUND(100.0 * s.abandoned_sessions / s.cart_sessions
             - LAG(100.0 * s.abandoned_sessions / s.cart_sessions) OVER (ORDER BY s.month), 2) AS abandonment_change_pp,
       ROUND(100.0 * s.purchase_sessions / s.sessions, 2)                  AS session_conversion_pct,
       ROUND(100.0 * e.removes / e.carts, 2)                               AS cart_remove_pct,
       ROUND(100.0 * e.purchase_items / e.carts, 2)                        AS cart_to_purchase_pct
FROM sess s
JOIN evt e USING (month)
ORDER BY s.month;


-- name: q10_december_vs_other_buyers
-- Business question: Are December (holiday) buyers worse quality than other buyers?
-- Technique: JOIN user_churn_features -> orders to classify by FIRST order month, so we compare
-- customers acquired in December with customers acquired earlier (not just "bought in Dec").
WITH first_order AS (
    SELECT user_id, MIN(order_ts) AS first_ts
    FROM orders
    GROUP BY user_id
)
SELECT CASE WHEN DATE_TRUNC('month', f.first_ts) = DATE '2019-12-01' THEN 'First order in Dec 2019'
            WHEN DATE_TRUNC('month', f.first_ts) = DATE '2019-11-01' THEN 'First order in Nov 2019'
            ELSE 'First order in Oct 2019 (left-censored)' END              AS acquisition_group,
       COUNT(*)                                                             AS buyers,
       ROUND(100.0 * AVG(u.churned), 2)                                     AS churn_rate_pct,
       ROUND(AVG(u.n_orders), 3)                                            AS avg_orders_oct_dec,
       ROUND(AVG(u.aov), 2)                                                 AS avg_aov,
       ROUND(AVG(u.total_spend), 2)                                         AS avg_spend_oct_dec,
       ROUND(AVG(u.recency_days), 1)                                        AS avg_recency_days,
       ROUND(AVG(u.future_spend), 2)                                        AS avg_jan_feb_spend
FROM user_churn_features u
JOIN first_order f USING (user_id)
GROUP BY 1
ORDER BY 1;


-- name: q11_churn_by_order_count
-- Business question: How does churn fall as customers place more orders? (the "second order" lever)
-- Technique: CASE bucketing + window SUM for each bucket's share of buyers and revenue.
SELECT CASE WHEN n_orders >= 4 THEN '4+' ELSE n_orders::VARCHAR END  AS orders_oct_dec,
       COUNT(*)                                                       AS buyers,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2)             AS buyer_share_pct,
       ROUND(100.0 * SUM(total_spend) / SUM(SUM(total_spend)) OVER (), 2) AS spend_share_pct,
       ROUND(100.0 * AVG(churned), 2)                                 AS churn_rate_pct,
       ROUND(SUM(future_spend), 2)                                    AS jan_feb_spend
FROM user_churn_features
GROUP BY 1
ORDER BY 1;


-- name: q12_churn_by_engagement_and_cart_removal
-- Business question: Do engagement decline and heavy cart removal signal churn?
-- Technique: CASE segmentation on last-31-day vs previous-30-day events and on cart_remove_rate.
WITH seg AS (
    SELECT churned,
           CASE WHEN events_last_31d = 0                     THEN '1. No activity in last 31d'
                WHEN events_last_31d <  events_prev_30d      THEN '2. Declining'
                WHEN events_last_31d =  events_prev_30d      THEN '3. Flat'
                ELSE                                              '4. Growing' END        AS engagement_trend,
           CASE WHEN n_carts = 0                THEN '0. No carts'
                WHEN cart_remove_rate < 0.25    THEN '1. <25% removed'
                WHEN cart_remove_rate < 0.50    THEN '2. 25-50% removed'
                WHEN cart_remove_rate < 0.75    THEN '3. 50-75% removed'
                ELSE                                 '4. 75%+ removed' END              AS cart_removal_band
    FROM user_churn_features
)
SELECT 'engagement_trend' AS dimension, engagement_trend AS segment,
       COUNT(*) AS buyers, ROUND(100.0 * AVG(churned), 2) AS churn_rate_pct
FROM seg GROUP BY 1, 2
UNION ALL
SELECT 'cart_removal_band', cart_removal_band,
       COUNT(*), ROUND(100.0 * AVG(churned), 2)
FROM seg GROUP BY 1, 2
ORDER BY 1, 2;


-- name: q13_pareto_revenue_concentration
-- Business question: How concentrated is revenue? What share comes from the top customers?
-- Technique: per-customer revenue, ROW_NUMBER for rank, running SUM for cumulative share.
WITH cust AS (
    SELECT user_id, SUM(order_value) AS revenue
    FROM orders
    GROUP BY user_id
),
ranked AS (
    SELECT revenue,
           ROW_NUMBER() OVER (ORDER BY revenue DESC)                            AS rnk,
           COUNT(*)     OVER ()                                                 AS n_customers,
           SUM(revenue) OVER (ORDER BY revenue DESC ROWS UNBOUNDED PRECEDING)   AS cum_revenue,
           SUM(revenue) OVER ()                                                 AS total_revenue
    FROM cust
)
SELECT top_pct,
       MAX(rnk)                                              AS customers,
       ROUND(100.0 * MAX(cum_revenue) / MAX(total_revenue), 2) AS revenue_share_pct
FROM ranked,
     (VALUES (1), (5), (10), (20), (50)) AS t(top_pct)
WHERE rnk <= CEIL(n_customers * top_pct / 100.0)
GROUP BY top_pct
ORDER BY top_pct;


-- name: q14_peak_hours_conversion
-- Business question: When do shoppers browse vs buy? (timing for push/WhatsApp sends; hours are UTC)
-- Technique: RANK over hour-of-week slots by conversion and by revenue.
WITH slots AS (
    SELECT day_of_week_0_sun,
           CASE day_of_week_0_sun WHEN 0 THEN 'Sun' WHEN 1 THEN 'Mon' WHEN 2 THEN 'Tue'
                WHEN 3 THEN 'Wed' WHEN 4 THEN 'Thu' WHEN 5 THEN 'Fri' ELSE 'Sat' END AS dow,
           hour_utc, views, purchase_items, revenue,
           purchase_items * 1.0 / NULLIF(views, 0) AS purchase_per_view
    FROM hour_dow_activity
)
SELECT dow, hour_utc, views, purchase_items,
       ROUND(revenue, 2)                                           AS revenue,
       ROUND(100.0 * purchase_per_view, 2)                         AS purchase_per_view_pct,
       RANK() OVER (ORDER BY revenue DESC)                         AS revenue_rank,
       RANK() OVER (ORDER BY purchase_per_view DESC)               AS conversion_rank
FROM slots
QUALIFY revenue_rank <= 10 OR conversion_rank <= 10
ORDER BY revenue_rank;


-- name: q15_session_depth_conversion
-- Business question: Do deeper sessions convert better, and where is abandonment worst?
-- Technique: aggregate across months by session-depth bucket; share of all purchases.
SELECT events_bucket                                                            AS events_per_session,
       SUM(sessions)                                                            AS sessions,
       ROUND(100.0 * SUM(sessions) / SUM(SUM(sessions)) OVER (), 2)             AS session_share_pct,
       ROUND(100.0 * SUM(sessions_with_cart) / SUM(sessions), 2)                AS cart_rate_pct,
       ROUND(100.0 * SUM(sessions_with_purchase) / SUM(sessions), 2)            AS purchase_rate_pct,
       ROUND(100.0 * SUM(abandoned_cart_sessions) / SUM(sessions_with_cart), 2) AS cart_abandonment_pct,
       ROUND(100.0 * SUM(sessions_with_purchase)
             / SUM(SUM(sessions_with_purchase)) OVER (), 2)                     AS share_of_purchases_pct
FROM session_summary
GROUP BY events_bucket
ORDER BY CASE events_bucket WHEN '1' THEN 1 WHEN '2-5' THEN 2 WHEN '6-20' THEN 3 ELSE 4 END;
