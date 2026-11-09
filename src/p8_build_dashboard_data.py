"""Phase 8a: build the Power BI star schema and the dashboard data bundle.

Inputs : Stage 1 tables (stage1_kaggle/data) + results of Phases 2-7 (outputs/).
Outputs: dashboard/powerbi/*.csv   star schema for Power BI (facts, dimensions, helper tables)
         dashboard/dashboard_data.json   aggregated data for the HTML dashboard
Deterministic (no randomness). Money is in currency units.
"""
import json
import numpy as np
import pandas as pd

from config import DASHBOARD, DATA as S1, OUTPUTS

PBI = DASHBOARD / "powerbi"
HTML = DASHBOARD
PBI.mkdir(parents=True, exist_ok=True)
HTML.mkdir(parents=True, exist_ok=True)
AS_OF = pd.Timestamp("2020-02-29")
TOP_N_PER_QUADRANT_HTML = 150  # at-risk list rows per quadrant embedded in the HTML dashboard

# Plays per value x risk quadrant (Phase 7 section 4) and for lapsed buyers not scored for Mar-Apr.
PLAYS = pd.DataFrame([
    ("Save now (high value, high risk)", 1, "Personalised win-back with a 10% offer (WhatsApp/push, email fallback)", "CRM / Retention"),
    ("Protect (high value, lower risk)", 2, "Loyalty perks and early access; no discount", "CRM / Loyalty"),
    ("Grow (lower value, lower risk)", 3, "Cross-sell bundles to lift basket size", "Merchandising"),
    ("Automate (lower value, high risk)", 4, "Automated replenishment / saved-cart nudge; no discount", "Marketing automation"),
    ("Lapsed (no order Dec-Feb)", 5, "Low-cost reactivation only; suppress from paid offers", "Marketing automation"),
], columns=["value_risk_quadrant", "quadrant_sort", "recommended_action", "action_owner"])


def date_key(s: pd.Series) -> pd.Series:
    return s.dt.strftime("%Y%m%d").astype(int)


# ------------------------------------------------------------------ fact_orders
orders = pd.read_csv(S1 / "orders.csv", parse_dates=["order_ts"]).sort_values(["user_id", "order_ts", "order_id"])
orders["order_seq"] = orders.groupby("user_id").cumcount() + 1
fact_orders = pd.DataFrame({
    "order_id": orders.order_id,
    "customer_key": orders.user_id,
    "date_key": date_key(orders.order_ts),
    "order_datetime_utc": orders.order_ts.dt.strftime("%Y-%m-%d %H:%M:%S"),
    "order_hour_utc": orders.order_ts.dt.hour,
    "items": orders["items"],
    "distinct_products": orders.distinct_products,
    "distinct_brands": orders.distinct_brands,
    "order_value": orders.order_value,
    "order_seq": orders.order_seq,
    "is_first_order": (orders.order_seq == 1).astype(int),
})
assert fact_orders.order_id.is_unique

# ------------------------------------------------------------------ dim_customer (all 110,518 buyers)
g = orders.groupby("user_id")
cust = pd.DataFrame({
    "first_order_date": g.order_ts.min().dt.date,
    "last_order_date": g.order_ts.max().dt.date,
    "acquisition_month": g.order_ts.min().dt.to_period("M").astype(str),
    "orders_oct_feb": g.size(),
    "revenue_oct_feb": g.order_value.sum().round(2),
})
cust["aov_oct_feb"] = (cust.revenue_oct_feb / cust.orders_oct_feb).round(2)
cust["october_cohort_left_censored"] = (cust.acquisition_month == "2019-10").astype(int)

status = pd.read_csv(OUTPUTS / "phase3/customer_status_by_user.csv").set_index("user_id")
cust["days_since_last_order"] = status.days_since_last_order
cust["status_feb29"] = status.status

ucf = pd.read_csv(S1 / "user_churn_features.csv", usecols=["user_id", "n_orders", "churned", "top_purchased_brand"]).set_index("user_id")
cust["in_churn_cohort_oct_dec"] = cust.index.isin(ucf.index).astype(int)
cust["orders_oct_dec"] = ucf.n_orders              # blank outside the Oct-Dec cohort
cust["orders_oct_dec_band"] = ucf.n_orders.clip(upper=4).map({1: "1", 2: "2", 3: "3", 4: "4+"})
cust["churned_jan_feb"] = ucf.churned            # blank for buyers acquired in Jan-Feb (not in the cohort)
cust["top_purchased_brand"] = ucf.top_purchased_brand

