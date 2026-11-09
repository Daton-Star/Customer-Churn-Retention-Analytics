# Phase 1 — Business Framing
**Project:** Customer Churn & Retention Analytics for E-Commerce
**Analyst:** Pooja Ingale · **Data:** REES46 "eCommerce Events History in Cosmetics Shop" (Kaggle), Oct 2019 – Feb 2020
**Framing:** real 2019–20 clickstream data, analysed with 2025–26 business context.

Every number below is in the running Key Numbers table ([key_numbers.csv](../key_numbers/key_numbers.csv), IDs in brackets like [K20]). Benchmarks are in [benchmarks.csv](benchmarks.csv), IDs like [B1]. Prices are in the dataset's own **currency units** (unspecified); they are not converted to ₹.

---

## 1. Problem statement
An online beauty & personal-care store attracts heavy browsing traffic, but most buyers never come back. Of the **72,225** customers who bought in Oct–Dec 2019 [K18], **85.02%** placed no order in Jan–Feb 2020 [K20]. Those customers who later churned had spent **2,858,778.71 currency units** in Oct–Dec, **74.18%** of the cohort's spend [K22, K23]. With acquisition costs rising (CAC up as much as 60% in five years [B4]; acquiring a customer is 5–25x costlier than retaining one [B2]), the store cannot keep buying replacement customers.

**Goal:** measure churn and the revenue at risk, find the behaviours and funnel frictions that drive it, predict who churns next, and fund the retention actions with the best expected ROI.

## 2. Stakeholders
| Stakeholder | What they need from this project | Decision they own |
|---|---|---|
| CEO / Leadership | Size of churn, revenue at risk, ROI of retention | Retention budget |
| CRM & Retention Marketing | Who to target, when, with which offer and channel (WhatsApp / push / email) | Campaign design and spend |
| E-commerce / Product (UX) | Where the view → cart → purchase funnel leaks; cart abandonment | Checkout and on-site fixes |
| Category & Brand Managers | Brands and categories that convert and retain well or badly | Assortment, brand partnerships, replenishment |
| Finance | CLV, break-even save rate, campaign ROI | Approve spend |
| Data / BI team | Reusable SQL, model, dashboards | Maintain the pipeline |

## 3. Business questions
1. **How big is churn, and how much revenue is at risk?** Churn rate of the Oct–Dec cohort, the spend of churners, and the expected future value of currently at-risk buyers. *(Phases 2, 3, 7)*
2. **Is our churn definition sound?** Do inter-purchase gaps support a 2-month window, and how sensitive is churn to the definition? *(Phase 3)*
3. **Which behaviours, brands, categories and funnel frictions drive churn?** Single orders, cart removals, engagement decline, brand/category mix, cart abandonment, session depth. *(Phases 2, 4, 5)*
4. **Do December holiday buyers retain worse than other buyers?** *(Phases 2, 4, 5)*
5. **Who will churn next, and who is worth saving?** Churn probability × customer value → risk tiers and an action list. *(Phases 6, 7)*
6. **Which retention actions should we fund, and what is the expected ROI?** Campaign simulation, break-even save rate, A/B test design. *(Phases 7, 9)*

## 4. KPI definitions
Grain and source are fixed now so every later phase computes KPIs the same way.

| KPI | Definition (formula) | Grain / source |
|---|---|---|
| **Churn rate** | Oct–Dec 2019 buyers with **no order in Jan–Feb 2020** ÷ all Oct–Dec 2019 buyers | User; `user_churn_features.churned` |
| **Retention rate** | 1 − churn rate (same cohort, same window). Cohort retention: share of a month-*m* cohort active in month *m+k* | User; `user_churn_features`, `cohort_retention_*.csv` |
| **Repeat-purchase rate** | Buyers with ≥ 2 orders ÷ all buyers, in a stated window | User; `orders.csv` |
| **AOV** | Revenue ÷ orders | Order; `orders.order_value` |
| **Purchase frequency** | Orders ÷ buyers, in a stated window | User; `orders.csv` |
| **Historical CLV** | Total spend per customer to date (Phase 7 adds predictive CLV via BG/NBD + Gamma-Gamma) | User; `orders.csv` |
| **Revenue at risk** | Σ over currently active buyers of P(churn) × expected value over the next period. Phase 1 proxy: Oct–Dec spend of buyers who churned | User; model output + CLV |
| **View → cart conversion** | Event level: cart events ÷ view events. User level (brand/category): buyers ÷ viewers where available | `daily_kpis`, `brand_monthly_funnel`, `category_monthly_funnel` |
| **Cart → purchase conversion** | Purchased items ÷ cart events (event level) | Same as above |
| **View → purchase conversion** | Purchased items ÷ view events | Same as above |
| **Cart abandonment rate** | Sessions with a cart event but **no purchase** ÷ sessions with a cart event | Session; `session_summary.csv` |
| **Cart removal rate** | Remove-from-cart events ÷ cart events | User; `user_churn_features.cart_remove_rate` |
| **MoM growth** | (Metric_m − Metric_m−1) ÷ Metric_m−1 for revenue, orders, buyers | Month; `orders.csv` |

**Order definition (from Stage 1):** an order = all purchase events by one user within one session.

