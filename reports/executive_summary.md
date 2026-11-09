# Executive Summary: Customer Churn & Retention, Cosmetics E-commerce

**Prepared by:** Pooja · **Data:** REES46 cosmetics online store, 1 Oct 2019 – 29 Feb 2020 (public Kaggle dataset) · **Money:** the dataset's currency units (not converted)
*Every figure cites the project's Key Numbers table ([key_numbers.csv](../key_numbers/key_numbers.csv)) by id.*

---

## 1. The question
Most of this store's buyers buy once and never come back. Acquiring customers keeps getting more expensive: online merchants' loss per new customer rose from $9 to $29 in under a decade [B4], and acquiring is 5–25× costlier than retaining [B2]. The business question is therefore:

> **Who is about to stop buying, how much revenue does that put at risk, and which retention actions pay for themselves?**

The data are real 2019–20 events, read with a 2025–26 lens. India's beauty and personal-care market is heading to about $34B by 2028, with online growing fastest [B8]. That is context for why retention matters, not a claim about this store.

## 2. What we worked with
- **Raw data:** 20,692,840 raw clickstream events, reduced in Stage 1 (Kaggle) to 19,583,618 clean events [K01, K04].
- **Customers and orders:** 155,617 orders from 110,518 buyers, worth 6,348,267.70 [K12–K14].
- **Churn definition:** an Oct–Dec 2019 buyer who placed no order in Jan–Feb 2020. The cohort is 72,225 buyers [K18].
  - The 60-day window is justified: 88.43% of repeat purchases happen within 60 days [K39], and only 4.01% of "churners" return in the following month [K70].
- **Validation:** the churn label was re-derived independently in SQL and matched for 72,225 of 72,225 buyers [K57].
- **Known limits:** October buyers are left-censored, because the data starts on 1 Oct, and brand is missing on 40.38% of revenue [K41].

## 3. Key findings

**1. Churn is the norm, and one-time buying drives it.**
- 85.02% of the Oct–Dec cohort did not return [K20].
- 81.59% of those buyers had bought only once [K24]. Single-order buyers churned at 90.37% vs 61.28% for repeat buyers, an odds ratio of 5.93 [K25, K26, K95].
- Each extra order lowers churn: 90.37% → 70.00% → 51.69% → 33.33% for 1, 2, 3 and 4+ orders [K48].

**2. Silence is the early warning.** Buyers with no site activity in their last 31 days churned at 92.93%, vs 77.24% for active buyers (+15.69 pp) [K99]. Heavy cart-removers churn *less*, because removal is engaged comparison shopping and not a warning sign [K96].

**3. The funnel leaks at checkout.** 87.21% of sessions with a cart end without an order [K30]. That is 16.99 pp above Baymard's 70.22% average [B1, K154], though the definitions differ.

**4. Value is concentrated.**
- The top 10% of customers bring 43.00% of revenue [K53].
- A Champion has spent 336.98 to date, against 41.77 for a Recent One-timer [K121].
- The top predicted-CLV decile delivered 49.70% of actual next-period spend [K127].

**5. Churn can be predicted well enough to act on.**
- An XGBoost model chosen by cross-validation reaches a holdout ROC-AUC of 0.7973, against 0.7293 for an RFM-only model on the same holdout [K105, K162].
- Calibrated risk tiers match actual churn within 1 point [K114].
- Accuracy is the wrong yardstick: "everyone churns" scores 85.02% accuracy but finds nobody to save [K108].
- The 20% lowest-risk buyers contain 56.38% of all stayers, a lift of 3.64× [K111].

## 4. The money
- **69,116 current buyers were scored** for Mar–Apr 2020, and 58,632.95 of them are expected to churn [K117].
- **Revenue already lost:** 74.18% of Oct–Dec revenue (2,858,778.71) came from buyers who never returned [K23, K22].
- **Revenue at risk (upper bound): 3,508,675.24** of 4,222,121.94 potential two-month spend [K130]. It assumes every at-risk buyer would spend like a retained one, so it is 1.41× the store's actual Jan–Feb revenue of 2,494,244.14 [K164, K163]. It sizes the prize and ranks customers; it is not a revenue forecast.
- **Value × risk targeting:** the 12,735 "Save now" buyers (high value, churn probability ≥ 0.80) hold 23.3% of that risk [K132].
  - A personalised win-back aimed at them returns a projected **+81.0%** at a 10% save rate: 14,642.53 net on 18,068.63 of cost per wave [K135].
  - It breaks even at a **4.69%** save rate, half the low end of practitioner win-back rates [K136, B7].
- **Blanket discounts don't work.** Discounting every high-value buyer only breaks even (+0.1%), because many of them weren't leaving [K137].

## 5. Recommendations (prioritised)

| # | Action | Owner | Expected impact |
|---|---|---|---|
| R1 | Personalised win-back for 12,735 Save-now buyers, with a holdout | CRM / Retention | +14,642.53 net per wave; break-even 4.69% [K135, K136] |
| R2 | No-discount automated nudges for 46,818 low-value, high-risk buyers | Marketing automation | +18,776.21 net; break-even 0.50% save rate [K152] |
| R3 | Second-order journey for first-time buyers, A/B tested first | CRM + Analytics | +5,035.11 a month at +2 pp [K149] |
| R4 | Cart-recovery flow | E-commerce | Each 1 pp less abandonment = 402,730.33 over five months [K153] |
| R5 | Protect loyal buyers with perks, not discounts | CRM / Loyalty | Saves 23,149.22 of discounts per campaign [K151] |
| R6–R8 | Post-holiday follow-up, brand data fixes, monthly re-scoring with holdouts | CRM, Data, Analytics | Enablers; see the full report |

**One correction to our own plan:** sizing showed that a 10% offer to *every* first-time buyer needs a +9.91 pp uplift to pay back [K148]. The A/B test therefore has three arms: control, message only, and message + offer. Each arm has 6,011 buyers, and the test runs for 13 weeks [K150].

## 6. Limitations
- **Scope:** one store and one season. Patterns transfer; levels may not.
- **Censoring:** the October cohort is left-censored.
- **Model estimates:** churn scores and CLV rank customers well, but BG/NBD over-forecasts post-holiday volume by 29% [K123]. Use them for ranking, not budgeting.
- **Assumptions:** campaign economics rest on stated assumptions (contact 0.50, 10% discount, 40% margin) [K134]. They are stress-tested, and only holdout tests can confirm them.
- **Correlation, not causation:** the statistical tests show association. The A/B test is how cause gets proven.

## 7. Next steps
1. **Weeks 1–2:** launch R1, R2 and R4, each with a 10% holdout.
2. **Then:** start the 3-arm second-order test.
3. **Every month:** re-score customers, check calibration by tier, and refresh the dashboard ([docs/index.html](../docs/index.html), published with GitHub Pages).