rfm = pd.read_csv(OUTPUTS / "phase4/rfm_by_user.csv").set_index("user_id")
cust["rfm_segment"] = rfm.segment
cust["rfm_score"] = (rfm.r.astype(str) + rfm.f.astype(str) + rfm.m.astype(str))
oof = pd.read_csv(OUTPUTS / "phase6/oof_churn_scores_oct_dec_cohort.csv").set_index("user_id")
cust["churn_score_oct_dec_oof"] = oof.churn_score

vr = pd.read_csv(OUTPUTS / "phase7/current_buyers_value_risk.csv").set_index("user_id")
assert vr.clv_90d.notna().all(), "Phase 7 CLV has blanks; re-run src/p7_clv_economics.py"
cust["current_buyer_dec_feb"] = cust.index.isin(vr.index).astype(int)
cust["aov_dec_feb"] = vr.aov
cust["churn_score_mar_apr"] = vr.churn_score_mar_apr
cust["risk_tier_mar_apr"] = vr.risk_tier
cust["revenue_at_risk_mar_apr"] = vr.revenue_at_risk
cust["value_if_retained_60d"] = vr.value_if_retained_60d
clv = pd.read_csv(OUTPUTS / "phase7/clv_90d_all_buyers.csv").set_index("user_id")
cust["clv_90d_predicted"] = clv.clv_90d
cust["p_alive"] = clv.p_alive.round(4)
cust["value_risk_quadrant"] = vr.quadrant
cust["value_risk_quadrant"] = cust.value_risk_quadrant.fillna("Lapsed (no order Dec-Feb)")
cust = cust.reset_index().rename(columns={"user_id": "customer_key"}).merge(PLAYS, on="value_risk_quadrant", how="left")
# Action priority: quadrant order first, then revenue at risk (highest first); lapsed buyers by Oct-Feb revenue.
cust["_rar"] = cust.revenue_at_risk_mar_apr.fillna(-1)
cust = cust.sort_values(["quadrant_sort", "_rar", "revenue_oct_feb", "customer_key"],
                        ascending=[True, False, False, True]).drop(columns="_rar")
cust["action_priority_rank"] = np.arange(1, len(cust) + 1)
assert len(cust) == orders.user_id.nunique()

# ------------------------------------------------------------------ dim_brand + fact_brand_monthly
bm = pd.read_csv(S1 / "brand_monthly_funnel.csv", parse_dates=["month"])
bt = bm.groupby("brand").agg(views=("views", "sum"), purchase_items=("purchase_items", "sum"),
                             revenue=("revenue", "sum")).reset_index()
bt = bt.sort_values(["revenue", "brand"], ascending=[False, True]).reset_index(drop=True)
bt["brand_key"] = np.arange(1, len(bt) + 1)
named_rank = bt.loc[bt.brand != "unknown", "revenue"].rank(ascending=False, method="first")
bt["revenue_rank_named"] = named_rank.astype("Int64")
bt["brand_tier"] = np.select([bt.brand == "unknown", (bt.revenue_rank_named <= 10).fillna(False).astype(bool), (bt.revenue_rank_named <= 50).fillna(False).astype(bool)],
                             ["Missing brand", "Top 10", "Top 11-50"], "Long tail")
dim_brand = bt[["brand_key", "brand", "brand_tier", "revenue_rank_named"]].assign(
    is_missing_brand=(bt.brand == "unknown").astype(int))
fact_brand_monthly = bm.merge(dim_brand[["brand_key", "brand"]], on="brand")
fact_brand_monthly.insert(0, "month_date_key", date_key(fact_brand_monthly.month))
fact_brand_monthly = fact_brand_monthly.drop(columns=["month", "brand"])

