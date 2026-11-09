# Completion Checklist

Every item in the project brief, mapped to where it lives in the repo. ✓ = done and verified. ◐ = done with a stated limitation.

## Working rules
| Rule | Status | Where / how |
|---|---|---|
| Phase by phase, with a 3–5 line summary after each | ✓ | "Phase N summary" at the end of each `reports/0N_*.md` |
| Clean, modular, commented, reproducible code with fixed seeds | ✓ | `src/p1_…p9_*.py`, `src/config.py`, `run_all.py`; seed 42 throughout; repo re-run compared with the originals (see README) |
| Running Key Numbers table; no number outside it | ✓ | `key_numbers/key_numbers.csv` (K01–K160); deliverables checked for numbers that aren't in it |
| Exact raw and clean row counts from `data_quality_report.csv` | ✓ | 20,692,840 raw / 19,583,618 clean [K01, K04] |
| Prices as "currency units", not ₹ | ✓ | All reports, dashboards, workbook |
| Use category_id and brand (category_code mostly missing) | ✓ | Phases 2 and 4; category_code missing on 98.29% of rows [K59] |
| Flag October cohort left-censoring | ✓ | Phases 2–8, README limitations, dashboard footer |
| Honest limitations | ✓ | "Limitations" section in every report; Phase 7 CLV fix and Phase 10 reproducibility fix documented [K144, K158] |
| 5–6 current benchmarks via web search | ✓ | `reports/benchmarks.csv` (B1–B8, with URLs and credibility notes) |
| 2019–20 data with a 2025–26 lens; India market as context only | ✓ | `reports/01_business_framing.md`, executive summary [B8] |

## Phases
| # | Deliverable | Status | Files |
|---|---|---|---|
| 1 | Business framing, baseline KPIs, benchmarks | ✓ | `reports/01_business_framing.md`, `reports/benchmarks.csv`, `src/p1_baseline.py` |
| 2 | SQL validation + 15 business queries (DuckDB) | ✓ | `sql/00_validation.sql` (6 checks), `sql/01_business_queries.sql` (15), `src/p2_run_sql.py`, `outputs/phase2/`, `reports/02_sql_findings.md` |
| 3 | Churn-definition validation | ✓ | `src/p3_churn_definition.py`, `reports/03_churn_definition.md`, 4 charts in `images/phase3/` |
| 4 | EDA and funnel diagnostics: 15–20 charts with a "so what" | ✓ | 18 charts in `images/phase4/`, `reports/04_eda_funnel.md` |
| 5 | 5–6 hypotheses: p-values, effect sizes, business meaning | ✓ | 6 tests, `reports/05_hypothesis_tests.md`, `outputs/phase5/hypothesis_results.csv` |
| 6 | Logistic regression / Random Forest / XGBoost; imbalance; stratified CV; ROC/PR-AUC; confusion matrix; lift/gain; precision@k; why accuracy misleads; SHAP; risk tiers | ✓ | `src/p6_churn_model.py`, `reports/06_churn_prediction.md`, 6 charts in `images/phase6/` |
| 7 | Historical CLV; BG/NBD + Gamma-Gamma with calibration vs holdout; value × risk; revenue at risk; campaign simulation (ROI, break-even, sensitivity); A/B design (power, duration, guardrails) | ✓ | `src/p7_clv_economics.py`, `reports/07_clv_retention_economics.md`, 5 charts in `images/phase7/` |
| 8a | Power BI star-schema CSVs: fact_orders, dim_customer (scores and segments), dim_brand, dim_date, fact_daily_kpis | ✓ | `dashboard/powerbi/` (+ fact_session_monthly, fact_brand_monthly, helper tables) |
| 8b | Power BI build guide: relationships, 15+ DAX measures, 3-page layout | ◐ | `dashboard/powerbi/POWERBI_BUILD_GUIDE.md`: 35 measures, each verified in Python (`measure_expected_values.csv`). The `.pbix` itself must be built in Power BI Desktop (Windows), which wasn't available here. |
| 8c | Interactive HTML dashboard (same 3 pages), live preview link | ✓ | `dashboard/index.html`, GitHub Pages copy in `docs/`, screenshots in `images/dashboard/` |
| 8d | Excel workbook: KPI summary, RFM segments, at-risk list with conditional formatting | ✓ | `dashboard/excel/churn_retention_workbook.xlsx` (formula checks recalculated: all OK), plus an ROI What-If sheet |
| 9 | 6–8 prioritised recommendations: segment, action, owner, impact, effort, KPI; impact-vs-effort table linked to findings | ✓ | `reports/09_recommendations.md` (8 actions), `images/phase9/p9_01_impact_effort.png` |
| 10a | Repo structure (stage1_kaggle, sql, notebooks, src, dashboard, reports, images), requirements.txt, README with Kaggle link placeholder | ✓ | Repo root |
| 10b | 2–3 page executive summary; 10–12 slide deck outline | ✓ | `reports/executive_summary.md`, `reports/slide_deck_outline.md` (12 slides) |
| 10c | Resume: title line, 4 bullets under 30 words with the real event count, 1-line version, DA and BA variants, 25 ATS keywords | ✓ | `reports/career/resume_and_linkedin.md` |
| 10d | LinkedIn post, 150–200 words | ✓ | `reports/career/resume_and_linkedin.md` (about 175 words) |
| 10e | Interview prep: 60-second pitch, STAR story, 15 Q&As including the 5 required questions | ✓ | `reports/career/interview_prep.md` |

