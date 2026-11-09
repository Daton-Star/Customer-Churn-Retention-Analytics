"""Phase 8d: Excel workbook for the retention team (openpyxl).

Sheets: README · KPI Summary (live formulas + check vs Key Numbers) · RFM Segments · At-Risk List (all 69,116
scored buyers, conditional formatting) · Value x Risk & Campaign · ROI What-If (live formulas on the At-Risk List)
· Key Numbers.
Output: dashboard/excel/churn_retention_workbook.xlsx. Run p8_build_dashboard_data.py first.
"""
import pandas as pd
from openpyxl import Workbook
from openpyxl.formatting.rule import CellIsRule, ColorScaleRule, DataBarRule, FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.table import Table, TableStyleInfo

from config import DASHBOARD, KEY_NUMBERS, OUTPUTS

PBI = DASHBOARD / "powerbi"
OUT = DASHBOARD / "excel"
OUT.mkdir(parents=True, exist_ok=True)

BLUE, ORANGE, AQUA, GRAY, INK = "2A78D6", "EB6834", "1BAF7A", "8A8984", "22211F"
HEAD = PatternFill("solid", fgColor="E5EFFB")
H_FONT = Font(bold=True, color=INK)
TITLE = Font(bold=True, size=14, color=INK)
NOTE = Font(italic=True, size=9, color="5F5E5A")
THIN = Border(bottom=Side(style="thin", color="E3E2DD"))
MONEY, INT, PCT, PROB = "#,##0.00", "#,##0", "0.00%", "0.00"
QUAD_FILL = {"Save now": "FCEBE3", "Protect": "E3F5EE", "Grow": "E5EFFB", "Automate": "EFEEEA"}

wb = Workbook()


def write_table(ws, df, r0, c0=1, name=None, formats=None, widths=None):
    """Write a DataFrame with a styled header; optionally register it as an Excel table."""
    for j, col in enumerate(df.columns):
        cell = ws.cell(r0, c0 + j, col)
        cell.font, cell.fill = H_FONT, HEAD
        cell.alignment = Alignment(wrap_text=True, vertical="center")
    for i, row in enumerate(df.itertuples(index=False), start=1):
        for j, v in enumerate(row):
            cell = ws.cell(r0 + i, c0 + j, None if pd.isna(v) else v)
            if formats and df.columns[j] in formats:
                cell.number_format = formats[df.columns[j]]
    if name:
        ref = f"{get_column_letter(c0)}{r0}:{get_column_letter(c0 + df.shape[1] - 1)}{r0 + len(df)}"
        t = Table(displayName=name, ref=ref)
        t.tableStyleInfo = TableStyleInfo(name="TableStyleLight1", showRowStripes=True)
        ws.add_table(t)
    for j, w in enumerate(widths or []):
        ws.column_dimensions[get_column_letter(c0 + j)].width = w
    return r0 + len(df)


kn = pd.read_csv(KEY_NUMBERS)
cust = pd.read_csv(PBI / "dim_customer.csv", low_memory=False)

# ------------------------------------------------------------------ At-Risk List (built first so KPI formulas can point at it)
ar = cust[cust.current_buyer_dec_feb == 1].sort_values("action_priority_rank")
ar = ar[["action_priority_rank", "customer_key", "value_risk_quadrant", "risk_tier_mar_apr", "churn_score_mar_apr",
         "clv_90d_predicted", "revenue_at_risk_mar_apr", "value_if_retained_60d", "orders_oct_feb", "revenue_oct_feb",
         "days_since_last_order", "status_feb29", "rfm_segment", "recommended_action", "action_owner", "aov_dec_feb"]].copy()
ar["value_risk_quadrant"] = ar.value_risk_quadrant.str.replace(r" \(.*", "", regex=True)
ar.columns = ["Priority", "Customer ID", "Quadrant", "Risk tier (Mar-Apr)", "Churn probability", "Predicted CLV 90d",
              "Revenue at risk", "Value if retained 60d", "Orders Oct-Feb", "Revenue Oct-Feb", "Days since last order",
              "Status 29 Feb", "RFM segment (Oct-Dec cohort)", "Recommended action", "Owner", "AOV Dec-Feb"]
