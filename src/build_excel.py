"""Builds excel/KandaCode_LP_Model.xlsx — a live Excel Solver model of the sell-or-store LP, plus supporting tables.
Solver settings are stored in the workbook (sheet-scoped solver_* names), so Data > Solver opens pre-filled."""
import json
import sys
from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.formatting.rule import ColorScaleRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.worksheet.datavalidation import DataValidation

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kandacode as kc  # noqa: E402

R = json.loads((kc.OUT / "results.json").read_text(encoding="utf-8"))
_nh = kc.load_nhrdf()["lasalgaon_price_rs_qtl"].dropna()
kc.LONG_HISTORY = _nh[_nh.index < pd.Period("2014-01", "M")]
monthly = pd.read_csv(kc.PROC / "maharashtra_onion_monthly.csv")

PLUM, COPPER, INK, PAPER, BLUSH = "6B1E4A", "C2683C", "1F1A1C", "FBF7F2", "F3DCD8"
F_T = Font(name="Calibri", size=18, bold=True, color=PLUM)
F_H = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
F_B = Font(name="Calibri", size=11, bold=True, color=INK)
F_N = Font(name="Calibri", size=11, color=INK)
F_S = Font(name="Calibri", size=9, italic=True, color="6E6468")
FILL_H = PatternFill("solid", fgColor=PLUM)
FILL_IN = PatternFill("solid", fgColor="FFF4D6")     # inputs (yellow-ish)
FILL_DEC = PatternFill("solid", fgColor="E6F0DC")    # decision variables (green)
FILL_OBJ = PatternFill("solid", fgColor=BLUSH)       # objective
thin = Side(style="thin", color="D9CFCB")
BOX = Border(left=thin, right=thin, top=thin, bottom=thin)
NUM0, NUM1, NUM3, PCT = "#,##0", "#,##0.0", "0.000", "0.0%"

wb = Workbook()

# ---------------------------------------------------------------- README
ws = wb.active
ws.title = "README"
ws.sheet_view.showGridLines = False
ws.column_dimensions["A"].width = 3
ws.column_dimensions["B"].width = 110
lines = [
    ("Kanda Code — Sell-or-Store LP model (Excel Solver)", F_T),
    ("Industry 4.0 (MS4001), IIT Madras BS · Team Kanda Code", F_S),
    ("", F_N),
    ("WHAT THIS WORKBOOK DOES", F_B),
    ("A farmer producer organisation (FPO) holds Q tonnes of rabi onion in April. Each month from April (t=1) to December (t=9) it decides how many", F_N),
    ("tonnes to sell (x_t). Unsold onions stay in storage (s_t) and lose a share δ each month to rot and weight loss, and cost h rupees per tonne per month.", F_N),
    ("The LP chooses x_1..x_9 to maximise forecast revenue minus storage cost.", F_N),
    ("", F_N),
    ("HOW TO RUN IT (2 minutes)", F_B),
    ("1. Open sheet LP_Model. Pick a Season (2023 or 2024) and a Scenario (A, B or C) in the yellow cells C5 and C6.", F_N),
    ("2. Data ▸ Solver (enable via File ▸ Options ▸ Add-ins ▸ Excel Add-ins ▸ Solver Add-in if missing). The model is already set up:", F_N),
    ("      Objective $C$27 (Max) · Changing cells $C$20:$K$20 · Simplex LP · Make unconstrained variables non-negative.", F_N),
    ("      Constraints: $C$21:$K$21 <= $C$9 (capacity) · $C$21:$K$21 >= 0 · $K$21 = 0 (clear by Dec) · $C$20 >= $C$10 (loan sale) · $D$20:$K$20 <= $C$11 (handling cap).", F_N),
    ("      Verified: Excel Solver (Simplex LP) reproduces the Python objective exactly (checked for 2023 A and B by automation; click Solve to check any case — cell D31 confirms the match).", F_N),
    ("3. Click Solve ▸ keep Solver solution. Row 20 is the plan; row 29 shows what it would actually have earned at real prices; row 31 is the Python (PuLP) answer for the same case.", F_N),
    ("4. For Sensitivity Report (shadow prices), tick 'Sensitivity' in the Solver Results dialog.", F_N),
    ("", F_N),
    ("SHEETS", F_B),
    ("LP_Model — the live Solver model.  Scenarios — δ, h, C per scenario with sources.  Prices — forecast (end-March) and actual Apr–Dec prices.", F_N),
    ("Data_Monthly — Maharashtra monthly onion price & arrivals 2014–2024 (Agmarknet via Mendeley).  Backtest — Python results 2017–2024.  Sensitivity — δ × h grid.  H1_Regression — price vs arrivals.", F_N),
    ("", F_N),
    ("UNITS", F_B),
    ("Prices in ₹ per tonne inside the LP (₹/quintal × 10). ₹/kg = ₹/tonne ÷ 1000. Quantities in tonnes.", F_N),
    ("", F_N),
    ("SOURCES", F_B),
    ("Prices: Shelar, Hajare & Mangarule (2025) Mendeley Data DOI 10.17632/ds9jmxp9zy.1 (Agmarknet). Validation: NHRDF Lasalgaon monthly, Mendeley DOI 10.17632/9dn4g8m97m.", F_N),
    ("Storage losses: ICAR-DOGR trials — ventilated 54.89%, DOGR cold storage 7.14% loss over 120 days (icar.org.in/en/node/4701).", F_N),
]
for i, (t, f) in enumerate(lines, start=2):
    c = ws.cell(row=i, column=2, value=t)
    c.font = f
    c.alignment = Alignment(wrap_text=False)

