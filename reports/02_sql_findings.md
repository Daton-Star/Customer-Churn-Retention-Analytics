# Phase 2 — SQL Validation & Business Queries (DuckDB)

**Files:** [00_validation.sql](../sql/00_validation.sql) · [01_business_queries.sql](../sql/01_business_queries.sql) · [p2_run_sql.py](../src/p2_run_sql.py) · results in [outputs/phase2/](../outputs/phase2/)
**Re-run:** `pip install duckdb pandas` then `python src/p2_run_sql.py 00_validation.sql 01_business_queries.sql`. Every query writes `outputs/phase2/<name>.csv`.
Every number cites the Key Numbers table ([key_numbers.csv](../key_numbers/key_numbers.csv)). Money is in currency units.

---

## 1. Data cleaning done in Stage 1 (from data_quality_report.csv)
| Step | Rows | Share of raw |
|---|---|---|
| Raw clickstream events (5 monthly files) | **20,692,840** | 100% |
| Exact duplicate rows removed | 1,109,098 | 5.36% |
| Negative-price rows removed | 131 | <0.01% |
| **Clean events** | **19,583,618** | 94.64% |
| Zero-price rows (kept, flagged) | 104,157 | 0.50% |
| Null user_session | 4,598 | 0.02% |
| Null brand → "unknown" | 8,757,117 | 42.32% |
| Null category_code → use category_id | 20,339,246 | 98.29% |
| Unique users · products · sessions | 1,639,358 · 54,571 · 4,535,941 | |
| Raw events: view · cart · remove · purchase | 9,657,821 · 5,768,333 · 3,979,679 · 1,287,007 | |
| Session-based orders · buyers | 155,617 · 110,518 | |

## 2. Table validation (00_validation.sql)
| Check | Result |
|---|---|
| Row counts | orders 155,617; user_churn_features 72,225; daily_kpis 152 days; brand funnel 1,260; category funnel 2,432; hour×dow 168; session summary 20; cohorts 15 + 15; products 54,566 |
| Primary keys | All 8 keys unique (order_id, user_id, date, month×brand, month×category, dow×hour, month×bucket, product_id) |
| Nulls in keys/measures | 0 in every table. Nulls only where expected: category_code (53,942 of 54,566 products) and avg_days_between_orders (58,931 = exactly the single-order buyers) |
| Ranges | Orders 2019-10-01 → 2020-02-29; order_value 0.13 → 1,738.10; no negative values; churn cohort first/last orders all inside Oct–Dec 2019; hours 0–23 |
| Cross-table reconciliation | Revenue in orders = daily_kpis = brand funnel = category funnel = products = 6,348,267.70. Orders (155,617) = purchase sessions in session_summary |
| Churn label | Re-derived from orders.csv for all 72,225 users: label, future_orders and future_spend match 100% [K57] |

**Minor notes:** products.csv has 54,566 rows vs 54,571 unique products in the quality report (5 products appear only in removed rows). Brand-funnel monthly revenue differs slightly from order-month revenue because events are bucketed by event month and orders by order timestamp; totals match exactly.

