"""Phase 5: statistical hypothesis tests on churn drivers.

H1 Single-order buyers churn more than repeat buyers            -> chi-square + two-proportion z-test
H2 Heavy cart-removers churn more                               -> Mann-Whitney U (overall and stratified)
H3 December-acquired buyers retain worse (recency-free window)  -> two-proportion z-test
H4 No activity in the last 31 days predicts churn               -> chi-square (3 groups) + z-test
H5 Churners had lower order values (AOV)                        -> Mann-Whitney U
H6 First-basket value differs by acquisition month              -> Kruskal-Wallis + pairwise Mann-Whitney
alpha = 0.05 with Bonferroni correction across the 6 primary tests.
Run: python src/p5_hypothesis_tests.py [data_dir] -> outputs/phase5/*.csv, images/phase5/*.png
"""
import sys
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
from scipy import stats

from viz_style import BLUE, GRAY, INK, INK2, ORANGE, SURFACE, plt, save, title  # noqa: E402
from config import DATA as DEFAULT_DATA, IMAGES, OUTPUTS  # noqa: E402

DATA = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DATA
OUT, CH = OUTPUTS / "phase5", IMAGES / "phase5"
OUT.mkdir(parents=True, exist_ok=True); CH.mkdir(parents=True, exist_ok=True)
ALPHA, N_TESTS = 0.05, 6

con = duckdb.connect()
con.sql(f"CREATE VIEW orders AS SELECT * FROM read_csv_auto('{DATA / 'orders.csv'}')")
u = con.sql(f"""
    WITH fo AS (SELECT user_id, MIN(order_ts) AS first_ts,
                       ARG_MIN(order_value, order_ts) AS first_order_value FROM orders GROUP BY 1)
    SELECT u.*, DATE_TRUNC('month', fo.first_ts) AS acq_month, fo.first_order_value
    FROM read_csv_auto('{DATA / 'user_churn_features.csv'}') u JOIN fo USING (user_id)""").df()


# ---------------------------------------------------------------- helpers
def two_prop(x1, n1, x2, n2):
    """Two-proportion z-test (pooled) + risk difference with 95% Wald CI, relative risk, odds ratio."""
    p1, p2 = x1 / n1, x2 / n2
    p = (x1 + x2) / (n1 + n2)
    z = (p1 - p2) / np.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    pval = 2 * stats.norm.sf(abs(z))
    se = np.sqrt(p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2)
    odds = (p1 / (1 - p1)) / (p2 / (1 - p2))
    h = 2 * np.arcsin(np.sqrt(p1)) - 2 * np.arcsin(np.sqrt(p2))  # Cohen's h
    return dict(p1=p1, p2=p2, z=z, p=pval, diff_pp=100 * (p1 - p2),
                ci_low_pp=100 * (p1 - p2 - 1.96 * se), ci_high_pp=100 * (p1 - p2 + 1.96 * se),
                rel_risk=p1 / p2, odds_ratio=odds, cohens_h=h)


def cramers_v(table):
    chi2, p, dof, _ = stats.chi2_contingency(table, correction=False)
    n = table.sum()
    return chi2, p, dof, np.sqrt(chi2 / (n * (min(table.shape) - 1)))


def mwu(a, b):
    """Mann-Whitney U (two-sided) + rank-biserial correlation (positive => a tends to be larger)."""
    res = stats.mannwhitneyu(a, b, alternative="two-sided")
    r_rb = 2 * res.statistic / (len(a) * len(b)) - 1
    return res.statistic, res.pvalue, r_rb


def magnitude(kind, v):
    v = abs(v)
    cuts = {"h": (0.2, 0.5, 0.8), "v": (0.1, 0.3, 0.5), "r": (0.1, 0.3, 0.5), "eps2": (0.01, 0.06, 0.14)}[kind]
    return "negligible" if v < cuts[0] else "small" if v < cuts[1] else "medium" if v < cuts[2] else "large"


rows, details = [], []


