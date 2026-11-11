"""Kanda Code - builds the mandatory 3-page FINAL REPORT (A4, Times New Roman 11 pt, single spacing).

Outputs
  report/KandaCode_Final_Report.docx   (python-docx)
  report/KandaCode_Final_Report.pdf    (docx2pdf -> MS Word)
  report/fig_report_1.png, fig_report_2.png, report/mark_rings.png   (figures drawn at print size)

Every number is read from outputs/results.json (the single source of truth, see docs/KEY_NUMBERS.md),
so the report stays consistent if the analysis is rerun. Run:  python src/build_report.py
"""
import json
import re
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mt
import numpy as np
import pandas as pd
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor, Mm

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
REP = ROOT / "report"
REP.mkdir(exist_ok=True)
R = json.loads((OUT / "results.json").read_text(encoding="utf-8"))

# ---- brand colours and fonts -------------------------------------------------------------------------
INK, MUTED, RULE, PAPER = "#1D1420", "#5E5260", "#E6DDE6", "#F8F5F9"
PLUM, COPPER, SLATE, GOLD, SCALLION, ROT = "#5B1A45", "#B85C38", "#8E8489", "#D9A441", "#3F7D3A", "#A33A3A"
FONT = "Times New Roman"
BODY_PT = 11


def rgb(h):
    h = h.lstrip("#")
    return RGBColor(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


# ---- numbers (all from results.json) -------------------------------------------------------------------
dq, val, sp, eda = R["data_quality"], R["validation_vs_lasalgaon"], R["spotcheck_2020_2024"], R["eda"]
h1, fc = R["h1"], R["forecast"]
m3 = h1["M3_month_year_FE"]
SS = R["strategy_summary_2017_2024"]
S23 = R["strategy_summary_2023_2024"]
TR = R["tests_robust"]
I4 = R["industry40"]
SEN = R["sensitivity_2017_2024"]
P24 = R["plan_2024"]
LPp = R["lp_params_base"]
SCN = R["scenarios"]
SIDX = pd.read_csv(OUT / "tables" / "seasonal_profile.csv", index_col=0)


def n0(x):
    """Rs-style integer with thousands separator; true minus sign."""
    s = f"{abs(x):,.0f}"
    return ("−" + s) if x < 0 else s


def mape(meth, part="decision_horizon"):
    return fc[part][meth]["MAPE"]


best = fc["best_method"]
labels = fc["labels"]
vh = fc["validation_horizon"]
ranked = sorted(vh, key=lambda k: vh[k]["MAPE"])
runner = ranked[1]
dv = R["decision_value_by_forecast_method_2017_2024"]
shape_vals = [dv[k]["C"] for k in dv if dv[k]["C"] > 0]
crf = I4["capital_recovery_factor_10y_10pct"]
uplift_cap = I4["uplift_C_over_B_rs_per_t_capacity_per_season"]
breakeven_capex = I4["capex_B_rs_per_t_capacity"] + uplift_cap / crf          # net annual benefit = 0
dC = SEN["delta_C"]
per_pp = (dC["0.005"] - dC["0.080"]) / ((0.080 - 0.005) * 100)                  # Rs/t per pp of monthly loss
mv = P24["C"]["marginal_values"]
hand = P24["C"]["shadow_handling_by_month"]                                       # May..Dec
xC = P24["C"]["x"]
nas = {r["year"]: r["gain_vs_harvest_per_t"] for r in R["backtest_nasik_2023_2024"] if r["scenario"] == "C"}
apr, nov = SIDX.loc["Apr", "price_index_mean"], SIDX.loc["Nov", "price_index_mean"]
lasi = eda["lasalgaon_seasonal_index_1996_2013"]
dist = dq["arrival_weight_by_district_pct_top6"]
rn = h1["robust_normalisation"]
m5 = h1["M5_dynamic_with_lagged_price"]
rev = h1["reverse_causality_lnA_on_lagged_price"]
pt = R["price_taker"]
c_ex = I4["capex_range"]
fd = fc["decision_horizon"][best]
_pv = [r for r in R["planned_vs_realised"] if r["year"] == 2024 and r["scenario"] == "C"][0]
pvr24 = (2024, _pv["forecast_objective_per_t"], _pv["net_per_t"])
fpo_net_lakh = I4['base_case']['net_annual_benefit_rs_per_t_capacity'] * LPp['C'] / 1e5     # net of capital, 700 t capacity
mm_delta = 1 - (1 - 0.1407) ** (1 / 6)                       # ICAR multi-module store: 14.07% lost in 6 months [5]

# ---- extension (added after the approved proposal): NASA POWER weather (H4) + value of loss information ----
W = R["weather"]
H4 = W["h4_rain_price_link"]
_lat, _lon = re.search(r"([\d.]+)N\s+([\d.]+)E", W["source"]).groups()
CLIM = W["climatology_2014_2024"]
rh_jas = [CLIM[m]["rh2m_pct"] for m in ("Jul", "Aug", "Sep")]
rain_feed_C = W["realtime_replan_nov_dec"]["C"]["mean_value_of_rain_feed"]
rain_feed_B = W["realtime_replan_nov_dec"]["B"]["mean_value_of_rain_feed"]
VOI = R["value_of_loss_information"]
_vgrid = lambda prices, s: {round(g_["delta_true"], 4): g_ for g_ in VOI[prices][s]["grid"]}
vB_fc, vC_pf = _vgrid("with_forecast_prices", "B"), _vgrid("with_perfect_price_foresight", "C")
voiC_hi = [g_["voi_sensor"] for d_, g_ in vC_pf.items() if 0.08 <= d_ <= 0.15]

# =========================================================================================================
# FIGURES (drawn at print size so 7-pt figure text prints at 7 pt)
# =========================================================================================================
plt.rcParams.update({
    "font.family": "Segoe UI", "font.size": 7, "axes.titlesize": 7.6, "axes.titleweight": "bold",
    "axes.labelsize": 7, "axes.edgecolor": "#BDB3B8", "axes.linewidth": 0.6, "axes.spines.top": False,
    "axes.spines.right": False, "axes.grid": True, "grid.color": "#EEE8EE", "grid.linewidth": 0.5,
    "axes.axisbelow": True, "xtick.color": MUTED, "ytick.color": MUTED, "xtick.labelsize": 6.5,
    "ytick.labelsize": 6.5, "axes.labelcolor": "#3E3539", "legend.frameon": False, "legend.fontsize": 6.3,
    "figure.facecolor": "white", "axes.facecolor": "white", "axes.titlelocation": "left", "axes.titlepad": 4,
    "xtick.major.size": 2, "ytick.major.size": 2, "xtick.major.width": 0.5, "ytick.major.width": 0.5,
})
monthly = pd.read_csv(ROOT / "data" / "processed" / "maharashtra_onion_monthly.csv")
monthly["ym"] = pd.PeriodIndex(monthly["ym"], freq="M")
monthly = monthly.set_index("ym")
nh = pd.read_csv(ROOT / "data" / "processed" / "lasalgaon_nhrdf_monthly.csv")
nh["ym"] = pd.PeriodIndex(nh["ym"], freq="M")
nh = nh.set_index("ym")
EVENTS = [("2019-09", "export ban"), ("2020-09", "export ban"), ("2023-08", "40% duty"), ("2023-12", "export ban")]
FIGW = 7.05
FIGH = 1.26


def rupee_k(v, _):
    return f"{v:,.0f}"


def fig1(path):
    fig, (a, b) = plt.subplots(1, 2, figsize=(FIGW, FIGH), gridspec_kw={"width_ratios": [2.35, 1]})
    ts = monthly.index.to_timestamp()
    for y in range(2014, 2025):
        a.axvspan(pd.Timestamp(f"{y}-04-01"), pd.Timestamp(f"{y}-05-31"), color="#EBC9C9", alpha=0.45, lw=0)
    a.plot(ts, monthly["price_rs_qtl"] / 100, color=PLUM, lw=1.25, label="Maharashtra composite (96 APMCs)")
    l = nh["lasalgaon_price_rs_qtl"].dropna()
    l = l[l.index >= pd.Period("2014-01", "M")]
    a.plot(l.index.to_timestamp(), l / 100, color=COPPER, lw=0.9, ls=(0, (3, 1.6)), label="Lasalgaon APMC, NHRDF (to Jun 2019)")
    for d, lab in EVENTS:
        x = pd.Timestamp(d + "-01")
        a.axvline(x, color=INK, lw=0.45, alpha=0.35)
        a.text(x - pd.Timedelta(days=25), 53, lab, rotation=90, va="top", ha="right", fontsize=5.6, color=MUTED)
    a.set_ylim(0, 55)
    a.set_xlim(pd.Timestamp("2013-11-01"), pd.Timestamp("2025-02-01"))
    a.set_ylabel("Rs per kg")
    a.set_title("(a) Monthly wholesale price, 2014–2024 (shaded: Apr–May harvest)", loc="left")
    a.legend(loc="upper left", ncol=1, handlelength=2.2, borderaxespad=0.2)
    # (b) seasonal index
    mon = list(SIDX.index)
    x = np.arange(12)
    v = SIDX["price_index_mean"].values
    cols = ["#CDBFC8" if i < 3 else PLUM for i in range(12)]
    b.bar(x, v, color=cols, width=0.68, alpha=0.9)
    b.scatter(x, [lasi[m] for m in mon], s=9, color=COPPER, zorder=3, edgecolor="white", lw=0.4,
              label="Lasalgaon 1996–2013")
    b.axhline(1, color=INK, lw=0.5, alpha=0.5)
    b.set_xticks(x, [m[0] for m in mon])
    b.set_ylim(0, 1.85)
    b.set_title("(b) Seasonal index (price ÷ year mean)", loc="left")
    b.text(3, v[3] + 0.12, f"{v[3]:.2f}", ha="center", fontsize=6.2, color=PLUM, fontweight="bold")
    b.text(10, v[10] + 0.06, f"{v[10]:.2f}", ha="center", fontsize=6.2, color=PLUM, fontweight="bold")
    from matplotlib.patches import Patch
    hs, ls = b.get_legend_handles_labels()
    b.legend(hs + [Patch(color=PLUM, alpha=0.9)], ls + ["2014–24 composite"], loc="upper left", fontsize=5.8,
             borderaxespad=0.1, handlelength=1.2, bbox_to_anchor=(0.0, 0.93))
    fig.tight_layout(pad=0.25, w_pad=1.0)
    fig.savefig(path, dpi=300)
    plt.close(fig)


def fig2(path):
    bt = pd.DataFrame(R["backtest_robust"])
    piv = lambda s: bt[bt.strategy == s].pivot(index="year", columns="scenario", values="gain_vs_harvest_per_t") / 1000
    fp, pf, cr = piv("forecast_plan"), piv("perfect_foresight"), piv("calendar_rule_exante")
    yrs = list(fp.index)
    x = np.arange(len(yrs))
    fig, (a, b) = plt.subplots(1, 2, figsize=(FIGW, FIGH), gridspec_kw={"width_ratios": [1.75, 1]})
    a.axvspan(5.5, 7.5, color=GOLD, alpha=0.10, lw=0)
    a.text(6.5, 23.8, "test seasons", ha="center", va="top", fontsize=5.9, color="#8A6A1E")
    a.bar(x - 0.2, fp["B"], width=0.36, color=COPPER, label="B chawl – LP plan (stores 0 t)")
    a.bar(x + 0.2, fp["C"], width=0.36, color=PLUM, label="C cold/IoT – LP plan")
    a.scatter(x - 0.2, cr["B"], marker="D", s=9, facecolor="white", edgecolor=COPPER, lw=0.8, zorder=3,
              label="Sep–Nov calendar rule (B, C)")
    a.scatter(x + 0.47, cr["C"], marker="D", s=9, facecolor="white", edgecolor=INK, lw=0.8, zorder=3)
    a.scatter(x + 0.2, pf["C"], marker="_", s=70, color=PLUM, lw=1.2, zorder=3, label="C perfect-foresight ceiling")
    for i, vv in enumerate(fp["C"]):
        if vv > 2.6:
            a.text(i + 0.2, vv - 0.9, f"{vv:+.1f}", ha="center", va="top", fontsize=5.4, color="white", fontweight="bold")
        else:
            a.text(i + 0.2, (vv + 0.4) if vv >= 0 else (vv - 0.45), f"{vv:+.1f}", ha="center",
                   va="bottom" if vv >= 0 else "top", fontsize=5.4, color=PLUM, fontweight="bold")
    a.axhline(0, color=INK, lw=0.6)
    a.set_xticks(x, [str(y) for y in yrs])
    a.set_ylim(-4.6, 24.6)
    a.set_ylabel("Rs '000 per t vs April sale")
    a.set_title("(a) Backtest at actual prices: gain over selling everything in April", loc="left")
    a.legend(loc="upper left", fontsize=5.7, ncol=2, borderaxespad=0.1, handlelength=1.4, labelspacing=0.2, columnspacing=1.0)
    # (b) loss-rate sensitivity
    dB = {float(k): v / 1000 for k, v in SEN["delta_B"].items()}
    dCc = {float(k): v / 1000 for k, v in SEN["delta_C"].items()}
    be = SEN["breakeven_delta_B"]
    b.axhline(0, color=INK, lw=0.6)
    b.plot([k * 100 for k in dCc], list(dCc.values()), color=PLUM, lw=1.3, marker="o", ms=2.6,
           label="cold/IoT-type cost (h = Rs 700)")
    b.plot([k * 100 for k in dB], list(dB.values()), color=COPPER, lw=1.3, marker="o", ms=2.6,
           label="chawl-type cost (h = Rs 250)")
    b.axvline(be * 100, color=ROT, lw=0.7, ls=(0, (2, 1.5)))
    b.text(be * 100 + 0.5, 0.75, f"chawl break-even\nδ = {be*100:.1f}%", fontsize=5.7, color=ROT, va="bottom")
    b.annotate("ICAR chawl\n18.05%", (18.05, 0), xytext=(21.5, 2.7), fontsize=5.6, color=COPPER,
               arrowprops=dict(arrowstyle="-", lw=0.5, color=COPPER))
    b.annotate("ICAR-DOGR cold\n1.83%", (1.8, dC["0.018"] / 1000), xytext=(4.2, 6.0), fontsize=5.6, color=PLUM,
               arrowprops=dict(arrowstyle="-", lw=0.5, color=PLUM))
    b.set_xlabel("Monthly storage loss δ (%)", labelpad=1)
    b.set_ylabel("Mean gain, Rs '000/t")
    b.set_ylim(-1.5, 7.4)
    b.set_xlim(-0.5, 27)
    b.set_title("(b) Value falls with every point of monthly loss", loc="left")
    b.legend(loc="upper right", fontsize=5.6, borderaxespad=0.1, handlelength=1.4)
    fig.tight_layout(pad=0.25, w_pad=1.0)
    fig.savefig(path, dpi=300)
    plt.close(fig)


def rings(path):
    fig, ax = plt.subplots(figsize=(0.9, 0.9))
    for i, r in enumerate(np.linspace(0.18, 0.95, 6)):
        ax.add_patch(plt.Circle((0, 0), r, fill=False, lw=0.9 if i < 5 else 1.6,
                                color=PLUM if i % 2 == 0 else COPPER, alpha=0.95 - i * 0.08))
    ax.add_patch(plt.Circle((0, 0), 0.07, color=GOLD))
    ax.set_xlim(-1, 1); ax.set_ylim(-1, 1); ax.set_aspect("equal"); ax.axis("off")
    fig.savefig(path, dpi=300, transparent=True, bbox_inches="tight", pad_inches=0)
    plt.close(fig)


F1, F2, MARK = REP / "fig_report_1.png", REP / "fig_report_2.png", REP / "mark_rings.png"
fig1(F1); fig2(F2); rings(MARK)

# =========================================================================================================
# DOCX helpers
# =========================================================================================================
doc = Document()
sec = doc.sections[0]
sec.page_width, sec.page_height = Mm(210), Mm(297)
MARG = Inches(0.5)
sec.left_margin = sec.right_margin = MARG
sec.top_margin = Inches(0.38)
sec.bottom_margin = Inches(0.37)
sec.header_distance = Inches(0.25)
sec.footer_distance = Inches(0.22)
TEXTW = (Mm(210) - 2 * MARG)

st = doc.styles["Normal"]
st.font.name = FONT
st.font.size = Pt(BODY_PT)
st.font.color.rgb = rgb(INK)
st.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
st.element.rPr.rFonts.set(qn("w:cs"), FONT)
pf0 = st.paragraph_format
pf0.line_spacing_rule = WD_LINE_SPACING.SINGLE
pf0.line_spacing = 1.0
pf0.space_after = Pt(1.5)
pf0.space_before = Pt(0)

TOKEN = re.compile(r"(\*\*.+?\*\*|\*[^*\s][^*]*?\*|_\{.+?\}|\^\{.+?\}|\[\[.+?\]\])")


def run(p, text, size=None, bold=False, italic=False, color=None, font=FONT, sub=False, sup=False, caps=False):
    r = p.add_run(text)
    r.font.name = font
    rpr = r._element.get_or_add_rPr()
    rf = rpr.find(qn("w:rFonts"))
    if rf is None:
        rf = OxmlElement("w:rFonts"); rpr.insert(0, rf)
    for a in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        rf.set(qn(a), font)
    r.font.size = Pt(size or BODY_PT)
    r.font.bold = bold
    r.font.italic = italic
    r.font.subscript = sub
    r.font.superscript = sup
    r.font.small_caps = caps
    if color:
        r.font.color.rgb = rgb(color)
    return r


def rich(p, text, size=None, color=None, base_bold=False):
    """Mini-markup: **bold**, *italic*, _{subscript}, ^{superscript}, [[plum bold]]."""
    for tok in TOKEN.split(text):
        if not tok:
            continue
        if tok.startswith("**"):
            run(p, tok[2:-2], size, bold=True, color=color)
        elif tok.startswith("[["):
            run(p, tok[2:-2], size, bold=True, color=PLUM)
        elif tok.startswith("_{"):
            run(p, tok[2:-1], size, sub=True, color=color, bold=base_bold, italic=True)
        elif tok.startswith("^{"):
            run(p, tok[2:-1], size, sup=True, color=color, bold=base_bold)
        elif tok.startswith("*") and tok.endswith("*") and len(tok) > 2:
            run(p, tok[1:-1], size, italic=True, color=color, bold=base_bold)
        else:
            run(p, tok, size, color=color, bold=base_bold)
    return p


def para(text="", size=None, align=WD_ALIGN_PARAGRAPH.JUSTIFY, after=1.5, before=0, color=None, keep=False, indent=None):
    p = doc.add_paragraph()
    p.alignment = align
    f = p.paragraph_format
    f.space_after, f.space_before = Pt(after), Pt(before)
    f.line_spacing_rule = WD_LINE_SPACING.SINGLE
    if keep:
        f.keep_with_next = True
    if indent is not None:
        f.left_indent = Inches(indent)
    if text:
        rich(p, text, size, color)
    return p


def border(p, side="bottom", color=RULE, sz=6, space=1):
    pPr = p._p.get_or_add_pPr()
    bdr = pPr.find(qn("w:pBdr"))
    if bdr is None:
        bdr = OxmlElement("w:pBdr"); pPr.append(bdr)
    e = OxmlElement(f"w:{side}")
    e.set(qn("w:val"), "single"); e.set(qn("w:sz"), str(sz)); e.set(qn("w:space"), str(space))
    e.set(qn("w:color"), color.lstrip("#"))
    bdr.append(e)


def heading(num, title):
    p = para(after=1, before=3, keep=True, align=WD_ALIGN_PARAGRAPH.LEFT)
    run(p, f"{num} ", 12, bold=True, color=PLUM)
    run(p, title, 12, bold=True, color=INK)
    border(p, "bottom", RULE, 4, 1)
    return p


def bullet(lead, text, size=None):
    p = para(after=1, indent=0.16)
    p.paragraph_format.first_line_indent = Inches(-0.13)
    run(p, "▪ ", (size or BODY_PT) - 2, color=PLUM)
    if lead:
        run(p, lead + " ", size, bold=True, color=PLUM)
    rich(p, text, size)
    return p


def shade(cell, hexcolor):
    tcPr = cell._tc.get_or_add_tcPr()
    s = OxmlElement("w:shd")
    s.set(qn("w:val"), "clear"); s.set(qn("w:color"), "auto"); s.set(qn("w:fill"), hexcolor.lstrip("#"))
    tcPr.append(s)


def cell_margins(table, top=25, bottom=25, left=60, right=60):
    tblPr = table._tbl.tblPr
    m = OxmlElement("w:tblCellMar")
    for k, v in (("top", top), ("bottom", bottom), ("left", left), ("right", right)):
        e = OxmlElement(f"w:{k}"); e.set(qn("w:w"), str(v)); e.set(qn("w:type"), "dxa"); m.append(e)
    tblPr.append(m)


def table_borders(table, outer=RULE, inner=RULE, inside_v=False, top_color=None, sz=4):
    tblPr = table._tbl.tblPr
    b = OxmlElement("w:tblBorders")
    for side in ("top", "left", "bottom", "right", "insideH", "insideV"):
        e = OxmlElement(f"w:{side}")
        if side in ("left", "right") or (side == "insideV" and not inside_v):
            e.set(qn("w:val"), "nil")
        else:
            e.set(qn("w:val"), "single")
            e.set(qn("w:sz"), str(10 if side == "top" and top_color else sz))
            e.set(qn("w:color"), ((top_color if side == "top" and top_color else (outer if side in ("top", "bottom") else inner)).lstrip("#")))
        b.append(e)
    tblPr.append(b)


def no_borders(table):
    tblPr = table._tbl.tblPr
    b = OxmlElement("w:tblBorders")
    for side in ("top", "left", "bottom", "right", "insideH", "insideV"):
        e = OxmlElement(f"w:{side}"); e.set(qn("w:val"), "nil"); b.append(e)
    tblPr.append(b)


def set_col_widths(table, widths):
    table.autofit = False
    tblPr = table._tbl.tblPr
    lay = OxmlElement("w:tblLayout"); lay.set(qn("w:type"), "fixed"); tblPr.append(lay)
    for row in table.rows:
        for i, w in enumerate(widths):
            row.cells[i].width = w
    grid = table._tbl.tblGrid
    for i, gc in enumerate(grid.findall(qn("w:gridCol"))):
        gc.set(qn("w:w"), str(int(widths[i] / 635)))


def cell_text(cell, text, size=9, bold=False, color=None, align=WD_ALIGN_PARAGRAPH.LEFT, after=0):
    p = cell.paragraphs[0]
    p.alignment = align
    p.paragraph_format.space_after = Pt(after)
    p.paragraph_format.space_before = Pt(0)
    for chunk_i, chunk in enumerate(text.split("\n")):
        if chunk_i:
            p = cell.add_paragraph(); p.alignment = align
            p.paragraph_format.space_after = Pt(after); p.paragraph_format.space_before = Pt(0)
        rich(p, chunk, size, color, base_bold=bold)
    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    return p


def data_table(rows, widths, header_fill=PLUM, size=9, zebra=True, aligns=None, container=None):
    host = container if container is not None else doc
    t = host.add_table(rows=len(rows), cols=len(rows[0]))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    table_borders(t, outer=PLUM, inner=RULE)
    cell_margins(t, 18, 18, 55, 55)
    for i, row in enumerate(rows):
        for j, txt in enumerate(row):
            c = t.cell(i, j)
            al = (aligns[j] if aligns else WD_ALIGN_PARAGRAPH.LEFT)
            if i == 0:
                shade(c, header_fill)
                cell_text(c, txt, size, bold=True, color="#FFFFFF", align=al)
            else:
                if zebra and i % 2 == 0:
                    shade(c, PAPER)
                cell_text(c, txt, size, align=al)
    set_col_widths(t, widths)
    # header row repeats / never split rows
    for ri, r_ in enumerate(t.rows):
        trPr = r_._tr.get_or_add_trPr()
        cs = OxmlElement("w:cantSplit"); trPr.append(cs)
        if ri < len(t.rows) - 1:
            for c in r_.cells:
                for cp_ in c.paragraphs:
                    cp_.paragraph_format.keep_with_next = True
    return t


def caption(text, after=2.5, before=1, keep=False):
    p = para(after=after, before=before, align=WD_ALIGN_PARAGRAPH.LEFT, keep=keep)
    lab, rest = text.split("|", 1)
    run(p, lab, 9, bold=True, color=PLUM)
    rich(p, rest, 9, MUTED)
    return p


def figure(path, cap):
    p = para(after=0, before=2, align=WD_ALIGN_PARAGRAPH.CENTER, keep=True)
    p.add_run().add_picture(str(path), width=Inches(FIGW))
    caption(cap)


def add_field(p, instr, size=8, color=MUTED):
    r = run(p, "", size, color=color)
    f1 = OxmlElement("w:fldChar"); f1.set(qn("w:fldCharType"), "begin")
    it = OxmlElement("w:instrText"); it.set(qn("xml:space"), "preserve"); it.text = instr
    f2 = OxmlElement("w:fldChar"); f2.set(qn("w:fldCharType"), "separate")
    t = OxmlElement("w:t"); t.text = "1"
    f3 = OxmlElement("w:fldChar"); f3.set(qn("w:fldCharType"), "end")
    for e in (f1, it, f2, t, f3):
        r._element.append(e)


# footer
fp = sec.footer.paragraphs[0]
fp.alignment = WD_ALIGN_PARAGRAPH.LEFT
run(fp, "KANDA CODE", 7.5, bold=True, color=PLUM)
run(fp, " When should onion farmers sell their crop? · Industry 4.0 (MS4001), IIT Madras BS · page ", 7.5, color=MUTED)
add_field(fp, "PAGE", 7.5)
run(fp, " of ", 7.5, color=MUTED)
add_field(fp, "NUMPAGES", 7.5)
border(fp, "top", RULE, 4, 2)



def mn(x, fmt="{:.2f}"):
    """Format a number with a true minus sign."""
    return fmt.format(x).replace("-", "−")


# =========================================================================================================
# TITLE BLOCK
# =========================================================================================================
tb = doc.add_table(rows=1, cols=2)
no_borders(tb)
cell_margins(tb, 0, 0, 0, 0)
set_col_widths(tb, [Inches(6.2), Inches(0.9)])
L, Rc = tb.cell(0, 0), tb.cell(0, 1)
p = L.paragraphs[0]
p.paragraph_format.space_after = Pt(1)
run(p, "IIT MADRAS BS DEGREE · INDUSTRY 4.0 (MS4001) · FINAL PROJECT REPORT", 8, bold=True, color="#9A7322")
p = L.add_paragraph(); p.paragraph_format.space_after = Pt(0)
run(p, "When Should Onion Farmers Sell Their Crop?", 17, bold=True, color=PLUM)
p = L.add_paragraph(); p.paragraph_format.space_after = Pt(1)
run(p, "A forecast-driven sell-or-store plan for Lasalgaon-belt FPOs", 12.5, italic=True, color=INK)
p = L.add_paragraph(); p.paragraph_format.space_after = Pt(0)
run(p, "Team Kanda Code", 9.5, bold=True, color=PLUM)
run(p, " · equal contribution, 20% each · <roll>@ds.study.iitm.ac.in · "
       "reproducible in Python + Excel", 9, color=MUTED)
pr = Rc.paragraphs[0]; pr.alignment = WD_ALIGN_PARAGRAPH.CENTER
pr.paragraph_format.space_after = Pt(0)
pr.add_run().add_picture(str(MARK), width=Inches(0.62))
pr2 = Rc.add_paragraph(); pr2.alignment = WD_ALIGN_PARAGRAPH.CENTER
run(pr2, "कांदा", 10, bold=True, color=PLUM, font="Nirmala UI")
pr2.paragraph_format.space_after = Pt(0)
Rc.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER

# members: one row, five equal cells
members = [("Raghuram Devarayi", "21f1005431"), ("Parashmani Datta", "21f2000987"), ("Kathan Desai", "24f1002390"),
           ("Yash Arabhavi", "22f3001882"), ("Aaryan Choudhary", "23f2003700")]
mt_ = doc.add_table(rows=1, cols=5)
no_borders(mt_)
table_borders(mt_, outer=RULE, inner=RULE, inside_v=True, sz=4)
cell_margins(mt_, 22, 22, 60, 40)
for j, (nm, roll) in enumerate(members):
    c = mt_.cell(0, j)
    p = c.paragraphs[0]; p.paragraph_format.space_after = Pt(0)
    run(p, nm, 9.5, bold=True, color=INK)
    run(p, f" {roll} ", 8.5, color=MUTED)
    run(p, "20%", 8.5, bold=True, color=SCALLION)
set_col_widths(mt_, [Inches(7.1 / 5)] * 5)
para(after=0).paragraph_format.line_spacing = Pt(3)

# at-a-glance strip
gl = doc.add_table(rows=2, cols=4)
no_borders(gl)
table_borders(gl, outer=PLUM, inner="#FFFFFF", top_color=PLUM)
cell_margins(gl, 18, 16, 70, 50)
glance = [
    (f"{apr:.2f}× → {nov:.2f}×", "Apr → Nov price, × the year’s mean", PLUM),
    ("0 t stored", f"best chawl plan ({SCN['B']['delta']*100:.0f}%/month loss)", COPPER),
    (f"+Rs {n0(I4['uplift_C_over_B_rs_per_t_harvest'])}/t", f"cold/IoT gain; won {TR['H3_C_vs_B']['wins']} of {TR['H3_C_vs_B']['n_seasons']} seasons", PLUM),
    (f"{I4['base_case']['simple_payback_seasons']:.2f} seasons", f"payback; ≈Rs {I4['fpo_annual_uplift_rs_lakh']:.1f} lakh/yr gross", SCALLION),
]
for j, (big, small, col) in enumerate(glance):
    shade(gl.cell(0, j), PAPER); shade(gl.cell(1, j), PAPER)
    cell_text(gl.cell(0, j), big, 12, bold=True, color=col)
    cell_text(gl.cell(1, j), small, 8, color=MUTED)
set_col_widths(gl, [Inches(7.1 / 4)] * 4)

# =========================================================================================================
# 1-4
# =========================================================================================================
heading("1", "Problem Statement")
para(f"Onion farmers in Maharashtra sell most of their rabi crop at the April–May harvest low, although November prices "
     f"beat April’s in every year 2014–24, by a median {eda['median_rise_apr_to_nov_pct']:.0f}%; Lasalgaon farmers have "
     f"been paid Rs 7–10/kg against a cultivation cost of Rs 22–25/kg [16]. Waiting is not free: stored onions shrink and rot – 54.89% in 120 days in a "
     f"ventilated *kanda chawl*, only 5.00–7.14% in cold storage [4]. **Decision problem:** a farmer producer organisation "
     f"(FPO) holds *Q* = {LPp['Q']:,.0f} t at harvest. How many tonnes should it sell in each month, April to December, so "
     f"that the price rise beats storage loss and cost – and what is low-loss, sensor-monitored storage worth?")

heading("2", "Motivation for Problem Selection")
para("**Recurring and large.** The government bought about 6.4 lakh t of onion for its buffer in 2023–24, yet in 2019 "
     "NAFED lost about 53% of a 57,372 t buffer held in traditional storage [16] – consistent with ICAR’s chawl loss rate. "
     "About 65% of the rabi crop is stored and sold in July–December; 1% more availability goes with a 1.3% fall in onion "
     "CPI [10]. **The hardest storage case.** Grains keep and have support prices; tomatoes cannot be stored; onion keeps "
     "4–6 months but rots fast, and its price is highly volatile, most of all at Lasalgaon, Asia’s largest onion market "
     "[9, 12]. **An Industry 4.0 decision.** The gap between 54.9% and about 7% loss prices controlled, IoT-monitored "
     "storage [15] in a tested storage-timing frame [13, 14].")

heading("3", "Research Questions")
para("**RQ1.** How strongly do arrivals move the onion price? **RQ2.** Does an optimised storage plan beat selling "
     "everything at harvest once losses and costs are counted, and in which months should the FPO sell? "
     "**RQ3.** What is low-loss (cold or IoT-monitored) storage worth per tonne, and does it repay its capital? "
     "**RQ4 (extension).** Does late-monsoon rain seen by satellite foreshadow the price rise, and what is sensing a "
     "store’s loss rate worth?")

heading("4", "Hypotheses, Objectives and Constraints")
para("**Hypotheses.** *From the approved proposal:* **H1:** price falls significantly as arrivals rise (β < 0 in a "
     "log–log regression); **H2:** an optimised plan with a ventilated chawl earns more than selling everything at harvest; "
     "**H3:** low-loss storage raises net revenue per tonne by a material margin over a chawl. *Extension beyond the "
     "approved proposal:* **H4:** heavier Sep–Oct rain is followed by a bigger rise from the April price to the Oct–Dec mean.")
para(f"**Objectives.** (O1) Build and validate a price benchmark; (O2) test H1; (O3) pick a March-origin forecast on "
     f"validation seasons only; (O4) solve a linear-programme (LP) sell-or-store plan per scenario with verified shadow "
     f"prices; (O5) backtest on unseen prices and value low-loss storage; (O6, extension) test H4 and value sensor "
     f"information. **Constraints.** *In the LP:* stock balance with monthly loss δ; capacity *C* = {LPp['C']:,.0f} t; an "
     f"April crop-loan sale ≥ *L* = {LPp['L']:,.0f} t; a grading-and-trucking cap *U* = {LPp['U']:,.0f} t/month in May–Dec "
     f"(the April sale goes field-run to traders); all stock sold by December. *On the project:* public secondary data and "
     f"syllabus methods only; the FPO is a price-taker – 1,000 t is {pt['share_april_pct']}% of Lasalgaon’s mean April "
     f"arrivals (implied price impact ≈{pt['implied_price_impact_april_pct']}%).")

# =========================================================================================================
# 5 EDA
# =========================================================================================================
heading("5", "Exploratory Data Analysis (EDA)")
para(f"**Data and the Lasalgaon pivot.** The main source is an Agmarknet compilation of {n0(dq['rows_all_india'])} all-India "
     f"daily mandi records, {dq['date_min'][:4]}–{dq['date_max'][:4]} [1]. Our planned first-week check found "
     f"**{dq['lasalgaon_rows_in_main_dataset']} rows** for Lasalgaon APMC, so we built a Maharashtra arrival-weighted modal "
     f"price, *P*_{{m}} = Σ*A*_{{i}}*p*_{{i}} / Σ*A*_{{i}} over market-days *i* of month *m*, from "
     f"{n0(dq['rows_maharashtra'])} rows in {dq['markets_maharashtra']} APMCs (Ahmednagar {dist['Ahmednagar']}%, Pune "
     f"{dist['Pune']}%, Solapur {dist['Sholapur']}% of weight), dropping {dq['dropped_price_outside_band']} rows "
     f"outside Rs 50–20,000/q and {dq['dropped_relative_price_outliers']} relative outliers (outside 0.2–5× the "
     f"same-day median). **A data trap:** on {n0(dq['market_days_with_multiple_variety_rows'])} market-days with several variety "
     f"rows, {dq['multi_row_market_days_with_repeated_arrivals_pct']:.0f}% repeat the *same* tonnage; summing would "
     f"double-count {n0(dq['tonnes_double_counted_if_rows_summed'])} t, so we keep one row per market-day "
     f"({n0(dq['market_days_clean'])}; {eda['monthly_obs']} months, none missing). **Validation.** Against NHRDF’s "
     f"Lasalgaon series [2] ({val['overlap_months']} months) *r* = {val['pearson_r_levels']:.2f} on levels, "
     f"{val['pearson_r_monthly_log_changes']:.2f} on monthly changes (mean ratio {val['mean_ratio_mh_to_lasalgaon']}); against "
     f"{sp['points']} independent 2020–24 Lasalgaon reports ({sp['msamb_points']} from MSAMB [3]) "
     f"*r* = {sp['pearson_r']:.2f}, our level a median {abs(sp['median_signed_gap_pct'])}% lower (Lasalgaon is the "
     f"premium market); Nasik APMC tracks Lasalgaon at *r* = {val['nasik_pearson_r']:.2f}. **Weather (extension).** NASA "
     f"POWER [17] satellite/reanalysis data (≈0.5° grid) give monthly temperature, relative humidity (RH) and bias-corrected "
     f"rain at Lasalgaon ({_lat}°N {_lon}°E), {H4['years'].replace('-', '–')}; RH is "
     f"{min(rh_jas):.0f}–{max(rh_jas):.0f}% in Jul–Sep, exactly when onions sit in a chawl – physical support for its high "
     f"loss rate.")
para(f"**Patterns.** Mean Rs {eda['price_mean_rs_kg']}/kg, from Rs {eda['price_min_rs_kg']} (Feb 2019) to Rs "
     f"{eda['price_max_rs_kg']} (Dec 2019); coefficient of variation {eda['overall_cv_pct']}%, month-on-month s.d. "
     f"{eda['mom_change_sd_pct']}%; the yearly maximum averages {eda['mean_max_over_min_within_year']}× the minimum. "
     f"The seasonal index (price ÷ year mean) bottoms at {apr:.3f} in April and peaks at {nov:.3f} in November "
     f"(Fig. 1b); November beat April in {eda['years_nov_above_apr']} of {eda['years']} years (median rise "
     f"{eda['median_rise_apr_to_nov_pct']}%), and the 1996–2013 Lasalgaon index (April {lasi['Apr']}, October {lasi['Oct']}) "
     f"has the same shape. The 2019, 2020 and 2023 spikes coincide with export bans or duties, imposed when prices surge [8].")
figure(F1, "Figure 1.|  (a) The composite tracks Lasalgaon; April–May is the trough. "
           "(b) Seasonal index 2014–24 (bars), Lasalgaon 1996–2013 (dots).")

# =========================================================================================================
# 6 METHODOLOGY
# =========================================================================================================
heading("6", "Methodology")
para(f"**H1 – regression.** OLS of ln *P*_{{m}} on ln *A*_{{m}} with 11 month and 10 year dummies ({m3['n']} months); "
     f"*A*_{{m}} is arrivals per market-day, because reporting markets rose from "
     f"{dq['mean_markets_reporting_per_month_2014']:.1f} to {dq['mean_markets_reporting_per_month_2024']:.1f} a month and raw "
     f"totals partly measure coverage. Residuals are autocorrelated (Durbin–Watson {m3['durbin_watson']}), so we use "
     f"Newey–West (HAC, 3-lag) standard errors, a one-sided test of β < 0 and robustness checks (normalisations, lags, "
     f"daily data, reverse regression).")
tb_lab = labels[fc['best_method_on_test_for_reference']].replace(" x ", " × ")
para(f"**Forecasting protocol.** Origin = end of March; forecast April–December (1–9 steps) on an expanding "
     f"window from 2014. Ten syllabus candidates: naive, seasonal naive, 12-month moving average, seasonal index × moving "
     f"average or exponential smoothing (index from our series or 28 years with NHRDF 1996–2013), "
     f"damped Holt–Winters and two regressions. **Selection rule (test held out):** lowest April–December MAPE on "
     f"validation seasons 2019–22, then one score on test seasons 2023–24. Selected: [[regression with trend + month "
     f"dummies]], ln *P*_{{t}} = *a* + *bt* + Σγ_{{k}}*D*_{{k,t}} (validation MAPE {vh[best]['MAPE']:.1f}% vs "
     f"{vh[runner]['MAPE']:.1f}% for seasonal naive): beyond accuracy, its month dummies carry the seasonal shape the "
     f"decision needs, the trend absorbs rising nominal prices, and it is interpretable. The test-best model ({tb_lab}, "
     f"{mape(fc['best_method_on_test_for_reference']):.1f}%) was not adopted: rankings are unstable (Holt–Winters "
     f"{vh['holt_winters']['MAPE']:.1f}% validation, {mape('holt_winters'):.1f}% test) and switching after seeing "
     f"the test would leak it.")
para("**Sell-or-store LP.** *x*_{t} = tonnes sold and *s*_{t} = tonnes in store at the end of month *t* (*t* = 1 April, …, "
     "9 December). Prices are exogenous (price-taker) and loss is proportional, so the model is a linear programme:", after=0.5)
p = para(align=WD_ALIGN_PARAGRAPH.CENTER, after=0.5, keep=True)
rich(p, "max *Z* = Σ*p̂*_{t}*x*_{t} − *h*Σ*s*_{t}  s.t. *s*_{1} = *Q* − *x*_{1};  "
        "*s*_{t} = (1 − δ)*s*_{t−1} − *x*_{t};  *s*_{t} ≤ *C*;  *x*_{1} ≥ *L*;  "
        "*x*_{t} ≤ *U* (*t* ≥ 2);  *s*_{9} = 0;  *x*, *s* ≥ 0")
para(f"Here δ = 1 − (1 − λ_{{120}})^{{1/4}} converts ICAR’s 120-day trial loss λ_{{120}} to a monthly rate (Table 1). "
     f"The LP is solved in PuLP (CBC), cross-checked in SciPy/HiGHS (objective gap ≤ Rs "
     f"{P24['C']['objective_abs_diff_rs']:.2f}) and Excel Solver; shadow prices are reported only after ±1 t "
     f"re-solves verify them.", after=1.5)
data_table([
    ["Scenario", "Monthly loss δ", "Storage cost *h*", "Capital cost", "Source"],
    ["A  No storage", "– (*C* = 0: sell all in April)", "–", "–", "current practice"],
    ["B  Ventilated kanda chawl", f"{SCN['B']['delta']*100:.2f}% (54.89% in 120 days)", f"Rs {SCN['B']['h']:,.0f}/t/month",
     f"Rs {n0(I4['capex_B_rs_per_t_capacity'])}/t", "[4], [6], [7]"],
    ["C  Cold / IoT-monitored", f"{SCN['C']['delta']*100:.2f}% (7.14% in 120 days)", f"Rs {SCN['C']['h']:,.0f}/t/month (operating)",
     f"Rs {n0(I4['base_case']['capex_C_rs_per_t'])}/t", "[4], [5], [15]"],
], [Inches(1.6), Inches(1.95), Inches(1.55), Inches(0.85), Inches(1.15)], size=9)
caption(f"Table 1.|  Storage scenarios. All share *Q* = {LPp['Q']:,.0f} t, *C* = {LPp['C']:,.0f} t, *L* = {LPp['L']:,.0f} t, "
        f"*U* = {LPp['U']:,.0f} t/month; capital is costed apart from *h*.", after=2)
para(f"**Backtest and evaluation.** For each season 2017–24 we forecast with data to March only, solve the LP, then "
     f"*implement the plan at actual prices*: net = Σ*p*_{{t}}*x*_{{t}} − *h*Σ*s*_{{t}}, gain = (net − *Q*·"
     f"*p*_{{April}}) / *Q* per tonne harvested. Benchmarks: rolling monthly re-planning, an ex-ante calendar rule (sell in "
     f"the top-3 seasonal-index months known at the origin – Sep, Oct, Nov every year) and perfect foresight (the ceiling). "
     f"One-sided paired *t* and Wilcoxon tests over 8 seasons; 2023–24 are the clean test seasons (2019–22 also "
     f"informed model choice). Sensitivity: one parameter at a time plus a δ × *h* grid. **Industry 4.0 value:** "
     f"C’s gain over B per tonne of capacity against the extra capital, as payback and annuity (recovery factor "
     f"{crf}, 10 yr at 10%).")
para(f"**Extension.** *H4:* OLS of ln(mean Oct–Dec ÷ April price) on Sep+Oct rain (a crop-calendar window, not "
     f"searched), one season per observation "
     f"(*n* = {H4['n_seasons']}, {H4['years'].replace('-', '–')}; NHRDF before 2014), HC1-robust *p*, leave-one-out and "
     f"subperiod refits, and a Jun–Sep monsoon placebo. *Value of information:* the store’s true δ varies on a grid; a "
     f"*blind* operator plans with the book δ, a *sensor* one measures δ from May and re-plans monthly, a *calibrated* one "
     f"knows δ before April – each run with our forecast and with perfect prices (the pure value of loss information). "
     f"A 1 Nov re-plan on the rain signal (β from earlier seasons only) values a real-time rain feed.")

# =========================================================================================================
# 7 RESULTS
# =========================================================================================================
heading("7", "Results")
H2B = SS["B|calendar_rule_exante"]
H3 = TR["H3_C_vs_B"]
_drop = H4['leave_one_out']['seasons_whose_removal_lifts_p_above_0_05']
data_table([
    ["Hypothesis", "Test", "Result", "Verdict"],
    ["H1  arrivals ↓ price", f"log–log OLS + month, year dummies; HAC; *n* = {m3['n']}",
     f"β = {mn(m3['elasticity'], '{:.3f}')}, OLS CI [{mn(m3['ci95_low'])}, {mn(m3['ci95_high'])}]; HAC one-sided *p* = "
     f"{h1['headline']['one_sided_p_hac']:.3f}; ≈ 0 with lagged price", "**Supported** (association)"],
    ["H2  chawl storage pays", f"LP in chawl (δ = {SCN['B']['delta']*100:.2f}%) vs harvest sale; 8 seasons",
     f"stores 0 t in 8/8 seasons (gain Rs 0); Sep–Nov rule in a chawl: Rs {n0(H2B['mean'])}/t, {H2B['losses']}/8 lost",
     f"**Not supported** (holds only if δ < {SEN['breakeven_delta_B']*100:.1f}%)"],
    ["H3  low-loss storage pays", "LP, C vs B, paired over 8 seasons",
     f"+Rs {n0(H3['mean_diff_rs_per_t'])}/t (median {n0(H3['median_diff_rs_per_t'])}), {H3['wins']}/8 wins; *t*-test *p* = "
     f"{H3['paired_t_one_sided_p']:.3f}, Wilcoxon *p* = {H3['wilcoxon_one_sided_p']:.3f}; 2023–24 +Rs {n0(S23['C|forecast_plan'])}/t",
     "**Strongly supported**"],
    ["H4  late rain ↑ rise (extension)", f"OLS on Sep+Oct rain, *n* = {H4['n_seasons']} seasons; LOO, placebo",
     f"≈+{(H4['rise_multiplier_per_100mm']-1)*100:.0f}% per 100 mm, *p* = {H4['p_ols']:.3f} (HC1 {H4['p_robust_HC1']:.4f}), "
     f"*R*^{{2}} {H4['r2']:.2f}; dropping {', '.join(map(str, _drop[:-1]))} or {_drop[-1]} → *p* > 0.05; placebo *p* = "
     f"{H4['placebo_jun_sep_monsoon']['p']:.2f}", "**Weakly supported** (suggestive)"],
], [Inches(1.25), Inches(1.5), Inches(3.27), Inches(1.25)], size=9)
caption("Table 2.|  Hypothesis tests. The chawl plan never stores, so B equals harvest sale and C vs B equals C vs A.")
para(f"**H1.** β = {mn(m3['elasticity'], '{:.3f}')} (HAC s.e. "
     f"{m3['se_hac']:.3f}, one-sided *p* = {h1['headline']['one_sided_p_hac']:.3f}; adj. *R*^{{2}} {m3['adj_r2']}): months "
     f"with 10% heavier arrivals have prices about {abs(m3['elasticity'])*10:.1f}% lower, as in [10, 11]. It is an association: "
     f"β weakens under other normalisations ({mn(rn['per_market_reporting']['elasticity'])}, "
     f"{mn(rn['total_arrivals']['elasticity'])}; *p* = {rn['per_market_reporting']['p_hac']:.2f}–{rn['total_arrivals']['p_hac']:.2f}), "
     f"vanishes once last month’s price enters ({mn(m5['elasticity'], '{:.3f}')}, *p* = {m5['p_hac']:.2f}), and last "
     f"month’s price predicts arrivals (*p* = {rev['p_hac']:.3f}) – supply and price are jointly determined. "
     f"**Forecast.** Test MAPE {fd['MAPE']}%, bias {mn(fd['bias_pct'], '{:.1f}')}%, direction right in "
     f"{fd['direction_hit_pct']:.1f}% of month-to-month moves: the level is off, the shape is right – and shape is what the "
     f"LP needs. Flat forecasts (naive, 12-month average) earn Rs 0 because they never show a reason to store; shape-aware "
     f"models earn Rs {n0(min(shape_vals))}–{n0(max(shape_vals))}/t. **2024 plan (C).** Sell {xC[0]:.0f} t in April "
     f"(capacity binds), then {xC[5]:.1f} t in September and {xC[6]:.0f} t each in October and November (handling cap "
     f"binds); {P24['C']['lost_total']:.1f} t is lost to shrinkage. Verified marginal values: storage +Rs "
     f"{n0(mv['capacity_C']['gain_if_plus_1t'])}/t, handling +Rs {n0(mv['handling_cap_U']['gain_if_plus_1t'])} per t/month "
     f"(Oct {n0(hand[5])} + Nov {n0(hand[6])}); the loan sale *L* is slack. Planned net Rs {n0(pvr24[1])}/t realised "
     f"Rs {n0(pvr24[2])}/t at actual prices, as the forecast was low.")

# side-by-side: backtest table + Industry 4.0 economics
outer = doc.add_table(rows=2, cols=2)
no_borders(outer)
cell_margins(outer, 0, 0, 0, 0)
set_col_widths(outer, [Inches(4.15), Inches(2.95)])
lc, rc = outer.cell(0, 0), outer.cell(0, 1)
lc.paragraphs[0].paragraph_format.space_after = Pt(0)
rc.paragraphs[0].paragraph_format.space_after = Pt(0)


def g(k):
    v = SS[k]
    return f"{n0(v['mean'])} ({v['wins']}/8)"


R_ = WD_ALIGN_PARAGRAPH.RIGHT
bt_rows = [["Strategy (Rs/t vs April sale)", "B chawl", "C cold/IoT", "C 2023–24"],
           ["LP on forecast (our plan)", g("B|forecast_plan"), g("C|forecast_plan"), n0(S23["C|forecast_plan"])],
           ["Rolling monthly re-plan", g("B|rolling_replan"), g("C|rolling_replan"), n0(S23["C|rolling_replan"])],
           ["Calendar rule Sep–Nov (ex-ante)", g("B|calendar_rule_exante"), g("C|calendar_rule_exante"), n0(S23["C|calendar_rule_exante"])],
           ["Perfect foresight (ceiling)", g("B|perfect_foresight"), g("C|perfect_foresight"), n0(S23["C|perfect_foresight"])]]
data_table(bt_rows, [Inches(1.78), Inches(0.75), Inches(0.85), Inches(0.72)], size=8.5, container=lc,
           aligns=[WD_ALIGN_PARAGRAPH.LEFT, R_, R_, R_])
cp = outer.cell(1, 0).paragraphs[0]; cp.paragraph_format.space_before = Pt(1.5); cp.paragraph_format.space_after = Pt(1.5)
run(cp, "Table 3.", 8.5, bold=True, color=PLUM)
rich(cp, "  Backtest: mean gain 2017–24 (wins of 8); last column 2023–24.", 8.5, MUTED)
ec_rows = [["Capex of C, Rs/t capacity", "Payback", "Net/yr, Rs/t"]]
for e, s_ in zip(c_ex, ["MIDH norm", "ICAR, base", "cold room"]):
    ec_rows.append([f"{n0(e['capex_C_rs_per_t'])} ({s_})", f"{e['simple_payback_seasons']:.2f} seas.",
                    n0(e['net_annual_benefit_rs_per_t_capacity'])])
data_table(ec_rows, [Inches(1.45), Inches(0.68), Inches(0.8)], size=8.5, container=rc,
           aligns=[WD_ALIGN_PARAGRAPH.LEFT, R_, R_])
cp = outer.cell(1, 1).paragraphs[0]; cp.paragraph_format.space_before = Pt(1.5); cp.paragraph_format.space_after = Pt(1.5)
run(cp, "Table 4.", 8.5, bold=True, color=PLUM)
rich(cp, "  Economics of C over B (10 yr, 10%).", 8.5, MUTED)

para(f"**Industry 4.0 value.** Low-loss storage adds Rs {n0(I4['uplift_C_over_B_rs_per_t_harvest'])}/t harvested "
     f"(Rs {I4['uplift_C_over_B_rs_per_kg']:.2f}/kg), Rs {n0(uplift_cap)} per t of capacity per season. Against Rs "
     f"{n0(I4['base_case']['extra_capex_rs_per_t_capacity'])}/t of extra capital it pays back in "
     f"**{I4['base_case']['simple_payback_seasons']:.2f} seasons** and nets Rs "
     f"{n0(I4['base_case']['net_annual_benefit_rs_per_t_capacity'])} per t of capacity a year after capital charges: "
     f"**≈Rs {I4['fpo_annual_uplift_rs_lakh']:.1f} lakh a year gross** for a 1,000 t FPO, ≈Rs {fpo_net_lakh:.1f} lakh net; "
     f"it stays worthwhile up to ≈Rs {n0(round(breakeven_capex, -2))}/t of capital. "
     f"**Sensitivity (Fig. 2b).** A chawl pays only below {SEN['breakeven_delta_B']*100:.1f}%/month loss "
     f"(Rs {n0(SEN['delta_B']['0.06'])}/t at 6%). Cold storage stays positive at δ = 8% (Rs {n0(dC['0.080'])}/t), at "
     f"*h* = Rs 1,400 (Rs {n0(SEN['h_C']['1400'])}/t) and with no handling cap (Rs {n0(SEN['U_C']['1000'])}/t); each "
     f"point of monthly loss removed is worth ≈Rs {n0(per_pp)}/t (mean slope, 0.5–8%). **Honest reading.** In cold storage the Sep–Nov "
     f"rule averaged more (Rs {n0(SS['C|calendar_rule_exante']['mean'])} vs {n0(SS['C|forecast_plan']['mean'])}/t): the "
     f"value comes mainly from the seasonal shape. The LP adapts to storage physics (the rule loses money in a "
     f"chawl), won the test seasons (Rs {n0(S23['C|forecast_plan'])} vs {n0(S23['C|calendar_rule_exante'])}/t) "
     f"and gives verified shadow prices.")
para(f"**Extension: weather and sensors.** Wettest-third seasons rose a median "
     f"{H4['wet_third']['median_rise_pct']:.0f}%, driest {H4['dry_third']['median_rise_pct']:.0f}% (same sign, "
     f"but significant in neither subperiod). A real-time rain feed is worth "
     f"**Rs {n0(rain_feed_C)}/t**: by November C holds at most *U* = {LPp['U']:,.0f} t, which the cap sells then "
     f"either way (B holds none) – handling capacity, not information, binds. *Loss sensing:* at the book "
     f"{SCN['B']['delta']*100:.0f}% the chawl plan sells all in April, so sensing never starts; a chawl *measured* at "
     f"8% earns **Rs {n0(vB_fc[0.08]['calibrated'])}/t** with our forecast, but above the "
     f"{SEN['breakeven_delta_B']*100:.1f}% break-even storing loses (14%: Rs {n0(vB_fc[0.14]['calibrated'])}/t). In cold "
     f"storage our low-biased forecast ({mn(fd['bias_pct'], '{:.1f}')}%) leaves sensing mixed; with accurate prices it "
     f"never hurts: **Rs {n0(min(voiC_hi))}–{n0(max(voiC_hi))}/t** if the store slips to 8–15%/month.")
figure(F2, "Figure 2.|  (a) Cold/IoT storage beats April sale in 7 of 8 seasons (2018: "
           f"Rs {n0(H3['min_diff_rs_per_t'])}/t); the chawl LP stores nothing. (b) Mean gain vs loss δ.")
para(f"**Limitations.** The composite runs ≈10% below Lasalgaon, whose gains would be higher (Nasik prices: "
     f"Rs {n0(nas[2023])} and {n0(nas[2024])}/t in 2023–24); H1 is an "
     f"association and H4 only suggestive; forecasts run low ({mn(fd['bias_pct'], '{:.0f}')}%; MAPE {fd['MAPE']}%); "
     f"loss rates extrapolate 120-day trials (ICAR’s multi-module store, C’s capex basis, loses "
     f"≈{mm_delta*100:.1f}%/month; at 3% C still gains Rs {n0(dC['0.030'])}/t); grading, price impact, credit and "
     f"export shocks are unmodelled; 8 seasons (2 test) make tests indicative.")

# =========================================================================================================
# 8 MANAGERIAL IMPLICATIONS
# =========================================================================================================
heading("8", "Managerial Implications")
bullet("FPOs.", f"At ICAR’s {SCN['B']['delta']*100:.0f}%/month chawl loss, sell at harvest; storage pays only if curing "
       f"and ventilation cut loss below ≈{SEN['breakeven_delta_B']*100:.0f}% – so **measure your store’s real loss "
       f"rate before the season** (measured at 8%, a chawl earns Rs {n0(vB_fc[0.08]['calibrated'])}/t). In low-loss storage, sell the excess over capacity in April, release in Sep–Nov, re-plan "
       f"monthly, and add Oct–Nov handling capacity before space (shadow prices "
       f"+Rs {n0(mv['handling_cap_U']['gain_if_plus_1t'])} vs +Rs {n0(mv['capacity_C']['gain_if_plus_1t'])}/t): logistics, "
       f"not information, binds.")
bullet("Govt buffer agencies (NAFED / NCCF).", f"Buying at the April trough is right, but traditional storage destroys "
       f"value – the 2019 buffer loss is consistent with chawl physics. Hold buffers in cold or monitored storage and release "
       f"them in Sep–Nov, when the index is "
       f"{SIDX.loc['Sep','price_index_mean']:.2f}–{nov:.2f}× the year’s mean.")
bullet("Storage investors and policy.", f"Low-loss storage repays in ≈{I4['base_case']['simple_payback_seasons']:.1f} "
       f"seasons at Rs {n0(I4['base_case']['capex_C_rs_per_t'])}/t and within one season at the MIDH Rs 8,000/t norm, but "
       f"loses money after capital charges at Rs 50,000/t. Tie subsidies to loss measured by temperature, humidity and gas "
       f"sensors (≈Rs {n0(per_pp)}/t per point of loss); sensors pay only with an unbiased forecast.")

# =========================================================================================================
# 9 REFERENCES
# =========================================================================================================
heading("9", "References (including the data source)")
REFS = [
    "**[Data]** Shelar R., Hajare A., Mangarule S. (2025). Spatio-temporal dataset for agricultural price forecasting "
    "2014–24 (Agmarknet). Mendeley Data V1, doi:10.17632/ds9jmxp9zy.1.",
    "**[Data]** NHRDF. Lasalgaon onion prices and arrivals, 1996–2019. Mendeley Data, doi:10.17632/9dn4g8m97m.1.",
    "**[Data]** MSAMB SMART weekly market reports, 2023–24. msamb.com/smart.",
    "ICAR. Onion cold storage – potential to stabilize price fluctuation. icar.org.in/en/node/4701.",
    "ICAR. Multi-module onion storage system. icar.org.in/hi/node/27226.",
    "MIDH Implementation Guidelines 2023–24 (storage cost norms).",
    "Khapte P.S. et al. (2023). Innovative onion storage structure. *Indian Horticulture*.",
    "DGFT Notif. 21/2015-20, 31/2015-20, 49/2023; Customs Notif. 48/2023.",
    "Thombare et al. (2026). Price behaviour and volatility in major onion markets of India. *Indian J. Agric. Res.*",
    "Roy et al. (2024). Vegetables inflation in India: tomato, onion and potato (TOP). RBI Working Paper.",
    "Kaur et al. (2020). Onion arrivals and price behaviour, Punjab. *Indian J. Agric. Mktg.*",
    "Ghosh et al. (2020). Onion price volatility, ARIMAX-GARCH. *Indian J. Agric. Sci.*",
    "Lai J.-Y., Myers R.J., Hanson S.D. (2003). Optimal on-farm grain storage by risk-averse farmers. *J. Agric. Appl. Econ.*",
    "Ahumada O., Villalobos J.R. (2009). Planning models in the agri-food supply chain: a review. *EJOR* 196(1):1–20.",
    "Mohammed et al. (2022). Ambient parameter monitoring in fresh fruit and vegetable supply chains using IoT. *Foods* 11(12):1777.",
    "Outlook Business (15 May 2026); Down To Earth (25 Nov 2022); ThePrint (20 Nov 2019); Krishi Jagran (26 Mar 2024).",
    "**[Data]** NASA Langley Research Center, POWER Project. Monthly point data (T2M, RH2M, PRECTOTCORR), "
    "https://power.larc.nasa.gov, accessed 10 Nov 2026.",
]
p = para(after=0, align=WD_ALIGN_PARAGRAPH.LEFT)
for k, ref in enumerate(REFS):
    run(p, f"[{k+1}] ", 8, bold=True, color=PLUM)
    rich(p, ref + (" " if k < len(REFS) - 1 else ""), 8)

DOCX = REP / "KandaCode_Final_Report.docx"
PDF = REP / "KandaCode_Final_Report.pdf"
doc.save(DOCX)
print("saved", DOCX)

if "--no-pdf" not in sys.argv:
    from docx2pdf import convert
    convert(str(DOCX), str(PDF))
    print("saved", PDF)
