# Phase 8: Dashboards

There are three views of the same model, and every figure traces to [key_numbers.csv](../key_numbers/key_numbers.csv). Money is in currency units.

| Deliverable | File | What it is |
|---|---|---|
| Power BI star schema | [dashboard/powerbi/](../dashboard/powerbi/) | 4 facts and 7 dimensions plus helper tables [K143]. Revenue reconciles to 6,348,267.70 [K14]. |
| Power BI build guide | [POWERBI_BUILD_GUIDE.md](../dashboard/powerbi/POWERBI_BUILD_GUIDE.md) | Relationships, 35 DAX measures (including a save-rate what-if), a 3-page layout and conditional formatting |
| Expected measure values | [measure_expected_values.csv](../dashboard/powerbi/measure_expected_values.csv) | Each DAX measure recomputed in pandas from the CSVs. All match Key Numbers. |
| Interactive HTML dashboard | [dashboard/index.html](../dashboard/index.html) · GitHub Pages copy: [docs/index.html](../docs/index.html) · [screenshots](../images/dashboard/) | 3 pages: Executive Overview, Funnel & Churn Drivers, At-Risk Action List. Includes a filterable list and a campaign what-if. |
| Excel workbook | [dashboard/excel/churn_retention_workbook.xlsx](../dashboard/excel/churn_retention_workbook.xlsx) | KPI summary with live formula checks, RFM segments, all 69,116 scored buyers ranked for contact, value × risk and campaign, an **ROI What-If** sheet (pick a quadrant, change save rate, margin, contact cost or discount; ROI and break-even recalculate from the At-Risk List and reproduce K135 and K136 at the defaults), Key Numbers |

## Rebuild
```
python3 src/p8_build_dashboard_data.py    # star schema CSVs + dashboard_data.json
python3 src/p8_verify_measures.py         # DAX expected values
python3 src/p8_build_html_dashboard.py    # dashboard/index.html (Chart.js 4.4.1 from cdnjs)
python3 src/p8_build_excel_workbook.py    # dashboard/excel/churn_retention_workbook.xlsx
```
`index.html` is self-contained apart from Chart.js. It can be served as-is from GitHub Pages (`dashboard/index.html` in the final repo) for a public preview link.

## Design choices
- **Customer-level snapshot measures** (churn, risk, CLV, revenue at risk) sit on `dim_customer`, so date slicers don't change them. The guide says to switch off those interactions.
- **No brand on orders.** Stage 1 orders have no product lines, so brand analysis uses the monthly brand funnel. The "unknown" brand is 40.38% of revenue [K41].
- **At-risk priority** = quadrant order (Save now → Protect → Grow → Automate → Lapsed), then revenue at risk. Each row carries a recommended action and an owner.
- **The what-if** uses the Phase 7 campaign formula. At the defaults (10% save rate, 40% margin) it reproduces ROI +81.0% and break-even 4.69% [K135, K136].

## Corrections made in Phases 8 and 10
**1. Blank CLV (found in Phase 8).** While building `dim_customer`, I found that 30,617 recent one-time buyers had a blank 90-day CLV [K144]. lifetimes takes the log of a term that is negative for buyers with T ≤ 50 days. I fixed it in `src/p7_clv_economics.py` (`expected_purchases()`) and re-ran Phase 7. Before this fix, Save now held only 3,376 buyers with a +92.8% ROI [K144].

**2. Non-deterministic deployment model (found in Phase 10).** When the repo was re-run end to end, the deployment model's numbers moved between runs. Its feature query had no `ORDER BY`, so DuckDB returned rows in a different order each time and the CV folds changed. I added `ORDER BY user_id` in `src/p6_churn_model.py`, confirmed two consecutive runs give identical results, and re-ran Phases 6–9. Before this fix the published values were Save now 12,270 buyers, ROI +72.8%, break-even 5.00% and revenue at risk 3,507,812.66 [K158].

Final values after both fixes: Save now 12,735 buyers [K132], ROI +81.0% [K135], break-even 4.69% [K136], and "All high-value" +0.1% [K137]. The recommendation is unchanged: target value × risk with an offer, and use no-discount automation for the rest.

## Limitations
- The CSV exports round scores, so Power BI totals can differ from Key Numbers in the second decimal. For example, revenue at risk is 3,508,675.25 vs 3,508,675.24 [K130], and expected churners from 2-decimal scores is 58,597.3 [K142] vs 58,632.95 [K117].
- KPI tiles show compact values (6.35M) for executives. Key Numbers ids sit in each tile's tooltip and behind the "Show sources" link in the footer, so the page stays traceable without looking like an audit file.
- Revenue at risk is labelled an upper bound on the dashboard (1.41× actual Jan–Feb revenue [K164]); the executive page leads with the historical 74.18% instead [K23].
- The HTML dashboard embeds the top 150 buyers per quadrant [K146]. The full list is in Excel and `dim_customer.csv`.
- The Power BI file itself (.pbix) is built by following the guide, because Power BI Desktop is Windows-only and can't be run here.
