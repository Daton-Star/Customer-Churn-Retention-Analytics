# Resume Section and LinkedIn Post

All figures come from [key_numbers.csv](../../key_numbers/key_numbers.csv). Rounded forms are logged as [K156], [K161] and [K165]. The resume uses rounded numbers because recruiters skim; keep the exact values for interviews. Campaign results are simulations, so they are always labelled "projected". Money is in the dataset's currency units, so never write ₹ or $. Label the work as a **personal / portfolio project on public data**.

**Avoid "3.5M at risk" on the resume.** It is an upper bound that is 1.41× the store's actual Jan–Feb revenue [K164], and a hiring manager will spot that. Use the historical figure instead: 74% of Oct–Dec revenue came from buyers who never returned [K23].

---

## Resume: project entry

### Two bullets that cover the whole project (225–235 characters each, counted with spaces)
Numbers from [K20, K23, K25, K26, K161, K165]. Character counts in brackets.

- Exposed revenue leakage in 20.7M e-commerce clickstream events using SQL (DuckDB) and Python: 85% of quarterly buyers never returned yet accounted for 74% of revenue, and one-time buyers churned at 90% vs 61% for repeat buyers. (227)
- Prioritised 69K customers with an XGBoost churn model (AUC 0.80) and RFM segments, then projected +81% ROI for a CLV-targeted win-back of 12.7K buyers and designed a 3-arm A/B test, delivered in Excel and a Power BI star schema. (228)

### Three bullets that cover the whole project (225–235 characters each, counted with spaces)
Data and churn insight, prediction and segmentation, economics and testing. Numbers from [K20, K23, K25, K26, K140, K161, K165, K166]. Character counts in brackets.

- Exposed revenue leakage by cleaning 20.7M e-commerce clickstream events in SQL (DuckDB) and Python: 85% of quarterly buyers never returned yet accounted for 74% of revenue; one-time buyers churned at 90% vs 61% for repeat buyers. (229)
- Prioritised 69K active customers by churn risk with an XGBoost model (AUC 0.80 vs 0.73 RFM baseline), SHAP drivers and RFM segmentation, giving retention teams a ranked customer contact list in Excel and a Power BI star schema. (227)
- Projected +81% ROI for a targeted win-back of 12.7K high-value, high-risk customers using lifetime value (CLV) and churn risk, showed blanket discounts only break even, and designed a 3-arm A/B test (6,011 per arm) to prove lift. (229)

### Four long-form bullets (225–235 characters each, counted with spaces)
Numbers from [K20, K23, K25, K26, K140, K161, K165]. Character counts in brackets.