ws_ar = wb.active
ws_ar.title = "At-Risk List"
ws_ar["A1"] = "At-risk action list: every buyer of Dec 2019 – Feb 2020, ranked for contact"
ws_ar["A1"].font = TITLE
ws_ar["A2"] = ("Sorted by quadrant (Save now first), then revenue at risk. Churn probability = calibrated chance of no order "
               "in Mar–Apr 2020 (Phase 6). CLV = BG/NBD × Gamma-Gamma (Phase 7), for ranking. Money in currency units.")
ws_ar["A2"].font = NOTE
last = write_table(ws_ar, ar, 4, name="AtRiskList",
                   formats={"Churn probability": PROB, "Predicted CLV 90d": MONEY, "Revenue at risk": MONEY,
                            "Value if retained 60d": MONEY, "Revenue Oct-Feb": MONEY, "Days since last order": "0.0",
                            "Priority": INT, "Customer ID": "0", "AOV Dec-Feb": MONEY},
                   widths=[9, 12, 12, 18, 11, 11, 13, 12, 9, 12, 11, 11, 18, 52, 20, 11])
ws_ar.freeze_panes = "C5"
rng = lambda col: f"{col}5:{col}{last}"
ws_ar.conditional_formatting.add(rng("E"), ColorScaleRule(start_type="num", start_value=0.3, start_color="1BAF7A",
                                                          mid_type="num", mid_value=0.6, mid_color="F5D06F",
                                                          end_type="num", end_value=0.95, end_color="E5553B"))
ws_ar.conditional_formatting.add(rng("G"), DataBarRule(start_type="min", end_type="percentile", end_value=99, color=BLUE))
ws_ar.conditional_formatting.add(rng("F"), DataBarRule(start_type="min", end_type="percentile", end_value=99, color=AQUA))
ws_ar.conditional_formatting.add(rng("K"), CellIsRule(operator="greaterThan", formula=["64"], font=Font(color="C8412F", bold=True)))
ws_ar.conditional_formatting.add(rng("K"), CellIsRule(operator="between", formula=["38", "64"], font=Font(color="B7791F", bold=True)))
for q, fill in QUAD_FILL.items():
    ws_ar.conditional_formatting.add(rng("C"), FormulaRule(formula=[f'$C5="{q}"'], fill=PatternFill("solid", fgColor=fill)))
ws_ar.row_dimensions[4].height = 30

# ------------------------------------------------------------------ KPI Summary
ws = wb.create_sheet("KPI Summary", 0)
ws["A1"] = "Customer churn & retention: KPI summary"
ws["A1"].font = TITLE
ws["A2"] = "REES46 cosmetics store, 1 Oct 2019 – 29 Feb 2020. Money in currency units (not converted). Ids refer to the Key Numbers sheet."
ws["A2"].font = NOTE
kmap = kn.set_index("id").value.to_dict()
kpis = [  # label, Key Numbers id, value shown, number format
    ("Raw events (Stage 1)", "K01", 20692840, INT), ("Clean events", "K04", 19583618, INT),
    ("Total revenue", "K14", 6348267.70, MONEY), ("Orders", "K12", 155617, INT), ("Buyers", "K13", 110518, INT),
    ("Average order value", "K15", 40.79, MONEY), ("Repeat-purchase rate (5 months)", "K17", 0.2109, PCT),
    ("Session cart abandonment", "K30", 0.8721, PCT), ("Churn rate (Oct-Dec buyers, no order Jan-Feb)", "K20", 0.8502, PCT),
    ("Share of Oct-Dec revenue from buyers who never returned", "K23", 0.7418, PCT),
    ("Churn: single-order vs repeat buyers", "K25/K26", "90.37% vs 61.28%", None),
    ("XGBoost holdout ROC-AUC", "K105", 0.7973, "0.0000"), ("Revenue at risk, Mar-Apr 2020 (upper bound: 1.41x actual Jan-Feb revenue, K164)", "K130", 3508675.24, MONEY),
    ("Save-now buyers (high value, high risk)", "K132", 12735, INT), ("Save-now campaign ROI (10% save rate)", "K135", 0.8104, "+0.0%"),
    ("Save-now break-even save rate", "K136", 0.0469, PCT), ("A/B test sample size per arm", "K140", 6011, INT),
]
ws.append([])
ws.append(["KPI", "Value", "Key Numbers id", "Key Numbers value"])
for c in ws[4]:
    c.font, c.fill = H_FONT, HEAD