# ------------------------------------------------------------------ dim_date + fact_daily_kpis
dates = pd.date_range("2019-10-01", "2020-02-29", freq="D")
dim_date = pd.DataFrame({
    "date_key": date_key(pd.Series(dates)), "date": dates.date, "year": dates.year,
    "month_num": dates.month, "month_name": dates.strftime("%b"), "year_month": dates.strftime("%Y-%m"),
    "month_start": dates.to_period("M").start_time.date,
    "month_sort": (dates.year - 2019) * 12 + dates.month,         # Oct 2019 = 22 ... Feb 2020 = 26
    "week_start_mon": (dates - pd.to_timedelta(dates.dayofweek, unit="D")).date,
    "day_of_week": dates.strftime("%a"), "dow_sort": dates.dayofweek + 1,
    "is_weekend": (dates.dayofweek >= 5).astype(int),
    "is_holiday_season": ((dates >= "2019-11-25") & (dates <= "2019-12-31")).astype(int),
    "period": np.where(dates < "2020-01-01", "Observation (Oct-Dec)", "Outcome (Jan-Feb)"),
})
daily = pd.read_csv(S1 / "daily_kpis.csv", parse_dates=["date"])
fact_daily_kpis = daily.assign(date_key=date_key(daily.date)).drop(columns="date")
fact_daily_kpis = fact_daily_kpis[["date_key"] + [c for c in fact_daily_kpis.columns if c != "date_key"]]
assert set(fact_daily_kpis.date_key) <= set(dim_date.date_key) and set(fact_orders.date_key) <= set(dim_date.date_key)

sess_m = pd.read_csv(S1 / "session_summary.csv", parse_dates=["month"])
fact_session_monthly = sess_m.assign(month_date_key=date_key(sess_m.month)).drop(columns=["month", "avg_session_minutes"])
fact_session_monthly = fact_session_monthly[["month_date_key"] + [c for c in fact_session_monthly.columns if c != "month_date_key"]]

# ------------------------------------------------------------------ helper tables (sort orders, scenario tables)
dim_rfm = pd.read_csv(OUTPUTS / "phase4/rfm_segments.csv")[["segment"]].rename(columns={"segment": "rfm_segment"})
dim_rfm["segment_sort"] = np.arange(1, len(dim_rfm) + 1)
dim_risk = pd.DataFrame({"risk_tier_mar_apr": ["Low (<0.60)", "Medium (0.60-0.80)", "High (0.80-0.90)", "Very high (>=0.90)"],
                         "risk_sort": [1, 2, 3, 4]})
dim_status = pd.DataFrame({"status_feb29": ["Active", "At-Risk", "Churned"], "status_sort": [1, 2, 3],
                           "rule": ["<=38 days since last order", "38-64 days", ">64 days"]})
assert set(cust.status_feb29.unique()) == set(dim_status.status_feb29), cust.status_feb29.unique()
campaign = pd.read_csv(OUTPUTS / "phase7/campaign_strategies.csv").rename(columns={"Unnamed: 0": "strategy"})
sens = pd.read_csv(OUTPUTS / "phase7/roi_sensitivity_save_rate_x_margin.csv").rename(columns={"Unnamed: 0": "save_rate"})
sens_long = sens.melt(id_vars="save_rate", var_name="gross_margin", value_name="roi")

shap_tbl = pd.read_csv(OUTPUTS / "phase6/shap_importance.csv")[["feature", "mean_abs_shap"]].head(15)

tables = dict(fact_orders=fact_orders, dim_customer=cust, dim_brand=dim_brand, fact_brand_monthly=fact_brand_monthly,
              dim_date=dim_date, fact_daily_kpis=fact_daily_kpis, fact_session_monthly=fact_session_monthly, dim_rfm_segment=dim_rfm, dim_risk_tier=dim_risk,
              dim_status=dim_status, dim_quadrant=PLAYS, campaign_strategies=campaign, roi_sensitivity=sens_long, shap_drivers=shap_tbl)
for name, df in tables.items():
    df.to_csv(PBI / f"{name}.csv", index=False)
    print(f"{name:22s} {len(df):>8,} rows  {df.shape[1]:>3} cols")

# ------------------------------------------------------------------ reconciliation checks
assert round(fact_orders.order_value.sum(), 2) == round(cust.revenue_oct_feb.sum(), 2)
print("revenue fact_orders", round(fact_orders.order_value.sum(), 2), "| dim_customer", round(cust.revenue_oct_feb.sum(), 2))
print("revenue at risk", round(cust.revenue_at_risk_mar_apr.sum(), 2), "| scored buyers", int(cust.current_buyer_dec_feb.sum()))

