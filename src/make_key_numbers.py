"""Writes docs/KEY_NUMBERS.md — every headline number, pulled from outputs/results.json (single source of truth)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
R = json.loads((ROOT / "outputs" / "results.json").read_text(encoding="utf-8"))
dq, v, sp, e, h, f = R["data_quality"], R["validation_vs_lasalgaon"], R["spotcheck_2020_2024"], R["eda"], R["h1"], R["forecast"]
ss, sm, t, i4, se, p, pt = (R["strategy_summary_2017_2024"], R["strategy_summary_2023_2024"], R["tests_robust"],
                            R["industry40"], R["sensitivity_2017_2024"], R["plan_2024"], R["price_taker"])
best, L = f["best_method"], f["labels"]


def n0(x):
    return f"{x:,.0f}"


out = []
A = out.append
A("# KEY NUMBERS — single source of truth (auto-generated from outputs/results.json)\n")
A("Units: data prices are Rs/quintal (100 kg). The LP uses Rs/tonne. Text uses Rs/kg (= Rs/quintal ÷ 100 = Rs/tonne ÷ 1000).\n")
A("## Data")
A(f"- Main dataset: Mendeley, Shelar, Hajare & Mangarule (2025), DOI 10.17632/ds9jmxp9zy.1, CC BY 4.0. An Agmarknet compilation of {dq['rows_all_india']:,} all-India daily records, 2014-01-01 to 2024-12-31.")
A(f"- Lasalgaon APMC rows in the main dataset: **{dq['lasalgaon_rows_in_main_dataset']}**. We found this in the planned first-week data check.")
A(f"- Maharashtra: {dq['rows_maharashtra']:,} rows from {dq['markets_maharashtra']} markets.")
A(f"  - Dropped {dq['dropped_price_outside_band']} rows priced outside Rs 50–20,000/q.")
A(f"  - Dropped {dq['dropped_relative_price_outliers']} relative outliers (outside 0.2–5× the same-day median).")
A(f"- Repeated arrivals across variety rows: {dq['market_days_with_multiple_variety_rows']:,} market-days have several variety rows, and {dq['multi_row_market_days_with_repeated_arrivals_pct']}% of them repeat the same tonnage on each row.")
A(f"  - Summing those rows would double-count {n0(dq['tonnes_double_counted_if_rows_summed'])} t.")
A(f"  - So we collapse to one row per market-day: {dq['market_days_clean']:,} clean market-days.")
A(f"- Price series: Maharashtra arrival-weighted modal price, monthly, 132 months, none missing.")
A(f"  - Markets reporting rise from {dq['mean_markets_reporting_per_month_2014']}/month (2014) to {dq['mean_markets_reporting_per_month_2024']}/month (2024).")
A(f"  - Arrival weight by district (%): {dq['arrival_weight_by_district_pct_top6']}")
A(f"- Validation against NHRDF's official Lasalgaon monthly series (Mendeley 10.17632/9dn4g8m97m, 1996–Jun 2019), {v['overlap_months']} overlapping months ({v['overlap_start']} to {v['overlap_end']}):")
A(f"  - r = {v['pearson_r_levels']} on levels and {v['pearson_r_monthly_log_changes']} on monthly % changes.")
A(f"  - Mean level ratio {v['mean_ratio_mh_to_lasalgaon']}; mean absolute gap {v['mean_abs_pct_gap']}%; direction agreement {v['direction_agreement_pct']}%.")
A(f"  - Nasik APMC vs Lasalgaon: r = {v['nasik_pearson_r']}. Composite vs Nasik, 2023–24: r = {v['composite_vs_nasik_r_2023_2024']}.")
A(f"  - Season shape, April → best later month (composite vs Lasalgaon): {v['season_shape']}")
A(f"- Spot-check, 2020–24: {sp['points']} independently reported Lasalgaon prices (8 MSAMB weekly reports plus news). r = {sp['pearson_r']}; median absolute gap {sp['median_abs_gap_pct']}%.")
A(f"  - Our series is lower in {sp['share_ours_below_pct']:.0f}% of points (median {sp['median_signed_gap_pct']}%), because Lasalgaon is the premium market.")
A(f"  - A level gap scales rupee values but barely moves the timing decision.")
A(f"- Lasalgaon history 1996–2013 ({dq['nhrdf_history_months_used_for_seasonality']} months) is used ONLY to estimate seasonal indices for the two '28-yr' forecast candidates.")

A("\n## EDA")
A(f"- Price level: mean Rs {e['price_mean_rs_kg']}/kg; minimum Rs {e['price_min_rs_kg']}/kg ({e['price_min_month']}); maximum Rs {e['price_max_rs_kg']}/kg ({e['price_max_month']}).")
A(f"- Volatility: overall CV {e['overall_cv_pct']}%; mean within-year CV {e['mean_within_year_cv_pct']}%.")
A(f"  - Month-on-month change SD {e['mom_change_sd_pct']}%; annualised volatility from monthly log returns {e['annualised_vol_from_monthly_pct']}%.")
A(f"  - Within a year, the maximum price averages {e['mean_max_over_min_within_year']}× the minimum.")
sp_ = {r['month']: r['price_index_mean'] for r in e['seasonal_profile']}
A(f"- Seasonal index (price ÷ that year's mean, 2014–24): {sp_}. The trough is in April–May, the peak in November.")
A(f"- Lasalgaon 1996–2013 seasonal index (NHRDF): {e['lasalgaon_seasonal_index_1996_2013']}")
A(f"- The November price beat April in {e['years_nov_above_apr']} of {e['years']} years. Median April→November rise: {e['median_rise_apr_to_nov_pct']}%.")
A(f"  - Median hindsight April→best-month rise: {e['median_rise_apr_to_best_pct_hindsight']}%. Best month by count: {e['years_best_month']}.")

A("\n## H1 (OLS of log price on log arrivals per market-day)")
for k in ["M1_simple", "M2_month_FE", "M3_month_year_FE", "M4_lagged_arrivals", "M5_dynamic_with_lagged_price", "D1_daily_sign_check"]:
    m = h[k]
    extra = f", lagged-price coef {m['lagged_price_coef']}" if m.get("lagged_price_coef") else ""
    A(f"- {k}: beta = {m['elasticity']}, p(OLS) = {m['p_ols']:.4f}, p(HAC) = {m['p_hac']:.4f}, adj R² = {m['adj_r2']}, n = {m['n']}, DW = {m['durbin_watson']}{extra}")
A(f"- HEADLINE (M3, month + year dummies): beta = {h['headline']['elasticity']}, one-sided p(HAC) = {h['headline']['one_sided_p_hac']:.4f}, H1 supported = {h['headline']['H1_supported']}.")
A("  - Months with 10% heavier arrivals have prices about 4.4% lower. This is an association, not a causal elasticity.")
A(f"- Robustness to how arrivals are normalised: {h['robust_normalisation']}")
A(f"- Reverse-causality check: last month's price predicts this month's arrivals (coef {h['reverse_causality_lnA_on_lagged_price']['elasticity']}, p = {h['reverse_causality_lnA_on_lagged_price']['p_hac']:.3f}). Prices and arrivals are jointly determined.")
A(f"- Price-taker check (order of magnitude):")
A(f"  - Selling 1,000 t in April is {pt['share_april_pct']}% of Lasalgaon April arrivals ({n0(pt['lasalgaon_mean_april_arrivals_t'])} t); implied price impact ~{pt['implied_price_impact_april_pct']}%.")
A(f"  - Selling 300 t in Oct/Nov is {pt['share_oct_nov_pct']}% of arrivals; implied impact ~{pt['implied_price_impact_oct_nov_pct']}%.")

A("\n## Forecasting (origin = end-March; horizon Apr–Dec = 1–9 months; expanding window)")
A(f"- Selection rule: {f['selection_rule']}.")
A(f"- **Chosen model: {L[best]}**, i.e. OLS of log price = a + b·t + 11 month dummies.")
A("- Each candidate, best validation MAPE first:")
for m in sorted(f["validation_horizon"], key=lambda k: f["validation_horizon"][k]["MAPE"]):
    dv = R["decision_value_by_forecast_method_2017_2024"][m]["C"]
    A(f"  - {L[m]}: validation MAPE {f['validation_horizon'][m]['MAPE']}%; test MAPE {f['decision_horizon'][m]['MAPE']}% (bias {f['decision_horizon'][m]['bias_pct']}%, direction hits {f['decision_horizon'][m]['direction_hit_pct']}%); 1-step MAPE {f['one_step'][m]['MAPE']}%; scenario-C decision value 2017–24 Rs {n0(dv)}/t")
A(f"- Best on the test set, for reference only: {L[f['best_method_on_test_for_reference']]}. SES-type models fit alpha = 1.0: the latest month carries the whole level, close to a random walk.")

A("\n## LP (one FPO; base parameters)")
b, sc = R["lp_params_base"], R["scenarios"]
A(f"- Q = {b['Q']:.0f} t; C = {b['C']:.0f} t; L = {b['L']:.0f} t (April crop-loan sale).")
A(f"- U = {b['U']:.0f} t/month, the grading and trucking cap for May–Dec. The April harvest sale goes field-run to traders, so it has no cap.")
A(f"- Storage cost: h_B = Rs {sc['B']['h']:.0f}/t/month; h_C = Rs {sc['C']['h']:.0f}/t/month (operating cost of an owned facility).")
A(f"- Monthly loss: delta_B = {sc['B']['delta']*100:.2f}%/month (ICAR ventilated: 54.89% in 120 days); delta_C = {sc['C']['delta']*100:.2f}%/month (ICAR-DOGR cold store: 7.14% in 120 days). Conversion: delta = 1 − (1 − L120)^(1/4).")
A(f"- 2024 plan, forecast made end-March 2024:")
A(f"  - Forecast price, Rs/t: {p['forecast_rs_t']}")
A(f"  - Actual price, Rs/t: {p['actual_rs_t']}")
for k in "ABC":
    A(f"  - {k}: x = {[round(x, 1) for x in p[k]['x']]}; objective Rs {p[k]['objective']/1e5:.1f} lakh; lost to rot {p[k]['lost_total']:.1f} t; PuLP vs SciPy diff Rs {p[k].get('objective_abs_diff_rs')}")
mv = p["C"]["marginal_values"]
A(f"- Verified marginal values, scenario C 2024 (re-solve with ±1 t):")
A(f"  - Storage capacity: +1 t → +Rs {mv['capacity_C']['gain_if_plus_1t']:,.0f}.")
A(f"  - Handling cap U: +1 t/month → +Rs {mv['handling_cap_U']['gain_if_plus_1t']:,.0f}. It binds in Oct and Nov (SciPy duals May..Dec = {p['C']['shadow_handling_by_month']}).")
A(f"  - Extra harvested tonne: +Rs {mv['harvest_Q']['gain_if_plus_1t']:,.0f}.")
A(f"  - Loan sale L: {mv['loan_sale_L']['gain_if_plus_1t']} (slack).")

A("\n## Backtest (evaluated at ACTUAL prices; gain vs selling everything in April, Rs per tonne harvested)")
for k in ["C|forecast_plan", "C|rolling_replan", "C|calendar_rule_exante", "C|calendar_rule_hindsight_OctNov", "C|perfect_foresight",
          "B|forecast_plan", "B|calendar_rule_exante", "B|perfect_foresight"]:
    x = ss[k]
    A(f"- 2017–24 {k}: mean {n0(x['mean'])}, median {n0(x['median'])}, min {n0(x['min'])}, max {n0(x['max'])}, wins {x['wins']}/{x['n']}, losses {x['losses']}")
A(f"- 2023–24 (pre-registered test seasons), means: {sm}")
A(f"- Ex-ante calendar rule months (top-3 seasonal index at origin): {R['calendar_rule_months'][0]['rule_months']}, every year.")
A(f"- Paired tests (8 seasons): {json.dumps(t)}")
A(f"- Nasik APMC robustness, 2023–24: {R['backtest_nasik_2023_2024']}")
A(f"- Planned vs realised, scenario C (year, planned Rs/t, realised Rs/t): {[(r['year'], r['forecast_objective_per_t'], r['net_per_t']) for r in R['planned_vs_realised'] if r['scenario'] == 'C']}")

A("\n## Sensitivity (mean realised gain vs harvest sale, Rs/t, 2017–24)")
for k, vv in se.items():
    A(f"- {k}: {vv}")

A("\n## Industry 4.0 value (scenario C over scenario B)")
A(f"- Uplift: Rs {n0(i4['uplift_C_over_B_rs_per_t_harvest'])}/t harvested (Rs {i4['uplift_C_over_B_rs_per_kg']}/kg).")
A(f"  - Per tonne of storage capacity: Rs {n0(i4['uplift_C_over_B_rs_per_t_capacity_per_season'])} per season.")
A(f"  - By season: {i4['uplift_by_season']}.")
A("- Capital cost per tonne of capacity:")
A("  - B: Rs 7,000/t (MIDH: Rs 1.75 lakh per 25 t unit).")
A("  - C base: Rs 16,667/t (ICAR multi-module: Rs 1.5 lakh per 9 t). Range Rs 8,000 (MIDH cold storage type 1) to Rs 50,000 (small cold room).")
A(f"- Base case: payback {i4['base_case']['simple_payback_seasons']} seasons; net annual benefit Rs {n0(i4['base_case']['net_annual_benefit_rs_per_t_capacity'])}/t capacity (CRF {i4['capital_recovery_factor_10y_10pct']}, 10 years at 10%).")
A(f"- Range (capex, payback seasons, net annual benefit): {[(c['capex_C_rs_per_t'], c['simple_payback_seasons'], c['net_annual_benefit_rs_per_t_capacity']) for c in i4['capex_range']]}")
A(f"- For a 1,000 t FPO: ≈ Rs {i4['fpo_annual_uplift_rs_lakh']} lakh a year. The 2023–24 test seasons alone give Rs {R['industry40_2023_2024_only']['uplift_C_over_B_rs_per_t_harvest']:,.0f}/t.")
wl = R["weather"]["h4_rain_price_link"]; rr = R["weather"]["realtime_replan_nov_dec"]; cl = R["weather"]["climatology_2014_2024"]
vf, va = R["value_of_loss_information"]["with_forecast_prices"], R["value_of_loss_information"]["with_perfect_price_foresight"]


def at(vv, k, d, col):
    return [g for g in vv[k]["grid"] if abs(g["delta_true"] - d) < 1e-9][0][col]


A("\n## Satellite weather layer (NASA POWER) — H4")
A(f"- Source: {R['weather']['source']}. Free, no key; satellite-derived/reanalysis, ~0.5° grid. Raw file in data/raw/nasa_power/.")
A("- Climate at Lasalgaon 2014–24 (T °C / RH % / rain mm): " + "; ".join(f"{m} {c['t2m_c']}/{c['rh2m_pct']}/{c['rain_mm']:.0f}" for m, c in cl.items()) + ".")
A("  - The chawl storage months Jul–Sep are the most humid (RH 82–85%), which is when ventilated stores rot fastest.")
A(f"- H4 (added after the proposal; Sep–Oct window chosen on crop-calendar grounds, not by searching): seasons with more Sep+Oct rain see a bigger rise from April to the Oct–Dec mean price. n = {wl['n_seasons']} seasons ({wl['years']}; NHRDF Lasalgaon before 2014, our composite from 2014).")
A(f"  - β = {wl['beta_per_100mm_log']} log points per 100 mm (≈ +{(wl['rise_multiplier_per_100mm'] - 1) * 100:.0f}% per 100 mm); OLS p = {wl['p_ols']}, robust (HC1) p = {wl['p_robust_HC1']}; R² = {wl['r2']}; OLS 95% CI {wl['ci95_ols_per_100mm']} per 100 mm.")
A(f"  - Spearman ρ = {wl['spearman_rho']} (p = {wl['spearman_p']}). Mean Sep+Oct rain {wl['mean_rain_sep_oct_mm']:.0f} mm.")
A(f"  - Wettest third (mean {wl['wet_third']['mean_rain_mm']:.0f} mm): median rise {wl['wet_third']['median_rise_pct']:.0f}%. Driest third ({wl['dry_third']['mean_rain_mm']:.0f} mm): {wl['dry_third']['median_rise_pct']:.0f}%.")
A(f"  - Fragility: leave-one-season-out β ranges {wl['leave_one_out']['beta_min']}–{wl['leave_one_out']['beta_max']} per 100 mm; p exceeds 0.05 only when dropping {wl['leave_one_out']['seasons_whose_removal_lifts_p_above_0_05']} (worst p = {wl['leave_one_out']['p_max']}). Subperiods: 1996–2013 β {wl['subperiods']['1996_2013']['beta_per_100mm_log']} (p {wl['subperiods']['1996_2013']['p']}, n {wl['subperiods']['1996_2013']['n']}); 2014–24 β {wl['subperiods']['2014_2024']['beta_per_100mm_log']} (p {wl['subperiods']['2014_2024']['p']}, n {wl['subperiods']['2014_2024']['n']}). Verdict: weakly supported, same sign in both periods, but dropping any one of the seasons listed above takes p above 0.05, so treat H4 as suggestive, not firm.")
A(f"  - Placebo, whole Jun–Sep monsoon: β = {wl['placebo_jun_sep_monsoon']['beta_per_100mm_log']} per 100 mm, p = {wl['placebo_jun_sep_monsoon']['p']}. Weaker, consistent with late rain mattering more.")
A(f"- Real-time use (1 Nov re-plan with the rain signal; β estimated on earlier seasons only): value of the rain feed = Rs {rr['C']['mean_value_of_rain_feed']:,.0f}/t (C) and Rs {rr['B']['mean_value_of_rain_feed']:,.0f}/t (B).")
A("  - Reason: the C plan enters November with 0 t (2017–19) or exactly U = 300 t (2020–24), so the handling cap leaves no choice; B holds nothing. The rain factor also scales November and December alike, so it barely changes which month is better. The binding constraint is handling capacity, not information.")
A("\n## Value of loss-rate information (sensor / digital-twin question)")
A("- Three operators, same April forecast; the store's true monthly loss δ varies. Blind = plans with the book δ and never learns. Sensor = measures δ from May and re-plans monthly. Calibrated = δ known before April from an earlier logged season. Gain = Rs/t vs harvest sale, mean 2017–24; handling cap enforced in execution.")
for lab, vv in [("Using our forecast", vf), ("With perfect price foresight (isolates the value of loss information)", va)]:
    A(f"- {lab}:")
    for k in "BC":
        A(f"  - {k} (book δ {vv[k]['book_delta'] * 100:.2f}%/month): " + "; ".join(
            f"δ {g['delta_true'] * 100:.1f}% → blind {n0(g['blind'])}, sensor {n0(g['sensor'])}, calibrated {n0(g['calibrated'])}" for g in vv[k]["grid"]) + ".")
A(f"- Chawl: with the book 18% the plan sells everything in April, so in-season sensing never starts (sensor = blind = 0). A chawl measured at 8%/month is worth Rs {n0(at(vf, 'B', 0.08, 'calibrated'))}/t with our forecast (Rs {n0(at(va, 'B', 0.08, 'voi_calibrated'))}/t more than blind with perfect prices). Measured 14%: Rs {n0(at(vf, 'B', 0.14, 'calibrated'))}/t: above the 12.4% break-even the plan's storage loses money, so the measurement mainly tells a good chawl from a bad one.")
A(f"- Cold store: with our forecast (test-season bias {f['decision_horizon'][best]['bias_pct']}%) sensing is mixed, because the low-biased forecast and the true loss push the plan in opposite directions. With accurate prices sensing is never worse and worth Rs {n0(at(va, 'C', 0.08, 'voi_sensor'))}–{n0(at(va, 'C', 0.15, 'voi_sensor'))}/t when the store degrades to 8–15%/month, and Rs {n0(at(va, 'C', 0.005, 'voi_sensor'))}/t if it runs better than book (0.5%).")
A("- Reading: sensors pay only alongside a good price forecast; their biggest use is calibrating a store's real loss rate before the season.")
(ROOT / "docs" / "KEY_NUMBERS.md").write_text("\n".join(out), encoding="utf-8")
print(len(out), "lines")
