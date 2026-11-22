"""Export the real project numbers for the viva presentation site (presentation/viva/).

Writes presentation/viva/data.js as `window.KC = {...}` so the site also opens straight from disk (file://),
then copies presentation/viva/ into presentation/web/ (the GitHub Pages folder) when that folder exists.
Every chart and headline number on the viva slides comes from this file; nothing is typed in by hand.

Run from the repository root:  python src/build_viva.py
GitHub Pages (CI has no raw parquet, so it reuses the committed data.js):  python src/build_viva.py --publish-only
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
VIVA = ROOT / "presentation" / "viva"
WEB = ROOT / "presentation" / "web"

TEAM = [
    {"name": "Raghuram Devarayi", "roll": "21f1005431", "part": "Problem & data"},
    {"name": "Parashmani Datta", "roll": "21f2000987", "part": "Price patterns & H1"},
    {"name": "Kathan Desai", "roll": "24f1002390", "part": "Forecast"},
    {"name": "Aaryan Choudhary", "roll": "23f2003700", "part": "Sell-or-store LP"},
    {"name": "Yash Arabhavi", "roll": "22f3001882", "part": "All-India & Industry 4.0"},
]


def r1(v, n=1):
    return None if v is None else round(float(v), n)


def main() -> None:
    import pandas as pd  # only needed to rebuild data.js; --publish-only runs without it

    R = json.loads((OUT / "results.json").read_text(encoding="utf-8"))
    eda, fc, plan = R["eda"], R["forecast"], R["plan_2024"]

    mon = pd.read_csv(ROOT / "data" / "processed" / "maharashtra_onion_monthly.csv")
    monthly = [{"ym": r.ym, "y": int(r.year), "m": int(r.month), "p": r1(r.price_rs_qtl / 100, 2),
                "a": r1(r.arrivals_t, 0)} for r in mon.itertuples()]

    # Actual Apr-Dec prices (Rs/qtl) for the forecast test seasons
    actual = {}
    for y in (2023, 2024):
        s = mon[(mon.year == y) & (mon.month >= 4)].sort_values("month")
        actual[str(y)] = [r1(v, 1) for v in s.price_rs_qtl]

    vh, dh = fc["validation_horizon"], fc["decision_horizon"]
    methods = [{"key": k, "label": fc["labels"][k], "val_mape": vh[k]["MAPE"], "test_mape": dh[k]["MAPE"],
                "test_dir": dh[k]["direction_hit_pct"]} for k in vh]

    bt = pd.read_csv(OUT / "tables" / "backtest_2017_2024.csv")
    fp = bt[bt.strategy == "forecast_plan"].pivot(index="year", columns="scenario", values="gain_vs_harvest_per_t")

    ai = json.loads((OUT / "all_india" / "summary.json").read_text(encoding="utf-8"))
    mk = pd.read_csv(OUT / "all_india" / "markets.csv")
    st = pd.read_csv(OUT / "all_india" / "states.csv")
    raw = pd.read_parquet(ROOT / "data" / "raw" / "onion_2014_2024.parquet", columns=["state", "district", "market", "lat", "lon"])
    cloud = raw.dropna(subset=["lat", "lon"]).drop_duplicates(["state", "district", "market"])

    las = pd.read_csv(ROOT / "data" / "processed" / "lasalgaon_nhrdf_monthly.csv")
    las = las[las.ym.isin(set(mon.ym))].dropna(subset=["lasalgaon_price_rs_qtl"])
    lasalgaon = [{"ym": r.ym, "p": r1(r.lasalgaon_price_rs_qtl / 100, 2)} for r in las.itertuples()]

    sens = R["sensitivity_2017_2024"]
    i40 = R["industry40"]
    h1 = R["h1"]

    KC = {
        "team": TEAM,
        "repo": "https://github.com/23f2003700/Kanda-Code",
        "data_doi": "https://doi.org/10.17632/ds9jmxp9zy.1",
        "dq": {k: R["data_quality"][k] for k in ("rows_all_india", "rows_maharashtra", "markets_maharashtra",
                                                   "lasalgaon_rows_in_main_dataset", "market_days_clean",
                                                   "tonnes_double_counted_if_rows_summed")},
        "validation": {"r": R["validation_vs_lasalgaon"]["pearson_r_levels"],
                       "months": R["validation_vs_lasalgaon"]["overlap_months"],
                       "nasik_r": R["validation_vs_lasalgaon"]["nasik_pearson_r"]},
        "monthly": monthly,
        "lasalgaon": lasalgaon,
        "season": [{"m": s["month"], "p": s["price_index_mean"], "a": s["arrivals_index_mean"]}
                   for s in eda["seasonal_profile"]],
        "eda": {"years_nov_above_apr": eda["years_nov_above_apr"], "years": eda["years"],
                "median_rise": eda["median_rise_apr_to_nov_pct"], "pmin": eda["price_min_rs_kg"],
                "pmin_m": eda["price_min_month"], "pmax": eda["price_max_rs_kg"], "pmax_m": eda["price_max_month"],
                "pmean": eda["price_mean_rs_kg"]},
        "h1": {"beta": h1["headline"]["elasticity"], "p": h1["headline"]["one_sided_p_hac"],
               "n": h1["M3_month_year_FE"]["n"], "beta_dyn": h1["M5_dynamic_with_lagged_price"]["elasticity"]},
        "forecast": {"methods": methods, "best": fc["best_method"],
                     "test": dh[fc["best_method"]], "paths": fc["paths"], "actual": actual},
        "lp": R["lp_params_base"],
        "pt": {"share_april_pct": R["price_taker"]["share_april_pct"],
               "impact_pct": R["price_taker"]["implied_price_impact_april_pct"]},
        "scen": {k: {"delta": v["delta"], "h": v["h"], "name": v["name"]} for k, v in R["scenarios"].items()},
        "plan": {"forecast": plan["forecast_rs_t"], "actual": plan["actual_rs_t"],
                 "C": {"x": [r1(v, 1) for v in plan["C"]["x"]], "s": [r1(v, 1) for v in plan["C"]["s"]],
                       "obj": plan["C"]["objective"], "lost": plan["C"]["lost_total"],
                       "shadow_cap": plan["C"]["marginal_values"]["capacity_C"]["gain_if_plus_1t"],
                       "shadow_U": plan["C"]["marginal_values"]["handling_cap_U"]["gain_if_plus_1t"],
                       "shadow_L": plan["C"]["marginal_values"]["loan_sale_L"]["gain_if_plus_1t"]},
                 "A_obj": plan["A"]["objective"], "B_obj": plan["B"]["objective"]},
        "backtest": {"years": [int(y) for y in fp.index], "B": [r1(v, 0) for v in fp["B"]],
                     "C": [r1(v, 0) for v in fp["C"]], "test": R["tests_robust"]["H3_C_vs_B"],
                     "calendar_B": R["strategy_summary_2017_2024"]["B|calendar_rule_exante"]["mean"],
                     "calendar_C": R["strategy_summary_2017_2024"]["C|calendar_rule_exante"]["mean"]},
        "i40": {"uplift": i40["uplift_C_over_B_rs_per_t_harvest"], "per_kg": i40["uplift_C_over_B_rs_per_kg"],
                "payback": i40["base_case"]["simple_payback_seasons"], "lakh": i40["fpo_annual_uplift_rs_lakh"],
                "capex_C": i40["base_case"]["capex_C_rs_per_t"], "capex_B": i40["capex_B_rs_per_t_capacity"],
                "net": i40["base_case"]["net_annual_benefit_rs_per_t_capacity"]},
        "sens": {"delta_C": sens["delta_C"], "delta_B": sens["delta_B"], "breakeven_B": sens["breakeven_delta_B"]},
        "ai": {"markets": ai["markets"], "states": ai["states"], "wins": ai["C_beats_harvest_markets"],
               "gain": ai["C_gain_vs_harvest_mean"], "by_season": ai["C_gain_by_season"],
               "seasons_pos": ai["C_gain_seasons_positive"], "p": ai["C_gain_season_t_p"],
               "B_storing": ai["B_markets_ever_storing"], "stress": ai["stress_extra_costs"],
               "mk": [{"s": r.state, "m": r.market, "lat": r1(r.lat, 3), "lon": r1(r.lon, 3),
                       "g": r1(r.C_gain_vs_harvest, 0), "w": bool(r.C_wins)}
                      for r in mk.dropna(subset=["lat", "lon"]).itertuples()],
               "states_tab": [{"s": r.state, "n": int(r.markets), "w": int(r.C_wins), "g": r1(r.C_gain_mean, 0)}
                              for r in st.itertuples()],
               "cloud": [[r1(a, 2), r1(b, 2)] for a, b in zip(cloud.lat, cloud.lon)]},
    }

    js = "/* Generated by src/build_viva.py from outputs/ - do not edit by hand. */\nwindow.KC = " + \
         json.dumps(KC, ensure_ascii=False, separators=(",", ":")) + ";\n"
    (VIVA / "data.js").write_text(js, encoding="utf-8")
    print(f"wrote presentation/viva/data.js ({len(js) / 1024:.0f} KB): {len(monthly)} months, "
          f"{len(KC['ai']['mk'])} scored markets, {len(KC['ai']['cloud'])} market points")

    # Cache-bust: stamp index.html's own files with a hash of their contents so a rebuilt deck is never stale
    own = ("deck.css", "data.js", "slides.js", "deck.js")
    ver = hashlib.sha256(b"".join((VIVA / f).read_bytes() for f in own)).hexdigest()[:10]
    idx = VIVA / "index.html"
    html = idx.read_text(encoding="utf-8")
    html2 = re.sub(r'(href|src)="(deck\.css|data\.js|slides\.js|deck\.js)(\?v=\w+)?"', rf'\1="\2?v={ver}"', html)
    if html2 != html:
        idx.write_text(html2, encoding="utf-8")


def publish() -> None:
    if WEB.exists():  # GitHub Pages build: viva deck at the site root, classic deck under /classic
        classic = WEB / "classic"
        if not classic.exists():
            tmp = WEB.parent / "_classic_tmp"
            shutil.rmtree(tmp, ignore_errors=True)
            shutil.move(str(WEB), str(tmp))
            WEB.mkdir()
            shutil.move(str(tmp), str(classic))
        for p in VIVA.iterdir():
            dst = WEB / p.name
            if p.is_dir():
                shutil.copytree(p, dst, dirs_exist_ok=True)
            else:
                shutil.copy2(p, dst)
        (WEB / ".nojekyll").write_text("", encoding="utf-8")
        print("copied viva deck into presentation/web/ (classic deck at /classic/)")


if __name__ == "__main__":
    if "--publish-only" not in sys.argv:
        main()
    publish()
