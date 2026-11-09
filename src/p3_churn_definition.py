"""Phase 3: validate the churn definition.

1. Inter-purchase gaps (all consecutive orders, and 1st->2nd order)
2. Time-to-second-order curve for first-time buyers with full follow-up
3. Sensitivity: alternative windows and label noise ("false churners")
4. Active / At-Risk / Churned segments as of 2020-02-29
Run: python src/p3_churn_definition.py [data_dir]   -> outputs/phase3/*.csv, images/phase3/*.png, printed summary
"""
import sys
from pathlib import Path

import duckdb
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from config import DATA as DEFAULT_DATA, IMAGES, OUTPUTS

DATA = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DATA
OUT, CH = OUTPUTS / "phase3", IMAGES / "phase3"
OUT.mkdir(parents=True, exist_ok=True); CH.mkdir(parents=True, exist_ok=True)

# Chart style (reference palette, light mode)
BLUE, ORANGE, AQUA, GRAY = "#2a78d6", "#eb6834", "#1baf7a", "#8a8984"
INK, INK2, SURFACE = "#0b0b0b", "#52514e", "#fcfcfb"
plt.rcParams.update({"figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "axes.edgecolor": "#d6d5d0",
                     "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2, "text.color": INK,
                     "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
                     "grid.color": "#ecebe7", "grid.linewidth": 0.8, "font.size": 10})

con = duckdb.connect()
con.sql(f"CREATE VIEW orders AS SELECT * FROM read_csv_auto('{DATA / 'orders.csv'}')")
con.sql(f"CREATE VIEW ucf AS SELECT * FROM read_csv_auto('{DATA / 'user_churn_features.csv'}')")
END = "TIMESTAMP '2020-02-29 23:59:59'"

# Each user's orders with sequence number and gap to the previous order
con.sql("""
CREATE TABLE seq AS
SELECT user_id, order_ts, order_value,
       ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY order_ts) AS n,
       DATE_DIFF('second', LAG(order_ts) OVER (PARTITION BY user_id ORDER BY order_ts), order_ts) / 86400.0 AS gap_days
FROM orders""")


def save(name, sql):
    df = con.sql(sql).df()
    df.to_csv(OUT / f"{name}.csv", index=False)
    print(f"\n== {name}\n{df.to_string(index=False)}")
    return df


# ---------- 1. Gap distribution ----------
gaps = save("gap_percentiles", """
SELECT CASE WHEN n = 2 THEN '1st -> 2nd order' ELSE '2nd+ -> next order' END AS gap_type,
       COUNT(*) AS gaps,
       ROUND(MEDIAN(gap_days), 1) AS median_days,
       ROUND(QUANTILE_CONT(gap_days, 0.75), 1) AS p75_days,
       ROUND(QUANTILE_CONT(gap_days, 0.90), 1) AS p90_days,
       ROUND(100 * AVG((gap_days <= 60)::INT), 2) AS pct_within_60d
FROM seq WHERE gap_days IS NOT NULL GROUP BY 1
UNION ALL
SELECT 'All repeat gaps', COUNT(*), ROUND(MEDIAN(gap_days), 1), ROUND(QUANTILE_CONT(gap_days, 0.75), 1),
       ROUND(QUANTILE_CONT(gap_days, 0.90), 1), ROUND(100 * AVG((gap_days <= 60)::INT), 2)
FROM seq WHERE gap_days IS NOT NULL ORDER BY 1""")

