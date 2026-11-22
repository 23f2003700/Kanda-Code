"""All-India robustness check: does the Kanda Code method hold outside the Maharashtra benchmark?

The same cleaning rules, the same forecast model selected for the main analysis (regression: trend + month dummies)
and the same sell-or-store LP (scenarios A, B, C) are applied unchanged to every Agmarknet onion market in the
main dataset that reports a price in at least 95% of the 132 months from 2014 to 2024. Nothing is re-tuned per market.

Outputs (outputs/all_india/):
  market_monthly.csv   arrival-weighted monthly modal price per qualifying market
  markets.csv          one row per market: coverage, seasonal swing, forecast error, storage results
  backtest.csv         one row per market x season x scenario
  states.csv           state roll-up
  summary.json         headline numbers quoted in the report and deck

Run:  python src/all_india.py   (about 5 minutes; needs data/raw/onion_2014_2024.parquet)
"""
from pathlib import Path
import json
import sys

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kandacode as kc  # noqa: E402

OUT = kc.OUT / "all_india"
METHOD = "regression_trend_season"           # the model selected on validation in the main analysis
YEARS = list(range(2017, 2025))              # same 8 backtest seasons as the main analysis
TEST_YEARS = (2023, 2024)                    # same pre-registered test seasons
MIN_COVERAGE = 0.95                          # share of the 132 months with a reported price
MAX_GAP = 2                                  # training gaps of up to 2 months are interpolated (inside the training window only)
FULL = pd.period_range("2014-01", "2024-12", freq="M")


def clean_all(df: pd.DataFrame) -> pd.DataFrame:
    """The main analysis's cleaning rules, applied state by state (relative outliers use the same-day median
       across markets of the same state), then one row per market-day."""
    df = df[df["modal_price_rs_qtl"].between(kc.PRICE_MIN, kc.PRICE_MAX) & (df["arrivals_tonnes"] > 0)]
    df = df.drop_duplicates(subset=["date", "state", "market", "variety", "grade"], keep="first")
    med = df.groupby(["state", "date"])["modal_price_rs_qtl"].transform("median")
    df = df[(df["modal_price_rs_qtl"] >= 0.2 * med) & (df["modal_price_rs_qtl"] <= 5 * med)].copy()
    # Collapse variety rows. Repeated market totals are counted once with the mean variety price;
    # genuinely different rows are summed with an arrival-weighted price (same rule as kc.clean_maharashtra).
    df["pa"] = df["modal_price_rs_qtl"] * df["arrivals_tonnes"]
    g = df.groupby(["state", "district", "market", "date"])
    md = g.agg(n=("arrivals_tonnes", "size"), uniq=("arrivals_tonnes", "nunique"), a_first=("arrivals_tonnes", "first"),
               a_sum=("arrivals_tonnes", "sum"), p_mean=("modal_price_rs_qtl", "mean"), pa=("pa", "sum")).reset_index()
    repeated = md["uniq"].eq(1)
    md["arrivals_tonnes"] = np.where(repeated, md["a_first"], md["a_sum"])
    md["modal_price_rs_qtl"] = np.where(repeated, md["p_mean"], md["pa"] / md["a_sum"])
    return md[["state", "district", "market", "date", "arrivals_tonnes", "modal_price_rs_qtl"]]


def market_monthly(md: pd.DataFrame) -> pd.DataFrame:
    """Arrival-weighted monthly modal price per market (as kc.build_market_monthly)."""
    md = md.assign(ym=md["date"].dt.to_period("M"), pa=md["modal_price_rs_qtl"] * md["arrivals_tonnes"])
    m = md.groupby(["state", "district", "market", "ym"]).agg(pa=("pa", "sum"), arrivals_t=("arrivals_tonnes", "sum"),
                                                              trading_days=("date", "nunique")).reset_index()
    m["price_rs_qtl"] = m["pa"] / m["arrivals_t"]
    return m.drop(columns="pa")


def training_series(series: pd.Series, origin: pd.Period) -> pd.Series | None:
    """Prices up to the forecast origin. Gaps of up to MAX_GAP months between two reports are filled by log
       interpolation (both ends lie before the origin, so nothing after the origin is used); a missing origin
       month carries the last report. Returns None if a longer gap remains."""
    y = series[series.index <= origin]
    y = y.loc[y.first_valid_index():]
    miss = y.isna()
    run = (~miss).cumsum()
    gap_len = miss.groupby(run).transform("sum")
    inside = miss & run.gt(0) & run.lt(run.max())
    if (inside & gap_len.gt(MAX_GAP)).any():
        return None
    y = np.exp(np.log(y).interpolate(limit_area="inside"))
    y = y.ffill(limit=MAX_GAP)
    return None if y.isna().any() else y


