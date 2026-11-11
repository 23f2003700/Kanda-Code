"""Run the full Kanda Code pipeline end to end and write every output used by the report, deck and viva guide."""
import json
import sys
import time
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kandacode as kc  # noqa: E402

t0 = time.time()
for d in (kc.PROC, kc.FIG, kc.TAB):
    d.mkdir(parents=True, exist_ok=True)

R = {"meta": {"project": "Kanda Code - When should onion farmers sell their crop?",
              "units": "prices Rs/quintal in data, Rs/tonne in LP, Rs/kg in text"}}

# 1. DATA -------------------------------------------------------------------
raw = kc.load_raw()
mh, clog = kc.clean_maharashtra(raw)
daily = kc.build_daily(mh)
monthly = kc.build_monthly(mh)
nasik = kc.build_market_monthly(mh, "Nasik")
nh = kc.load_nhrdf()
kc.LONG_HISTORY = nh["lasalgaon_price_rs_qtl"].dropna()
kc.LONG_HISTORY = kc.LONG_HISTORY[kc.LONG_HISTORY.index < pd.Period("2014-01", "M")]

R["data_quality"] = clog
R["data_quality"]["monthly_missing"] = [str(p) for p in monthly.index[monthly["price_rs_qtl"].isna()]]
R["data_quality"]["daily_days"] = int(len(daily))
R["data_quality"]["median_markets_reporting_per_day"] = float(daily["markets_reporting"].median())
cov = monthly.groupby("year")["markets_reporting"].mean()
R["data_quality"]["mean_markets_reporting_per_month_2014"] = round(float(cov.loc[2014]), 1)
R["data_quality"]["mean_markets_reporting_per_month_2024"] = round(float(cov.loc[2024]), 1)
R["data_quality"]["nasik_missing_months"] = [str(p) for p in nasik.index[nasik["price_rs_qtl"].isna()]]
w = mh.groupby("district")["arrivals_tonnes"].sum()
R["data_quality"]["arrival_weight_by_district_pct_top6"] = (w / w.sum() * 100).sort_values(ascending=False).head(6).round(1).to_dict()
R["data_quality"]["markets_top10_by_arrivals"] = (mh.groupby("market")["arrivals_tonnes"].sum()
                                                  .sort_values(ascending=False).head(10).round(0).to_dict())
R["data_quality"]["nhrdf_history_months_used_for_seasonality"] = int(len(kc.LONG_HISTORY))
R["validation_vs_lasalgaon"] = kc.validate_against_lasalgaon(monthly, nasik, nh)
R["spotcheck_2020_2024"] = kc.spotcheck_2020_2024(monthly)

monthly.reset_index().assign(ym=lambda d: d["ym"].astype(str)).to_csv(kc.PROC / "maharashtra_onion_monthly.csv", index=False)
daily.reset_index().to_csv(kc.PROC / "maharashtra_onion_daily.csv", index=False)
nasik.reset_index(names="ym").assign(ym=lambda d: d["ym"].astype(str)).to_csv(kc.PROC / "nasik_apmc_monthly.csv", index=False)
nh.reset_index().assign(ym=lambda d: d["ym"].astype(str)).to_csv(kc.PROC / "lasalgaon_nhrdf_monthly.csv", index=False)

series = monthly["price_rs_qtl"].dropna()

# 2. EDA --------------------------------------------------------------------
R["eda"] = kc.eda_stats(monthly, daily)
prof = kc.seasonal_profile(monthly)
prof.round(4).to_csv(kc.TAB / "seasonal_profile.csv")
R["eda"]["seasonal_profile"] = prof.round(3).reset_index(names="month").to_dict(orient="records")
lsi = kc._seasonal_indices(kc.LONG_HISTORY)
R["eda"]["lasalgaon_seasonal_index_1996_2013"] = {kc.MONTHS[k - 1]: round(float(v), 3) for k, v in lsi.items()}

# 3. H1 ---------------------------------------------------------------------
R["h1"] = kc.h1_regressions(monthly, daily)
base = kc.LPParams()
R["price_taker"] = kc.price_taker_check(monthly, base.Q, base.U, R["h1"]["headline"]["elasticity"], nh)

# 4. Forecasting ------------------------------------------------------------
fe = kc.evaluate_forecasts(series)
R["forecast"] = fe
best = fe["best_method"]
R["forecast"]["best_label"] = kc.FORECAST_LABELS[best]
R["forecast"]["labels"] = kc.FORECAST_LABELS

# 5/6. LP + backtest ---------------------------------------------------------
R["lp_params_base"] = asdict(base)
R["scenarios"] = {k: {**v, "delta": v.get("delta", base.delta)} for k, v in kc.SCENARIOS.items()}
main_years = [2023, 2024]
robust_years = list(range(2017, 2025))
bt_rob = kc.backtest(series, robust_years, base, best)
bt_main = bt_rob[bt_rob["year"].isin(main_years)].reset_index(drop=True)
bt_main.to_csv(kc.TAB / "backtest_2023_2024.csv", index=False)
bt_rob.to_csv(kc.TAB / "backtest_2017_2024.csv", index=False)
R["backtest_main"] = bt_main.round(2).to_dict(orient="records")
R["backtest_robust"] = bt_rob.round(2).to_dict(orient="records")
R["tests_main"] = kc.paired_tests(bt_main)
R["tests_robust"] = kc.paired_tests(bt_rob)

