# Slide Deck Outline: "Who Will Stop Buying, and What Is It Worth?"

12 slides (16:9) for a 10-minute stakeholder or interview presentation. Each slide lists its **headline**, its **visual** (repo path), and **speaker notes**. Figures cite [key_numbers.csv](../key_numbers/key_numbers.csv).

| # | Headline (the slide title is the takeaway) | Visual | Speaker notes |
|---|---|---|---|
| 1 | **85% of buyers never came back. Here is who to save, and what it pays** | Title slide with three KPI tiles: 85% churn, 74% of Oct–Dec revenue from buyers who never returned, +81% projected ROI [K20, K23, K135] | Name, role, dataset: REES46 cosmetics, Oct 2019 – Feb 2020. Real 2019–20 data, 2025–26 lens. |
| 2 | **Retention is cheaper than acquisition, and acquisition keeps getting dearer** | Two benchmark callouts: acquisition 5–25× costlier [B2]; loss per new customer $9 → $29 [B4] | Why the business should care. India's beauty e-commerce market is context only [B8]. |
| 3 | **20.7M events became one trusted customer table** | Pipeline diagram: Kaggle Stage 1 → DuckDB SQL (6 checks, 15 queries) → Python → Power BI / HTML / Excel [K156, K157] | Data quality: 1,109,098 duplicates removed [K02]; the label re-derived in SQL matched 72,225 of 72,225 buyers [K57]. |
| 4 | **A 60-day churn window fits how people actually rebuy** | `images/phase3/p3_01_interpurchase_gap_hist.png` | 88.43% of repeat gaps fall within 60 days [K39]; false churn is 4.01% [K70]. The October cohort is left-censored. |
| 5 | **The checkout leaks: 87% of cart sessions end without an order** | `images/phase4/p4_01_funnel_overall.png` | 58.54% of views get a cart add, but only 22.75% of cart adds are purchased [K28, K29, K30]. |
| 6 | **The second order is the moment that matters** | `images/phase4/p4_17_churn_by_orders.png` | Churn 90.37% → 33.33% from 1 order to 4+ [K48]; odds ratio 5.93 [K95]. |
| 7 | **Silence predicts churn; cart removals don't** | `images/phase5/p5_01_churn_gaps_ci.png` | +15.69 pp after a silent month [K99]. H2 reversed: removers churn less [K96]. Effect sizes, not p-values. |
| 8 | **The model finds the customers worth keeping. Accuracy would have hidden that** | `images/phase6/p6_03_gain_lift.png` + `p6_01_roc_pr_curves.png` | Holdout AUC 0.7973 vs 0.7293 RFM baseline [K105, K162]. "Everyone churns" = 85.02% accuracy [K108]. Lift 3.64× [K111]. |
| 9 | **Habit and recency drive risk** | `images/phase6/p6_04_shap_importance.png` | Active days, last-31-day activity, repeat gap [K112]. Calibrated tiers are within 1 pt [K114]. |
| 10 | **Fund retention where value and risk are both high** | `images/phase7/p7_03_value_risk_matrix.png` | 12,735 Save-now buyers [K132]. Revenue at risk 3,508,675.24 is an upper bound (1.41× actual Jan–Feb revenue) [K130, K164]; say so before anyone asks. |
| 11 | **Targeted win-back returns +81.0%; blanket discounts only break even** | `images/phase7/p7_05_strategy_roi.png` + `p7_04_roi_sensitivity.png` | Break-even 4.69% [K136]; high-value blanket +0.1% [K137]. Assumptions [K134]. |
| 12 | **Three quick wins now, one big bet tested properly** | `images/phase9/p9_01_impact_effort.png` | R1, R2, R4 now; 3-arm second-order test (6,011 per arm, 13 weeks) [K150]. Ask: approve the pilot and the holdout. |

**Appendix slides (optional):** the definition sensitivity chart (`p3_03`), the RFM segments (`p4_13`, `p4_14`), the A/B design table (Phase 7 §7), the limitations, and screenshots of the dashboard's three pages.

**Design notes:** one message per slide, with the headline stating it. Use the project palette (blue `#2a78d6` for the main series, orange `#eb6834` for highlights), currency units on every money axis, and a source line under each chart.