def record(h, hypothesis, test, stat, p, effect_name, effect, kind, result_text, business):
    p_adj = min(1.0, p * N_TESTS)
    rows.append(dict(id=h, hypothesis=hypothesis, test=test, statistic=round(stat, 3), p_value=p,
                     p_bonferroni=p_adj, significant=p_adj < ALPHA, effect_size=effect_name,
                     effect_value=round(effect, 4), magnitude=magnitude(kind, effect),
                     result=result_text, business_meaning=business))
    print(f"\n{h}: {result_text}\n   {test}: stat={stat:.3f}, p={p:.3g}, p_bonf={p_adj:.3g}, "
          f"{effect_name}={effect:.4f} ({magnitude(kind, effect)})")


# ---------------------------------------------------------------- H1 single vs repeat buyers
single = u.n_orders == 1
x1, n1 = int(u.churned[single].sum()), int(single.sum())
x2, n2 = int(u.churned[~single].sum()), int((~single).sum())
tp = two_prop(x1, n1, x2, n2)
chi2, p, dof, v = cramers_v(np.array([[x1, n1 - x1], [x2, n2 - x2]]))
details.append(dict(id="H1", **tp, chi2=chi2))
record("H1", "Single-order buyers churn more than repeat buyers", "Chi-square (2x2) + two-proportion z-test",
       chi2, p, "Cramér's V", v, "v",
       f"Churn {100*tp['p1']:.2f}% (single, n={n1:,}) vs {100*tp['p2']:.2f}% (repeat, n={n2:,}); "
       f"diff {tp['diff_pp']:.2f} pp [95% CI {tp['ci_low_pp']:.2f}, {tp['ci_high_pp']:.2f}]; RR {tp['rel_risk']:.2f}; "
       f"OR {tp['odds_ratio']:.2f}; Cohen's h {tp['cohens_h']:.2f}",
       "Supported. A single-order buyer is ~6x more likely (odds) to churn: the second order is the key retention moment.")

# ---------------------------------------------------------------- H2 cart removal
carts = u[u.n_carts > 0]
U, p, r = mwu(carts.cart_remove_rate[carts.churned == 1], carts.cart_remove_rate[carts.churned == 0])
med_c, med_r = carts.cart_remove_rate[carts.churned == 1].median(), carts.cart_remove_rate[carts.churned == 0].median()
strata = []
for lab, sub in [("single-order", carts[carts.n_orders == 1]), ("repeat", carts[carts.n_orders > 1])]:
    _, ps, rs = mwu(sub.cart_remove_rate[sub.churned == 1], sub.cart_remove_rate[sub.churned == 0])
    strata.append(f"{lab}: r={rs:.3f} (p={ps:.2g})")
    details.append(dict(id=f"H2_{lab}", rank_biserial=rs, p=ps))
record("H2", "Buyers who remove more items from cart churn more", "Mann-Whitney U (cart_remove_rate, churned vs retained)",
       U, p, "Rank-biserial r", r, "r",
       f"Median removal rate {med_c:.3f} (churned) vs {med_r:.3f} (retained), n={len(carts):,}; stratified "
       + "; ".join(strata),
       "Rejected as stated: churners remove LESS. Cart removal signals active comparison shopping by engaged users, "
       "so it should not trigger churn alerts.")

# ---------------------------------------------------------------- H3 December-acquired, recency-free
# Comparing churn in Jan-Feb directly is confounded by recency (Dec buyers bought more recently), and
# among single-order buyers acquisition month and recency are the same thing. So use a window anchored
# on each buyer's FIRST order: "no 2nd order within 60 days of the first order". Every Nov/Dec first-time
# buyer has >= 60 days of follow-up before 29 Feb 2020. Oct is excluded (left-censored).
h3 = con.sql("""
    WITH s AS (SELECT user_id, order_ts, ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY order_ts) n FROM orders),
         f AS (SELECT user_id, order_ts AS t1, DATE_TRUNC('month', order_ts) AS m FROM s WHERE n = 1),
         t AS (SELECT user_id, order_ts AS t2 FROM s WHERE n = 2)
    SELECT strftime(f.m, '%b') AS acq, COUNT(*) AS n,
           SUM(CASE WHEN t.t2 IS NULL OR DATE_DIFF('second', f.t1, t.t2) > 60 * 86400 THEN 1 ELSE 0 END) AS no_repeat
    FROM f LEFT JOIN t USING (user_id)
    WHERE f.m IN ('2019-11-01', '2019-12-01') GROUP BY 1""").df().set_index("acq")