# ------------------------------------------------------------------ HTML dashboard bundle
P2 = OUTPUTS / "phase2"
monthly = pd.read_csv(P2 / "q01_monthly_kpis_mom.csv")
funnel_m = pd.read_csv(OUTPUTS / "phase4/funnel_by_month.csv")
sess = pd.read_csv(S1 / "session_summary.csv")
aband = pd.read_csv(P2 / "q09_cart_abandonment_trend.csv")
nvr = pd.read_csv(P2 / "q03_new_vs_returning_buyers.csv")
churn_orders = pd.read_csv(P2 / "q11_churn_by_order_count.csv")
rfm_seg = pd.read_csv(OUTPUTS / "phase4/rfm_segments.csv")
status_seg = pd.read_csv(OUTPUTS / "phase3/customer_status_segments.csv")
shap = pd.read_csv(OUTPUTS / "phase6/shap_importance.csv").head(10)
tiers = pd.read_csv(OUTPUTS / "phase6/current_risk_tiers_mar_apr.csv")
quad = pd.read_csv(OUTPUTS / "phase7/value_risk_matrix.csv")
brands = pd.read_csv(OUTPUTS / "phase4/top15_brands_by_views.csv")
cohort_b = pd.read_csv(OUTPUTS / "phase4/cohort_retention_buyers_pct.csv")
hyp = pd.read_csv(OUTPUTS / "phase5/hypothesis_results.csv")

sn = cust[cust.value_risk_quadrant == "Save now (high value, high risk)"]
top = cust[cust.current_buyer_dec_feb == 1].groupby("value_risk_quadrant", sort=False).head(TOP_N_PER_QUADRANT_HTML)
action_cols = ["action_priority_rank", "customer_key", "value_risk_quadrant", "risk_tier_mar_apr", "churn_score_mar_apr",
               "clv_90d_predicted", "revenue_at_risk_mar_apr", "orders_oct_feb", "revenue_oct_feb",
               "days_since_last_order", "status_feb29", "recommended_action", "action_owner"]

bundle = {
    "monthly": monthly.to_dict("records"),
    "daily": daily.assign(date=daily.date.dt.strftime("%Y-%m-%d"))[["date", "revenue", "buyers", "views", "carts", "purchase_items"]].to_dict("records"),
    "funnel_monthly": funnel_m.to_dict("records"),
    "funnel_totals": {"views": int(daily.views.sum()), "carts": int(daily.carts.sum()), "purchase_items": int(daily.purchase_items.sum())},
    "sessions": {"sessions": int(sess.sessions.sum()), "with_cart": int(sess.sessions_with_cart.sum()),
                 "with_purchase": int(sess.sessions_with_purchase.sum()), "abandoned": int(sess.abandoned_cart_sessions.sum())},
    "abandonment": aband.to_dict("records"),
    "new_vs_returning": nvr.to_dict("records"),
    "churn_by_orders": churn_orders.to_dict("records"),
    "rfm_segments": rfm_seg.to_dict("records"),
    "status": status_seg.to_dict("records"),
    "shap": shap.to_dict("records"),
    "risk_tiers": tiers.to_dict("records"),
    "quadrants": quad.to_dict("records"),
    "campaign": campaign.to_dict("records"),
    "brands": brands.to_dict("records"),
    "cohort_buyers": cohort_b.to_dict("records"),
    "hypotheses": hyp.to_dict("records"),
    "action_list": top[action_cols].replace({np.nan: None}).to_dict("records"),
    "action_list_total": int(cust.current_buyer_dec_feb.sum()),
    # Sufficient statistics for the Save-now what-if (Phase 7 campaign maths, any save rate s / margin m):
    # incremental revenue = s*A; cost = 0.10*(s*B + C) + 0.50*n
    "save_now_stats": {k: float(v) for k, v in {
        "A": (sn.churn_score_mar_apr * sn.value_if_retained_60d).sum(),
        "B": (sn.aov_dec_feb * sn.churn_score_mar_apr).sum(),
        "C": (sn.aov_dec_feb * (1 - sn.churn_score_mar_apr)).sum(),
        "n": len(sn)}.items()},
}
json.dump(bundle, open(HTML / "dashboard_data.json", "w"), default=lambda o: o.item() if hasattr(o, "item") else str(o))
print("dashboard_data.json", round((HTML / "dashboard_data.json").stat().st_size / 1e3), "KB")
