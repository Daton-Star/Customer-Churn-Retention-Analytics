# Stage 1: Kaggle event reduction

Stage 1 is a Kaggle notebook that reads the raw **REES46 cosmetics shop** clickstream (Oct 2019 to Feb 2020, 20,692,840 raw events: views, add-to-cart, remove-from-cart, purchases), cleans it (exact duplicates, null sessions, non-positive prices) and reduces it to the 11 summary tables in [data/](data/). Purchase events are grouped into orders, and a churn label is built for Oct to Dec 2019 buyers (churned = no order in Jan to Feb 2020).

Kaggle notebook: <ADD LINK>

Everything downstream (Phases 1 to 9 in [../src/](../src/)) reads only these tables, so the full analysis reruns locally in minutes without the 20M-row raw data. Timestamps are UTC.

| Table | Rows | Grain / contents |
|---|---:|---|
| [orders.csv](data/orders.csv) | 155,617 | One row per order: order_id, user_id, order_ts, items, distinct_products, distinct_brands, order_value (110,518 buyers) |
| [user_churn_features.csv](data/user_churn_features.csv) | 72,225 | One row per Oct to Dec 2019 buyer: 36 columns of behaviour features, plus the label-window columns future_orders, future_spend, churned (never used as features) |
| [daily_kpis.csv](data/daily_kpis.csv) | 152 | One row per day: events, views, carts, removes, purchase_items, active_users, sessions, buyers, revenue |
| [brand_monthly_funnel.csv](data/brand_monthly_funnel.csv) | 1,260 | Month x brand: views, carts, removes, purchase_items, viewers, buyers, revenue ("unknown" is the largest brand) |
| [category_monthly_funnel.csv](data/category_monthly_funnel.csv) | 2,432 | Month x category_id: views, carts, removes, purchase_items, buyers, revenue (category_code mostly blank) |
| [hour_dow_activity.csv](data/hour_dow_activity.csv) | 168 | Day of week (0 = Sunday) x hour (UTC): events, views, carts, purchase_items, revenue |
| [session_summary.csv](data/session_summary.csv) | 20 | Month x session-depth bucket (1, 2-5, 6-20, 21+ events): sessions, sessions with cart / purchase, abandoned-cart sessions, avg session minutes |
| [cohort_retention_visitors.csv](data/cohort_retention_visitors.csv) | 15 | First-visit month x months since: active users |
| [cohort_retention_buyers.csv](data/cohort_retention_buyers.csv) | 15 | First-purchase month x months since: active buyers |
| [products.csv](data/products.csv) | 54,566 | One row per product: category, brand, median price, views, carts, purchase_items, revenue |
| [data_quality_report.csv](data/data_quality_report.csv) | 20 | check_name, value: raw and clean row counts, duplicates, nulls, event counts, date range, headline churn rate |