for label, kid, val, fmt in kpis:
    ws.append([label, val, kid, " · ".join(str(kmap.get(k, "")) for k in kid.split("/"))])
    if fmt:
        ws.cell(ws.max_row, 2).number_format = fmt
r = ws.max_row + 2
ws.cell(r, 1, "Live checks against the At-Risk List sheet (formulas)").font = H_FONT
checks = [
    ("Scored buyers", f"=COUNTA('At-Risk List'!B5:B{last})", 69116, INT),
    ("Revenue at risk (sum)", f"=SUM('At-Risk List'!G5:G{last})", 3508675.24, MONEY),
    ("Expected churners (sum of probabilities)", f"=SUM('At-Risk List'!E5:E{last})", 58597.3, "#,##0.0"),
    ("Save-now buyers", f"=COUNTIF('At-Risk List'!C5:C{last},\"Save now\")", 12735, INT),
    ("Save-now revenue at risk", f"=SUMIF('At-Risk List'!C5:C{last},\"Save now\",'At-Risk List'!G5:G{last})", 817779.03, MONEY),
]
ws.append(["Check", "Formula result", "Expected", "Match (±1)"])
for c in ws[ws.max_row]:
    c.font, c.fill = H_FONT, HEAD
for label, f, exp, fmt in checks:
    ws.append([label, f, exp])
    rr = ws.max_row
    ws.cell(rr, 4, f'=IF(ABS(B{rr}-C{rr})<=1,"OK","CHECK")')
    for c in (2, 3):
        ws.cell(rr, c).number_format = fmt
ws.conditional_formatting.add(f"D{r + 2}:D{ws.max_row}", CellIsRule(operator="equal", formula=['"OK"'], font=Font(color="1A8F63", bold=True)))
ws.conditional_formatting.add(f"D{r + 2}:D{ws.max_row}", CellIsRule(operator="equal", formula=['"CHECK"'], font=Font(color="C8412F", bold=True)))

r = ws.max_row + 2
ws.cell(r, 1, "Monthly KPIs").font = H_FONT
mk = pd.read_csv(OUTPUTS / "phase2/q01_monthly_kpis_mom.csv")
mk["month"] = mk.month.str[:7]
for c in ["revenue_mom_pct", "orders_mom_pct", "buyers_mom_pct"]:
    mk[c] = mk[c] / 100
mk.columns = ["Month", "Orders", "Buyers", "Revenue", "AOV", "Orders per buyer", "Revenue MoM", "Orders MoM", "Buyers MoM"]
end = write_table(ws, mk, r + 1, name="MonthlyKPIs", formats={"Orders": INT, "Buyers": INT, "Revenue": MONEY, "AOV": MONEY,
                  "Orders per buyer": "0.000", "Revenue MoM": "+0.00%;-0.00%", "Orders MoM": "+0.00%;-0.00%", "Buyers MoM": "+0.00%;-0.00%"})
ws.conditional_formatting.add(f"G{r + 2}:G{end}", ColorScaleRule(start_type="num", start_value=-0.3, start_color="F4B5A8",
                                                                  mid_type="num", mid_value=0, mid_color="FFFFFF",
                                                                  end_type="num", end_value=0.3, end_color="B9E3CF"))
