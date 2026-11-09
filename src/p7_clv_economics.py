"""Phase 7: customer value & retention economics.

 A. Historical CLV (spend to date) overall and by RFM segment
 B. BG/NBD (purchase frequency / dropout) fitted on Oct-Dec 2019, validated on Jan-Feb 2020 holdout
 C. Gamma-Gamma (spend per order) on repeat buyers; predicted vs actual holdout spend
 D. Refit on Oct 2019-Feb 2020 -> predicted 90-day CLV for every buyer as of 29 Feb 2020
 E. Value x risk matrix for current buyers (Phase 6 calibrated churn probabilities)
 F. Revenue at risk for Mar-Apr 2020
 G. Retention campaign simulation: cost, save rate (benchmark range), ROI, break-even, sensitivity
 H. A/B test design (power-based sample size) for the top recommendation
Assumptions are labelled ASSUMPTION and are parameters, not data. Run: python src/p7_clv_economics.py [data_dir]
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from lifetimes import BetaGeoFitter, GammaGammaFitter
from lifetimes.utils import calibration_and_holdout_data
from scipy import stats
from scipy.special import hyp2f1
from sklearn.metrics import roc_auc_score

from viz_style import AQUA, BLUE, GRAY, INK, INK2, ORANGE, SEQ_BLUE, SURFACE, plt, save, title  # noqa: E402
from config import DATA as DEFAULT_DATA, IMAGES, OUTPUTS  # noqa: E402

DATA = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DATA
OUT, CH = OUTPUTS / "phase7", IMAGES / "phase7"
OUT.mkdir(parents=True, exist_ok=True); CH.mkdir(parents=True, exist_ok=True)
K = {}  # key numbers for this phase -> outputs/phase7/phase7_numbers.json

# ---------------------------------------------------------------- ASSUMPTIONS (campaign economics)
CONTACT_COST = 0.50      # ASSUMPTION: blended cost per targeted customer (WhatsApp/push/email), currency units
DISCOUNT = 0.10          # ASSUMPTION: 10% off the next order
GROSS_MARGIN = 0.40      # ASSUMPTION: gross margin on incremental revenue (sensitivity 30-50%)
SAVE_RATE = 0.10         # Base save rate = low end of the cited 10-30% win-back range [B7]; sensitivity 2.5-30%
HIGH_VALUE_PCTL = 0.70   # top 30% of predicted CLV = "high value"
HIGH_RISK = 0.80         # calibrated churn probability >= 0.80 = "high risk" (Phase 6 High/Very high tiers)

orders = pd.read_csv(DATA / "orders.csv", parse_dates=["order_ts"])
orders["day"] = orders.order_ts.dt.floor("D")
ucf = pd.read_csv(DATA / "user_churn_features.csv")

# ---------------------------------------------------------------- A. Historical CLV
hist = orders.groupby("user_id").agg(orders=("order_id", "count"), spend=("order_value", "sum"))
K["hist_clv_mean"] = hist.spend.mean(); K["hist_clv_median"] = hist.spend.median()
K["hist_clv_p90"] = hist.spend.quantile(0.9); K["hist_clv_buyers"] = len(hist)
rfm = pd.read_csv(OUTPUTS / "phase4" / "rfm_by_user.csv")
seg_clv = rfm.merge(hist, left_on="user_id", right_index=True).groupby("segment").agg(
    buyers=("user_id", "count"), avg_clv_oct_feb=("spend", "mean"), median_clv=("spend", "median"),
    total_clv=("spend", "sum")).sort_values("avg_clv_oct_feb", ascending=False)
seg_clv.round(2).to_csv(OUT / "historical_clv_by_rfm_segment.csv")
print(seg_clv.round(2))

# ---------------------------------------------------------------- B. BG/NBD calibration vs holdout
# lifetimes counts repeat purchase DAYS (several orders on one day count once); T and recency in days.
cal = calibration_and_holdout_data(orders, "user_id", "day", calibration_period_end="2019-12-31",
                                   observation_period_end="2020-02-29", freq="D", monetary_value_col="order_value")
bgf = BetaGeoFitter(penalizer_coef=0.001).fit(cal.frequency_cal, cal.recency_cal, cal.T_cal)
cal["pred_purchases_holdout"] = bgf.conditional_expected_number_of_purchases_up_to_time(
    60, cal.frequency_cal, cal.recency_cal, cal.T_cal)
cal["p_alive"] = bgf.conditional_probability_alive(cal.frequency_cal, cal.recency_cal, cal.T_cal)
actual_spend = orders[orders.order_ts >= "2020-01-01"].groupby("user_id").order_value.sum()
cal["actual_spend_holdout"] = actual_spend.reindex(cal.index).fillna(0)
cal["bought_holdout"] = (cal.frequency_holdout > 0).astype(int)
K.update(bgnbd_params=bgf.params_.round(4).to_dict(),
         holdout_pred_purchase_days=cal.pred_purchases_holdout.sum(), holdout_actual_purchase_days=cal.frequency_holdout.sum(),
         holdout_mae_purchases=np.mean(np.abs(cal.pred_purchases_holdout - cal.frequency_holdout)),
         holdout_corr_purchases=np.corrcoef(cal.pred_purchases_holdout, cal.frequency_holdout)[0, 1],
         auc_expected_purchases_vs_any_holdout_purchase=roc_auc_score(cal.bought_holdout, cal.pred_purchases_holdout))
cal["f_bucket"] = cal.frequency_cal.clip(upper=5).astype(int).astype(str).replace("5", "5+")
fb = cal.groupby("f_bucket").agg(buyers=("T_cal", "size"), predicted=("pred_purchases_holdout", "mean"),
                                 actual=("frequency_holdout", "mean"))
fb.round(4).to_csv(OUT / "bgnbd_holdout_by_frequency.csv")
print(fb.round(3)); print({k: K[k] for k in list(K)[-5:]})

fig, ax = plt.subplots(figsize=(8, 4))
x = np.arange(len(fb)); w = 0.38
ax.bar(x - w / 2, fb.predicted, w - 0.03, color=BLUE, label="BG/NBD predicted")
ax.bar(x + w / 2, fb.actual, w - 0.03, color=ORANGE, label="Actual (Jan-Feb holdout)")
ax.set_xticks(x, fb.index); ax.set_xlabel("Repeat purchase days in Oct-Dec (calibration)")
ax.set_ylabel("Avg purchase days in Jan-Feb"); ax.legend(loc="upper left"); ax.grid(axis="x", visible=False)
title(ax, "BG/NBD calibration (Oct-Dec) vs holdout (Jan-Feb)",
      f"Total predicted {K['holdout_pred_purchase_days']:,.0f} vs actual {K['holdout_actual_purchase_days']:,.0f} purchase days")
save(fig, CH / "p7_01_bgnbd_holdout.png")

# ---------------------------------------------------------------- C. Gamma-Gamma
rep = cal[(cal.frequency_cal > 0) & (cal.monetary_value_cal > 0)]
K["gg_freq_monetary_corr"] = np.corrcoef(rep.frequency_cal, rep.monetary_value_cal)[0, 1]  # assumption check (~0)
ggf = GammaGammaFitter(penalizer_coef=0.001).fit(rep.frequency_cal, rep.monetary_value_cal)
pop_aov = ggf.conditional_expected_average_profit(pd.Series([0]), pd.Series([0.0])).iloc[0]
cal["exp_aov"] = np.where(cal.frequency_cal > 0,
                          ggf.conditional_expected_average_profit(cal.frequency_cal, cal.monetary_value_cal.clip(lower=0.01)),
                          pop_aov)
cal["pred_spend_holdout"] = cal.pred_purchases_holdout * cal.exp_aov
K.update(gg_params=ggf.params_.round(4).to_dict(), gg_population_aov=pop_aov,
         holdout_pred_spend=cal.pred_spend_holdout.sum(), holdout_actual_spend=cal.actual_spend_holdout.sum(),
         holdout_spend_corr=np.corrcoef(cal.pred_spend_holdout, cal.actual_spend_holdout)[0, 1],
         holdout_spend_spearman=stats.spearmanr(cal.pred_spend_holdout, cal.actual_spend_holdout).correlation)
cal["dec"] = pd.qcut(cal.pred_spend_holdout.rank(method="first"), 10, labels=False) + 1
dd = cal.groupby("dec").agg(predicted=("pred_spend_holdout", "sum"), actual=("actual_spend_holdout", "sum"))
dd.round(2).to_csv(OUT / "clv_holdout_by_decile.csv")
K["top_decile_actual_spend_share"] = dd.actual.iloc[-1] / dd.actual.sum()
cal.reset_index().round(4).to_csv(OUT / "bgnbd_calibration_holdout_by_user.csv", index=False)
fig, ax = plt.subplots(figsize=(8, 4))
x = np.arange(1, 11)
ax.bar(x - 0.2, dd.predicted / 1e3, 0.37, color=BLUE, label="Predicted (BG/NBD x Gamma-Gamma)")
ax.bar(x + 0.2, dd.actual / 1e3, 0.37, color=ORANGE, label="Actual")
ax.set_xticks(x); ax.set_xlabel("Predicted-CLV decile (10 = highest)"); ax.set_ylabel("Jan-Feb spend (thousands)")
ax.legend(loc="upper left"); ax.grid(axis="x", visible=False)
title(ax, "60-day CLV: predicted vs actual holdout spend by decile",
      f"Top predicted decile delivers {100*K['top_decile_actual_spend_share']:.1f}% of actual Jan-Feb spend")
save(fig, CH / "p7_02_clv_holdout_deciles.png")

def expected_purchases(model, t, x, recency, T):
    """BG/NBD E[purchases in (T, T+t] | x, recency, T] (Fader, Hardie & Lee 2005, eq. 10).
    lifetimes takes log(hyp2f1(...)), which is NaN when the term is negative: here that happens for
    one-time buyers with T <= 50 days (a + b - 1 < 0). Same formula, evaluated without the log."""
    r, alpha, a, b = (model.params_[k] for k in ("r", "alpha", "a", "b"))
    x, recency, T = (np.asarray(v, dtype=float) for v in (x, recency, T))
    hyp = hyp2f1(r + x, b + x, a + b + x - 1, t / (alpha + T + t))
    num = (a + b + x - 1) / (a - 1) * (1 - hyp * ((alpha + T) / (alpha + t + T)) ** (r + x))
    den = 1 + (x > 0) * (a / (b + x - 1)) * ((alpha + T) / (alpha + recency)) ** (r + x)
    return num / den


# ---------------------------------------------------------------- D. Full-period refit -> 90-day CLV
# Built by hand: lifetimes' summary_data_from_transaction_data mis-computes recency/T on current pandas.
# Same definitions: purchases aggregated per day; frequency = repeat days; recency = last - first day;
# T = end - first day; monetary = mean daily spend over repeat days (first day excluded).
daily = orders.groupby(["user_id", "day"]).order_value.sum().reset_index()
END = pd.Timestamp("2020-02-29")
first_day = daily.groupby("user_id").day.transform("min")
daily["is_repeat"] = daily.day > first_day
g = daily.groupby("user_id")
full = pd.DataFrame({"frequency": g.size() - 1,
                     "recency": (g.day.max() - g.day.min()).dt.days.astype(float),
                     "T": (END - g.day.min()).dt.days.astype(float)})
full["monetary_value"] = daily[daily.is_repeat].groupby("user_id").order_value.mean().reindex(full.index).fillna(0)
bgf_f = BetaGeoFitter(penalizer_coef=0.001).fit(full.frequency, full.recency, full["T"])
repf = full[(full.frequency > 0) & (full.monetary_value > 0)]
ggf_f = GammaGammaFitter(penalizer_coef=0.001).fit(repf.frequency, repf.monetary_value)
pop_aov_f = ggf_f.conditional_expected_average_profit(pd.Series([0]), pd.Series([0.0])).iloc[0]
full["p_alive"] = bgf_f.conditional_probability_alive(full.frequency, full.recency, full["T"])
full["pred_purchases_90d"] = expected_purchases(bgf_f, 90, full.frequency, full.recency, full["T"])
full["exp_aov"] = np.where(full.frequency > 0, ggf_f.conditional_expected_average_profit(
    full.frequency, full.monetary_value.clip(lower=0.01)), pop_aov_f)
full["clv_90d"] = full.pred_purchases_90d * full.exp_aov          # undiscounted 90-day horizon
assert full.clv_90d.notna().all(), "NaN CLV"
full = full.join(hist)
full.reset_index().round(4).to_csv(OUT / "clv_90d_all_buyers.csv", index=False)
K.update(full_buyers=len(full), clv90_total=full.clv_90d.sum(), clv90_mean=full.clv_90d.mean(),
         clv90_median=full.clv_90d.median(), bgnbd_full_params=bgf_f.params_.round(4).to_dict())

# ---------------------------------------------------------------- E/F. Value x risk, revenue at risk
cur = pd.read_csv(OUTPUTS / "phase6" / "current_buyers_churn_scores_mar_apr.csv")
cur = cur.merge(full[["clv_90d", "p_alive"]], left_on="user_id", right_index=True, how="left")
# Value if retained (Mar-Apr): own Dec-Feb AOV x average 60-day orders of historically retained buyers
retained_orders_60d = ucf.loc[ucf.churned == 0, "future_orders"].mean()
K["retained_avg_orders_60d"] = retained_orders_60d
cur["value_if_retained_60d"] = cur.aov * retained_orders_60d
cur["revenue_at_risk"] = cur.churn_score_mar_apr * cur.value_if_retained_60d
v_cut = cur.clv_90d.quantile(HIGH_VALUE_PCTL)
K["high_value_cutoff_clv90"] = v_cut
hv, hr = cur.clv_90d >= v_cut, cur.churn_score_mar_apr >= HIGH_RISK
cur["quadrant"] = np.select([hv & hr, hv & ~hr, ~hv & ~hr], ["Save now (high value, high risk)",
                            "Protect (high value, lower risk)", "Grow (lower value, lower risk)"],
                            "Automate (lower value, high risk)")
quad = cur.groupby("quadrant").agg(buyers=("user_id", "count"), avg_churn_prob=("churn_score_mar_apr", "mean"),
                                   clv_90d=("clv_90d", "sum"), dec_feb_spend=("total_spend", "sum"),
                                   revenue_at_risk=("revenue_at_risk", "sum"))
quad["rar_share"] = quad.revenue_at_risk / quad.revenue_at_risk.sum()
quad.round(4).to_csv(OUT / "value_risk_matrix.csv")
cur.round(4).to_csv(OUT / "current_buyers_value_risk.csv", index=False)
K.update(rar_total=cur.revenue_at_risk.sum(), current_buyers=len(cur),
         value_if_retained_total=cur.value_if_retained_60d.sum())
print(quad.round(3)); print("revenue at risk", K["rar_total"])

fig, ax = plt.subplots(figsize=(8.5, 6.4))
smp = cur.sample(12000, random_state=42)
qc = {"Save now (high value, high risk)": ORANGE, "Protect (high value, lower risk)": AQUA,
      "Grow (lower value, lower risk)": BLUE, "Automate (lower value, high risk)": GRAY}
for q_, c_ in qc.items():
    s_ = smp[smp.quadrant == q_]
    ax.scatter(s_.churn_score_mar_apr, s_.clv_90d.clip(upper=cur.clv_90d.quantile(0.995)), s=9, color=c_, alpha=0.5,
               label=f"{q_}: {quad.loc[q_, 'buyers']:,.0f} buyers, {100*quad.loc[q_, 'rar_share']:.0f}% of revenue at risk")
ax.axvline(HIGH_RISK, color=INK2, linestyle="--", linewidth=1); ax.axhline(v_cut, color=INK2, linestyle="--", linewidth=1)
ax.set_xlabel("Churn probability, Mar-Apr 2020 (calibrated)"); ax.set_ylabel("Predicted 90-day CLV (currency units)")
ax.legend(loc="upper left", bbox_to_anchor=(0, -0.14), fontsize=8.5, markerscale=2, ncols=1)
title(ax, "Value x risk matrix: 69,116 current buyers (12,000-point sample shown)",
      "Fund retention where value and risk are both high")
save(fig, CH / "p7_03_value_risk_matrix.png")

# ---------------------------------------------------------------- G. Campaign simulation
def campaign(df, s=SAVE_RATE, m=GROSS_MARGIN, c=CONTACT_COST, d=DISCOUNT):
    p, V, aov = df.churn_score_mar_apr.values, df.value_if_retained_60d.values, df.aov.values
    inc_rev = (s * p * V).sum()
    disc_cost = (d * aov * (s * p + (1 - p))).sum()     # discount used by savers AND by buyers who'd buy anyway
    contact = c * len(df)
    cost = disc_cost + contact
    net = m * inc_rev - cost
    be = (d * aov * (1 - p) + c).sum() / (p * (m * V - d * aov)).sum()   # break-even save rate
    return dict(targeted=len(df), expected_saves=(s * p).sum(), incremental_revenue=inc_rev,
                incremental_gross_profit=m * inc_rev, discount_cost=disc_cost, contact_cost=contact,
                total_cost=cost, net_profit=net, roi=net / cost, break_even_save_rate=be)


strategies = {
    "Save now quadrant (high value, high risk)": cur[cur.quadrant.str.startswith("Save now")],
    "All high-value buyers (top 30% CLV)": cur[hv],
    "All high-risk buyers (p >= 0.80)": cur[hr],
    "Everyone (69,116 buyers)": cur,
}
sim = pd.DataFrame({k: campaign(v) for k, v in strategies.items()}).T
sim.round(4).to_csv(OUT / "campaign_strategies.csv")
print(sim.round(3).T)
target = strategies["Save now quadrant (high value, high risk)"]
save_rates = [0.025, 0.05, 0.075, 0.10, 0.15, 0.20, 0.30]
margins = [0.30, 0.40, 0.50]
sens = pd.DataFrame({f"margin {int(m*100)}%": [campaign(target, s=s, m=m)["roi"] for s in save_rates] for m in margins},
                    index=[f"save {s:.1%}" for s in save_rates])
sens.round(4).to_csv(OUT / "roi_sensitivity_save_rate_x_margin.csv")
sens_cost = pd.DataFrame({f"contact {c:.2f}": [campaign(target, c=c, d=d)["roi"] for d in (0.05, 0.10, 0.15, 0.20)]
                          for c in (0.10, 0.50, 1.00)}, index=["discount 5%", "discount 10%", "discount 15%", "discount 20%"])
sens_cost.round(4).to_csv(OUT / "roi_sensitivity_offer_x_contact.csv")
print(sens.round(3)); print(sens_cost.round(3))

fig, ax = plt.subplots(figsize=(7.5, 4.2))
im = ax.imshow(sens.values, cmap="RdBu", vmin=-max(abs(sens.values.min()), sens.values.max()),
               vmax=max(abs(sens.values.min()), sens.values.max()), aspect="auto")
for i in range(sens.shape[0]):
    for j in range(sens.shape[1]):
        v = sens.values[i, j]
        ax.text(j, i, f"{100*v:+.0f}%", ha="center", va="center", fontsize=9.5,
                color="white" if abs(v) > 0.6 * np.abs(sens.values).max() else INK)
ax.set_xticks(range(3), sens.columns); ax.set_yticks(range(len(save_rates)), sens.index); ax.grid(False)
be = campaign(target)["break_even_save_rate"]
title(ax, "ROI of the 'Save now' campaign: save rate x gross margin",
      f"Break-even save rate {100*be:.1f}% at 40% margin (benchmark range 10-30%)")
save(fig, CH / "p7_04_roi_sensitivity.png")

fig, ax = plt.subplots(figsize=(8.5, 3.8))
ss = sim.sort_values("roi")
bars = ax.barh(ss.index, 100 * ss.roi, color=[ORANGE if "Save now" in i else BLUE for i in ss.index], height=0.55)
for b, (_, r) in zip(bars, ss.iterrows()):
    ax.text(max(b.get_width(), 0) + 3, b.get_y() + b.get_height() / 2,
            f"ROI {100*r.roi:+.0f}%  |  net {r.net_profit:,.0f}  |  {r.targeted:,.0f} targeted", va="center", fontsize=8.5)
ax.axvline(0, color=INK2, linewidth=1); ax.grid(axis="y", visible=False); ax.set_xlabel("ROI (%)")
ax.set_xlim(min(0, 100 * ss.roi.min()) - 10, 100 * ss.roi.max() + 120)
title(ax, "Who to target: ROI by strategy (save rate 10%, margin 40%)", "Value x risk gives the best ROI with a fifth of the contacts")
save(fig, CH / "p7_05_strategy_roi.png")

# ---------------------------------------------------------------- H. A/B test design
# Primary metric: 60-day repeat-purchase rate of first-time buyers. Baseline = Nov+Dec 2019 first-time buyers.
h3 = pd.read_csv(OUTPUTS / "phase5" / "h3_no_repeat_60d.csv")
p0 = 1 - h3.no_repeat.sum() / h3.n.sum()
mde = 0.02                                             # +2 pp absolute
p1 = p0 + mde
za, zb = stats.norm.ppf(1 - 0.05 / 2), stats.norm.ppf(0.80)
pbar = (p0 + p1) / 2
n_arm = int(np.ceil((za * np.sqrt(2 * pbar * (1 - pbar)) + zb * np.sqrt(p0 * (1 - p0) + p1 * (1 - p1))) ** 2 / mde ** 2))
first_buyers = orders.groupby("user_id").order_ts.min()
new_per_month = first_buyers[first_buyers >= "2019-11-01"].dt.to_period("M").value_counts().sort_index()
weekly = new_per_month.mean() / (30.4 / 7)
enrol_weeks = int(np.ceil(2 * n_arm / weekly))
K.update(ab_baseline_repeat60=p0, ab_mde_pp=100 * mde, ab_n_per_arm=n_arm, ab_new_buyers_per_month=new_per_month.mean(),
         ab_enrol_weeks=enrol_weeks, ab_total_weeks=enrol_weeks + int(np.ceil(60 / 7)))
new_per_month.to_csv(OUT / "new_first_time_buyers_per_month.csv")
print("A/B:", {k: K[k] for k in K if k.startswith("ab_")})

K.update({f"break_even_save_now": be, "save_now": campaign(target), "assumptions": dict(
    contact_cost=CONTACT_COST, discount=DISCOUNT, gross_margin=GROSS_MARGIN, save_rate=SAVE_RATE,
    high_value_pctl=HIGH_VALUE_PCTL, high_risk=HIGH_RISK)})
json.dump(K, open(OUT / "phase7_numbers.json", "w"), indent=2, default=lambda o: float(o) if hasattr(o, "__float__") else str(o))
print(json.dumps(K, indent=2, default=float))
