"""Phase 4: EDA & funnel diagnostics -> images/phase4/p4_*.png, outputs/phase4/*.csv

Charts: funnel (overall, monthly, brands, categories), cart abandonment, session depth,
hour x day-of-week (UTC), cohort retention (visitors, buyers), RFM segments, Pareto,
December holiday-cohort quality, churn by orders and engagement.
Run: python src/p4_eda.py [data_dir]
"""
import sys
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from viz_style import (AQUA, BLUE, GRAY, INK, INK2, ORANGE, SEQ_BLUE, SURFACE,  # noqa: E402
                       plt, save, title)
from config import DATA as DEFAULT_DATA, IMAGES, OUTPUTS  # noqa: E402

DATA = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DATA
CH, OUT = IMAGES / "phase4", OUTPUTS / "phase4"
CH.mkdir(parents=True, exist_ok=True); OUT.mkdir(parents=True, exist_ok=True)

con = duckdb.connect()
for t in ["orders", "user_churn_features", "daily_kpis", "brand_monthly_funnel", "category_monthly_funnel",
          "hour_dow_activity", "session_summary", "cohort_retention_visitors", "cohort_retention_buyers",
          "products"]:
    con.sql(f"CREATE VIEW {t} AS SELECT * FROM read_csv_auto('{DATA / (t + '.csv')}')")
q = lambda s: con.sql(s).df()  # noqa: E731
notes = []  # (chart, key figure) rows -> outputs/phase4/chart_notes.csv


def note(chart, text):
    notes.append({"chart": chart, "figure": text})
    print(f"[{chart}] {text}")


def bar_labels(ax, bars, fmt, horizontal=False, pad=0.6):
    for b in bars:
        v = b.get_width() if horizontal else b.get_height()
        if horizontal:
            ax.text(v + pad, b.get_y() + b.get_height() / 2, fmt(v), va="center", fontsize=8.5, color=INK)
        else:
            ax.text(b.get_x() + b.get_width() / 2, v + pad, fmt(v), ha="center", fontsize=8.5, color=INK)


# ---------------------------------------------------------------- 1. Overall funnel
f = q("""SELECT SUM(views) v, SUM(carts) c, SUM(purchase_items) p FROM daily_kpis""").iloc[0]
s = q("""SELECT SUM(sessions) s, SUM(sessions_with_cart) c, SUM(sessions_with_purchase) p FROM session_summary""").iloc[0]
fig, axes = plt.subplots(1, 2, figsize=(10, 3.8))
for ax, vals, labs, ttl in [
    (axes[0], [f.v, f.c, f.p], ["Product views", "Add-to-cart", "Items purchased"], "Event funnel"),
    (axes[1], [s.s, s.c, s.p], ["All sessions", "Sessions with cart", "Sessions with purchase"], "Session funnel"),
]:
    bars = ax.barh(labs[::-1], vals[::-1], color=["#86b6ef", "#3987e5", "#184f95"], height=0.6)
    for b, v in zip(bars, vals[::-1]):
        ax.text(v, b.get_y() + b.get_height() / 2, f" {v/1e6:.2f}M ({100*v/vals[0]:.1f}%)",
                va="center", fontsize=9, color=INK)
    ax.set_xlim(0, vals[0] * 1.45); ax.grid(axis="y", visible=False); ax.set_xticks([])
    ax.set_title(ttl, loc="left", fontsize=10, color=INK2)
fig.suptitle(f"Only {100*s.p/s.s:.2f}% of sessions end in a purchase; {100*(s.c-0)/s.s:.2f}% add to cart",
             x=0.01, ha="left", fontsize=11)
save(fig, CH / "p4_01_funnel_overall.png")
note("p4_01", f"session conversion {100*s.p/s.s:.2f}%, cart sessions {100*s.c/s.s:.2f}%, "
     f"cart events per view {100*f.c/f.v:.2f}%, purchased items per view {100*f.p/f.v:.2f}%")

