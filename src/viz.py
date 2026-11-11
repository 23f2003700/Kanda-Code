"""Kanda Code figure set — one visual language across report, deck, viva guide and showcase."""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kandacode as kc  # noqa: E402

# ---- brand -----------------------------------------------------------------
INK = "#1F1A1C"
PLUM = "#6B1E4A"      # red-onion aubergine — Scenario C / primary
COPPER = "#C2683C"    # onion-skin copper — Scenario B
SLATE = "#8E8489"     # Scenario A / neutral
BLUSH = "#E9A9A1"
SCALLION = "#4F7A34"
GOLD = "#D9A441"
PAPER = "#FFFFFF"
GRID = "#ECE6E1"
SC = {"A": SLATE, "B": COPPER, "C": PLUM}

plt.rcParams.update({
    "font.family": "Segoe UI", "font.size": 9, "axes.titlesize": 10.5, "axes.titleweight": "bold",
    "axes.labelsize": 9, "axes.edgecolor": "#BDB3AE", "axes.linewidth": 0.8, "axes.spines.top": False,
    "axes.spines.right": False, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8, "axes.axisbelow": True,
    "xtick.color": "#5E5458", "ytick.color": "#5E5458", "axes.labelcolor": "#3E3539", "legend.frameon": False,
    "legend.fontsize": 8, "figure.facecolor": PAPER, "axes.facecolor": PAPER, "savefig.dpi": 220,
    "savefig.bbox": "tight", "axes.titlelocation": "left", "axes.titlepad": 8,
})

R = json.loads((kc.OUT / "results.json").read_text(encoding="utf-8"))
monthly = pd.read_csv(kc.PROC / "maharashtra_onion_monthly.csv")
monthly["ym"] = pd.PeriodIndex(monthly["ym"], freq="M")
monthly = monthly.set_index("ym")
nh = pd.read_csv(kc.PROC / "lasalgaon_nhrdf_monthly.csv")
nh["ym"] = pd.PeriodIndex(nh["ym"], freq="M")
nh = nh.set_index("ym")
series = monthly["price_rs_qtl"]
ts = series.index.to_timestamp()

EVENTS = [("2019-09", "Export ban"), ("2020-09", "Export ban"), ("2023-08", "40% export duty"),
          ("2023-12", "Export ban"), ("2024-05", "Ban lifted")]


def save(fig, name):
    fig.savefig(kc.FIG / f"{name}.png")
    plt.close(fig)


def rs_kg(ax, axis="y"):
    f = mt.FuncFormatter(lambda v, _: f"₹{v:,.0f}")
    (ax.yaxis if axis == "y" else ax.xaxis).set_major_formatter(f)


# F1 — ten years of boom and bust ---------------------------------------------
def f1():
    fig, ax = plt.subplots(figsize=(7.2, 2.9))
    for y in range(2014, 2025):
        ax.axvspan(pd.Timestamp(f"{y}-04-01"), pd.Timestamp(f"{y}-05-31"), color=BLUSH, alpha=0.28, lw=0)
    ax.plot(ts, series / 100, color=PLUM, lw=1.8, label="Maharashtra benchmark (Agmarknet, 96 APMCs)")
    l = nh["lasalgaon_price_rs_qtl"].dropna()
    l = l[l.index >= pd.Period("2014-01", "M")]
    ax.plot(l.index.to_timestamp(), l / 100, color=COPPER, lw=1.1, ls="--", label="Lasalgaon APMC (NHRDF)")
    for d, lab in EVENTS:
        x = pd.Timestamp(d + "-01")
        ax.axvline(x, color=INK, lw=0.6, alpha=0.35)
        ax.text(x, 52, lab, rotation=90, va="top", ha="right", fontsize=6.5, color="#5E5458")
    ax.set_ylim(0, 54)
    rs_kg(ax)
    ax.set_ylabel("Wholesale price (₹/kg)")
    ax.set_title("Onion prices crash every April–May harvest and peak in Oct–Nov")
    ax.text(pd.Timestamp("2014-04-10"), 3.0, "harvest\nwindow", fontsize=6.5, color="#9B5B55")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=2)
    save(fig, "f1_price_history")