for col, w in zip("ABCDEFGHI", [44, 16, 16, 30, 13, 15, 13, 12, 12]):
    ws.column_dimensions[col].width = w

# ------------------------------------------------------------------ RFM Segments
ws = wb.create_sheet("RFM Segments", 1)
ws["A1"] = "RFM segments: Oct–Dec 2019 buyers (72,225), churn measured in Jan–Feb 2020"
ws["A1"].font = TITLE
ws["A2"] = "R and F scored 1–5 with NTILE (ties broken by customer id). The October cohort is left-censored: data starts 1 Oct 2019."
ws["A2"].font = NOTE
rs = pd.read_csv(OUTPUTS / "phase4/rfm_segments.csv")
hc = pd.read_csv(OUTPUTS / "phase7/historical_clv_by_rfm_segment.csv")[["segment", "avg_clv_oct_feb"]]
rs = rs.merge(hc, on="segment", how="left")
for c in ["churn_rate", "buyer_share", "revenue_share", "churn_share"]:
    rs[c] = rs[c] / 100
rs = rs[["segment", "buyers", "buyer_share", "revenue", "revenue_share", "churners", "churn_rate", "churn_share",
         "avg_spend", "avg_recency", "avg_orders", "jan_feb_spend", "avg_clv_oct_feb"]]
rs.columns = ["Segment", "Buyers", "Share of buyers", "Revenue Oct-Dec", "Share of revenue", "Churners", "Churn rate",
              "Share of churners", "Avg spend", "Avg recency (days)", "Avg orders", "Jan-Feb spend", "Avg CLV to date (Oct-Feb)"]
end = write_table(ws, rs, 4, name="RFMSegments", formats={"Buyers": INT, "Share of buyers": PCT, "Revenue Oct-Dec": MONEY,
                  "Share of revenue": PCT, "Churners": INT, "Churn rate": PCT, "Share of churners": PCT, "Avg spend": MONEY,
                  "Avg recency (days)": "0.0", "Avg orders": "0.00", "Jan-Feb spend": MONEY, "Avg CLV to date (Oct-Feb)": MONEY},
                  widths=[20, 10, 10, 15, 10, 10, 10, 10, 11, 11, 10, 14, 14])
ws.conditional_formatting.add(f"G5:G{end}", ColorScaleRule(start_type="min", start_color="1BAF7A", mid_type="percentile",
                                                           mid_value=50, mid_color="F5D06F", end_type="max", end_color="E5553B"))
ws.conditional_formatting.add(f"H5:H{end}", DataBarRule(start_type="num", start_value=0, end_type="max", color=ORANGE))
ws.conditional_formatting.add(f"M5:M{end}", DataBarRule(start_type="num", start_value=0, end_type="max", color=BLUE))
ws.row_dimensions[4].height = 30
ws.cell(end + 2, 1, "Read it: Recent One-timers are 29.21% of buyers and 30.51% of churners [K89]; Champions churn at 28.67% [K86].").font = NOTE

# ------------------------------------------------------------------ Value x Risk & Campaign
ws = wb.create_sheet("Value x Risk & Campaign", 3)
ws["A1"] = "Value × risk quadrants and retention campaign economics (Phase 7)"
ws["A1"].font = TITLE
ws["A2"] = "ASSUMPTIONS [K134]: contact 0.50 per customer, 10% discount (paid by all who buy), 40% gross margin, 10% save rate."
ws["A2"].font = NOTE
q = pd.read_csv(PBI / "dim_quadrant.csv").merge(pd.read_csv(OUTPUTS / "phase7/value_risk_matrix.csv"),
                                               left_on="value_risk_quadrant", right_on="quadrant")