# The observed gaps are right-censored by the 5-month window (long gaps can't be seen).
# So also measure, for first-time buyers with >= 120 days of follow-up (first order in Oct 2019),
# the share who come back within d days: a censoring-free time-to-second-order curve.
curve = save("time_to_second_order_oct_first_buyers", """
WITH first AS (
    SELECT user_id, MIN(order_ts) AS t1 FROM orders GROUP BY user_id
    HAVING MIN(order_ts) < '2019-11-01'
),
second AS (
    SELECT s.user_id, s.gap_days FROM seq s JOIN first USING (user_id) WHERE s.n = 2
),
days AS (SELECT UNNEST(RANGE(0, 121)) AS d)
SELECT d AS days_since_first_order,
       (SELECT COUNT(*) FROM first) AS buyers,
       ROUND(100.0 * (SELECT COUNT(*) FROM second WHERE gap_days <= d) / (SELECT COUNT(*) FROM first), 3) AS pct_returned
FROM days ORDER BY d""")
c = curve.set_index("days_since_first_order")["pct_returned"]
captured_60_of_120 = round(100 * c[60] / c[120], 2)
print(f"\nOct first-time buyers: returned by 30d {c[30]}%, 60d {c[60]}%, 90d {c[90]}%, 120d {c[120]}%"
      f" -> 60-day window captures {captured_60_of_120}% of returns seen within 120 days")
pd_summary = con.sql(f"SELECT {c[30]} r30, {c[60]} r60, {c[90]} r90, {c[120]} r120, {captured_60_of_120} pct_60_of_120").df()
pd_summary.to_csv(OUT / "time_to_second_order_summary.csv", index=False)

# ---------- 2. Sensitivity of the churn definition ----------
# Each definition: observation window -> prediction window; churned = no order in prediction window.
defs = [
    ("A. Baseline: Oct-Dec -> Jan-Feb (2 months)", "2019-10-01", "2020-01-01", "2020-01-01", "2020-03-01"),
    ("B. Shorter window: Oct-Dec -> Jan only (1 month)", "2019-10-01", "2020-01-01", "2020-01-01", "2020-02-01"),
    ("C. Longer window: Oct-Nov -> Dec-Feb (3 months)", "2019-10-01", "2019-12-01", "2019-12-01", "2020-03-01"),
    ("D. Same 2-month length, shifted: Oct-Nov -> Dec-Jan", "2019-10-01", "2019-12-01", "2019-12-01", "2020-02-01"),
]
rows = []
for name, o0, o1, p0, p1 in defs:
    rows.append(con.sql(f"""
        WITH obs AS (SELECT DISTINCT user_id FROM orders WHERE order_ts >= '{o0}' AND order_ts < '{o1}'),
             fut AS (SELECT DISTINCT user_id FROM orders WHERE order_ts >= '{p0}' AND order_ts < '{p1}')
        SELECT '{name}' AS definition, COUNT(*) AS cohort_buyers,
               ROUND(100.0 * AVG((f.user_id IS NULL)::INT), 2) AS churn_rate_pct
        FROM obs o LEFT JOIN fut f USING (user_id)""").df())
import pandas as pd
sens = pd.concat(rows)
sens.to_csv(OUT / "sensitivity_definitions.csv", index=False)
print("\n== sensitivity_definitions\n" + sens.to_string(index=False))

# Label noise: of Oct-Nov buyers labelled churned by a 2-month window (no order Dec-Jan),
# how many come back in month 3 (Feb)? Those are "false churners" a 2-month label misses.
noise = save("label_noise_month3_return", """
WITH obs AS (SELECT DISTINCT user_id FROM orders WHERE order_ts < '2019-12-01'),
     m12 AS (SELECT DISTINCT user_id FROM orders WHERE order_ts >= '2019-12-01' AND order_ts < '2020-02-01'),
     m3  AS (SELECT DISTINCT user_id FROM orders WHERE order_ts >= '2020-02-01')
SELECT COUNT(*) AS labelled_churned_2m,
       COUNT(m3.user_id) AS returned_in_month3,
       ROUND(100.0 * COUNT(m3.user_id) / COUNT(*), 2) AS false_churn_pct
FROM obs o
LEFT JOIN m12 ON m12.user_id = o.user_id
LEFT JOIN m3  ON m3.user_id = o.user_id
WHERE m12.user_id IS NULL""")

# Baseline label by order count: is the noise concentrated in single-order buyers?
save("baseline_churn_by_recency_band", """
SELECT CASE WHEN recency_days <= 30 THEN '1. Last order in Dec (<=30d)'
            WHEN recency_days <= 61 THEN '2. Last order in Nov (31-61d)'
            ELSE '3. Last order in Oct (62-92d)' END AS recency_band,
       COUNT(*) AS buyers, ROUND(100 * AVG(churned), 2) AS churn_rate_pct
FROM ucf GROUP BY 1 ORDER BY 1""")