def run_market(series: pd.Series, base: kc.LPParams) -> list[dict]:
    rows = []
    for yr in YEARS:
        origin = pd.Period(f"{yr}-03", "M")
        act = kc.season_prices(series, yr)
        tr = training_series(series, origin)
        if tr is None or np.isnan(act).any() or len(tr) < 36:
            continue
        fc = kc.forecast(tr, 9, METHOD) * 10.0
        mape = float(np.mean(np.abs(fc - act) / act) * 100)
        harvest_net = base.Q * act[0]
        for key in ["B", "C"]:
            q = kc.scenario_params(base, key)
            plan = kc.solve_lp(fc, q, return_duals=False)
            oracle = kc.solve_lp(act, q, return_duals=False)
            ev = kc.evaluate_plan(plan["x"], plan["s"], act, q.h)
            rows.append({"year": yr, "scenario": key, "mape_pct": mape,
                         "harvest_net_per_t": harvest_net / base.Q, "net_per_t": ev["net"] / base.Q,
                         "gain_vs_harvest_per_t": (ev["net"] - harvest_net) / base.Q,
                         "oracle_gain_per_t": (oracle["objective"] - harvest_net) / base.Q,
                         "stored": bool(plan["x"][0] < base.Q - 1e-6)})
    return rows


def stress_extra_costs(monthly: pd.DataFrame, mk: pd.DataFrame, base: kc.LPParams) -> dict:
    """Stress test with costs the main model leaves out: a 1% market fee, Rs 500/t selling cost on every tonne sold
       and a 1% price discount per month in store (quality loss). Prices are adjusted in both the forecast the LP
       plans on and the actual prices it is valued at; the LP itself is unchanged (scenario C)."""
    q = kc.scenario_params(base, "C")
    disc = 1 - 0.01 * np.arange(q.T)
    rows = []
    keys = mk[["state", "district", "market"]]
    for (state, district, market), g in monthly.merge(keys).groupby(["state", "district", "market"]):
        s = g.set_index("ym")["price_rs_qtl"].reindex(FULL)
        for yr in YEARS:
            tr, act = training_series(s, pd.Period(f"{yr}-03", "M")), kc.season_prices(s, yr)
            if tr is None or np.isnan(act).any() or len(tr) < 36:
                continue
            fc = kc.forecast(tr, 9, METHOD) * 10.0 * disc * 0.99 - 500.0
            aa = act * disc * 0.99 - 500.0
            plan = kc.solve_lp(fc, q, return_duals=False)
            ev = kc.evaluate_plan(plan["x"], plan["s"], aa, q.h)
            rows.append((state, market, yr, (ev["net"] - base.Q * aa[0]) / base.Q))
    r = pd.DataFrame(rows, columns=["state", "market", "year", "gain"])
    per_market, per_season = r.groupby(["state", "market"]).gain.mean(), r.groupby("year").gain.mean()
    return {"assumptions": "1% fee, Rs 500/t selling cost, 1%/month quality discount; cold storage (C)",
            "markets": int(len(per_market)), "C_beats_harvest_markets": int((per_market > 0).sum()),
            "C_gain_vs_harvest_mean": float(per_market.mean()), "C_gain_by_season": per_season.round(1).to_dict(),
            "C_gain_season_t_p": float(stats.ttest_1samp(per_season, 0).pvalue),
            "losing_markets": [f"{m} ({s})" for (s, m), v in per_market.items() if v <= 0]}


def seasonal_shape(series: pd.Series) -> dict:
    """Seasonal index (price / that year's mean), complete calendar years only."""
    s = series.dropna()
    df = pd.DataFrame({"p": s.values, "y": s.index.year, "m": s.index.month})
    full_years = df.groupby("y")["m"].nunique().loc[lambda c: c.eq(12)].index
    df = df[df.y.isin(full_years)]
    idx = (df.p / df.groupby("y").p.transform("mean")).groupby(df.m).mean()
    return {"april_index": float(idx[4]), "peak_month": int(idx.loc[5:12].idxmax()), "peak_index": float(idx.loc[5:12].max()),
            "trough_month": int(idx.idxmin()), "nov_over_apr": float(idx[11] / idx[4])}