g = bt_rob.groupby(["scenario", "strategy"])["gain_vs_harvest_per_t"]
R["strategy_summary_2017_2024"] = {f"{s}|{t}": {"mean": round(float(v.mean()), 0), "median": round(float(v.median()), 0),
                                                "min": round(float(v.min()), 0), "max": round(float(v.max()), 0),
                                                "wins": int((v > 0.5).sum()), "losses": int((v < -0.5).sum()), "n": int(len(v))}
                                   for (s, t), v in g}
R["strategy_summary_2023_2024"] = {f"{s}|{t}": round(float(v.mean()), 0)
                                   for (s, t), v in bt_main.groupby(["scenario", "strategy"])["gain_vs_harvest_per_t"]}
fp = bt_rob[bt_rob["strategy"] == "forecast_plan"]
R["planned_vs_realised"] = fp[["year", "scenario", "forecast_objective_per_t", "net_per_t", "oracle_net_per_t"]].round(0).to_dict(orient="records")
R["calendar_rule_months"] = bt_rob[bt_rob["strategy"] == "calendar_rule_exante"].drop_duplicates("year")[["year", "rule_months"]].to_dict(orient="records")

# robustness of the forecast choice: every method's realised plan value
by_method = {}
for meth in kc.FORECAST_METHODS:
    b = kc.backtest(series, robust_years, base, meth)
    f = b[b["strategy"] == "forecast_plan"].groupby("scenario")["gain_vs_harvest_per_t"].mean()
    by_method[meth] = {k: round(float(v), 0) for k, v in f.items()}
R["decision_value_by_forecast_method_2017_2024"] = by_method

# Nasik APMC robustness (same pipeline, single-market prices, complete from 2016)
nas_series = nasik["price_rs_qtl"].dropna()
nas_series = nas_series[nas_series.index >= pd.Period("2016-01", "M")]
R["data_quality"]["nasik_missing_months_from_2016"] = int(nasik.loc[pd.Period("2016-01", "M"):, "price_rs_qtl"].isna().sum())
bt_nas = kc.backtest(nas_series, main_years, base, best)
R["backtest_nasik_2023_2024"] = bt_nas[bt_nas["strategy"] == "forecast_plan"][["year", "scenario", "net_per_t", "gain_vs_harvest_per_t"]].round(0).to_dict(orient="records")

# decision-time LP (illustrative plan, forecast made at end of March 2024) incl. VERIFIED marginal values
tr = series[series.index <= pd.Period("2024-03", "M")]
fc24 = kc.forecast(tr, 9, best) * 10
R["plan_2024"] = {"forecast_rs_t": np.round(fc24, 0).tolist(), "actual_rs_t": np.round(kc.season_prices(series, 2024), 0).tolist()}
for k in "ABC":
    q = kc.scenario_params(base, k)
    sol = kc.solve_lp(fc24, q)
    if k == "A":
        for key in ("shadow_capacity_by_month", "shadow_capacity_total", "shadow_handling_by_month", "shadow_min_harvest_sale", "shadow_extra_tonne_harvest"):
            sol[key] = None
    sol["marginal_values"] = kc.marginal_values(fc24, q)
    R["plan_2024"][k] = sol

# 7. Sensitivity + Industry 4.0 value ---------------------------------------
R["sensitivity_2017_2024"] = kc.sensitivity(series, robust_years, base, best)
R["industry40"] = kc.industry40_value(bt_rob, base)
R["industry40_2023_2024_only"] = kc.industry40_value(bt_main, base)

# 8. Industry 4.0 extensions: NASA POWER satellite weather (H4) + value of loss-rate sensing -------------
wx = kc.load_power()
price_long = pd.concat([kc.LONG_HISTORY, series]).sort_index()
wx.reset_index().assign(ym=lambda d: d["ym"].astype(str)).to_csv(kc.PROC / "lasalgaon_nasa_power_monthly.csv", index=False)
w14 = wx[wx.index >= pd.Period("2014-01", "M")]
R["weather"] = {"source": "NASA POWER monthly point API, 20.15N 74.23E (Lasalgaon), 1996-2024; T2M, RH2M, PRECTOTCORR",
                "h4_rain_price_link": kc.weather_price_link(price_long, wx),
                "climatology_2014_2024": {kc.MONTHS[m - 1]: {"t2m_c": round(float(g["t2m_c"].mean()), 1),
                                                             "rh2m_pct": round(float(g["rh2m_pct"].mean()), 1),
                                                             "rain_mm": round(float(g["rain_mm"].mean()), 0)}
                                          for m, g in w14.groupby(w14.index.month)}}
R["weather"]["realtime_replan_nov_dec"] = kc.weather_replan_backtest(series, price_long, wx, robust_years, base, best)
R["value_of_loss_information"] = {
    "with_forecast_prices": kc.value_of_loss_information(series, robust_years, base, best),
    "with_perfect_price_foresight": kc.value_of_loss_information(series, robust_years, base, best, price_source="actual")}

R["meta"]["runtime_s"] = round(time.time() - t0, 1)
(kc.OUT / "results.json").write_text(json.dumps(kc.to_jsonable(R), indent=1), encoding="utf-8")
print("done in", R["meta"]["runtime_s"], "s")