# ---------------------------------------------------------------- Scenarios
sc = wb.create_sheet("Scenarios")
sc.sheet_view.showGridLines = False
hdr = ["Scenario", "Storage", "Monthly loss δ", "Storage cost h (₹/t/month)", "Capacity C (t)", "120-day loss (ICAR)", "Basis"]
base = R["lp_params_base"]
rows = [
    ["A", "No storage — sell all at harvest", 0.0, 0, 0, None, "Today's typical small farmer"],
    ["B", "Ventilated kanda chawl", R["scenarios"]["B"]["delta"], R["scenarios"]["B"]["h"], base["C"], 0.5489, "1−(1−0.5489)^(1/4), ICAR ventilated storage"],
    ["C", "Cold / IoT-monitored storage", R["scenarios"]["C"]["delta"], R["scenarios"]["C"]["h"], base["C"], 0.0714, "1−(1−0.0714)^(1/4), ICAR-DOGR cold storage"],
]
sc["B2"] = "Storage scenarios (inputs to LP_Model)"; sc["B2"].font = F_T
for j, h in enumerate(hdr):
    c = sc.cell(row=4, column=2 + j, value=h); c.font = F_H; c.fill = FILL_H; c.alignment = Alignment(wrap_text=True, vertical="center")
for i, r in enumerate(rows):
    for j, v in enumerate(r):
        c = sc.cell(row=5 + i, column=2 + j, value=v); c.font = F_N; c.border = BOX
    sc.cell(row=5 + i, column=4).number_format = "0.00%"
    sc.cell(row=5 + i, column=7).number_format = "0.00%"
for col, w in zip("BCDEFGH", [10, 34, 15, 22, 15, 18, 46]):
    sc.column_dimensions[col].width = w
sc.row_dimensions[4].height = 32

# ---------------------------------------------------------------- Prices
pr = wb.create_sheet("Prices")
pr.sheet_view.showGridLines = False
pr["B2"] = "Prices used by the LP (₹ per tonne)"; pr["B2"].font = F_T
pr["B3"] = f"Forecast = {R['forecast']['best_label']}, made with data up to end-March of the season (no peeking). Actual = Maharashtra arrival-weighted modal price."
pr["B3"].font = F_S
pr.cell(row=5, column=2, value="Series").font = F_H; pr.cell(row=5, column=2).fill = FILL_H
for j, m in enumerate(kc.SEASON):
    c = pr.cell(row=5, column=3 + j, value=m); c.font = F_H; c.fill = FILL_H; c.alignment = Alignment(horizontal="center")