- Exposed revenue leakage in 20.7M e-commerce clickstream events: buyers who never returned (85% of the quarter's customers) accounted for 74% of quarterly revenue, found through churn and cohort analysis in SQL (DuckDB) and Python. (230)
- Pinpointed the second order as the top retention lever: one-time buyers churned at 90% vs 61% for repeat buyers, proven with hypothesis testing and RFM segmentation, then turned it into a 3-arm A/B test design (6,011 per arm). (226)
- Prioritised 69K active customers by churn risk with an XGBoost model (AUC 0.80 vs 0.73 RFM baseline) and SHAP drivers, so retention teams reach the highest-risk customers first through a ranked Excel action list and dashboard. (226)
- Projected +81% ROI for a targeted win-back of 12.7K high-value, high-risk customers, breaking even below a 5% save rate, and showed blanket discounts only break even, by combining churn risk with predicted customer lifetime value. (230)

### Impact bullets (final: outcome first, XYZ form)
Each bullet leads with a quantified outcome, then the method and tool, under 30 words. Simulated results say "projected" or "showed". Numbers from [K20, K23, K25, K26, K57, K135, K136, K140, K148, K161, K165, K166, K167]. Paste as plain text in a single-column resume.

1. Exposed revenue leakage: buyers who never returned (85% of the quarter's customers) accounted for 74% of quarterly revenue, found through churn and cohort analysis in SQL and Python.
2. Pinpointed the top retention lever, the second order: one-time buyers churned at 90% vs 61% for repeat buyers, proven with hypothesis testing and RFM segmentation in Python.
3. Enabled trusted analysis of 20.7M clickstream events by cleaning them into order and customer tables with SQL (DuckDB) and Python, achieving a 100% churn-label match across 72,225 buyers.
4. *(Data Analyst)* Prioritised 69K active customers by churn risk with an XGBoost model (AUC 0.80 vs 0.73 baseline) and SHAP drivers, so retention teams target the highest-risk first.
   *(Business Analyst)* Prioritised 69K active customers for retention outreach by building a churn-risk score that ranks who to contact first, with drivers explained in plain business terms.
5. Projected +81% ROI for a targeted win-back of 12.7K high-value, high-risk customers, breaking even below a 5% save rate, by combining churn risk with customer lifetime value.
6. Protected margin by showing a blanket 10% new-buyer discount would lose money unless repeat buying rose 10 points; redesigned it as a 3-arm A/B test (6,011 per arm).
7. Sized a ~6% revenue upside for every 1-point cut in cart abandonment (87% of cart sessions ended without an order) and proposed a cart-recovery flow with a holdout test.
8. Turned churn scores into a ranked contact list for 69K customers through Excel and interactive HTML dashboards, plus a Power BI star schema with 35 DAX measures.

**Pick by role:** Data Analyst 1, 4 (DA), 5, then 3. Business Analyst 1, 5, 6, then 4 (BA). E-commerce or product roles: add 7.
**After you build the .pbix:** change bullet 8 to "…through Power BI (35 DAX measures), Excel and interactive HTML dashboards."

**Title line** (plain separators, so ATS parsers read every tool)
> **Customer Churn & Retention Analytics** | Python | SQL | DuckDB | Power BI | Excel | Machine Learning | Statistics | Personal project on public data (20.7M events)

**Core bullets** (each under 30 words). On a one-page resume, use the first three, or the three from the variant that matches the job.
- Processed 20.7M e-commerce clickstream events into order and customer tables; validated them in DuckDB SQL with 6 integrity checks and 15 business queries (CTEs, window functions).
- Found 74% of Oct–Dec revenue came from buyers who never returned; one-time buyers churned at 90% vs 61% for repeat buyers.
- Built an XGBoost churn model (AUC 0.80 vs 0.73 RFM baseline) with SHAP drivers; targeted 12.7K high-value buyers in a win-back projecting +81% ROI.
- Delivered Power BI, Excel and interactive HTML dashboards (executive, funnel, at-risk action list) with 35 verified DAX measures and 8 prioritised recommendations.

**One-line version**
> Churn & retention analytics on 20.7M e-commerce events (SQL, Python, XGBoost AUC 0.80, Power BI): found 74% of quarterly revenue came from non-returning buyers; targeted win-back projects +81% ROI.

### Variant A: Data Analyst (technical depth), pick 3
- Cleaned and validated 20.7M clickstream events into order and customer tables; re-derived the churn label in SQL, matching 72,225 of 72,225 buyers.
- Wrote 15 DuckDB SQL analyses (CTEs, window functions, NTILE RFM, cohorts, Pareto) and 18 EDA charts on funnel, cohort and RFM behaviour.
- Compared logistic regression, Random Forest and XGBoost with 5-fold CV; reported AUC 0.80, PR-AUC and 3.6× lift instead of a misleading 85% accuracy.
- Built a 35-measure Power BI star schema and an Excel what-if model linking save rate and margin to campaign ROI.

### Variant B: Business Analyst (decisions and stakeholders), pick 3
- Framed churn as a revenue problem: 85% of Oct–Dec buyers never returned, and they had brought 74% of that quarter's revenue.
- Simulated retention campaigns with ROI, break-even and sensitivity; a targeted win-back projects +81% ROI while blanket high-value discounts only break even.
- Delivered 8 prioritised recommendations with owners, KPIs and a 3-arm A/B test design (6,011 per arm), plus executive, funnel and action-list dashboards.
- Turned 6 hypothesis tests into campaign triggers: a silent last month adds about 16 points of churn, while cart removals signal engagement, not risk.

### 25 ATS keywords
These are the terms Indian Data Analyst and Business Analyst job posts actually use, and every one is covered by this project.

SQL · DuckDB · Python · pandas · Excel · Power BI · DAX · Data Cleaning · ETL · Data Visualization · KPI Dashboards · Stakeholder Reporting · Clickstream Analytics · Funnel Analysis · Cart Abandonment · Cohort Analysis · RFM Segmentation · Churn Prediction · Predictive Modeling · XGBoost · SHAP · Hypothesis Testing · A/B Testing · Customer Lifetime Value (CLV) · ROI Analysis

*If you have room in a skills line, also add:* scikit-learn, Statistics, Customer Segmentation.

---

## LinkedIn post (about 180 words)

Post it only once the GitHub, dashboard and Kaggle links are live. Attach [linkedin_carousel.pdf](linkedin_carousel.pdf) as a document, because a carousel gets far more reach than a text post.

> **85% of buyers never came back. So who's worth saving?**
>
> I just finished an end-to-end churn and retention project on real cosmetics e-commerce data: 20.7M clickstream events and 110K buyers (REES46, Oct 2019 – Feb 2020).
>
> What I found:
> 🔹 85% of Oct–Dec buyers placed no order in Jan–Feb, and they had brought 74% of that quarter's revenue. One-time buyers churned at 90% vs 61% for repeat buyers, so the second order is the moment that matters.
> 🔹 A silent last month raised churn by about 16 points. Cart removals didn't. They signal engaged shoppers.
> 🔹 An XGBoost model (AUC 0.80) ranks who is likely to leave. A model that predicts "everyone churns" is 85% accurate, and useless.
> 🔹 Targeting 12.7K high-value, high-risk buyers projects a +81% ROI and breaks even below a 5% save rate. Blanket discounts only break even.
>
> Biggest lesson: a "10% off for every new buyer" test would need a ~10-point lift to pay back, so I redesigned it with a message-only arm.
>
> Stack: SQL (DuckDB), Python, XGBoost, SHAP, Power BI, Excel.
> 🔗 Dashboard: [link] · Code: [GitHub link] · Kaggle notebook: [link]
>
> #DataAnalytics #CustomerRetention #SQL #Python #PowerBI #BusinessAnalytics #DataAnalyst