# F2 — seasonality ------------------------------------------------------------
def f2():
    prof = pd.DataFrame(R["eda"]["seasonal_profile"])
    fig, ax = plt.subplots(figsize=(3.6, 2.7))
    x = np.arange(12)
    ax.fill_between(x, prof["price_index_min"], prof["price_index_max"], color=BLUSH, alpha=0.35, lw=0, label="range 2014–24")
    ax.plot(x, prof["price_index_mean"], color=PLUM, lw=2, marker="o", ms=3.5, label="mean price index")
    ax.axhline(1, color=INK, lw=0.6, alpha=0.4)
    for i in (3, 4):
        ax.axvspan(i - 0.5, i + 0.5, color=BLUSH, alpha=0.18, lw=0)
    ax.set_xticks(x, [m[0] for m in kc.MONTHS])
    ax.set_ylabel("Price ÷ annual average")
    ax.set_title("Seasonal price index")
    ax.annotate(f"Apr: {prof['price_index_mean'][3]:.2f}×", (3, prof["price_index_mean"][3]), xytext=(4.6, 0.32), fontsize=7.5, color=PLUM,
                arrowprops=dict(arrowstyle="-", color=PLUM, lw=0.6))
    ax.annotate(f"Nov: {prof['price_index_mean'][10]:.2f}×", (10, prof["price_index_mean"][10]), xytext=(6.4, 2.25), fontsize=7.5, color=PLUM,
                arrowprops=dict(arrowstyle="-", color=PLUM, lw=0.6))
    ax.legend(loc="upper left", fontsize=7)
    save(fig, "f2_seasonality")


# F3 — price vs arrivals (H1) ---------------------------------------------------
def f3():
    m = monthly.dropna(subset=["price_rs_qtl"])
    lnA = np.log(m["arrivals_per_market_day_t"]); lnP = np.log(m["price_rs_qtl"])
    # partial out month & year effects (Frisch–Waugh) to show the H1 slope honestly
    D = pd.get_dummies(pd.DataFrame({"mon": m["month"].astype(str), "yr": m["year"].astype(str)}), drop_first=True).astype(float)
    X = np.column_stack([np.ones(len(m)), D.values])
    rA = lnA - X @ np.linalg.lstsq(X, lnA, rcond=None)[0]
    rP = lnP - X @ np.linalg.lstsq(X, lnP, rcond=None)[0]
    b = R["h1"]["M3_month_year_FE"]["elasticity"]
    fig, ax = plt.subplots(figsize=(3.6, 2.7))
    cmap = plt.get_cmap("twilight_shifted")
    sc = ax.scatter(rA, rP, c=m["month"], cmap=cmap, s=14, alpha=0.85, edgecolor="white", lw=0.3)
    xx = np.linspace(rA.min(), rA.max(), 10)
    ax.plot(xx, b * xx, color=INK, lw=1.6)
    ax.set_xlabel("Arrivals (log, month & year removed)")
    ax.set_ylabel("Price (log, month & year removed)")
    ax.set_title(f"H1: elasticity = {b:.2f}  (p = {R['h1']['M3_month_year_FE']['p_hac']:.3f})")
    cb = fig.colorbar(sc, ax=ax, pad=0.01, ticks=[1, 4, 7, 10])
    cb.ax.set_yticklabels(["Jan", "Apr", "Jul", "Oct"], fontsize=7); cb.outline.set_visible(False)
    save(fig, "f3_price_arrivals")


# F4 — forecast test ------------------------------------------------------------
def f4():
    fe = R["forecast"]
    best = fe["best_method"]
    alt = "seasonal_ses_long" if best != "seasonal_ses_long" else "holt_winters"
    show = [best, alt, "moving_average_12"]
    col = {best: PLUM, alt: SCALLION, "moving_average_12": SLATE}
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.6), sharey=True)
    for ax, yr in zip(axes, (2023, 2024)):
        idx = pd.period_range(f"{yr-1}-07", f"{yr}-12", freq="M")
        ax.plot(idx.to_timestamp(), series.reindex(idx) / 100, color=INK, lw=2, label="actual")
        fut = pd.period_range(f"{yr}-04", f"{yr}-12", freq="M").to_timestamp()
        for m in show:
            ax.plot(fut, np.array(fe["paths"][m][str(yr)]) / 100, color=col[m], lw=1.5,
                    ls="-" if m == best else "--", label=kc.FORECAST_LABELS[m].replace("Seasonal index x ", "Seasonal × "))
        ax.axvline(pd.Timestamp(f"{yr}-03-31"), color=INK, lw=0.7, ls=":")
        ax.text(pd.Timestamp(f"{yr}-03-20"), 37, "forecast\norigin", ha="right", fontsize=6.5, color="#5E5458")
        ax.set_title(f"{yr} season, forecast made end-March")
        ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%b"))
        rs_kg(ax)
    axes[0].set_ylabel("₹/kg")
    axes[0].set_ylim(4, 38)
    fig.legend(*axes[1].get_legend_handles_labels(), loc="upper center", bbox_to_anchor=(0.5, 0.02), ncol=4, fontsize=7)
    save(fig, "f4_forecast_test")