# ---------------------------------------------------------------- 2. Funnel by month
m = q("""SELECT DATE_TRUNC('month', date) AS month, SUM(views) v, SUM(carts) c, SUM(purchase_items) p
         FROM daily_kpis GROUP BY 1 ORDER BY 1""")
m["view_to_cart"] = 100 * m.c / m.v; m["cart_to_purchase"] = 100 * m.p / m.c; m["view_to_purchase"] = 100 * m.p / m.v
m.to_csv(OUT / "funnel_by_month.csv", index=False)
fig, ax = plt.subplots(figsize=(8, 4))
lab = m.month.dt.strftime("%b %y")
for col, colr, name in [("view_to_cart", BLUE, "View → cart"), ("cart_to_purchase", ORANGE, "Cart → purchase"),
                        ("view_to_purchase", AQUA, "View → purchase")]:
    ax.plot(lab, m[col], color=colr, linewidth=2, marker="o", markersize=7, markeredgecolor=SURFACE,
            markeredgewidth=2, label=name)
    ax.text(len(lab) - 0.9, m[col].iloc[-1], f"{name} {m[col].iloc[-1]:.1f}%", va="center", fontsize=9, color=INK)
ax.set_xlim(-0.3, len(lab) + 1.3); ax.set_ylabel("Conversion (%)"); ax.legend(loc="upper left", ncols=3)
ax.set_ylim(0, m.view_to_cart.max() * 1.25)
title(ax, "Funnel conversion by month (event level)",
      f"Cart → purchase peaked in Nov ({m.cart_to_purchase.max():.1f}%) and slid to {m.cart_to_purchase.iloc[-1]:.1f}% by Feb")
save(fig, CH / "p4_02_funnel_by_month.png")
note("p4_02", "; ".join(f"{r.month:%b}: v2c {r.view_to_cart:.2f}% c2p {r.cart_to_purchase:.2f}% v2p {r.view_to_purchase:.2f}%"
                        for r in m.itertuples()))

# ---------------------------------------------------------------- 3. Daily revenue
d = q("SELECT date, revenue, AVG(revenue) OVER (ORDER BY date ROWS 6 PRECEDING) AS r7 FROM daily_kpis ORDER BY date")
pk = d.loc[d.revenue.idxmax()]
fig, ax = plt.subplots(figsize=(9, 3.8))
ax.plot(d.date, d.revenue, color="#b7d3f6", linewidth=1, label="Daily revenue")
ax.plot(d.date, d.r7, color=BLUE, linewidth=2, label="7-day average")
ax.annotate(f"Peak {pk.date:%d %b}: {pk.revenue:,.0f}", (pk.date, pk.revenue), xytext=(10, -5),
            textcoords="offset points", fontsize=9)
ax.set_ylabel("Revenue (currency units)"); ax.legend(loc="upper right")
title(ax, "Daily revenue, Oct 2019 – Feb 2020", f"Late-November sales produce the biggest spike (peak {pk.date:%d %b})")
save(fig, CH / "p4_03_daily_revenue.png")
note("p4_03", f"peak day {pk.date:%Y-%m-%d} revenue {pk.revenue:.2f}")

# ---------------------------------------------------------------- 4. Brand conversion
b = q("""SELECT brand, SUM(views) v, SUM(carts) c, SUM(removes) r, SUM(purchase_items) p, SUM(revenue) rev
         FROM brand_monthly_funnel GROUP BY brand ORDER BY v DESC LIMIT 15""")