## 5. Baseline snapshot (what leadership sees on day 1)
| Metric | Value | Ref |
|---|---|---|
| Raw clickstream events processed in Stage 1 | **20,692,840** | K01 |
| Clean events after dedup and filters | **19,583,618** | K04 |
| Orders · buyers (Oct–Feb) | 155,617 · 110,518 | K12, K13 |
| Revenue (Oct–Feb) | 6,348,267.70 currency units | K14 |
| AOV | 40.79 currency units | K15 |
| Repeat-purchase rate (5 months) | 21.09% | K17 |
| Churn rate (Oct–Dec buyers, no order Jan–Feb) | **85.02%** | K20 |
| Churn: single-order vs multi-order buyers | 90.37% vs 61.28% | K25, K26 |
| Session cart abandonment | 87.21% (benchmark 70.22% [B1]) | K30 |
| Session conversion | 3.43% | K31 |

**Early signals to test later:** 81.59% of the cohort bought only once [K24], and single-order buyers churn far more; that is hypothesis H1 for Phase 5. Session cart abandonment sits well above the Baymard average, though the definitions differ (Baymard measures checkout-level abandonment across studies, ours is any session with a cart event), so Phase 4 will treat that comparison with care.

## 6. Data cleaning done in Stage 1 (pooja's Kaggle notebook)
| Step | Rows affected | Ref |
|---|---|---|
| Raw events loaded (5 monthly files) | 20,692,840 | K01 |
| Exact duplicate rows removed | 1,109,098 | K02 |
| Negative-price rows removed | 131 | K03 |
| Zero-price rows (kept; flagged) | 104,157 | K10 |
| Null user_session | 4,598 | data_quality_report |
| Null brand (standardised to "unknown") | 8,757,117 | K08 |
| Null category_code (so we use category_id) | 20,339,246 | K09 |
| **Clean events** | **19,583,618** | K04 |

Phase 2 re-validates every table (row counts, keys, nulls, ranges) in DuckDB.

## 7. Scope
**In scope:** buyers and visitors of one online cosmetics store, Oct 2019 – Feb 2020; churn of Oct–Dec buyers measured in Jan–Feb; funnel, cohort, RFM, statistical tests, churn model, CLV, retention economics, dashboards and recommendations.

**Out of scope:** marketing spend and actual CAC (not in the data), margins/costs (ROI uses stated assumptions and cited benchmarks), returns and refunds, demographics and geography, product-level text, and any currency conversion.

## 8. Market context (2025–26, context only)
- **Rising CAC:** acquisition costs up as much as 60% in five years; merchants lose $29 per new customer vs $9 in 2013 [B4].
- **Retention economics:** acquiring a customer costs 5–25x more than retaining one, and +5% retention has been linked to +25–95% profit (Bain) [B2, B3].
- **Cart abandonment** averages 70.22% across 50 studies [B1].
- **Beauty repeat rate:** 17% of new Health & Beauty customers repurchase within 180 days [B5].
- **Triggered messaging works:** automations were 2% of email sends but 30% of email revenue in 2025, and abandoned-cart + welcome flows drove 76% of automation orders [B6].
- **India:** the beauty & personal-care market is projected at $34B by 2028 with online channels growing ~25% CAGR (Nykaa × Redseer, 2024), and Redseer now projects ~$40B by 2030 [B8]. Used as context only; it is never mixed with this dataset's numbers.
- **Save-rate range for the campaign simulation:** 10–30% reactivation is a practitioner estimate from a secondary compilation [B7]. It will be used only as a sensitivity range, not a point estimate.

## 9. Assumptions
1. Churn = no purchase in the 2-month window after the observation period. This is a business definition, not a cancellation event; Phase 3 tests it against inter-purchase gaps and an alternative window.
2. Session-based orders from Stage 1 are treated as real orders.
3. All timestamps are UTC; hour-of-day patterns are UTC, not local time.
4. Retention-campaign costs and save rates are assumptions anchored to cited benchmarks and shown with sensitivity tables.

## 10. Limitations
- **Short window:** 5 months total, and only a 2-month prediction window. Beauty replenishment cycles can exceed 2 months, so some "churners" may simply be slow repurchasers (Phase 3 quantifies this).
- **Left-censoring:** October cohorts include customers who existed before Oct 2019, so October "new" cohorts are inflated and their retention is not comparable to later cohorts.
- **Seasonality:** the observation window includes Black Friday and December holidays, and the prediction window is post-holiday Jan–Feb, which can exaggerate churn.
- **Missing attributes:** category_code is missing on 20,339,246 of 20,692,840 raw rows and brand on 8,757,117, so category analysis uses category_id and "unknown" is the largest brand group.
- **No cost, margin, or marketing data:** ROI relies on assumptions and benchmarks.
- **Single store, 2019–20:** pre-dates quick commerce and current WhatsApp-first CRM, so findings are directional for today's market.
- **Currency** is unspecified; values are reported in currency units.
- **Small count mismatches:** session_summary totals 4,537,808 sessions vs 4,535,941 unique sessions in the quality report, likely because a few sessions span a month boundary. This is immaterial for rates and will be checked in Phase 2.

## Phase 1 summary
Churn is the core problem: 85.02% of Oct–Dec buyers did not return in Jan–Feb, and they carried 74.18% of the cohort's spend. Single-order buyers (81.59% of the cohort) churn at 90.37% vs 61.28% for repeat buyers, which makes the second purchase the key lever to investigate. KPIs, scope, limitations and 8 cited benchmarks are fixed, and the Key Numbers table holds 31 verified numbers. Next is Phase 2: validating the tables and writing the 15 business SQL queries in DuckDB.