q = q[["value_risk_quadrant", "buyers", "avg_churn_prob", "dec_feb_spend", "revenue_at_risk", "rar_share", "recommended_action", "action_owner"]]
q.columns = ["Quadrant", "Buyers", "Avg churn probability", "Dec-Feb spend", "Revenue at risk", "Share of revenue at risk", "Play", "Owner"]
end = write_table(ws, q, 4, name="Quadrants", formats={"Buyers": INT, "Avg churn probability": "0.000", "Dec-Feb spend": MONEY,
                  "Revenue at risk": MONEY, "Share of revenue at risk": "0.0%"}, widths=[34, 10, 12, 15, 15, 12, 58, 22])
ws.conditional_formatting.add(f"E5:E{end}", DataBarRule(start_type="num", start_value=0, end_type="max", color=ORANGE))
r = end + 2
cp = pd.read_csv(PBI / "campaign_strategies.csv").sort_values("roi", ascending=False)
cp = cp[["strategy", "targeted", "expected_saves", "incremental_revenue", "total_cost", "net_profit", "roi", "break_even_save_rate"]]
cp.columns = ["Strategy", "Targeted", "Expected saves", "Incremental revenue", "Total cost", "Net profit", "ROI", "Break-even save rate"]
ws.cell(r, 1, "Who to target").font = H_FONT
end = write_table(ws, cp, r + 1, name="Strategies", formats={"Targeted": INT, "Expected saves": "#,##0.0", "Incremental revenue": MONEY,
                  "Total cost": MONEY, "Net profit": MONEY, "ROI": "+0.0%;-0.0%", "Break-even save rate": PCT})
ws.conditional_formatting.add(f"G{r + 2}:G{end}", DataBarRule(start_type="num", start_value=0, end_type="max", color=AQUA))
r = end + 2
ws.cell(r, 1, "Save-now ROI sensitivity: save rate × gross margin").font = H_FONT
sens = pd.read_csv(OUTPUTS / "phase7/roi_sensitivity_save_rate_x_margin.csv").rename(columns={"Unnamed: 0": "Save rate"})
end = write_table(ws, sens, r + 1, formats={c: "+0.0%;-0.0%" for c in sens.columns[1:]})
ws.conditional_formatting.add(f"B{r + 2}:D{end}", ColorScaleRule(start_type="num", start_value=-0.6, start_color="E5553B",
                                                                  mid_type="num", mid_value=0, mid_color="FFFFFF",
                                                                  end_type="num", end_value=1.5, end_color="1BAF7A"))
ws.cell(end + 1, 1, "Break-even is a 4.69% save rate at 40% margin [K136]; ROI range −56.9% to +332.9% [K138].").font = NOTE

# ------------------------------------------------------------------ ROI What-If (inputs drive live formulas on the At-Risk List)
ws = wb.create_sheet("ROI What-If")
ws["A1"] = "Retention campaign what-if: change the yellow cells"
ws["A1"].font = TITLE
ws["A2"] = ("Same formula as Phase 7 (src/p7_clv_economics.py, campaign()): saves = save rate × churn probability; the discount is "
            "also paid by targeted buyers who would have bought anyway. Defaults reproduce K135 and K136 for Save now.")
ws["A2"].font = NOTE
INPUT = PatternFill("solid", fgColor="FFF4C2")
AR = lambda col: f"'At-Risk List'!${col}$5:${col}${last}"
inputs = [("Target quadrant", "Save now", None), ("Save rate", 0.10, "0.0%"), ("Gross margin", 0.40, "0%"),
          ("Contact cost per buyer", 0.50, "0.00"), ("Discount", 0.10, "0%")]
ws.append([]); ws.append(["Input", "Value"])
for c in ws[4]:
    c.font, c.fill = H_FONT, HEAD
for label, v, fmt in inputs:
    ws.append([label, v]); ws.cell(ws.max_row, 2).fill = INPUT
    if fmt:
        ws.cell(ws.max_row, 2).number_format = fmt