b["v2p"] = 100 * b.p / b.v; b["c2p"] = 100 * b.p / b.c; b["v2c"] = 100 * b.c / b.v; b["remove"] = 100 * b.r / b.c
b.to_csv(OUT / "top15_brands_by_views.csv", index=False)
bb = b.sort_values("v2p")
fig, ax = plt.subplots(figsize=(8, 5))
colors = [GRAY if x == "unknown" else BLUE for x in bb.brand]
bars = ax.barh(bb.brand, bb.v2p, color=colors, height=0.62)
bar_labels(ax, bars, lambda v: f"{v:.1f}%", horizontal=True, pad=0.2)
ax.axvline(100 * f.p / f.v, color=INK2, linestyle="--", linewidth=1)
ax.text(100 * f.p / f.v + 0.2, -0.9, f"store avg {100*f.p/f.v:.1f}%", fontsize=8.5, color=INK2)
ax.grid(axis="y", visible=False); ax.set_xlabel("Items purchased per 100 views")
title(ax, "View → purchase conversion, 15 most-viewed brands",
      f"{bb.brand.iloc[-1]} converts {bb.v2p.iloc[-1]:.1f}% vs {bb.brand.iloc[0]} {bb.v2p.iloc[0]:.1f}%: a {bb.v2p.iloc[-1]/bb.v2p.iloc[0]:.1f}x gap")
save(fig, CH / "p4_04_brand_conversion.png")
note("p4_04", f"best {bb.brand.iloc[-1]} {bb.v2p.iloc[-1]:.2f}%, worst {bb.brand.iloc[0]} {bb.v2p.iloc[0]:.2f}%, store {100*f.p/f.v:.2f}%")

# ---------------------------------------------------------------- 5. Brand cart behaviour scatter
fig, ax = plt.subplots(figsize=(8, 5))
ax.scatter(b.v2c, b.c2p, s=np.sqrt(b.v) / 4, color=BLUE, alpha=0.75, edgecolor=SURFACE, linewidth=1.5)
for r in b.itertuples():
    ax.annotate(r.brand, (r.v2c, r.c2p), xytext=(5, 3), textcoords="offset points", fontsize=8, color=INK2)
ax.set_xlabel("View → cart (%)"); ax.set_ylabel("Cart → purchase (%)")
title(ax, "Where each top brand leaks: browsing vs checkout (bubble = views)",
      f"Low view→cart brands ({', '.join(b.nsmallest(3, 'v2c').brand)}) lose shoppers before the cart;\n"
      f"cart→purchase only spans {b.c2p.min():.0f}-{b.c2p.max():.0f}% across brands")
save(fig, CH / "p4_05_brand_leak_scatter.png")

# ---------------------------------------------------------------- 6. Category conversion
c = q("""WITH f AS (SELECT category_id, SUM(views) v, SUM(carts) c, SUM(purchase_items) p, SUM(revenue) rev
                    FROM category_monthly_funnel GROUP BY 1),
              tb AS (SELECT category_id, brand, ROW_NUMBER() OVER (PARTITION BY category_id ORDER BY SUM(revenue) DESC) rn
                     FROM products WHERE brand <> 'unknown' GROUP BY 1, 2),
              pr AS (SELECT category_id, MEDIAN(median_price) price FROM products GROUP BY 1)
         SELECT f.*, tb.brand, pr.price FROM f LEFT JOIN tb ON tb.category_id = f.category_id AND tb.rn = 1
         LEFT JOIN pr ON pr.category_id = f.category_id ORDER BY rev DESC LIMIT 12""")
c["v2p"] = 100 * c.p / c.v
c["label"] = [f"…{str(i)[-4:]} ({br if isinstance(br, str) else 'no brand'}, med {p:.0f})"
              for i, br, p in zip(c.category_id, c.brand, c.price)]
c.to_csv(OUT / "top12_categories_by_revenue.csv", index=False)
cc = c.sort_values("v2p")
fig, ax = plt.subplots(figsize=(8.5, 5))
bars = ax.barh(cc.label, cc.v2p, color=[ORANGE if p >= 40 else BLUE for p in cc.price], height=0.62)
bar_labels(ax, bars, lambda v: f"{v:.1f}%", horizontal=True, pad=0.2)
ax.grid(axis="y", visible=False); ax.set_xlabel("Items purchased per 100 views")
title(ax, "View → purchase, top 12 categories by revenue (orange = median price ≥ 40)",
      "High-ticket categories (median price ≥ 40) attract views but convert under 4%")