best = R["forecast"]["best_method"]
price_rows = {}
r = 6
for yr in (2023, 2024):
    fc = [v * 10 for v in R["forecast"]["paths"][best][str(yr)]]
    act = kc.season_prices(monthly.assign(ym=pd.PeriodIndex(monthly["ym"], freq="M")).set_index("ym")["price_rs_qtl"], yr).tolist()
    for lab, vals in ((f"{yr} forecast", fc), (f"{yr} actual", act)):
        pr.cell(row=r, column=2, value=lab).font = F_B
        for j, v in enumerate(vals):
            c = pr.cell(row=r, column=3 + j, value=round(float(v), 0)); c.number_format = NUM0; c.border = BOX
        price_rows[lab] = r
        r += 1
pr.column_dimensions["B"].width = 18
for j in range(9):
    pr.column_dimensions[chr(ord("C") + j)].width = 11
ch = LineChart(); ch.title = "Forecast vs actual, ₹/t"; ch.height = 7; ch.width = 18
data = Reference(pr, min_col=2, max_col=11, min_row=6, max_row=9)
ch.add_data(data, from_rows=True, titles_from_data=True)
ch.set_categories(Reference(pr, min_col=3, max_col=11, min_row=5))
pr.add_chart(ch, "B12")

# ---------------------------------------------------------------- LP_Model
lp = wb.create_sheet("LP_Model", 1)
lp.sheet_view.showGridLines = False
lp["B2"] = "Sell-or-store linear programme"; lp["B2"].font = F_T
lp["B3"] = "Yellow = inputs · Green = Solver decision cells · Pink = objective. Run Data ▸ Solver (pre-configured)."; lp["B3"].font = F_S
labels = [("Season", 5), ("Scenario", 6), ("Harvest held Q (t)", 8), ("Storage capacity C (t)", 9),
          ("Min. April sale L (t)", 10), ("Handling cap U (t/month, May–Dec)", 11), ("Monthly loss δ", 12), ("Storage cost h (₹/t/month)", 13)]
for lab, row in labels:
    lp.cell(row=row, column=2, value=lab).font = F_B
lp["C5"] = 2024; lp["C6"] = "C"
for a in ("C5", "C6"):
    lp[a].fill = FILL_IN; lp[a].border = BOX; lp[a].font = F_B
dv1 = DataValidation(type="list", formula1='"2023,2024"', allow_blank=False); lp.add_data_validation(dv1); dv1.add("C5")
dv2 = DataValidation(type="list", formula1='"A,B,C"', allow_blank=False); lp.add_data_validation(dv2); dv2.add("C6")
lp["C8"] = base["Q"]
lp["C9"] = "=INDEX(Scenarios!$F$5:$F$7,MATCH($C$6,Scenarios!$B$5:$B$7,0))"
lp["C10"] = f'=IF($C$6="A",$C$8,{base["L"]})'
lp["C11"] = base["U"]
lp["C12"] = "=INDEX(Scenarios!$D$5:$D$7,MATCH($C$6,Scenarios!$B$5:$B$7,0))"
lp["C13"] = "=INDEX(Scenarios!$E$5:$E$7,MATCH($C$6,Scenarios!$B$5:$B$7,0))"
for a in ("C8", "C11"):
    lp[a].fill = FILL_IN
for a in ("C8", "C9", "C10", "C11", "C12", "C13"):
    lp[a].border = BOX; lp[a].font = F_N
    lp[a].number_format = NUM0
lp["C12"].number_format = "0.00%"
lp["D9"] = "from Scenarios"; lp["D12"] = "from Scenarios"; lp["D13"] = "from Scenarios"; lp["D10"] = "= Q if scenario A"
for a in ("D9", "D10", "D12", "D13"):
    lp[a].font = F_S

