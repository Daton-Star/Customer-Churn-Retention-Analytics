# Interview Prep: Customer Churn & Retention Project

Figures cite [key_numbers.csv](../../key_numbers/key_numbers.csv). Practise saying the numbers in round form out loud (for example "about 85%") once you know the exact value behind each one. Text in **[brackets]** is for you to fill in with what you actually did. Never claim anything you didn't do.

---

## 60-second pitch
> "I took a public cosmetics e-commerce dataset, 20.7 million clickstream events and 110 thousand buyers from late 2019, and asked a business question: who is about to stop buying, what is that worth, and which retention actions pay for themselves?
> I validated the data in SQL, defined churn as no order in the next 60 days, and backed that window with repurchase-gap data. 85% of buyers didn't come back, and one-time buyers were the core of the problem.
> I built an XGBoost model with a holdout AUC of about 0.80, calibrated it into risk tiers, and combined risk with predicted lifetime value. Those non-returning buyers had brought about 74% of the quarter's revenue. Ranking by value and risk picked 12,735 buyers for a targeted win-back that projects an 81% return, about 14.6 thousand net per wave, and breaks even below a 5% save rate.
> I delivered it as Power BI, HTML and Excel dashboards with eight prioritised recommendations and an A/B test plan."

*(Exact values: 85.02% [K20], 74.18% [K23], AUC 0.7973 [K105], +81.0% and 14,642.53 net [K135], 4.69% [K136].)*

## STAR story: "Tell me about a time your analysis changed a decision"
- **Situation:** 85.02% of the store's Oct–Dec buyers didn't return [K20]. The obvious play was a discount for every valuable customer.
- **Task:** Work out who to target and whether a retention campaign would pay for itself, with numbers a manager could trust.
- **Action:**
  - Scored churn risk with a calibrated XGBoost model, whose tiers came within 1 point of actual churn [K114].
  - Predicted 90-day CLV with BG/NBD.
  - Simulated four targeting strategies with ROI, break-even and sensitivity.
  - While building the dashboard, found that 30,617 recent buyers had a blank CLV because of a library edge case [K144]. Fixed the formula, re-ran everything, and corrected the earlier figures openly.
- **Result:**
  - Targeting the 12,735 high-value, high-risk buyers projects +81.0% ROI with a 4.69% break-even [K132, K135, K136]. A blanket high-value discount only breaks even (+0.1%) [K137].
  - Sizing the planned "10% off for every new buyer" test showed it needs a +9.91 pp uplift to pay back [K148]. I redesigned it with a message-only arm, avoiding a projected loss of 21,222.86 a month at the planned effect size [K149].

---

## 21 questions with answers

**1. How did you handle 20M rows?**
I split the work into two stages.
- **Stage 1 (Kaggle):** reduced the raw 20,692,840 events [K01] to eleven summary tables at order, customer, day and brand-month grain. It removed 1,109,098 exact duplicates and 131 negative-price rows, leaving 19,583,618 clean events [K02–K04]. **[Describe exactly how you processed the raw files in Kaggle, e.g. chunked reads, dtype downcasting, or DuckDB/Polars, and how long it took. Only what you did.]**
- **Stage 2 (local):** everything downstream runs on 155,617 orders and 72,225 customer rows [K12, K18] in DuckDB and pandas, in minutes, on a laptop. I validated that the summary tables reconcile: revenue matches 6,348,267.70 across tables [K14], and the churn label re-derived from orders matched 72,225 of 72,225 buyers [K57].

**2. How did you define churn?**
A buyer from Oct–Dec 2019 with no order in Jan–Feb 2020, which gives 85.02% [K20]. I didn't pick 60 days arbitrarily:
- 88.43% of repeat purchases happen within 60 days [K39].
- A 60-day window captures 80.65% of returns that happen within 120 days [K66].
- Only 4.01% of "churners" came back in the third month [K70].

One honest caveat, which I raise before they do: the 88% is right-censored. In a 5-month window I can't see long gaps, so short gaps are over-represented. That's why I also tested 1-month and 3-month windows (89.59% and 78.83% churn [K67, K68]), and the drivers stayed the same. The October cohort is left-censored because the data starts on 1 Oct, so I flagged it and excluded it where it would bias results.