## Recruiter-review fixes (done)
- [x] Dashboard screenshots at the top of the README, plus a 2×2 grid of key charts
- [x] Dashboard copied to `docs/` for GitHub Pages; the private preview link is removed from every document
- [x] Repo slimmed: large regenerable CSVs are git-ignored, Power BI tables zipped, no file over 25 MB
- [x] Model comparison fixed to holdout vs holdout (0.7973 vs 0.7293 [K105, K162]); the old text compared holdout with a CV score
- [x] Resume bullets use rounded numbers and label campaign ROI as "projected" [K161]

## Recruiter-review fixes, round 2 (done 2026-10-20)
- [x] Revenue at risk reframed as an upper bound everywhere (1.41× actual Jan–Feb revenue [K163, K164]); the headline is now the historical 74.18% of Oct–Dec revenue from buyers who never returned [K23]
- [x] Dashboard tiles show compact values; Key Numbers ids moved to tooltips and a "Show sources" toggle; screenshots refreshed
- [x] Resume: plain-separator title line, 3-bullet role variants, 25 ATS keywords swapped toward terms Indian DA/BA job posts use
- [x] LinkedIn post uses rounded numbers; 7-page carousel PDF added (`reports/career/linkedin_carousel.pdf`, `src/p10_linkedin_carousel.py`)
- [x] Interview prep: right-censoring caveat, ROI with its scale, 6 new questions (16–21)
- [x] Excel ROI What-If sheet with live formulas, checked against K135 and K136
- [x] KPI tree and stakeholder question → metric → decision page (`reports/kpi_tree.md`)

## Things only you can add
- [ ] Publish the repo on GitHub, then turn on Pages (Settings → Pages → `main` / `/docs`) and paste the link in `README.md` and the LinkedIn post
- [ ] Make your Stage 1 Kaggle notebook public, link it in `README.md`, `stage1_kaggle/README.md` and the LinkedIn post, and save a copy as `stage1_kaggle/stage1_kaggle.ipynb`
- [ ] How you processed the raw 20.7M events in Kaggle: `reports/career/interview_prep.md` Q1 (bracketed)
- [ ] Your LinkedIn URL: `README.md`
- [ ] Rehearse: run `python run_all.py` yourself, change one setting (for example a 90-day churn window), and answer interview Q16–Q21 out loud
- [ ] Record a 2-minute walkthrough of the dashboard (Loom or unlisted YouTube) and link it at the top of `README.md`
- [ ] In Excel, add one sheet you build by hand: a pivot table with a slicer on the At-Risk List (pivot tables can't be generated reliably from code)
- [ ] Keep `churn-predictor-retention-advisor` private, or retitle it, so recruiters see one flagship churn project
- [ ] Build the `.pbix` from `dashboard/powerbi/POWERBI_BUILD_GUIDE.md`, save it to `dashboard/powerbi/`, and add page screenshots to `images/powerbi/` and the README (high priority for Indian DA roles)