# F5 — the plan -----------------------------------------------------------------
def f5():
    p = R["plan_2024"]
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(7.2, 2.6), gridspec_kw={"width_ratios": [1.25, 1]})
    x = np.arange(9)
    w = 0.27
    for i, k in enumerate("ABC"):
        ax.bar(x + (i - 1) * w, p[k]["x"], w, color=SC[k], label=f"{k}: {kc.SCENARIOS[k]['name']}")
    ax.set_xticks(x, kc.SEASON)
    ax.set_ylabel("Tonnes sold")
    ax.set_title("Optimal monthly sales, 2024 (1,000 t)")
    ax.legend(fontsize=6.8, loc="upper center")
    ax2.plot(x, np.array(p["forecast_rs_t"]) / 1000, color=COPPER, lw=1.6, ls="--", marker="o", ms=3, label="forecast (end-Mar)")
    ax2.plot(x, np.array(p["actual_rs_t"]) / 1000, color=INK, lw=1.8, marker="o", ms=3, label="actual")
    ax2b = ax2.twinx()
    ax2b.fill_between(x, p["C"]["s"], color=PLUM, alpha=0.13, lw=0, step=None)
    ax2b.set_ylabel("Stock in C (t)", color=PLUM)
    ax2b.spines["right"].set_visible(True); ax2b.grid(False)
    ax2.set_xticks(x, kc.SEASON)
    ax2.set_ylabel("₹/kg")
    ax2.set_title("Price path and stock held")
    ax2.legend(fontsize=7, loc="upper left")
    ax2.set_zorder(ax2b.get_zorder() + 1); ax2.patch.set_visible(False)
    save(fig, "f5_lp_plan_2024")


# F6 — backtest -----------------------------------------------------------------
def f6():
    bt = pd.DataFrame(R["backtest_robust"])
    fp = bt[bt.strategy == "forecast_plan"].pivot(index="year", columns="scenario", values="gain_vs_harvest_per_t")
    pf = bt[bt.strategy == "perfect_foresight"].pivot(index="year", columns="scenario", values="gain_vs_harvest_per_t")
    yrs = fp.index.values
    x = np.arange(len(yrs))
    fig, ax = plt.subplots(figsize=(7.2, 2.6))
    ax.bar(x - 0.2, fp["B"] / 1000, 0.38, color=COPPER, label="B ventilated chawl — forecast plan")
    ax.bar(x + 0.2, fp["C"] / 1000, 0.38, color=PLUM, label="C cold / IoT storage — forecast plan")
    ax.scatter(x - 0.2, pf["B"] / 1000, marker="_", s=160, color=COPPER, lw=2, zorder=3)
    ax.scatter(x + 0.2, pf["C"] / 1000, marker="_", s=160, color=PLUM, lw=2, zorder=3, label="perfect-foresight ceiling (B copper, C plum)")
    cr = bt[bt.strategy == "calendar_rule_exante"].pivot(index="year", columns="scenario", values="gain_vs_harvest_per_t")
    ax.scatter(x + 0.2, cr["C"] / 1000, marker="D", s=16, facecolor="white", edgecolor=INK, lw=0.8, zorder=4, label="fixed Sep–Nov calendar rule (C)")
    ax.scatter(x - 0.2, cr["B"] / 1000, marker="D", s=16, facecolor="white", edgecolor=COPPER, lw=0.8, zorder=4)
    ax.axhline(0, color=INK, lw=0.8)
    for i, v in enumerate(fp["C"].values):
        ax.text(i + 0.2, v / 1000 + (0.4 if v >= 0 else -1.2), f"{v/1000:+.1f}", ha="center", fontsize=7, color=PLUM)
    ax.set_xticks(x, yrs)
    ax.set_ylabel("Gain vs selling all in April\n(₹ '000 per tonne)")
    t = R["tests_robust"]["H3_C_vs_B"]
    ax.set_title(f"Backtest on unseen prices: low-loss storage wins {t['wins']} of {t['n_seasons']} seasons (mean +₹{t['mean_diff_rs_per_t']:,.0f}/t)")
    ax.legend(fontsize=7, loc="upper left", ncol=1)
    ax.add_patch(matplotlib.patches.Rectangle((5.5, ax.get_ylim()[0]), 2, ax.get_ylim()[1] - ax.get_ylim()[0], color=GOLD, alpha=0.08, lw=0))
    ax.text(6.5, ax.get_ylim()[1] * 0.93, "test years", ha="center", fontsize=7, color="#8A6A1E")
    save(fig, "f6_backtest")