dv = DataValidation(type="list", formula1='"Save now,Protect,Grow,Automate"', allow_blank=False)
ws.add_data_validation(dv); dv.add("B5")
Q, S, M, C, D = "$B$5", "$B$6", "$B$7", "$B$8", "$B$9"
sel = f"({AR('C')}={Q})"
ws.append([]); ws.append(["Building block (from the At-Risk List)", "Value"])
for c in ws[ws.max_row]:
    c.font, c.fill = H_FONT, HEAD
blocks = [("Buyers targeted", f"=COUNTIF({AR('C')},{Q})", INT),
          ("Σ churn probability × value if retained", f"=SUMPRODUCT({sel}*{AR('E')}*{AR('H')})", MONEY),
          ("Σ AOV × churn probability", f"=SUMPRODUCT({sel}*{AR('P')}*{AR('E')})", MONEY),
          ("Σ AOV × (1 − churn probability)", f"=SUMPRODUCT({sel}*{AR('P')}*(1-{AR('E')}))", MONEY),
          ("Σ churn probability (expected churners)", f"=SUMIF({AR('C')},{Q},{AR('E')})", "#,##0.0")]
for label, f, fmt in blocks:
    ws.append([label, f]); ws.cell(ws.max_row, 2).number_format = fmt
N, A, B, Cc, P = "$B$12", "$B$13", "$B$14", "$B$15", "$B$16"
ws.append([]); ws.append(["Result", "Value"])
for c in ws[ws.max_row]:
    c.font, c.fill = H_FONT, HEAD
results = [("Expected saves", f"={S}*{P}", "#,##0.0"), ("Incremental revenue", f"={S}*{A}", MONEY),
           ("Total cost (discount + contact)", f"={D}*({S}*{B}+{Cc})+{C}*{N}", MONEY),
           ("Net profit", f"={M}*{S}*{A}-B21", MONEY), ("ROI", "=B22/B21", "+0.0%;-0.0%"),
           ("Break-even save rate", f"=({D}*{Cc}+{C}*{N})/({M}*{A}-{D}*{B})", "0.00%")]
for label, f, fmt in results:
    ws.append([label, f]); ws.cell(ws.max_row, 2).number_format = fmt
ws.conditional_formatting.add("B23", CellIsRule(operator="lessThan", formula=["0"], font=Font(color="C8412F", bold=True)))
ws.conditional_formatting.add("B23", CellIsRule(operator="greaterThanOrEqual", formula=["0"], font=Font(color="12805C", bold=True)))
ws.append([]); ws.append(["Check (defaults, Save now)", "Formula result", "Key Numbers", "Match"])
for c in ws[ws.max_row]:
    c.font, c.fill = H_FONT, HEAD
for label, cell, exp, kid, tol in [("ROI", "B23", 0.8104, "K135", 0.002), ("Break-even save rate", "B24", 0.0469, "K136", 0.0002),
                                   ("Net profit", "B22", 14642.53, "K135", 5)]:
    ws.append([label, f"={cell}", exp, f'=IF(AND({Q}="Save now",{S}=0.1,{M}=0.4,{C}=0.5,{D}=0.1),IF(ABS(B{ws.max_row + 1}-C{ws.max_row + 1})<={tol},"OK ({kid})","CHECK"),"inputs changed")'])
    ws.cell(ws.max_row, 2).number_format = ws.cell(ws.max_row, 3).number_format = "0.00%" if exp < 1 else MONEY
r = ws.max_row + 2
ws.cell(r, 1, "ROI by save rate for the chosen quadrant, margin, contact cost and discount").font = H_FONT
ws.cell(r + 1, 1, "Save rate").font = H_FONT; ws.cell(r + 1, 2, "ROI").font = H_FONT
for i, sr in enumerate([0.025, 0.05, 0.075, 0.10, 0.15, 0.20, 0.30], start=r + 2):
    ws.cell(i, 1, sr).number_format = "0.0%"
    ws.cell(i, 2, f"=({M}*A{i}*{A}-({D}*(A{i}*{B}+{Cc})+{C}*{N}))/({D}*(A{i}*{B}+{Cc})+{C}*{N})").number_format = "+0.0%;-0.0%"
