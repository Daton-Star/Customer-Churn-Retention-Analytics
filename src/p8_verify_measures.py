"""Phase 8b: recompute every DAX measure in the Power BI guide with pandas, from the exported CSVs only.

This proves the star schema reproduces the Key Numbers before anyone opens Power BI.
Output: dashboard/powerbi/measure_expected_values.csv (measure, expected value at report level, Key Numbers id).
"""
import pandas as pd

from config import DASHBOARD

PBI = DASHBOARD / "powerbi"
fo = pd.read_csv(PBI / "fact_orders.csv")
dc = pd.read_csv(PBI / "dim_customer.csv", low_memory=False)
dk = pd.read_csv(PBI / "fact_daily_kpis.csv")
ss = pd.read_csv(PBI / "fact_session_monthly.csv")

SAVE_NOW = "Save now (high value, high risk)"
CONTACT, DISCOUNT, MARGIN, SAVE = 0.50, 0.10, 0.40, 0.10    # Phase 7 ASSUMPTIONS [K134]

rev, n_ord, buyers = fo.order_value.sum(), len(fo), fo.customer_key.nunique()
orders_per = fo.groupby("customer_key").size()
coh = dc[dc.in_churn_cohort_oct_dec == 1]
sn = dc[dc.value_risk_quadrant == SAVE_NOW]
p, V, aov = sn.churn_score_mar_apr, sn.value_if_retained_60d, sn.aov_dec_feb
inc_rev = (SAVE * p * V).sum()
cost = (DISCOUNT * aov * (SAVE * p + (1 - p))).sum() + CONTACT * len(sn)
net = MARGIN * inc_rev - cost

be = (DISCOUNT * (aov * (1 - p)).sum() + CONTACT * len(sn)) / (MARGIN * (p * V).sum() - DISCOUNT * (aov * p).sum())
churn_by_orders = coh.assign(b=coh.orders_oct_dec.clip(upper=4)).groupby("b").churned_jan_feb.mean()

rows = [
    ("Total Revenue", round(rev, 2), "K14"),
    ("Total Orders", n_ord, "K12"),
    ("Buyers", buyers, "K13"),
    ("AOV", round(rev / n_ord, 2), "K15"),
    ("Orders per Buyer", round(n_ord / buyers, 3), "K16"),
    ("Repeat Purchase Rate", f"{100 * (orders_per >= 2).mean():.2f}%", "K17"),
    ("Cart to View %", f"{100 * dk.carts.sum() / dk.views.sum():.2f}%", "K28"),
    ("Purchase per Cart %", f"{100 * dk.purchase_items.sum() / dk.carts.sum():.2f}%", "K29"),
    ("Cart Abandonment %", f"{100 * ss.abandoned_cart_sessions.sum() / ss.sessions_with_cart.sum():.2f}%", "K30"),
    ("Session Conversion %", f"{100 * ss.sessions_with_purchase.sum() / ss.sessions.sum():.2f}%", "K31"),
    ("Churn Cohort Buyers", len(coh), "K18"),
    ("Churned Buyers", int(coh.churned_jan_feb.sum()), "K19"),
    ("Churn Rate", f"{100 * coh.churned_jan_feb.mean():.2f}%", "K20"),
    ("Scored Current Buyers", int(dc.current_buyer_dec_feb.sum()), "K117"),
    ("Expected Churners Mar-Apr", round(dc.churn_score_mar_apr.sum(), 1), "K142 (K117 = 58632.95 from unrounded scores)"),
    ("Revenue at Risk", round(dc.revenue_at_risk_mar_apr.sum(), 2), "K130 (3508675.24 before 4-decimal CSV rounding)"),
    ("Predicted CLV 90d", round(dc.clv_90d_predicted.sum(), 2), "K128 (1849732.14 before 4-decimal CSV rounding)"),
    ("Save-now Buyers", len(sn), "K132"),
    ("Save-now Revenue at Risk", round(sn.revenue_at_risk_mar_apr.sum(), 2), "K132"),
    ("Active / At-Risk / Churned buyers (Feb 29)",
     " / ".join(str(int((dc.status_feb29 == s).sum())) for s in ["Active", "At-Risk", "Churned"]), "K73-K75"),
    ("Save-now Campaign Net Profit (save rate 10%)", round(net, 2), "K135"),
    ("Save-now Campaign ROI (save rate 10%)", f"{100 * net / cost:+.1f}%", "K135"),
    ("Save-now Break-even Save Rate", f"{100 * be:.2f}%", "K136"),
    ("Churn Rate by Oct-Dec orders 1 / 2 / 3 / 4+", " / ".join(f"{100 * v:.2f}%" for v in churn_by_orders), "K48"),
]
out = pd.DataFrame(rows, columns=["measure", "expected_value", "key_numbers_id"])
out.to_csv(PBI / "measure_expected_values.csv", index=False)
print(out.to_string(index=False))