**3. How did you avoid leakage?**
- Features come only from the observation window (Oct–Dec). The label window's columns (future orders and spend) and all timestamps are dropped, and the code asserts they never enter the model.
- I chose the model on 5-fold cross-validation and kept a stratified 20% holdout untouched for the final check [K103].
- Calibration used out-of-fold predictions.
- To score customers today, I built a separate orders-only model that I could recompute for a new window. It scores lower (CV AUC 0.7348 [K116]), but it is honest.

**4. Why not accuracy?**
Churn is 85% of the data, so a model that says "everyone churns" gets 85.02% accuracy, better than my model's 76.61% [K108], and it is useless: it finds nobody to save and ranks no one. I used:
- ROC-AUC for ranking: 0.7973 [K105]
- PR-AUC for the minority "stays" class: 0.4682 vs a 0.1498 baseline [K105]
- Lift: the lowest-risk 10% are 3.64× more likely to stay [K111]
- Calibration [K114]

**5. Your data is from 2019–20. Is it still relevant?**
The *levels* are specific to this store and era. The *mechanics* aren't: one-time buyers churning, silence as a warning sign, and value concentration. If anything, retention matters more now:
- The loss per new customer more than tripled over 2013–2022 [B4].
- Health and beauty stores see only 17% of new customers repurchase within 180 days [B5].
- Automated lifecycle messages are 2% of email sends but 30% of email revenue [B6].
- India's beauty e-commerce market is growing fast [B8].

I'd re-run the same pipeline on current data before acting, which is why it's fully scripted.

**6. Why XGBoost?**
It had the best 5-fold CV AUC (0.7932, vs 0.7919 for Random Forest and 0.7877 for logistic regression [K104]), and I selected on CV, not the holdout. The margin over logistic regression is small. If interpretability mattered more than that small gap, logistic regression would be a defensible choice, and the RFM-only baseline at 0.7151 shows how much the behavioural features add.

**7. How did you handle class imbalance?**
Here churn is the *majority*, and the hard part is finding the 15% who stay. I used class weights (`class_weight="balanced"`, `scale_pos_weight` in XGBoost) and stratified folds, and I reported PR-AUC for both classes. I didn't oversample, because weighting achieved the same effect without synthetic rows.

**8. Why calibrate?**
Class weighting distorts probabilities. Isotonic calibration made predicted churn match actual churn within 1 point in every tier [K114]. That matters because revenue at risk multiplies probability by value, so a raw score would have overstated it.

**9. What did SHAP show, and is it causal?**
The top drivers were active days, activity in the last 31 days, and the gap between orders [K112]. Habit and recency protect customers. SHAP explains the model's associations, not causes. That is why the recommendations end in an A/B test, not a rollout.

**10. How reliable is your CLV?**
I fitted BG/NBD and Gamma-Gamma on Oct–Dec and validated on Jan–Feb.
- **Ranking is good:** the top predicted decile delivered 49.70% of actual spend [K127].
- **Levels are too high:** it over-forecast purchases by 29% [K123], because it was calibrated on the Black Friday quarter.

So I used CLV only to *rank* customers, never to budget, and said so.

**11. How did you decide who to target?**
Value × risk. "Save now" means top-30% predicted CLV and churn probability ≥ 0.80, which is 12,735 buyers [K131, K132]. I compared four strategies on net profit and ROI under stated assumptions (0.50 contact, 10% discount, 40% margin [K134]) and stress-tested the save rate and margin. Targeted win-back returns a projected +81.0% (14,642.53 net on 18,068.63 of cost per wave) and breaks even at 4.69%, while blanket high-value discounts return +0.5% [K135–K137].

**12. How would you run the A/B test?**
- **Population:** new first-time buyers, randomised at the customer level into three arms: control, message only, and message + 10% offer.
- **Size:** 6,011 per arm, for a +2 pp lift on a 17.89% baseline at α = 0.05 and 80% power [K139, K140].
- **Duration:** about 4 weeks of enrolment plus 9 weeks of follow-up [K150].
- **Guardrails:** margin per order, unsubscribes and complaints.
- **Checks:** sample-ratio mismatch, and no peeking.

The decision rule is to roll out only the arm whose uplift clears its own break-even.

**13. What surprised you?**
- Cart removals were *protective*. Churners removed less (rank-biserial −0.163 [K96]), and buyers who never removed anything churned at 98.35% [K97]. I would have alerted on the wrong signal.
- A discount for every new buyer would lose money unless it lifted repeat buying by almost 10 points [K148].