ws.conditional_formatting.add(f"B{r + 2}:B{r + 8}", ColorScaleRule(start_type="num", start_value=-0.6, start_color="E5553B",
                                                                    mid_type="num", mid_value=0, mid_color="FFFFFF",
                                                                    end_type="num", end_value=1.5, end_color="1BAF7A"))
ws.column_dimensions["A"].width = 46; ws.column_dimensions["B"].width = 16; ws.column_dimensions["C"].width = 14; ws.column_dimensions["D"].width = 16
ws.sheet_properties.tabColor = AQUA

# ------------------------------------------------------------------ Key Numbers + README
ws = wb.create_sheet("Key Numbers")
ws["A1"] = "Key Numbers: every number in the project deliverables comes from this table"
ws["A1"].font = TITLE
write_table(ws, kn.fillna(""), 3, name="KeyNumbers", widths=[7, 60, 46, 14, 50, 8])
ws.freeze_panes = "A4"
for row in ws.iter_rows(min_row=4, max_col=3):
    for c in row:
        c.alignment = Alignment(wrap_text=True, vertical="top")

ws = wb.create_sheet("README", 0)
lines = [
    ("Churn & Retention Workbook", TITLE),
    ("REES46 cosmetics e-commerce events, 1 Oct 2019 – 29 Feb 2020: real 2019–20 data, read with 2025–26 business context.", None),
    ("", None),
    ("Sheets", H_FONT),
    ("KPI Summary: headline KPIs with their Key Numbers ids, live formula checks, monthly KPIs.", None),
    ("RFM Segments: 9 segments of Oct–Dec buyers with churn, revenue and CLV; colour scale on churn rate.", None),
    ("At-Risk List: all 69,116 buyers of Dec–Feb, ranked for contact, with recommended action and owner. Filter by Quadrant or Owner.", None),
    ("Value x Risk & Campaign: quadrants, targeting strategies and ROI sensitivity.", None),
    ("ROI What-If: pick a quadrant and change save rate, margin, contact cost or discount; ROI and break-even recalculate from the At-Risk List.", None),
    ("Key Numbers: the source table for every figure.", None),
    ("", None),
    ("Definitions", H_FONT),
    ("Churn: an Oct–Dec 2019 buyer with no order in Jan–Feb 2020 (85.02% [K20]).", None),
    ("Status on 29 Feb 2020: Active ≤38 days since last order, At-Risk 38–64 days, Churned >64 days.", None),
    ("Churn probability: calibrated XGBoost (orders-only deployment model) probability of no order in Mar–Apr 2020.", None),
    ("Revenue at risk: churn probability × value if retained (own Dec–Feb AOV × 1.593 orders [K129]). Its total is an upper bound, 1.41× actual Jan–Feb revenue [K164].", None),
    ("Save now = top-30% predicted CLV (≥ 17.32 [K131]) and churn probability ≥ 0.80.", None),
    ("", None),
    ("Limitations", H_FONT),
    ("One store, one season; October cohort left-censored; scores and CLV are estimates for ranking; campaign figures rest on stated assumptions.", None),
    ("Money is in the dataset's currency units and is not converted to ₹.", None),
]
for i, (text, font) in enumerate(lines, start=1):
    ws.cell(i, 1, text)
    if font:
        ws.cell(i, 1).font = font
ws.column_dimensions["A"].width = 130

wb["README"].sheet_properties.tabColor = GRAY
wb["At-Risk List"].sheet_properties.tabColor = ORANGE
wb["KPI Summary"].sheet_properties.tabColor = BLUE
path = OUT / "churn_retention_workbook.xlsx"
wb.save(path)
print(path, round(path.stat().st_size / 1e6, 1), "MB;", "sheets:", wb.sheetnames, "; at-risk rows:", last - 4)