lp.cell(row=16, column=2, value="Month  t →").font = F_H; lp.cell(row=16, column=2).fill = FILL_H
for j, m in enumerate(kc.SEASON):
    c = lp.cell(row=16, column=3 + j, value=f"{m}  ({j+1})"); c.font = F_H; c.fill = FILL_H; c.alignment = Alignment(horizontal="center")
c = lp.cell(row=16, column=12, value="Total"); c.font = F_H; c.fill = FILL_H
rowlab = {17: "Forecast price p̂ₜ (₹/t)", 18: "Actual price (₹/t)", 20: "Sell xₜ (t)  ← Solver", 21: "Stock sₜ (t)",
          22: "Lost to rot (t)", 23: "Revenue p̂ₜ·xₜ (₹)", 24: "Storage cost h·sₜ (₹)"}
for rr, lab in rowlab.items():
    lp.cell(row=rr, column=2, value=lab).font = F_B
for j in range(9):
    col = chr(ord("C") + j)
    prev = chr(ord("C") + j - 1)
    lp[f"{col}17"] = f'=IF($C$5=2023,Prices!{col}{price_rows["2023 forecast"]},Prices!{col}{price_rows["2024 forecast"]})'
    lp[f"{col}18"] = f'=IF($C$5=2023,Prices!{col}{price_rows["2023 actual"]},Prices!{col}{price_rows["2024 actual"]})'
    lp[f"{col}20"] = 0
    lp[f"{col}20"].fill = FILL_DEC
    lp[f"{col}21"] = "=$C$8-C20" if j == 0 else f"=(1-$C$12)*{prev}21-{col}20"
    lp[f"{col}22"] = 0 if j == 0 else f"=$C$12*{prev}21"
    lp[f"{col}23"] = f"={col}17*{col}20"
    lp[f"{col}24"] = f"=$C$13*{col}21"
    for rr in (17, 18, 20, 21, 22, 23, 24):
        lp[f"{col}{rr}"].number_format = NUM1 if rr in (20, 21, 22) else NUM0
        lp[f"{col}{rr}"].border = BOX
# open on the solved 2024 / C plan (PuLP solution on the same rounded forecast); Solver re-solves any case
_m = monthly.assign(ym=pd.PeriodIndex(monthly["ym"], freq="M")).set_index("ym")["price_rs_qtl"].dropna()
_fc = [round(float(v), 0) for v in kc.forecast(_m[_m.index <= pd.Period("2024-03", "M")], 9, R["forecast"]["best_method"]) * 10]
_sol = kc.solve_lp(_fc, kc.scenario_params(kc.LPParams(**R["lp_params_base"]), "C"), return_duals=False)
for j, v in enumerate(_sol["x"]):
    lp[f"{chr(ord('C') + j)}20"] = round(float(v), 4)
for rr in (20, 22, 23, 24):
    lp[f"L{rr}"] = f"=SUM(C{rr}:K{rr})"; lp[f"L{rr}"].number_format = NUM0; lp[f"L{rr}"].font = F_B
lp["B27"] = "Objective Z = Σ p̂ₜxₜ − h Σ sₜ (₹)"; lp["B27"].font = F_B
lp["C27"] = "=SUMPRODUCT(C17:K17,C20:K20)-$C$13*SUM(C21:K21)"
lp["C27"].fill = FILL_OBJ; lp["C27"].number_format = NUM0; lp["C27"].font = Font(bold=True, size=12, color=PLUM); lp["C27"].border = BOX
lp["D27"] = "=C27/$C$8"; lp["D27"].number_format = '#,##0" ₹/t"'
lp["B29"] = "Realised at ACTUAL prices (₹)"; lp["B29"].font = F_B
lp["C29"] = "=SUMPRODUCT(C18:K18,C20:K20)-$C$13*SUM(C21:K21)"; lp["C29"].number_format = NUM0
lp["D29"] = "=C29/$C$8"; lp["D29"].number_format = '#,##0" ₹/t"'
lp["B30"] = "Sell-all-in-April benchmark (₹)"; lp["B30"].font = F_B
lp["C30"] = "=$C$8*C18"; lp["C30"].number_format = NUM0
lp["D30"] = "=(C29-C30)/$C$8"; lp["D30"].number_format = '+#,##0" ₹/t gain";-#,##0" ₹/t loss"'
lp["B31"] = "Python (PuLP/CBC) objective, same case (₹)"; lp["B31"].font = F_B
# python objectives for each (season, scenario) at its forecast
py = {}
mser = monthly.assign(ym=pd.PeriodIndex(monthly["ym"], freq="M")).set_index("ym")["price_rs_qtl"].dropna()
for yr in (2023, 2024):
    fc = kc.forecast(mser[mser.index <= pd.Period(f"{yr}-03", "M")], 9, best) * 10
    fc = [round(float(v), 0) for v in fc]  # identical to the rounded values in Prices
    lpb = kc.LPParams(**R["lp_params_base"])
    for k in "ABC":
        py[(yr, k)] = kc.solve_lp(fc, kc.scenario_params(lpb, k), return_duals=False)["objective"]