save(fig, CH / "p4_06_category_conversion.png")
note("p4_06", "; ".join(f"{r.category_id}: v2p {r.v2p:.2f}% price {r.price:.2f}" for r in c.itertuples()))

# ---------------------------------------------------------------- 7. Cart abandonment trend
a = q("""SELECT month, SUM(abandoned_cart_sessions) * 100.0 / SUM(sessions_with_cart) AS ab
         FROM session_summary GROUP BY 1 ORDER BY 1""")
fig, ax = plt.subplots(figsize=(8, 3.8))
bars = ax.bar(a.month.dt.strftime("%b %y"), a.ab, color=BLUE, width=0.55)
bar_labels(ax, bars, lambda v: f"{v:.1f}%", pad=0.8)
ax.axhline(70.22, color=ORANGE, linestyle="--", linewidth=1.5)
ax.text(4.35, 71.5, "Baymard avg 70.22%", ha="right", fontsize=9, color=INK2)
ax.set_ylim(0, 100); ax.set_ylabel("Cart sessions without purchase (%)"); ax.grid(axis="x", visible=False)
title(ax, "Cart abandonment by month (session level)",
      "Every month sits 15-19 points above the Baymard average (definitions differ; see notes)")
save(fig, CH / "p4_07_cart_abandonment.png")
note("p4_07", "; ".join(f"{r.month:%b}: {r.ab:.2f}%" for r in a.itertuples()))

# ---------------------------------------------------------------- 8. Session depth
sd = q("""SELECT events_bucket, SUM(sessions) s, SUM(sessions_with_purchase) * 100.0 / SUM(sessions) pr,
                 SUM(abandoned_cart_sessions) * 100.0 / SUM(sessions_with_cart) ab
          FROM session_summary GROUP BY 1""")
sd["o"] = sd.events_bucket.map({"1": 0, "2-5": 1, "6-20": 2, "21+": 3}); sd = sd.sort_values("o")
fig, axes = plt.subplots(1, 2, figsize=(10, 3.8))
bars = axes[0].bar(sd.events_bucket, sd.pr, color=BLUE, width=0.55)
bar_labels(axes[0], bars, lambda v: f"{v:.2f}%", pad=0.5)
axes[0].set_title("Purchase rate (%)", loc="left", fontsize=10, color=INK2)
bars = axes[1].bar(sd.events_bucket, sd.ab, color=ORANGE, width=0.55)
bar_labels(axes[1], bars, lambda v: f"{v:.1f}%", pad=1)
axes[1].set_title("Cart abandonment (%)", loc="left", fontsize=10, color=INK2); axes[1].set_ylim(0, 110)
for ax in axes:
    ax.set_xlabel("Events per session"); ax.grid(axis="x", visible=False)
fig.suptitle("Deeper sessions convert far better: 21+ event sessions buy at 15x the rate of 2-5 event sessions",
             x=0.01, ha="left", fontsize=11)
save(fig, CH / "p4_08_session_depth.png")

# ---------------------------------------------------------------- 9. Hour x DOW heatmap (UTC)
h = q("SELECT day_of_week_0_sun dow, hour_utc, revenue, purchase_items, views FROM hour_dow_activity")
dows = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
grid = h.pivot(index="dow", columns="hour_utc", values="revenue").reindex(range(7))
fig, ax = plt.subplots(figsize=(10, 3.6))
im = ax.imshow(grid.values, aspect="auto", cmap=SEQ_BLUE)
ax.set_yticks(range(7), dows); ax.set_xticks(range(0, 24, 2), [f"{x:02d}" for x in range(0, 24, 2)])
ax.set_xlabel("Hour (UTC)"); ax.grid(False)
cb = fig.colorbar(im, ax=ax, pad=0.01); cb.set_label("Revenue", color=INK2); cb.outline.set_visible(False)
by_dow = h.groupby("dow").revenue.sum()
title(ax, "Revenue by day of week and hour (UTC)",
      f"Weekday late mornings UTC dominate; {dows[by_dow.idxmin()]} is the weakest day")