# F7 — sensitivity heat map -------------------------------------------------------
def f7():
    g = R["sensitivity_2017_2024"]["grid_delta_h"]
    ds = list(g.keys()); hs = list(g[ds[0]].keys())
    M = np.array([[g[d][h] for h in hs] for d in ds]) / 1000
    fig, ax = plt.subplots(figsize=(3.6, 2.7))
    from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm
    cm = LinearSegmentedColormap.from_list("kc", [COPPER, "#F6EFEA", PLUM])
    im = ax.imshow(M, cmap=cm, norm=TwoSlopeNorm(0, vmin=min(M.min(), -1), vmax=M.max()), aspect="auto")
    for i in range(len(ds)):
        for j in range(len(hs)):
            ax.text(j, i, f"{M[i,j]:+.1f}", ha="center", va="center", fontsize=7, color=INK if abs(M[i, j]) < 4 else "white")
    ax.set_xticks(range(len(hs)), [f"₹{int(h)}" for h in hs], fontsize=7)
    ax.set_yticks(range(len(ds)), [f"{float(d)*100:.0f}%" for d in ds], fontsize=7)
    ax.set_xlabel("Storage cost h (₹/t/month)")
    ax.set_ylabel("Monthly loss δ")
    ax.grid(False)
    be = R["sensitivity_2017_2024"]["breakeven_delta_B"]
    ax.set_title(f"Gain vs harvest sale (₹'000/t) · break-even δ ≈ {be*100:.1f}%/mo at ₹250", fontsize=7.5)
    save(fig, "f7_sensitivity")


# F8 — data validation ------------------------------------------------------------
def f8():
    v = R["validation_vs_lasalgaon"]
    j = monthly[["price_rs_qtl"]].join(nh, how="inner").dropna()
    fig, ax = plt.subplots(figsize=(3.6, 2.7))
    ax.scatter(j["lasalgaon_price_rs_qtl"] / 100, j["price_rs_qtl"] / 100, s=14, color=PLUM, alpha=0.8, edgecolor="white", lw=0.3)
    mx = max(j.max()[["price_rs_qtl", "lasalgaon_price_rs_qtl"]]) / 100 * 1.05
    ax.plot([0, mx], [0, mx], color=INK, lw=0.7, ls="--")
    ax.set_xlabel("Lasalgaon APMC, NHRDF (₹/kg)")
    ax.set_ylabel("Our Maharashtra series (₹/kg)")
    ax.set_title(f"Validation: r = {v['pearson_r_levels']:.3f}, n = {v['overlap_months']} months")
    save(fig, "f8_validation")


# F9 — forecast accuracy bars ---------------------------------------------------------
def f9():
    fv = R["forecast"]["validation_horizon"]
    fe = R["forecast"]["decision_horizon"]
    best = R["forecast"]["best_method"]
    order = sorted(fv, key=lambda k: fv[k]["MAPE"])
    fig, ax = plt.subplots(figsize=(3.6, 2.9))
    y = np.arange(len(order))
    ax.barh(y, [fv[k]["MAPE"] for k in order], color=[PLUM if k == best else "#CDBFC5" for k in order], height=0.62, label="validation 2019–22 (selects)")
    ax.scatter([fe[k]["MAPE"] for k in order], y, color=COPPER, s=16, zorder=3, label="test 2023–24")
    ax.set_yticks(y, [kc.FORECAST_LABELS[k].replace("Seasonal index x ", "Seasonal × ").replace(" (damped trend + seasonality)", "")
                      .replace("Regression: ", "Reg: ").replace("28-yr seasonal", "28-yr seas.") for k in order], fontsize=6.8)
    ax.invert_yaxis()
    ax.set_xlabel("MAPE, Apr–Dec from March origin (%)")
    ax.set_title("Forecast model selection")
    ax.legend(fontsize=7, loc="lower right")
    save(fig, "f9_forecast_accuracy")