lp["N16"] = "Python objective lookup"; lp["N16"].font = F_S
rr = 17
for (yr, k), v in py.items():
    lp[f"N{rr}"] = f"{yr}{k}"; lp[f"O{rr}"] = round(v, 0); lp[f"O{rr}"].number_format = NUM0
    rr += 1
lp["C31"] = "=VLOOKUP($C$5&$C$6,$N$17:$O$22,2,FALSE)"; lp["C31"].number_format = NUM0
lp["D31"] = '=IF(ABS(C27-C31)<=1,"✔ matches Excel Solver","run Solver to compare")'
lp["B33"] = "Constraint checks"; lp["B33"].font = F_B
checks = [("Capacity: max sₜ ≤ C", '=IF(MAX(C21:K21)<=$C$9+0.001,"OK","VIOLATED")'),
          ("No negative stock", '=IF(MIN(C21:K21)>=-0.001,"OK","VIOLATED")'),
          ("Clear by December s₉ = 0", '=IF(ABS(K21)<=0.001,"OK","VIOLATED")'),
          ("Loan sale x₁ ≥ L", '=IF(C20>=$C$10-0.001,"OK","VIOLATED")'),
          ("Handling cap xₜ ≤ U (May–Dec)", '=IF(MAX(D20:K20)<=$C$11+0.001,"OK","VIOLATED")')]
for i, (lab, f) in enumerate(checks):
    lp.cell(row=34 + i, column=2, value=lab).font = F_N
    lp.cell(row=34 + i, column=3, value=f).font = F_B
lp.column_dimensions["A"].width = 2; lp.column_dimensions["B"].width = 38
for j in range(10):
    lp.column_dimensions[chr(ord("C") + j)].width = 13
lp.column_dimensions["N"].width = 14; lp.column_dimensions["O"].width = 14
bc = BarChart(); bc.title = "Plan: tonnes sold per month"; bc.height = 7; bc.width = 16
bc.add_data(Reference(lp, min_col=3, max_col=11, min_row=20), from_rows=True, titles_from_data=False)
bc.set_categories(Reference(lp, min_col=3, max_col=11, min_row=16)); bc.legend = None
lp.add_chart(bc, "E33")