save(fig, CH / "p4_09_hour_dow_heatmap.png")
by_hour = h.groupby("hour_utc")[["purchase_items", "views", "revenue"]].sum()
by_hour["conv"] = 100 * by_hour.purchase_items / by_hour.views
note("p4_09", f"weakest dow {dows[by_dow.idxmin()]} {by_dow.min():.2f}, strongest {dows[by_dow.idxmax()]} {by_dow.max():.2f}; "
     f"peak hour {by_hour.revenue.idxmax()} UTC")

# ---------------------------------------------------------------- 10. Hourly traffic vs conversion
fig, axes = plt.subplots(2, 1, figsize=(9, 5), sharex=True)
axes[0].bar(by_hour.index, by_hour.views / 1e3, color=BLUE, width=0.7)
axes[0].set_title("Product views (thousands)", loc="left", fontsize=10, color=INK2); axes[0].grid(axis="x", visible=False)
axes[1].plot(by_hour.index, by_hour.conv, color=ORANGE, linewidth=2, marker="o", markersize=5,
             markeredgecolor=SURFACE)
axes[1].set_title("Items purchased per 100 views", loc="left", fontsize=10, color=INK2)
axes[1].set_xlabel("Hour (UTC)"); axes[1].set_xticks(range(0, 24, 2))
fig.suptitle("Traffic peaks late morning to evening UTC; night-time visitors are fewer but convert better",
             x=0.01, ha="left", fontsize=11)
save(fig, CH / "p4_10_hourly_traffic_conversion.png")
note("p4_10", f"conversion max {by_hour.conv.max():.2f}% at {by_hour.conv.idxmax()}h, min {by_hour.conv.min():.2f}% at {by_hour.conv.idxmin()}h")


# ---------------------------------------------------------------- 11-12. Cohort retention heatmaps
def cohort_heatmap(table, fname, who, sub):
    r = q(f"SELECT cohort_month, months_since, users FROM {table}")
    base = r[r.months_since == 0].set_index("cohort_month").users
    r["pct"] = 100 * r.users / r.cohort_month.map(base)
    p = r.pivot(index="cohort_month", columns="months_since", values="pct")
    p.to_csv(OUT / f"{table}_pct.csv")
    fig, ax = plt.subplots(figsize=(8, 3.8))
    shown = p.copy(); shown[0] = np.nan  # month 0 is 100% by definition; leave blank so colour shows months 1+
    im = ax.imshow(shown.values, cmap=SEQ_BLUE, vmin=0, vmax=np.nanmax(shown.values))
    for i in range(p.shape[0]):
        for j in range(p.shape[1]):
            v = p.values[i, j]
            if not np.isnan(v):
                txt = f"{int(base.iloc[i]):,}" if j == 0 else f"{v:.1f}%"
                dark = (j > 0) and v > np.nanmax(shown.values) * 0.6
                ax.text(j, i, txt, ha="center", va="center", fontsize=9, color="white" if dark else INK)
    ax.set_yticks(range(p.shape[0]), [f"{x:%b %Y}" + (" *" if x.month == 10 else "") for x in p.index])
    ax.set_xticks(range(p.shape[1]), ["Size"] + [f"M+{k}" for k in range(1, p.shape[1])])
    ax.grid(False); ax.tick_params(length=0)
    for sp in ax.spines.values():
        sp.set_visible(False)
    fig.suptitle(f"Monthly cohort retention: {who}\n{sub}", x=0.01, ha="left", fontsize=11)
    fig.text(0.01, 0.01, "* October cohort is left-censored: it includes users active before Oct 2019.",
             fontsize=8, color=INK2)
    save(fig, CH / fname)
    return p