## 3. Key findings from the 15 queries
| # | Query (technique) | Finding | So what |
|---|---|---|---|
| Q01 | Monthly KPIs + MoM (LAG) | Revenue peaked in Nov at 1,533,081.09, fell 30.26% in Dec, then rebounded 22.32% in Jan [K32–K34] | November (Black Friday) is the acquisition peak; December is weak for this store, so the holiday surge is a November story |
| Q02 | Cumulative revenue (running SUM, 7-day avg) | Daily revenue path and cumulative share are in results for dashboard use | Feeds the Executive Overview trend line |
| Q03 | New vs returning buyers (MIN OVER) | Returning share of monthly buyers grew from 14.60% (Nov) to 29.93% (Feb) [K36] | The repeat base is building, but 70% of each month's buyers are still first-timers |
| Q04 | Inter-purchase gaps (LAG) | Median gap 18.9 days, p75 38.0, p90 63.8; 88.43% of repeat gaps are within 60 days [K38, K39] | A 2-month window captures most real repeat behaviour, so the churn definition is defensible (tested further in Phase 3) |
| Q05 | RFM scores (NTILE ×3) ↔ churn label (JOIN) | Churn falls steadily from 94.48% (RFM 3) to 44.66% (RFM 15) [K40] | Simple RFM already ranks risk well; this is the baseline the ML model must beat |
| Q06 | Top brands (RANK overall + by month) | Missing brand is 40.38% of revenue; runail leads named brands at 5.41% [K41, K42] | Brand insights cover ~60% of revenue; fixing brand tagging is a data-quality action |
| Q07 | Brand conversion (ratios, RANK) | View→purchase ranges from 7.59% (concept) to 22.50% (bpw.style) among brands with 50k+ views [K43] | Low converters (concept, kapous, estel) are candidates for content, price or assortment review |
| Q08 | Category conversion ↔ products (JOIN) | Top category 1487580005092295511 (top brand uno) earns 418,307.97 [K44]; the #2 category (strong, median price 97.46) converts only 1.38% of views | High-ticket categories browse a lot but rarely buy, which suggests price or trust friction |
| Q09 | Cart abandonment trend (CTEs + LAG) | Session cart abandonment eased from 89.24% (Oct) to 85.83% (Dec), then rose to 87.55% (Feb) [K45] | Abandonment is persistently high and worsening after the holidays, so a cart-recovery flow is a priority |
| Q10 | December vs other acquisition cohorts (JOIN) | Churn by first-order month: Dec 87.34%, Nov 85.63%, Oct 82.61% (Oct left-censored); Dec-acquired AOV 35.68 vs 41.89 [K46, K47] | December-acquired customers are lower value and churn more, which is the holiday-cohort effect to test in Phase 5 |
| Q11 | Churn by order count (window shares) | Churn by orders: 1 → 90.37%, 2 → 70.00%, 3 → 51.69%, 4+ → 33.33% [K48]; single-order buyers hold 58.80% of cohort spend [K49] | **Getting the second order is the biggest lever**: each extra order cuts churn by roughly 20 points |
| Q12 | Engagement trend & cart removal (CASE) | No activity in the last 31 days → 92.93% churn [K50] vs 67.17–82.12% with any activity [K51]. Heavy cart removers churn *less* (81.53% vs 89.05%) [K52] | Silence is the warning sign, not cart removal. Removal looks like active comparison shopping by engaged users |
| Q13 | Pareto (running SUM) | Top 1% of customers = 11.19% of revenue, top 10% = 43.00%, top 20% = 59.31% [K53] | Revenue is concentrated; the top decile justifies VIP-level retention spend |
| Q14 | Peak hours (RANK, UTC) | Top revenue slot is Thu 11:00 UTC (72,788.65) [K54]; best conversion occurs in low-traffic night hours (UTC) | Schedule pushes and WhatsApp messages just before the late-morning UTC peak |
| Q15 | Session depth vs conversion | Single-event sessions are 63.78% of sessions but 0.88% of purchases [K55]; 21+ event sessions convert at 31.97% vs 2.13% for 2–5 events [K56] | Bounce traffic dominates; moving visitors from 2–5 to 6+ events (recommendations, search) is where conversion grows |

## 4. Interpretation notes for later phases
- **The December nuance:** Phase 1 saw that customers who *bought* in December churned less (78.7% vs 88.4%). Q10 shows why: that comparison is driven by recency. Customers *acquired* in December churn more (87.34%) and spend less. Phase 5 will test this properly.
- **The cart-removal hypothesis is reversed in raw data** (Q12). Phase 5 will test it with Mann-Whitney and control for engagement.
- **Engagement decline:** the strong signal is zero activity in the last 31 days. "Declining but active" users churn least, because any recent activity is protective.

## Phase 2 summary
All 11 tables passed validation: keys are unique, there are no unexpected nulls, revenue reconciles to 6,348,267.70 across five tables, and the churn label re-derives 100% from orders.csv. The 15 queries use CTEs, JOINs, LAG, NTILE, RANK and running totals. Three findings stand out. Churn falls from 90.37% after one order to 33.33% after four or more. Inactivity in the final month predicts churn at 92.93%. And 88.43% of repeat gaps fall within 60 days, which supports the 2-month churn window going into Phase 3.