# ---------- 3. Active / At-Risk / Churned segments as of 2020-02-29 ----------
# Thresholds from the repeat-gap distribution: Active <= p75 gap, At-Risk p75..p90, Churned > p90.
allg = gaps[gaps.gap_type == "All repeat gaps"].iloc[0]
p75, p90 = float(allg.p75_days), float(allg.p90_days)
seg = save("customer_status_segments", f"""
WITH last AS (
    SELECT user_id, MAX(order_ts) AS last_ts, COUNT(*) AS orders, SUM(order_value) AS revenue
    FROM orders GROUP BY user_id
)
SELECT CASE WHEN DATE_DIFF('second', last_ts, {END}) / 86400.0 <= {p75} THEN '1. Active'
            WHEN DATE_DIFF('second', last_ts, {END}) / 86400.0 <= {p90} THEN '2. At-Risk'
            ELSE '3. Churned (lapsed)' END AS status,
       COUNT(*) AS buyers,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS buyer_share_pct,
       ROUND(SUM(revenue), 2) AS revenue_oct_feb,
       ROUND(100.0 * SUM(revenue) / SUM(SUM(revenue)) OVER (), 2) AS revenue_share_pct,
       ROUND(100.0 * AVG((orders >= 2)::INT), 2) AS repeat_buyer_pct
FROM last GROUP BY 1 ORDER BY 1""")
con.sql(f"""COPY (
    SELECT user_id, MAX(order_ts) AS last_order_ts, COUNT(*) AS orders, ROUND(SUM(order_value), 2) AS revenue,
           ROUND(DATE_DIFF('second', MAX(order_ts), {END}) / 86400.0, 1) AS days_since_last_order,
           CASE WHEN DATE_DIFF('second', MAX(order_ts), {END}) / 86400.0 <= {p75} THEN 'Active'
                WHEN DATE_DIFF('second', MAX(order_ts), {END}) / 86400.0 <= {p90} THEN 'At-Risk'
                ELSE 'Churned' END AS status
    FROM orders GROUP BY user_id) TO '{OUT / 'customer_status_by_user.csv'}' (HEADER)""")

# ---------- Charts ----------
# 1. Gap histogram
g = con.sql("SELECT gap_days FROM seq WHERE gap_days IS NOT NULL").df().gap_days
fig, ax = plt.subplots(figsize=(8, 4.2))
ax.hist(g, bins=range(0, 152, 4), color=BLUE, edgecolor=SURFACE, linewidth=1.5)
for v, lab in [(float(allg.median_days), "median"), (p75, "p75"), (p90, "p90")]:
    ax.axvline(v, color=INK2, linewidth=1, linestyle="--")
    ax.text(v + 1.5, ax.get_ylim()[1] * 0.92, f"{lab} {v:.0f}d", color=INK2, fontsize=9)
ax.axvspan(0, 60, color=AQUA, alpha=0.08)
ax.set_title(f"Days between consecutive orders ({len(g):,} repeat gaps)\n"
             f"{allg.pct_within_60d}% of repeat gaps are within the 60-day window", loc="left", fontsize=11)
ax.set_xlabel("Days since previous order"); ax.set_ylabel("Repeat orders")
fig.tight_layout(); fig.savefig(CH / "p3_01_interpurchase_gap_hist.png", dpi=150); plt.close(fig)

# 2. Time-to-second-order curve
fig, ax = plt.subplots(figsize=(8, 4.2))
ax.plot(c.index, c.values, color=BLUE, linewidth=2)
for d in (30, 60, 90, 120):
    ax.plot(d, c[d], "o", color=BLUE, markersize=7, markeredgecolor=SURFACE, markeredgewidth=2)
    ax.annotate(f"{c[d]:.1f}% by day {d}", (d, c[d]), textcoords="offset points", xytext=(-10, 10),
                ha="right", fontsize=9, color=INK)