pv = cohort_heatmap("cohort_retention_visitors", "p4_11_cohort_visitors.png", "visitors (any event)",
                    "Only ~10% of visitors come back the next month")
pb = cohort_heatmap("cohort_retention_buyers", "p4_12_cohort_buyers.png", "buyers (purchase)",
                    "Under 10% of Nov-Jan buyers purchase again the next month; Oct is inflated by existing customers")
note("p4_11", "visitor M+1: " + ", ".join(f"{i:%b} {v:.2f}%" for i, v in pv[1].dropna().items()))
note("p4_12", "buyer M+1: " + ", ".join(f"{i:%b} {v:.2f}%" for i, v in pb[1].dropna().items()))

# ---------------------------------------------------------------- 13-14. RFM segmentation
# Observation window Oct-Dec 2019, snapshot 2020-01-01; joined to churn label (Jan-Feb).
# R = recency quintile; F = order-count bands (most buyers have 1 order, so quintiles would tie);
# M = spend quintile. Segments use R and F (standard RFM map); M is reported.
con.sql("""
CREATE TABLE rfm AS
WITH obs AS (
    SELECT user_id, DATE_DIFF('day', MAX(order_ts), TIMESTAMP '2020-01-01') AS recency_days,
           COUNT(*) AS frequency, SUM(order_value) AS monetary
    FROM orders WHERE order_ts < '2020-01-01' GROUP BY user_id
), sc AS (
    SELECT *, NTILE(5) OVER (ORDER BY recency_days DESC, user_id) AS r,  -- user_id breaks ties deterministically
           CASE WHEN frequency = 1 THEN 1 WHEN frequency = 2 THEN 2 WHEN frequency = 3 THEN 3
                WHEN frequency <= 5 THEN 4 ELSE 5 END AS f,
           NTILE(5) OVER (ORDER BY monetary, user_id) AS m
    FROM obs
)
SELECT sc.*, u.churned, u.future_spend,
       CASE WHEN r >= 4 AND f >= 4 THEN 'Champions'
            WHEN r >= 3 AND f >= 3 THEN 'Loyal'
            WHEN r >= 4 AND f = 2  THEN 'Potential Loyalists'
            WHEN r >= 4 AND f = 1  THEN 'Recent One-timers'
            WHEN r = 3             THEN 'Need Attention'
            WHEN f >= 4            THEN 'Can''t Lose Them'
            WHEN f >= 2            THEN 'At Risk'
            WHEN r = 2             THEN 'Hibernating'
            ELSE 'Lost' END AS segment
FROM sc JOIN user_churn_features u USING (user_id)""")
con.sql(f"COPY rfm TO '{OUT / 'rfm_by_user.csv'}' (HEADER)")
seg = q("""SELECT segment, COUNT(*) buyers, SUM(monetary) revenue, SUM(churned) churners,
                  AVG(churned) * 100 churn_rate, AVG(monetary) avg_spend, AVG(recency_days) avg_recency,
                  AVG(frequency) avg_orders, SUM(future_spend) jan_feb_spend
           FROM rfm GROUP BY 1""")
seg["buyer_share"] = 100 * seg.buyers / seg.buyers.sum()
seg["revenue_share"] = 100 * seg.revenue / seg.revenue.sum()
seg["churn_share"] = 100 * seg.churners / seg.churners.sum()
order = ["Champions", "Loyal", "Potential Loyalists", "Recent One-timers", "Need Attention",
         "Can't Lose Them", "At Risk", "Hibernating", "Lost"]
seg = seg.set_index("segment").loc[order].reset_index()
seg.round(2).to_csv(OUT / "rfm_segments.csv", index=False)
print(seg.round(2).to_string(index=False))