h3.assign(no_repeat_pct=100 * h3.no_repeat / h3.n).to_csv(OUT / "h3_no_repeat_60d.csv")
x1, n1 = int(h3.loc["Dec", "no_repeat"]), int(h3.loc["Dec", "n"])
x2, n2 = int(h3.loc["Nov", "no_repeat"]), int(h3.loc["Nov", "n"])
tp = two_prop(x1, n1, x2, n2)
details.append(dict(id="H3", **tp))
# Raw Jan-Feb churn comparison (confounded by recency) for context
raw = two_prop(int(u.churned[u.acq_month == "2019-12-01"].sum()), int((u.acq_month == "2019-12-01").sum()),
               int(u.churned[u.acq_month == "2019-11-01"].sum()), int((u.acq_month == "2019-11-01").sum()))
details.append(dict(id="H3_raw", **raw))
record("H3", "December (holiday) acquired buyers retain worse than November acquired",
       "Two-proportion z-test on 'no 2nd order within 60 days of first order' (recency-free)",
       tp["z"], tp["p"], "Cohen's h", tp["cohens_h"], "h",
       f"No 2nd order within 60 days: {100*tp['p1']:.2f}% (Dec-acquired, n={n1:,}) vs {100*tp['p2']:.2f}% "
       f"(Nov-acquired, n={n2:,}); diff {tp['diff_pp']:.2f} pp [CI {tp['ci_low_pp']:.2f}, {tp['ci_high_pp']:.2f}]; "
       f"RR {tp['rel_risk']:.3f}. Raw Jan-Feb churn diff {raw['diff_pp']:.2f} pp",
       "Statistically supported but practically small (negligible effect size): holiday-acquired buyers are slightly less likely to come back within 60 days. "
       "Worth a tailored post-holiday second-order offer, but it is not the main churn driver.")

# ---------------------------------------------------------------- H4 engagement in last 31 days
grp = np.select([u.events_last_31d == 0, u.events_last_31d < u.events_prev_30d],
                ["No activity", "Declining"], "Flat or growing")
tab = pd.crosstab(grp, u.churned)
chi2, p, dof, v = cramers_v(tab.values)
na = grp == "No activity"
tp = two_prop(int(u.churned[na].sum()), int(na.sum()), int(u.churned[~na].sum()), int((~na).sum()))
details.append(dict(id="H4", **tp, chi2=chi2))
tab.assign(churn_rate=lambda t: 100 * t[1] / (t[0] + t[1])).to_csv(OUT / "h4_engagement_crosstab.csv")
record("H4", "Buyers with no site activity in the last 31 days churn more",
       "Chi-square (3 engagement groups x churn) + two-proportion z-test (none vs any)",
       chi2, p, "Cramér's V", v, "v",
       f"Churn {100*tp['p1']:.2f}% (no activity, n={int(na.sum()):,}) vs {100*tp['p2']:.2f}% (any activity); "
       f"diff {tp['diff_pp']:.2f} pp [CI {tp['ci_low_pp']:.2f}, {tp['ci_high_pp']:.2f}]; OR {tp['odds_ratio']:.2f}",
       "Supported: silence is the warning sign. Trigger re-engagement after ~30 days without a visit, "
       "rather than on a dip in activity.")

# ---------------------------------------------------------------- H5 AOV churned vs retained
U, p, r = mwu(u.aov[u.churned == 1], u.aov[u.churned == 0])
m1, m0 = u.aov[u.churned == 1].median(), u.aov[u.churned == 0].median()
record("H5", "Churners had lower average order value than retained buyers", "Mann-Whitney U (AOV)",
       U, p, "Rank-biserial r", r, "r",
       f"Median AOV {m1:.2f} (churned) vs {m0:.2f} (retained)",
       "Statistically real but small: basket size alone is a weak churn signal, so the model needs behaviour "
       "(orders, recency, activity), not just spend.")