ax.axvline(60, color=INK2, linewidth=1, linestyle="--")
ax.set_title(f"Share of October first-time buyers who placed a 2nd order\n"
             f"Day 60 captures {captured_60_of_120}% of the returns seen by day 120", loc="left", fontsize=11)
ax.set_xlabel("Days since first order"); ax.set_ylabel("% returned"); ax.set_xlim(0, 122); ax.set_ylim(0, None)
fig.tight_layout(); fig.savefig(CH / "p3_02_time_to_second_order.png", dpi=150); plt.close(fig)

# 3. Sensitivity bars
fig, ax = plt.subplots(figsize=(8, 3.6))
labels = [d.split(": ")[1] for d in sens.definition]
colors = [BLUE] + [GRAY] * (len(labels) - 1)
bars = ax.barh(labels[::-1], sens.churn_rate_pct[::-1], color=colors[::-1], height=0.55)
for b, v in zip(bars, sens.churn_rate_pct[::-1]):
    ax.text(v + 0.5, b.get_y() + b.get_height() / 2, f"{v:.1f}%", va="center", fontsize=9, color=INK)
ax.set_xlim(0, 100); ax.grid(axis="y", visible=False)
ax.set_title("Churn rate under alternative definitions (baseline in blue)", loc="left", fontsize=11)
ax.set_xlabel("Churn rate (%)")
fig.tight_layout(); fig.savefig(CH / "p3_03_definition_sensitivity.png", dpi=150); plt.close(fig)

# 4. Status segments
fig, ax = plt.subplots(figsize=(8, 3.2))
segc = [AQUA, ORANGE, GRAY]
y = list(range(len(seg)))[::-1]
ax.barh(y, seg.buyer_share_pct, color=segc, height=0.55)
for yi, (_, r) in zip(y, seg.iterrows()):
    ax.text(r.buyer_share_pct + 0.8, yi, f"{r.buyers:,} buyers ({r.buyer_share_pct}%), {r.revenue_share_pct}% of revenue",
            va="center", fontsize=9, color=INK)
ax.set_yticks(y, [s.split(". ")[1] for s in seg.status]); ax.set_xlim(0, 100); ax.grid(axis="y", visible=False)
ax.set_title(f"Buyer status on 29 Feb 2020 (Active <= {p75:.0f}d, At-Risk {p75:.0f}-{p90:.0f}d since last order)",
             loc="left", fontsize=11)
ax.set_xlabel("% of buyers")
fig.tight_layout(); fig.savefig(CH / "p3_04_status_segments.png", dpi=150); plt.close(fig)
print("\ncharts written")

# ---------- 4. Do the main drivers hold under the alternative definition? ----------
save("driver_stability_by_definition", """
WITH a AS (  -- baseline A: Oct-Dec -> Jan-Feb
    SELECT o.user_id, COUNT(*) AS n_obs,
           MAX((SELECT COUNT(*) FROM orders f WHERE f.user_id = o.user_id AND f.order_ts >= '2020-01-01')) = 0 AS churned
    FROM orders o WHERE o.order_ts < '2020-01-01' GROUP BY o.user_id
),
c AS (       -- alternative C: Oct-Nov -> Dec-Feb
    SELECT o.user_id, COUNT(*) AS n_obs,
           MAX((SELECT COUNT(*) FROM orders f WHERE f.user_id = o.user_id AND f.order_ts >= '2019-12-01')) = 0 AS churned
    FROM orders o WHERE o.order_ts < '2019-12-01' GROUP BY o.user_id
)
SELECT 'A. Oct-Dec -> Jan-Feb' AS definition,
       ROUND(100 * AVG(churned::INT) FILTER (WHERE n_obs = 1), 2) AS churn_single_order_pct,
       ROUND(100 * AVG(churned::INT) FILTER (WHERE n_obs >= 2), 2) AS churn_multi_order_pct
FROM a
UNION ALL
SELECT 'C. Oct-Nov -> Dec-Feb',
       ROUND(100 * AVG(churned::INT) FILTER (WHERE n_obs = 1), 2),
       ROUND(100 * AVG(churned::INT) FILTER (WHERE n_obs >= 2), 2)
FROM c""")