fig, ax = plt.subplots(figsize=(10, 4.6))
x = np.arange(len(seg)); w = 0.27
for k, (col, colr, name) in enumerate([("buyer_share", BLUE, "Share of buyers"),
                                       ("revenue_share", AQUA, "Share of Oct-Dec revenue"),
                                       ("churn_share", ORANGE, "Share of churners")]):
    ax.bar(x + (k - 1) * w, seg[col], width=w - 0.03, color=colr, label=name)
ax.set_xticks(x, [s.replace(" ", "\n", 1) for s in seg.segment], fontsize=8.5)
ax.set_ylabel("%"); ax.legend(loc="upper right"); ax.grid(axis="x", visible=False)
title(ax, "RFM segments: size, revenue and churn share (Oct-Dec 2019 behaviour)",
      f"Champions + Loyal: {seg.buyer_share[:2].sum():.1f}% of buyers, {seg.revenue_share[:2].sum():.1f}% of revenue; "
      f"one-time segments supply {seg[seg.avg_orders == 1].churn_share.sum():.1f}% of churners")
save(fig, CH / "p4_13_rfm_segments_share.png")

fig, ax = plt.subplots(figsize=(8, 4.2))
ss = seg.sort_values("churn_rate")
bars = ax.barh(ss.segment, ss.churn_rate, color=BLUE, height=0.6)
bar_labels(ax, bars, lambda v: f"{v:.1f}%", horizontal=True, pad=0.8)
ax.axvline(85.02, color=INK2, linestyle="--", linewidth=1); ax.text(85.5, len(seg) - 0.45, "overall 85.0%", fontsize=8.5, color=INK2)
ax.set_xlim(0, 105); ax.grid(axis="y", visible=False); ax.set_xlabel("Churn rate in Jan-Feb 2020 (%)")
title(ax, "Churn rate by RFM segment", f"Even Champions churn at {seg.churn_rate[0]:.1f}%; Lost customers churn at {seg.churn_rate.iloc[-1]:.1f}%")
save(fig, CH / "p4_14_rfm_churn_rate.png")

# ---------------------------------------------------------------- 15. Pareto
cust = q("SELECT SUM(order_value) rev FROM orders GROUP BY user_id ORDER BY rev DESC")
cum = cust.rev.cumsum() / cust.rev.sum() * 100
xs = np.arange(1, len(cust) + 1) / len(cust) * 100
fig, ax = plt.subplots(figsize=(7.5, 4.2))
ax.plot(xs, cum, color=BLUE, linewidth=2)
ax.plot([0, 100], [0, 100], color=GRAY, linestyle=":", linewidth=1)
for pct in (10, 20, 50):
    yv = cum.iloc[int(np.ceil(len(cust) * pct / 100)) - 1]
    ax.plot(pct, yv, "o", color=BLUE, markersize=7, markeredgecolor=SURFACE, markeredgewidth=2)
    ax.annotate(f"top {pct}% → {yv:.1f}%", (pct, yv), xytext=(8, -14), textcoords="offset points", fontsize=9)
ax.set_xlabel("% of customers (ranked by revenue)"); ax.set_ylabel("% of revenue (cumulative)")
ax.set_xlim(0, 100); ax.set_ylim(0, 102)
title(ax, "Revenue concentration (Pareto), Oct 2019 – Feb 2020", "The top 20% of customers bring 59% of revenue")
save(fig, CH / "p4_15_pareto.png")

# ---------------------------------------------------------------- 16. December holiday cohort quality
dq = q("""WITH fo AS (SELECT user_id, DATE_TRUNC('month', MIN(order_ts)) m FROM orders GROUP BY 1)
          SELECT fo.m, COUNT(*) buyers, AVG(u.churned) * 100 churn, AVG(u.aov) aov, AVG(u.n_orders) orders,
                 AVG((u.n_orders >= 2)::INT) * 100 repeat_in_obs
          FROM user_churn_features u JOIN fo USING (user_id) GROUP BY 1 ORDER BY 1""")