# F10 — satellite rain vs post-harvest price rise (H4) ------------------------------
def f10():
    w = R["weather"]["h4_rain_price_link"]
    d = pd.DataFrame(w["table"])
    fig, ax = plt.subplots(figsize=(4.6, 2.9))
    old = d["year"] < 2014
    ax.scatter(d.loc[old, "rain_sep_oct_mm"], d.loc[old, "rise_pct"], s=22, color=SLATE, alpha=0.85, label="NHRDF Lasalgaon 1996–2013", zorder=3)
    ax.scatter(d.loc[~old, "rain_sep_oct_mm"], d.loc[~old, "rise_pct"], s=26, color=PLUM, label="Our composite 2014–24", zorder=3)
    xs = np.linspace(d["rain_sep_oct_mm"].min(), d["rain_sep_oct_mm"].max(), 50)
    a = np.mean(d["rise_log"]) - w["beta_per_mm"] * np.mean(d["rain_sep_oct_mm"])
    ax.plot(xs, (np.exp(a + w["beta_per_mm"] * xs) - 1) * 100, color=COPPER, lw=1.6, label="log-linear fit")
    for _, r in d[d["year"].isin([2018, 2019, 2020, 2005, 1998, 2023])].iterrows():
        ax.annotate(str(int(r["year"])), (r["rain_sep_oct_mm"], r["rise_pct"]), xytext=(4, 3), textcoords="offset points", fontsize=7, color=INK)
    ax.set_xlabel("Sep + Oct rain at Lasalgaon, NASA POWER (mm)")
    ax.set_ylabel("Oct–Dec price vs April (% rise)")
    ax.set_title(f"H4: +{(w['rise_multiplier_per_100mm'] - 1) * 100:.0f}% bigger rise per 100 mm of late rain (n = {w['n_seasons']}, p = {w['p_ols']:.3f})", fontsize=9)
    ax.legend(fontsize=7, loc="upper left")
    save(fig, "f10_rain_price")


# F11 — value of knowing the store's real loss rate -----------------------------------
def f11():
    va = R["value_of_loss_information"]["with_perfect_price_foresight"]
    vf = R["value_of_loss_information"]["with_forecast_prices"]
    fig, axs = plt.subplots(1, 2, figsize=(6.4, 2.7), sharey=False)
    for ax, k, title in [(axs[0], "B", "Ventilated chawl (book δ 18%)"), (axs[1], "C", "Cold / IoT store (book δ 1.8%)")]:
        gf = pd.DataFrame(vf[k]["grid"]); ga = pd.DataFrame(va[k]["grid"])
        x = gf["delta_true"] * 100
        ax.plot(x, gf["blind"] / 1000, color=SLATE, lw=1.5, marker="o", ms=3, label="blind (book δ)")
        ax.plot(x, gf["calibrated"] / 1000, color=COPPER if k == "B" else PLUM, lw=1.8, marker="o", ms=3, label="δ measured (our forecast)")
        ax.plot(x, ga["calibrated"] / 1000, color=COPPER if k == "B" else PLUM, lw=1.2, ls="--", label="δ measured + perfect prices (ceiling)")
        ax.axvline(vf[k]["book_delta"] * 100, color=INK, lw=0.6, alpha=0.5)
        ax.axhline(0, color=INK, lw=0.6, alpha=0.4)
        ax.set_title(title, fontsize=9)
        ax.set_xlabel("True monthly loss δ (%)")
    axs[0].set_ylabel("Gain vs harvest sale (₹'000/t)")
    axs[0].legend(fontsize=6.5, loc="upper right")
    fig.suptitle("What a measured loss rate is worth, 2017–24", x=0.01, ha="left", fontsize=10.5, fontweight="bold")
    fig.tight_layout()
    save(fig, "f11_value_of_information")


if __name__ == "__main__":
    for f in (f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11):
        f()
    print("figures:", sorted(p.name for p in kc.FIG.glob("*.png")))