# Solver model stored as sheet-scoped defined names (what Excel writes when you click Solve/Save)
sid = wb.sheetnames.index("LP_Model")
solver = {
    "solver_adj": "LP_Model!$C$20:$K$20", "solver_opt": "LP_Model!$C$27", "solver_typ": "1", "solver_val": "0",
    "solver_eng": "2", "solver_neg": "1", "solver_lin": "1", "solver_ver": "3", "solver_num": "5",
    "solver_lhs1": "LP_Model!$C$21:$K$21", "solver_rel1": "1", "solver_rhs1": "LP_Model!$C$9",
    "solver_lhs2": "LP_Model!$C$21:$K$21", "solver_rel2": "3", "solver_rhs2": "0",
    "solver_lhs3": "LP_Model!$K$21", "solver_rel3": "2", "solver_rhs3": "0",
    "solver_lhs4": "LP_Model!$C$20", "solver_rel4": "3", "solver_rhs4": "LP_Model!$C$10",
    "solver_lhs5": "LP_Model!$D$20:$K$20", "solver_rel5": "1", "solver_rhs5": "LP_Model!$C$11",
    "solver_cvg": "0.0001", "solver_drv": "1", "solver_est": "1", "solver_itr": "2147483647", "solver_mip": "2147483647",
    "solver_nod": "2147483647", "solver_pre": "0.000001", "solver_rbv": "1", "solver_scl": "1", "solver_sho": "2",
    "solver_ssz": "100", "solver_tim": "2147483647", "solver_tol": "0", "solver_rlx": "2", "solver_mrt": "0.075",
    "solver_msl": "2", "solver_nwt": "1", "solver_rsd": "0", "solver_soc": "0", "solver_lva": "0", "solver_ntri": "1000",
    "solver_ntrr": "1", "solver_ntmr": "1", "solver_ntia": "1", "solver_ntip": "1",
}
for k, v in solver.items():
    dn = DefinedName(k, attr_text=v, localSheetId=sid, hidden=True)
    lp.defined_names[k] = dn

# ---------------------------------------------------------------- Data_Monthly
dm = wb.create_sheet("Data_Monthly")
cols = ["ym", "price_rs_qtl", "arrivals_t", "markets_reporting", "trading_days", "arrivals_per_market_day_t"]
heads = ["Month", "Price ₹/quintal (arrival-weighted modal)", "Arrivals (t)", "Markets reporting", "Trading days", "Arrivals per market-day (t)"]
for j, h in enumerate(heads):
    c = dm.cell(row=1, column=1 + j, value=h); c.font = F_H; c.fill = FILL_H; c.alignment = Alignment(wrap_text=True)
for i, row in enumerate(monthly[cols].itertuples(index=False), start=2):
    for j, v in enumerate(row):
        c = dm.cell(row=i, column=1 + j, value=(round(float(v), 2) if j and pd.notna(v) else v))
        if j in (1, 2, 5):
            c.number_format = NUM1
dm.freeze_panes = "A2"
for j, w in enumerate([10, 22, 14, 12, 12, 18]):
    dm.column_dimensions[chr(ord("A") + j)].width = w
lc = LineChart(); lc.title = "Maharashtra onion price, ₹/quintal"; lc.height = 8; lc.width = 24; lc.legend = None
lc.add_data(Reference(dm, min_col=2, min_row=1, max_row=len(monthly) + 1), titles_from_data=True)
lc.set_categories(Reference(dm, min_col=1, min_row=2, max_row=len(monthly) + 1))
dm.add_chart(lc, "H2")

# ---------------------------------------------------------------- Backtest
bt = pd.DataFrame(R["backtest_robust"])
bsh = wb.create_sheet("Backtest")
bsh["A1"] = "Backtest 2017–2024 (Python): net ₹ per tonne harvested, evaluated at ACTUAL prices"; bsh["A1"].font = F_T
piv = bt.pivot_table(index="year", columns=["scenario", "strategy"], values="net_per_t").round(0)
piv.columns = [f"{a} · {b.replace('_', ' ')}" for a, b in piv.columns]
for j, h in enumerate(["Season"] + list(piv.columns)):
    c = bsh.cell(row=3, column=1 + j, value=h); c.font = F_H; c.fill = FILL_H; c.alignment = Alignment(wrap_text=True)
for i, (yr, row) in enumerate(piv.iterrows(), start=4):
    bsh.cell(row=i, column=1, value=int(yr))
    for j, v in enumerate(row.values):
        c = bsh.cell(row=i, column=2 + j, value=float(v)); c.number_format = NUM0
bsh.row_dimensions[3].height = 45
for j in range(len(piv.columns) + 1):
    bsh.column_dimensions[chr(ord("A") + j)].width = 15
