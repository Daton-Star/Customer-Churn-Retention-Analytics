"""Phase 1 baseline sizing: headline scale numbers used in the business framing.
Run: python src/p1_baseline.py [data_dir]   (default: config.DATA = stage1_kaggle/data)"""
import sys, duckdb
from pathlib import Path

from config import DATA as DEFAULT_DATA

DATA = Path(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DATA)
con = duckdb.connect()
for t in ["orders", "user_churn_features", "daily_kpis", "session_summary", "data_quality_report"]:
    con.sql(f"CREATE VIEW {t} AS SELECT * FROM read_csv_auto('{DATA / (t + '.csv')}')")

QUERIES = {
    # Order-level scale (Oct 2019 - Feb 2020)
    "orders_overall": """
        SELECT COUNT(*) AS orders, COUNT(DISTINCT user_id) AS buyers,
               ROUND(SUM(order_value), 2) AS revenue, ROUND(AVG(order_value), 2) AS aov,
               ROUND(COUNT(*) * 1.0 / COUNT(DISTINCT user_id), 3) AS orders_per_buyer
        FROM orders""",
    # Repeat-purchase rate over the full 5 months: buyers with 2+ orders
    "repeat_rate_5m": """
        SELECT ROUND(AVG((n >= 2)::INT), 4) AS repeat_rate
        FROM (SELECT user_id, COUNT(*) n FROM orders GROUP BY 1)""",
    # Churn cohort: Oct-Dec buyers, churned = no order in Jan-Feb 2020
    "churn_cohort": """
        SELECT COUNT(*) AS cohort_buyers, SUM(churned) AS churned_buyers,
               ROUND(AVG(churned), 4) AS churn_rate,
               ROUND(SUM(total_spend), 2) AS cohort_spend_oct_dec,
               ROUND(SUM(total_spend) FILTER (WHERE churned = 1), 2) AS churned_spend_oct_dec,
               ROUND(SUM(total_spend) FILTER (WHERE churned = 1) / SUM(total_spend), 4) AS churned_spend_share,
               ROUND(AVG((n_orders = 1)::INT), 4) AS single_order_share,
               ROUND(SUM(future_spend), 2) AS retained_spend_jan_feb
        FROM user_churn_features""",
    "churn_by_single_order": """
        SELECT n_orders = 1 AS single_order, COUNT(*) AS buyers, ROUND(AVG(churned), 4) AS churn_rate
        FROM user_churn_features GROUP BY 1 ORDER BY 1""",
    # Event-level funnel from daily KPIs (cleaned events)
    "funnel_events": """
        SELECT SUM(views) AS n_views, SUM(carts) AS n_carts, SUM(removes) AS n_removes, SUM(purchase_items) AS n_purchase_items,
               ROUND(SUM(carts) / SUM(views), 4) AS cart_events_per_view,
               ROUND(SUM(purchase_items) / SUM(carts), 4) AS purchase_items_per_cart_event
        FROM daily_kpis""",
    # Session-based cart abandonment: sessions with a cart but no purchase
    "cart_abandonment_sessions": """
        SELECT SUM(sessions) AS n_sessions, SUM(sessions_with_cart) AS cart_sessions,
               SUM(sessions_with_purchase) AS purchase_sessions, SUM(abandoned_cart_sessions) AS abandoned,
               ROUND(SUM(abandoned_cart_sessions) / SUM(sessions_with_cart), 4) AS cart_abandonment_rate,
               ROUND(SUM(sessions_with_purchase) / SUM(sessions), 4) AS session_conversion
        FROM session_summary""",
}

if __name__ == "__main__":
    print(con.sql("SELECT * FROM data_quality_report").df().to_string(index=False))
    for name, q in QUERIES.items():
        print(f"\n== {name}\n" + con.sql(q).df().to_string(index=False))