**14. Tell me about a mistake.**
Two, both caught by checks rather than by luck.
- **Blank CLV:** a library function returned blanks for 30,617 recent one-time buyers [K144]. My segment counts quietly excluded them, so "Save now" looked like 3,376 buyers with +92.8% ROI. I caught it while building the dashboard by asserting there were no missing values, re-implemented the formula, checked it against the library wherever the library worked, and re-ran the analysis.
- **A result that wouldn't repeat:** when I re-ran the whole repo before publishing, the deployment model gave slightly different numbers each run. A SQL query had no `ORDER BY`, so rows came back in a different order and the cross-validation folds changed. I added the `ORDER BY`, proved two runs were identical, and corrected the headline from 12,270 buyers and +72.8% to 12,735 and +81.0% [K158, K132, K135].

The lesson: assert completeness at every hand-off, and treat "same input, same output" as a test, not an assumption. Fixed seeds alone weren't enough.

**15. What would you do next, or in production?**
- Re-score customers monthly with a calibration check per tier.
- Keep a permanent 10% holdout so every campaign's ROI is measured, not projected.
- Add product-line data to unlock brand cross-sell (brand is missing on 40.38% of revenue [K41]).
- Move from churn prediction to uplift modelling once A/B data exists, so the store targets who will *respond*, not only who will leave.

**16. Your revenue at risk is bigger than your revenue. How?**
Good catch, and it's deliberate. Revenue at risk (3,508,675.24 [K130]) assumes every at-risk buyer would spend like a retained one, so it is an upper bound: 1.41× the store's real Jan–Feb revenue of 2,494,244.14 [K163, K164]. I use it to rank customers and size the prize, never as a forecast. The hard number is historical: 74.18% of Oct–Dec revenue came from buyers who didn't return [K23]. What a campaign can realistically recover is save rate × value, for example about 81.8 thousand of incremental revenue for the Save-now group at a 10% save rate [K135].

**17. Is AUC 0.80 good?**
It's good enough to rank, which is the job. The lowest-risk 10% are 3.64× more likely to stay than average [K111]. The real test is whether targeting by score beats random targeting in a live campaign, and that's what the holdout group measures.

**18. Explain Gamma-Gamma to a marketing manager.**
One model (BG/NBD) predicts *how often* someone will buy again; the other (Gamma-Gamma) predicts *how much* they spend per order. Multiply them and you get expected value. I used it to rank customers, not to set a budget, because it over-forecast the post-holiday months by 29% [K123].

**19. Why isotonic calibration and not Platt scaling?**
Isotonic regression makes no assumption about the shape of the miscalibration, and it is fitted with 3-fold cross-validation on tens of thousands of buyers (`CalibratedClassifierCV(method="isotonic", cv=3)` in `src/p6_churn_model.py`), so there is enough data for it not to overfit. Platt scaling assumes an S-shaped correction and suits small samples. The check that matters is the result: predicted and actual churn agree within 1 point per tier [K114].

**20. Why DuckDB and not MySQL?**
It runs SQL straight on CSV files on a laptop with no server to set up. The SQL is standard (CTEs, window functions, NTILE, LAG), so it ports to MySQL 8 or PostgreSQL with almost no changes. **[Practise writing 3–4 of the 15 queries from memory, for example monthly repeat-purchase rate, on paper.]**

**21. Did you use AI tools?**
Answer honestly. For example: "Yes, I used an AI assistant for code and drafting. I framed the questions, made the analytical calls, checked every figure against a source table, and I can rerun and explain any step." **[Only say what is true for you, and run `python run_all.py` yourself before interviews.]**

---

## Quick-reference numbers
- 20.7M events / 110K buyers / 155K orders [K156]
- Churn 85.02% [K20]; one-order vs repeat 90.37% vs 61.28% [K25, K26]
- Holdout AUC 0.7973 vs 0.7293 for the RFM baseline [K105, K162]; naive accuracy 85.02% [K108]
- 74.18% of Oct–Dec revenue from buyers who never returned [K23]
- Revenue at risk 3,508,675.24 is an **upper bound**, 1.41× actual Jan–Feb revenue of 2,494,244.14 [K130, K164, K163]
- Save-now 12,735 [K132]; projected ROI +81.0% (14,642.53 net per wave), break-even 4.69% [K135, K136]
- A/B: 6,011 per arm, 3 arms, 13 weeks [K150]