t = R["tests_robust"]
bsh.cell(row=14, column=1, value="Paired tests (forecast plans)").font = F_B
for i, (k, v) in enumerate(t.items(), start=15):
    bsh.cell(row=i, column=1, value=k)
    bsh.cell(row=i, column=2, value=f"mean diff ₹{v['mean_diff_rs_per_t']:,.0f}/t · wins {v['wins']}/{v['n_seasons']} · paired-t p={v['paired_t_one_sided_p']} · Wilcoxon p={v['wilcoxon_one_sided_p']}")

# ---------------------------------------------------------------- Sensitivity
se = wb.create_sheet("Sensitivity")
se["A1"] = "Average realised gain vs selling all in April (₹ per tonne), 2017–2024 — storage of the chawl type"; se["A1"].font = F_T
g = R["sensitivity_2017_2024"]["grid_delta_h"]
hs = list(next(iter(g.values())).keys())
se.cell(row=3, column=1, value="δ / h →").font = F_H; se.cell(row=3, column=1).fill = FILL_H
for j, h in enumerate(hs):
    c = se.cell(row=3, column=2 + j, value=f"₹{h}"); c.font = F_H; c.fill = FILL_H
for i, (d, rowv) in enumerate(g.items(), start=4):
    se.cell(row=i, column=1, value=float(d)).number_format = "0%"
    for j, h in enumerate(hs):
        se.cell(row=i, column=2 + j, value=rowv[h]).number_format = NUM0
se.conditional_formatting.add(f"B4:{chr(ord('B') + len(hs) - 1)}{3 + len(g)}",
                              ColorScaleRule(start_type="min", start_color="F2C7A9", mid_type="num", mid_value=0, mid_color="FFFFFF", end_type="max", end_color="C9A3B8"))
se.cell(row=12, column=1, value=f"Break-even monthly loss for chawl storage (h = ₹250): {R['sensitivity_2017_2024']['breakeven_delta_B']:.1%}").font = F_B
rr = 14
for key in ["delta_B", "delta_C", "h_B", "h_C", "C_capacity_C", "L_C", "U_C"]:
    se.cell(row=rr, column=1, value=key).font = F_B
    for j, (k, v) in enumerate(R["sensitivity_2017_2024"][key].items()):
        se.cell(row=rr, column=2 + j, value=k); se.cell(row=rr + 1, column=2 + j, value=v).number_format = NUM0
    rr += 3
se.column_dimensions["A"].width = 16

# ---------------------------------------------------------------- H1
hr = wb.create_sheet("H1_Regression")
hr["A1"] = "H1 — log price on log arrivals (elasticity β)"; hr["A1"].font = F_T
heads = ["Model", "Formula", "n", "β (elasticity)", "SE (OLS)", "p (OLS)", "SE (HAC)", "p (HAC)", "Adj. R²", "95% CI low", "95% CI high"]
for j, h in enumerate(heads):
    c = hr.cell(row=3, column=1 + j, value=h); c.font = F_H; c.fill = FILL_H
for i, (k, v) in enumerate([(k, v) for k, v in R["h1"].items() if k[:1] in "MD"], start=4):
    vals = [k, v["formula"], v["n"], v["elasticity"], v["se_ols"], v["p_ols"], v["se_hac"], v["p_hac"], v["adj_r2"], v["ci95_low"], v["ci95_high"]]
    for j, x in enumerate(vals):
        c = hr.cell(row=i, column=1 + j, value=x)
        if j in (5, 7):
            c.number_format = "0.0000"
hr.cell(row=11, column=1, value=R["h1"]["headline"]["interpretation"]).font = F_B
for j, w in enumerate([26, 36, 7, 14, 10, 10, 10, 10, 9, 11, 11]):
    hr.column_dimensions[chr(ord("A") + j)].width = w

out = kc.ROOT / "excel" / "KandaCode_LP_Model.xlsx"
out.parent.mkdir(exist_ok=True)
wb.active = 1
wb.save(out)
print("wrote", out, {f"{y}{k}": round(v) for (y, k), v in py.items()})