def figure(mk: pd.DataFrame, st: pd.DataFrame, summary: dict):
    """f12: where cold storage beat harvest sale (map of market locations) and the state roll-up."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    PLUM, SLATE, RED, INK, GRID = "#6B1E4A", "#8E8489", "#B3261E", "#1F1A1C", "#ECE6E1"
    plt.rcParams.update({"font.family": "Segoe UI", "font.size": 9, "axes.titlesize": 10.5, "axes.titleweight": "bold",
                         "axes.spines.top": False, "axes.spines.right": False, "axes.edgecolor": "#BDB3AE",
                         "axes.grid": True, "grid.color": GRID, "axes.axisbelow": True, "axes.titlelocation": "left",
                         "savefig.dpi": 220, "savefig.bbox": "tight", "legend.frameon": False, "legend.fontsize": 8})
    fig, (a, b) = plt.subplots(1, 2, figsize=(11, 5.2), gridspec_kw={"width_ratios": [1, 1.25]})
    win = mk[mk.C_wins]
    lose = mk[~mk.C_wins]
    sizes = 12 + 0.004 * mk.C_gain_vs_harvest.clip(lower=0)
    a.scatter(win.lon, win.lat, s=sizes[win.index], c=PLUM, alpha=.7, lw=.4, edgecolor="white",
              label=f"Cold storage beat harvest sale ({len(win)})")
    a.scatter(lose.lon, lose.lat, s=40, marker="x", c=RED, lw=1.5, label=f"Did not ({len(lose)})")
    a.set_xlim(68, 92); a.set_ylim(7, 36); a.set_aspect("equal")
    a.set_xlabel("Longitude"); a.set_ylabel("Latitude")
    a.set_title(f"{summary['markets']} markets, {summary['states']} states")
    a.legend(loc="upper right")
    nolat = int(mk.lat.isna().sum())
    a.text(0.99, 0.01, "Points at district centroids (2 Uttarakhand markets overlap)"
           + (f"; {nolat} market without coordinates" if nolat else ""),
           transform=a.transAxes, ha="right", va="bottom", fontsize=6.5, color=SLATE)
    s = st.sort_values("C_gain_mean")
    colors = [PLUM if v > 0 else RED for v in s.C_gain_mean]
    b.barh(s.state + "  (" + s.markets.astype(str) + ")", s.C_gain_mean, color=colors)
    b.axvline(0, color=INK, lw=.8)
    b.set_xlabel("Mean gain of cold storage over selling all at harvest (Rs/t)")
    b.set_title("Same forecast + LP, unchanged, 2017-2024 backtest")
    for y, (v, w, n) in enumerate(zip(s.C_gain_mean, s.C_wins, s.markets)):
        b.text(v + 80, y, f"₹{v:,.0f}  ·  {w}/{n} win", va="center", fontsize=7.5, color=INK)
    b.set_xlim(min(0, s.C_gain_mean.min()) - 200, s.C_gain_mean.max() * 1.35)
    fig.suptitle("All-India check: the Kanda Code method outside Maharashtra", x=0.01, ha="left", fontsize=12,
                 fontweight="bold", color=INK)
    fig.savefig(kc.FIG / "f12_all_india.png")
    plt.close(fig)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    raw = kc.load_raw(["date", "state", "district", "market", "variety", "grade", "arrivals_tonnes", "modal_price_rs_qtl"])
    monthly = market_monthly(clean_all(raw))
    cover = monthly.groupby(["state", "district", "market"])["ym"].nunique() / len(FULL)
    keep = cover[cover >= MIN_COVERAGE].index
    monthly = monthly.set_index(["state", "district", "market"]).loc[keep].reset_index()
    monthly.assign(ym=monthly["ym"].astype(str)).to_csv(OUT / "market_monthly.csv", index=False, float_format="%.2f")

    base = kc.LPParams()
    bt_rows, mk_rows = [], []
    for (state, district, market), m in monthly.groupby(["state", "district", "market"]):
        series = m.set_index("ym")["price_rs_qtl"].reindex(FULL)
        rows = run_market(series, base)
        for r in rows:
            r.update(state=state, district=district, market=market)
        bt_rows += rows
        bt = pd.DataFrame(rows)
        rec = {"state": state, "district": district, "market": market, "coverage_pct": round(100 * cover[(state, district, market)], 1),
               "median_arrivals_t_month": float(m["arrivals_t"].median()), **seasonal_shape(series),
               "seasons_scored": int(bt.year.nunique()) if len(bt) else 0}
        if len(bt):
            c, b = bt[bt.scenario.eq("C")].set_index("year"), bt[bt.scenario.eq("B")].set_index("year")
            test = c[c.index.isin(TEST_YEARS)]
            rec.update(mape_all_pct=float(c.mape_pct.mean()), mape_test_pct=float(test.mape_pct.mean()) if len(test) else np.nan,
                       C_gain_vs_harvest=float(c.gain_vs_harvest_per_t.mean()), C_seasons_won=int((c.gain_vs_harvest_per_t > 0).sum()),
                       C_minus_B=float((c.net_per_t - b.net_per_t).mean()), C_beats_B_seasons=int((c.net_per_t > b.net_per_t + 1e-6).sum()),
                       B_gain_vs_harvest=float(b.gain_vs_harvest_per_t.mean()), B_ever_stores=bool(b.stored.any()),
                       C_oracle_gain=float(c.oracle_gain_per_t.mean()))
        mk_rows.append(rec)

    bt = pd.DataFrame(bt_rows)
    mk = pd.DataFrame(mk_rows)
    mk = mk[mk.seasons_scored >= 6].copy()                       # need most of the 8 seasons for a per-market verdict
    bt = bt.merge(mk[["state", "district", "market"]], on=["state", "district", "market"])
    coords = kc.load_raw(["state", "district", "market", "lat", "lon"]).drop_duplicates(["state", "district", "market"])
    mk = mk.merge(coords, on=["state", "district", "market"], how="left")
    mk["C_wins"] = mk.C_gain_vs_harvest > 0
    mk["harvest_low"] = mk.trough_month.isin([3, 4, 5])          # cheapest month falls in the March-May rabi arrivals
    mk = mk.sort_values(["state", "market"])
    bt.to_csv(OUT / "backtest.csv", index=False, float_format="%.2f")
    mk.to_csv(OUT / "markets.csv", index=False, float_format="%.3f")

    st = mk.groupby("state").agg(markets=("market", "size"), C_wins=("C_wins", "sum"),
                                 C_gain_mean=("C_gain_vs_harvest", "mean"), C_minus_B_mean=("C_minus_B", "mean"),
                                 nov_over_apr=("nov_over_apr", "median"), mape_test=("mape_test_pct", "median")).reset_index()
    st.sort_values("C_gain_mean", ascending=False).to_csv(OUT / "states.csv", index=False, float_format="%.1f")

    # Market-level tests: one value per market (its mean over seasons). Markets share the same seasons, so they are
    # not fully independent; the season-level test (one all-India mean per season, n = 8) is the conservative check.
    c_gain, c_minus_b = mk.C_gain_vs_harvest, mk.C_minus_B
    corr = stats.spearmanr(mk.nov_over_apr, mk.C_gain_vs_harvest)
    by_season = bt[bt.scenario.eq("C")].groupby("year").gain_vs_harvest_per_t.mean()
    cb = bt.pivot_table(index=["state", "district", "market", "year"], columns="scenario", values="net_per_t")
    cb_season = (cb["C"] - cb["B"]).groupby(level="year").mean()
    summary = {
        "method": METHOD, "seasons": YEARS, "coverage_rule": f">= {MIN_COVERAGE:.0%} of months 2014-2024 and >= 6 scored seasons",
        "markets": int(len(mk)), "states": int(mk.state.nunique()), "market_seasons": int(bt[bt.scenario.eq('C')].shape[0]),
        "C_beats_harvest_markets": int(mk.C_wins.sum()),
        "C_gain_vs_harvest_mean": float(c_gain.mean()), "C_gain_vs_harvest_median": float(c_gain.median()),
        "C_gain_wilcoxon_p": float(stats.wilcoxon(c_gain).pvalue), "C_gain_t_p": float(stats.ttest_1samp(c_gain, 0).pvalue),
        "C_beats_B_markets": int((c_minus_b > 0).sum()), "C_minus_B_mean": float(c_minus_b.mean()),
        "C_minus_B_wilcoxon_p": float(stats.wilcoxon(c_minus_b).pvalue),
        "B_markets_ever_storing": int(mk.B_ever_stores.sum()), "B_gain_vs_harvest_mean": float(mk.B_gain_vs_harvest.mean()),
        "C_gain_by_season": by_season.round(1).to_dict(), "C_gain_seasons_positive": int((by_season > 0).sum()),
        "C_gain_season_t_p": float(stats.ttest_1samp(by_season, 0).pvalue),
        "C_minus_B_by_season": cb_season.round(1).to_dict(), "C_minus_B_season_t_p": float(stats.ttest_1samp(cb_season, 0).pvalue),
        "C_market_season_win_rate": float((bt[bt.scenario.eq('C')].gain_vs_harvest_per_t > 0).mean()),
        "mape_test_median": float(mk.mape_test_pct.median()),
        "harvest_low_markets": int(mk.harvest_low.sum()),
        "C_win_rate_harvest_low": float(mk[mk.harvest_low].C_wins.mean()) if mk.harvest_low.any() else None,
        "C_win_rate_other": float(mk[~mk.harvest_low].C_wins.mean()) if (~mk.harvest_low).any() else None,
        "spearman_swing_vs_gain": {"rho": float(corr.statistic), "p": float(corr.pvalue)},
        "losing_markets": mk.loc[~mk.C_wins, ["state", "market", "C_gain_vs_harvest", "nov_over_apr", "trough_month"]]
                            .round(2).to_dict("records"),
        "stress_extra_costs": stress_extra_costs(monthly, mk, base),
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, default=float))
    figure(mk.reset_index(drop=True), st, summary)
    print(json.dumps({k: v for k, v in summary.items() if k != "losing_markets"}, indent=2, default=float))
    print(st.sort_values("C_gain_mean", ascending=False).round(1).to_string(index=False))


if __name__ == "__main__":
    main()