dq.to_csv(OUT / "acquisition_month_quality.csv", index=False)
fig, axes = plt.subplots(1, 2, figsize=(10, 3.8))
labs = ["Oct *", "Nov", "Dec"]
cols = [GRAY, BLUE, ORANGE]
bars = axes[0].bar(labs, dq.churn, color=cols, width=0.55); bar_labels(axes[0], bars, lambda v: f"{v:.1f}%", pad=0.8)
axes[0].set_ylim(0, 100); axes[0].set_title("Churn rate in Jan-Feb (%)", loc="left", fontsize=10, color=INK2)
bars = axes[1].bar(labs, dq.aov, color=cols, width=0.55); bar_labels(axes[1], bars, lambda v: f"{v:.2f}", pad=0.5)
axes[1].set_title("Average order value (currency units)", loc="left", fontsize=10, color=INK2)
for ax in axes:
    ax.grid(axis="x", visible=False); ax.set_xlabel("Month of first order")
fig.suptitle("December-acquired customers churn more and spend less per order", x=0.01, ha="left", fontsize=11)
fig.text(0.01, 0.01, "* October is left-censored (includes pre-existing customers) and has the longest observation window.",
         fontsize=8, color=INK2)
save(fig, CH / "p4_16_december_cohort_quality.png")

# ---------------------------------------------------------------- 17. Churn by number of orders
co = q("""SELECT CASE WHEN n_orders >= 4 THEN '4+' ELSE n_orders::VARCHAR END k, COUNT(*) n, AVG(churned) * 100 churn
          FROM user_churn_features GROUP BY 1 ORDER BY 1""")
fig, ax = plt.subplots(figsize=(7.5, 3.8))
bars = ax.bar(co.k, co.churn, color=BLUE, width=0.55); bar_labels(ax, bars, lambda v: f"{v:.1f}%", pad=1)
for b, n in zip(bars, co.n):
    ax.text(b.get_x() + b.get_width() / 2, 4, f"n={n:,}", ha="center", fontsize=8.5, color="white")
ax.set_ylim(0, 100); ax.grid(axis="x", visible=False)
ax.set_xlabel("Orders in Oct-Dec 2019"); ax.set_ylabel("Churn rate (%)")
title(ax, "Churn falls ~20 points with every extra order", "Converting one-time buyers into 2-order buyers is the core lever")
save(fig, CH / "p4_17_churn_by_orders.png")

# ---------------------------------------------------------------- 18. Churn by engagement in last 31 days
e = q("""SELECT CASE WHEN events_last_31d = 0 THEN 'No activity' WHEN events_last_31d < events_prev_30d THEN 'Declining'
                     ELSE 'Flat or growing' END k,
                COUNT(*) n, AVG(churned) * 100 churn
         FROM user_churn_features GROUP BY 1""")
e["o"] = e.k.map({"No activity": 0, "Declining": 1, "Flat or growing": 2}); e = e.sort_values("o")
fig, ax = plt.subplots(figsize=(7.5, 3.8))
bars = ax.bar(e.k, e.churn, color=[ORANGE, BLUE, BLUE], width=0.55); bar_labels(ax, bars, lambda v: f"{v:.1f}%", pad=1)
for b, n in zip(bars, e.n):
    ax.text(b.get_x() + b.get_width() / 2, 4, f"n={n:,}", ha="center", fontsize=8.5, color="white")
ax.set_ylim(0, 100); ax.grid(axis="x", visible=False)
ax.set_xlabel("Site activity in the last 31 days of Dec vs the previous 30"); ax.set_ylabel("Churn rate (%)")
title(ax, "Silence predicts churn: no December activity → 93% churn", "Any recent browsing is protective, even if it is declining")
save(fig, CH / "p4_18_churn_by_engagement.png")
note("p4_18", "; ".join(f"{r.k}: {r.churn:.2f}% (n={r.n})" for r in e.itertuples()))

pd.DataFrame(notes).to_csv(OUT / "chart_notes.csv", index=False)
print("done:", len(list(CH.glob("p4_*.png"))), "charts")