# ---------------------------------------------------------------- H6 first basket by acquisition month
groups = {f"{m:%b}": u.first_order_value[u.acq_month == m] for m in sorted(u.acq_month.unique())}
H, p = stats.kruskal(*groups.values())
eps2 = (H - len(groups) + 1) / (len(u) - len(groups))
pair = []
keys = list(groups)
for i in range(len(keys)):
    for j in range(i + 1, len(keys)):
        _, pp, rr = mwu(groups[keys[i]], groups[keys[j]])
        pair.append(dict(pair=f"{keys[i]} vs {keys[j]}", p_bonferroni=min(1, pp * 3), rank_biserial=rr))
pd.DataFrame(pair).to_csv(OUT / "h6_pairwise.csv", index=False)
meds = {k: v.median() for k, v in groups.items()}
record("H6", "First-order basket value differs by acquisition month (Oct*/Nov/Dec)",
       "Kruskal-Wallis + pairwise Mann-Whitney (Bonferroni x3)", H, p, "Epsilon-squared", eps2, "eps2",
       "Median first-order value " + ", ".join(f"{k} {v:.2f}" for k, v in meds.items()) + "; pairwise: "
       + "; ".join(f"{d['pair']} r={d['rank_biserial']:.3f}" for d in pair),
       "Differences exist but are tiny: December buyers do not start with much smaller baskets, so their weaker "
       "retention comes from behaviour after the first order.")

res = pd.DataFrame(rows)
res.to_csv(OUT / "hypothesis_results.csv", index=False)
pd.DataFrame(details).to_csv(OUT / "hypothesis_details.csv", index=False)

# ---------------------------------------------------------------- charts
# 1. Churn-rate gaps with 95% CI for the proportion hypotheses
dd = pd.DataFrame(details).set_index("id")
items = [("H1", "Single-order vs repeat buyers"), ("H4", "No activity in last 31d vs any"),
         ("H3", "Dec- vs Nov-acquired: no repeat in 60d"), ("H3_raw", "Dec- vs Nov-acquired: Jan-Feb churn (raw)")]
fig, ax = plt.subplots(figsize=(8.5, 3.6))
for k, (hid, lab) in enumerate(items[::-1]):
    r_ = dd.loc[hid]
    ax.plot([r_.ci_low_pp, r_.ci_high_pp], [k, k], color=BLUE, linewidth=2)
    ax.plot(r_.diff_pp, k, "o", color=BLUE, markersize=8, markeredgecolor=SURFACE, markeredgewidth=2)
    ax.text(r_.ci_high_pp + 0.8, k, f"+{r_.diff_pp:.1f} pp", va="center", fontsize=9, color=INK)
ax.axvline(0, color=INK2, linewidth=1)
ax.set_yticks(range(len(items)), [lab for _, lab in items[::-1]]); ax.grid(axis="y", visible=False)
ax.set_xlabel("Difference in churn rate, percentage points (95% CI)")
ax.set_xlim(-2, max(dd.loc[[h for h, _ in items], "ci_high_pp"]) + 6)
title(ax, "How much higher is churn? (two-proportion tests)",
      "Order count and recent activity dwarf the holiday-cohort effect")
save(fig, CH / "p5_01_churn_gaps_ci.png")

# 2. Churn by cart-removal decile (H2)
carts = carts.assign(decile=pd.qcut(carts.cart_remove_rate.rank(method="first"), 10, labels=False) + 1)
dec = carts.groupby("decile").agg(churn=("churned", "mean"), med=("cart_remove_rate", "median"))
dec.to_csv(OUT / "h2_churn_by_removal_decile.csv")
fig, ax = plt.subplots(figsize=(8, 3.8))
bars = ax.bar(dec.index.astype(str), 100 * dec.churn, color=BLUE, width=0.6)
for b, v in zip(bars, dec.churn):
    ax.text(b.get_x() + b.get_width() / 2, 100 * v + 1, f"{100*v:.0f}%", ha="center", fontsize=8.5, color=INK)
ax.set_ylim(0, 108); ax.grid(axis="x", visible=False)
ax.set_xlabel("Cart-removal-rate decile (1 = removes least, 10 = removes most)"); ax.set_ylabel("Churn rate (%)")
title(ax, "H2 reversed: heavier cart-removers churn slightly less",
      "Removing items is a sign of engaged comparison shopping, not dissatisfaction")
save(fig, CH / "p5_02_churn_by_cart_removal_decile.png")
print("\nsaved", OUT / "hypothesis_results.csv")
