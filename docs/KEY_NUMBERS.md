# KEY NUMBERS — single source of truth (auto-generated from outputs/results.json)

Units: data prices are Rs/quintal (100 kg). The LP uses Rs/tonne. Text uses Rs/kg (= Rs/quintal ÷ 100 = Rs/tonne ÷ 1000).

## Data
- Main dataset: Mendeley, Shelar, Hajare & Mangarule (2025), DOI 10.17632/ds9jmxp9zy.1, CC BY 4.0. An Agmarknet compilation of 965,314 all-India daily records, 2014-01-01 to 2024-12-31.
- Lasalgaon APMC rows in the main dataset: **0**. We found this in the planned first-week data check.
- Maharashtra: 91,898 rows from 96 markets.
  - Dropped 42 rows priced outside Rs 50–20,000/q.
  - Dropped 58 relative outliers (outside 0.2–5× the same-day median).
- Repeated arrivals across variety rows: 5,672 market-days have several variety rows, and 100.0% of them repeat the same tonnage on each row.
  - Summing those rows would double-count 1,979,857 t.
  - So we collapse to one row per market-day: 85,346 clean market-days.
- Price series: Maharashtra arrival-weighted modal price, monthly, 132 months, none missing.
  - Markets reporting rise from 34.0/month (2014) to 63.8/month (2024).
  - Arrival weight by district (%): {'Ahmednagar': 38.5, 'Pune': 18.4, 'Sholapur': 15.2, 'Mumbai': 9.3, 'Chattrapati Sambhajinagar': 4.2, 'Kolhapur': 3.7}
- Validation against NHRDF's official Lasalgaon monthly series (Mendeley 10.17632/9dn4g8m97m, 1996–Jun 2019), 66 overlapping months (2014-01 to 2019-06):
  - r = 0.9896 on levels and 0.9254 on monthly % changes.
  - Mean level ratio 0.973; mean absolute gap 8.78%; direction agreement 87.7%.
  - Nasik APMC vs Lasalgaon: r = 0.9724. Composite vs Nasik, 2023–24: r = 0.9805.
  - Season shape, April → best later month (composite vs Lasalgaon): [{'year': 2014, 'rise_composite_pct': 128.0, 'rise_lasalgaon_pct': 112.4}, {'year': 2015, 'rise_composite_pct': 307.9, 'rise_lasalgaon_pct': 277.9}, {'year': 2016, 'rise_composite_pct': 30.5, 'rise_lasalgaon_pct': 18.2}, {'year': 2017, 'rise_composite_pct': 426.6, 'rise_lasalgaon_pct': 602.0}, {'year': 2018, 'rise_composite_pct': 63.2, 'rise_lasalgaon_pct': 95.5}]
- Spot-check, 2020–24: 19 independently reported Lasalgaon prices (8 MSAMB weekly reports plus news). r = 0.9; median absolute gap 17.7%.
  - Our series is lower in 84% of points (median -10.2%), because Lasalgaon is the premium market.
  - A level gap scales rupee values but barely moves the timing decision.
- Lasalgaon history 1996–2013 (216 months) is used ONLY to estimate seasonal indices for the two '28-yr' forecast candidates.

## EDA
- Price level: mean Rs 14.88/kg; minimum Rs 4.51/kg (2019-02); maximum Rs 50.56/kg (2019-12).
- Volatility: overall CV 60.9%; mean within-year CV 48.8%.
  - Month-on-month change SD 32.5%; annualised volatility from monthly log returns 101.5%.
  - Within a year, the maximum price averages 4.58× the minimum.
- Seasonal index (price ÷ that year's mean, 2014–24): {'Jan': 1.086, 'Feb': 0.873, 'Mar': 0.641, 'Apr': 0.553, 'May': 0.577, 'Jun': 0.789, 'Jul': 0.894, 'Aug': 1.126, 'Sep': 1.205, 'Oct': 1.401, 'Nov': 1.546, 'Dec': 1.308}. The trough is in April–May, the peak in November.
- Lasalgaon 1996–2013 seasonal index (NHRDF): {'Jan': 1.118, 'Feb': 0.883, 'Mar': 0.65, 'Apr': 0.609, 'May': 0.613, 'Jun': 0.784, 'Jul': 0.896, 'Aug': 1.091, 'Sep': 1.225, 'Oct': 1.491, 'Nov': 1.422, 'Dec': 1.218}
- The November price beat April in 11 of 11 years. Median April→November rise: 148.3%.
  - Median hindsight April→best-month rise: 218.3%. Best month by count: {'Nov': 5, 'Oct': 2, 'Aug': 1, 'Jul': 1, 'Dec': 1, 'Sep': 1}.

## H1 (OLS of log price on log arrivals per market-day)
- M1_simple: beta = -0.7565, p(OLS) = 0.0000, p(HAC) = 0.0082, adj R² = 0.126, n = 132, DW = 0.34
- M2_month_FE: beta = -0.6701, p(OLS) = 0.0002, p(HAC) = 0.0025, adj R² = 0.358, n = 132, DW = 0.33
- M3_month_year_FE: beta = -0.442, p(OLS) = 0.0126, p(HAC) = 0.0131, adj R² = 0.529, n = 132, DW = 0.52
- M4_lagged_arrivals: beta = -0.1338, p(OLS) = 0.4507, p(HAC) = 0.5220, adj R² = 0.504, n = 131, DW = 0.52
- M5_dynamic_with_lagged_price: beta = -0.0144, p(OLS) = 0.8957, p(HAC) = 0.9151, adj R² = 0.831, n = 131, DW = 1.68, lagged-price coef 0.811
- D1_daily_sign_check: beta = -0.0769, p(OLS) = 0.0000, p(HAC) = 0.0129, adj R² = 0.55, n = 3972, DW = 0.1
- HEADLINE (M3, month + year dummies): beta = -0.442, one-sided p(HAC) = 0.0066, H1 supported = True.
  - Months with 10% heavier arrivals have prices about 4.4% lower. This is an association, not a causal elasticity.
- Robustness to how arrivals are normalised: {'per_market_day (headline)': {'elasticity': -0.442, 'p_hac': 0.013143454812303371}, 'per_market_reporting': {'elasticity': -0.2717, 'p_hac': 0.05817453276444939}, 'total_arrivals': {'elasticity': -0.2471, 'p_hac': 0.07899010601129246}, 'per_market_day_excl_covid_AprMay2020': {'elasticity': -0.5717, 'p_hac': 0.0005223251100616336}}
- Reverse-causality check: last month's price predicts this month's arrivals (coef -0.1548, p = 0.011). Prices and arrivals are jointly determined.
- Price-taker check (order of magnitude):
  - Selling 1,000 t in April is 3.6% of Lasalgaon April arrivals (27,752 t); implied price impact ~1.59%.
  - Selling 300 t in Oct/Nov is 1.79% of arrivals; implied impact ~0.79%.

## Forecasting (origin = end-March; horizon Apr–Dec = 1–9 months; expanding window)
- Selection rule: lowest Apr-Dec MAPE on validation seasons 2019-2022; scored on 2023-2024.
- **Chosen model: Regression: trend + month dummies**, i.e. OLS of log price = a + b·t + 11 month dummies.
- Each candidate, best validation MAPE first:
  - Regression: trend + month dummies: validation MAPE 36.94%; test MAPE 29.5% (bias -17.11%, direction hits 93.75%); 1-step MAPE 27.08%; scenario-C decision value 2017–24 Rs 4,546/t
  - Seasonal naive (same month last year): validation MAPE 42.06%; test MAPE 34.84% (bias -25.89%, direction hits 87.5%); 1-step MAPE 39.86%; scenario-C decision value 2017–24 Rs 3,980/t
  - Naive (last month): validation MAPE 44.44%; test MAPE 45.62% (bias -41.37%, direction hits 0.0%); 1-step MAPE 21.68%; scenario-C decision value 2017–24 Rs 0/t
  - 28-yr seasonal index x moving average: validation MAPE 47.35%; test MAPE 29.49% (bias -27.11%, direction hits 81.25%); 1-step MAPE 20.12%; scenario-C decision value 2017–24 Rs 6,182/t
  - Regression: level + month effects: validation MAPE 48.6%; test MAPE 30.45% (bias -29.11%, direction hits 87.5%); 1-step MAPE 21.65%; scenario-C decision value 2017–24 Rs 5,155/t
  - Seasonal index x moving average: validation MAPE 50.68%; test MAPE 29.32% (bias -28.21%, direction hits 93.75%); 1-step MAPE 20.86%; scenario-C decision value 2017–24 Rs 4,009/t
  - Holt-Winters (damped trend + seasonality): validation MAPE 57.36%; test MAPE 23.85% (bias -23.21%, direction hits 93.75%); 1-step MAPE 12.94%; scenario-C decision value 2017–24 Rs 4,546/t
  - 28-yr seasonal index x exponential smoothing: validation MAPE 58.02%; test MAPE 19.55% (bias -18.17%, direction hits 81.25%); 1-step MAPE 13.66%; scenario-C decision value 2017–24 Rs 6,006/t
  - Seasonal index x exponential smoothing: validation MAPE 58.23%; test MAPE 22.45% (bias -22.2%, direction hits 93.75%); 1-step MAPE 14.04%; scenario-C decision value 2017–24 Rs 4,294/t
  - 12-month moving average: validation MAPE 62.27%; test MAPE 43.87% (bias -17.93%, direction hits 0.0%); 1-step MAPE 34.81%; scenario-C decision value 2017–24 Rs 0/t
- Best on the test set, for reference only: 28-yr seasonal index x exponential smoothing. SES-type models fit alpha = 1.0: the latest month carries the whole level, close to a random walk.

## LP (one FPO; base parameters)
- Q = 1000 t; C = 700 t; L = 250 t (April crop-loan sale).
- U = 300 t/month, the grading and trucking cap for May–Dec. The April harvest sale goes field-run to traders, so it has no cap.
- Storage cost: h_B = Rs 250/t/month; h_C = Rs 700/t/month (operating cost of an owned facility).
- Monthly loss: delta_B = 18.05%/month (ICAR ventilated: 54.89% in 120 days); delta_C = 1.83%/month (ICAR-DOGR cold store: 7.14% in 120 days). Conversion: delta = 1 − (1 − L120)^(1/4).
- 2024 plan, forecast made end-March 2024:
  - Forecast price, Rs/t: [8474.0, 8673.0, 11495.0, 12934.0, 16329.0, 17416.0, 21506.0, 22988.0, 18820.0]
  - Actual price, Rs/t: [11587.0, 13614.0, 21898.0, 24295.0, 29215.0, 36881.0, 31113.0, 34101.0, 27081.0]
  - A: x = [1000.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]; objective Rs 84.7 lakh; lost to rot 0.0 t; PuLP vs SciPy diff Rs 0.0
  - B: x = [1000.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]; objective Rs 84.7 lakh; lost to rot 0.0 t; PuLP vs SciPy diff Rs 0.0
  - C: x = [300.0, 0.0, 0.0, 0.0, 0.0, 21.2, 300.0, 300.0, 0.0]; objective Rs 132.5 lakh; lost to rot 78.8 t; PuLP vs SciPy diff Rs 0.0081
- Verified marginal values, scenario C 2024 (re-solve with ±1 t):
  - Storage capacity: +1 t → +Rs 4,028.
  - Handling cap U: +1 t/month → +Rs 6,526. It binds in Oct and Nov (SciPy duals May..Dec = [-0.0, -0.0, -0.0, -0.0, -0.0, 3050.84, 3474.79, -0.0]).
  - Extra harvested tonne: +Rs 8,474.
  - Loan sale L: 0.0 (slack).

## Backtest (evaluated at ACTUAL prices; gain vs selling everything in April, Rs per tonne harvested)
- 2017–24 C|forecast_plan: mean 4,546, median 3,840, min -1,181, max 10,733, wins 7/8, losses 1
- 2017–24 C|rolling_replan: mean 4,511, median 3,826, min -1,181, max 10,733, wins 7/8, losses 1
- 2017–24 C|calendar_rule_exante: mean 5,508, median 6,336, min -1,324, max 10,734, wins 7/8, losses 1
- 2017–24 C|calendar_rule_hindsight_OctNov: mean 7,110, median 8,571, min -1,507, max 13,190, wins 7/8, losses 1
- 2017–24 C|perfect_foresight: mean 8,558, median 9,828, min 532, max 19,439, wins 8/8, losses 0
- 2017–24 B|forecast_plan: mean 0, median 0, min 0, max 0, wins 0/8, losses 0
- 2017–24 B|calendar_rule_exante: mean -1,149, median -1,165, min -3,381, max 1,764, wins 2/8, losses 6
- 2017–24 B|perfect_foresight: mean 791, median 675, min 0, max 1,764, wins 5/8, losses 0
- 2023–24 (pre-registered test seasons), means: {'A|forecast_plan': 0.0, 'B|calendar_rule_exante': 345.0, 'B|calendar_rule_hindsight_OctNov': -718.0, 'B|forecast_plan': 0.0, 'B|perfect_foresight': 1120.0, 'B|rolling_replan': 0.0, 'C|calendar_rule_exante': 9117.0, 'C|calendar_rule_hindsight_OctNov': 9840.0, 'C|forecast_plan': 9980.0, 'C|perfect_foresight': 10981.0, 'C|rolling_replan': 9980.0}
- Ex-ante calendar rule months (top-3 seasonal index at origin): Oct,Nov,Sep, every year.
- Paired tests (8 seasons): {"H2_B_vs_A": {"n_seasons": 8, "mean_diff_rs_per_t": 0.0, "median_diff_rs_per_t": 0.0, "min_diff_rs_per_t": 0.0, "max_diff_rs_per_t": 0.0, "wins": 0, "ties": 8, "paired_t_one_sided_p": null, "wilcoxon_one_sided_p": null, "note": "not testable: every season identical (the B plan never stores, so it equals harvest sale)"}, "C_vs_A": {"n_seasons": 8, "mean_diff_rs_per_t": 4546.0, "median_diff_rs_per_t": 3840.0, "min_diff_rs_per_t": -1181.0, "max_diff_rs_per_t": 10733.0, "wins": 7, "ties": 0, "paired_t_one_sided_p": 0.0062, "wilcoxon_one_sided_p": 0.0078}, "H3_C_vs_B": {"n_seasons": 8, "mean_diff_rs_per_t": 4546.0, "median_diff_rs_per_t": 3840.0, "min_diff_rs_per_t": -1181.0, "max_diff_rs_per_t": 10733.0, "wins": 7, "ties": 0, "paired_t_one_sided_p": 0.0062, "wilcoxon_one_sided_p": 0.0078}}
- Nasik APMC robustness, 2023–24: [{'year': 2023, 'scenario': 'A', 'net_per_t': 6589.0, 'gain_vs_harvest_per_t': 0.0}, {'year': 2023, 'scenario': 'B', 'net_per_t': 6589.0, 'gain_vs_harvest_per_t': 0.0}, {'year': 2023, 'scenario': 'C', 'net_per_t': 18099.0, 'gain_vs_harvest_per_t': 11510.0}, {'year': 2024, 'scenario': 'A', 'net_per_t': 13159.0, 'gain_vs_harvest_per_t': 0.0}, {'year': 2024, 'scenario': 'B', 'net_per_t': 13159.0, 'gain_vs_harvest_per_t': 0.0}, {'year': 2024, 'scenario': 'C', 'net_per_t': 26536.0, 'gain_vs_harvest_per_t': 13377.0}]
- Planned vs realised, scenario C (year, planned Rs/t, realised Rs/t): [(2017, 6526.0, 8076.0), (2018, 8521.0, 5530.0), (2019, 6215.0, 9874.0), (2020, 10354.0, 14861.0), (2021, 12650.0, 12762.0), (2022, 13815.0, 10080.0), (2023, 12486.0, 16668.0), (2024, 13251.0, 20813.0)]

## Sensitivity (mean realised gain vs harvest sale, Rs/t, 2017–24)
- delta_B: {'0.06': 3172.0, '0.10': 890.0, '0.14': -508.0, '0.18': 0.0, '0.22': 0.0, '0.26': 0.0}
- delta_C: {'0.005': 5514.0, '0.018': 4568.0, '0.030': 3444.0, '0.050': 2389.0, '0.080': 374.0}
- h_B: {'0': -734.0, '125': -238.0, '250': 0.0, '500': 0.0, '750': 0.0, '1000': 0.0}
- h_C: {'0': 7971.0, '350': 6301.0, '700': 4546.0, '1050': 3041.0, '1400': 1069.0, '2000': 0.0}
- C_capacity_B: {'300': 0.0, '500': 0.0, '700': 0.0, '900': 0.0, '1000': 0.0}
- C_capacity_C: {'300': 1770.0, '500': 3161.0, '700': 4546.0, '900': 4797.0, '1000': 4797.0}
- L_B: {'100': 0.0, '300': 0.0, '500': 0.0, '700': 0.0}
- L_C: {'100': 4546.0, '300': 4546.0, '500': 3161.0, '700': 1770.0}
- U_C: {'150': 4132.0, '300': 4546.0, '500': 4314.0, '1000': 4131.0}
- grid_delta_h: {'0.02': {'0': 7844.0, '250': 6686.0, '500': 5234.0, '750': 4240.0, '1000': 3119.0}, '0.06': {'0': 4556.0, '250': 3172.0, '500': 2481.0, '750': 1039.0, '1000': 199.0}, '0.10': {'0': 1941.0, '250': 890.0, '500': -43.0, '750': -529.0, '1000': -228.0}, '0.14': {'0': 327.0, '250': -508.0, '500': -219.0, '750': 0.0, '1000': 0.0}, '0.18': {'0': -730.0, '250': 0.0, '500': 0.0, '750': 0.0, '1000': 0.0}, '0.22': {'0': 0.0, '250': 0.0, '500': 0.0, '750': 0.0, '1000': 0.0}}
- breakeven_delta_B: 0.1243

## Industry 4.0 value (scenario C over scenario B)
- Uplift: Rs 4,546/t harvested (Rs 4.55/kg).
  - Per tonne of storage capacity: Rs 6,495 per season.
  - By season: {'2017': 2929.0, '2018': -1181.0, '2019': 3069.0, '2020': 4865.0, '2021': 4610.0, '2022': 2118.0, '2023': 10733.0, '2024': 9226.0}.
- Capital cost per tonne of capacity:
  - B: Rs 7,000/t (MIDH: Rs 1.75 lakh per 25 t unit).
  - C base: Rs 16,667/t (ICAR multi-module: Rs 1.5 lakh per 9 t). Range Rs 8,000 (MIDH cold storage type 1) to Rs 50,000 (small cold room).
- Base case: payback 1.49 seasons; net annual benefit Rs 4,921/t capacity (CRF 0.1627, 10 years at 10%).
- Range (capex, payback seasons, net annual benefit): [(8000.0, 0.15, 6332.0), (16667.0, 1.49, 4921.0), (50000.0, 6.62, -503.0)]
- For a 1,000 t FPO: ≈ Rs 45.5 lakh a year. The 2023–24 test seasons alone give Rs 9,980/t.

## Satellite weather layer (NASA POWER) — H4
- Source: NASA POWER monthly point API, 20.15N 74.23E (Lasalgaon), 1996-2024; T2M, RH2M, PRECTOTCORR. Free, no key; satellite-derived/reanalysis, ~0.5° grid. Raw file in data/raw/nasa_power/.
- Climate at Lasalgaon 2014–24 (T °C / RH % / rain mm): Jan 20.4/44.9/3; Feb 23.6/31.7/2; Mar 27.2/30.7/13; Apr 30.8/29.4/6; May 31.4/42.5/17; Jun 28.2/67.7/132; Jul 25.4/82.4/258; Aug 24.7/84.4/196; Sep 24.5/85.0/199; Oct 23.9/74.7/67; Nov 21.6/65.6/15; Dec 20.3/56.2/9.
  - The chawl storage months Jul–Sep are the most humid (RH 82–85%), which is when ventilated stores rot fastest.
- H4 (added after the proposal; Sep–Oct window chosen on crop-calendar grounds, not by searching): seasons with more Sep+Oct rain see a bigger rise from April to the Oct–Dec mean price. n = 29 seasons (1996-2024; NHRDF Lasalgaon before 2014, our composite from 2014).
  - β = 0.181 log points per 100 mm (≈ +20% per 100 mm); OLS p = 0.0361, robust (HC1) p = 0.0025; R² = 0.153; OLS 95% CI [0.013, 0.349] per 100 mm.
  - Spearman ρ = 0.46 (p = 0.012). Mean Sep+Oct rain 237 mm.
  - Wettest third (mean 338 mm): median rise 208%. Driest third (137 mm): 123%.
  - Fragility: leave-one-season-out β ranges 0.145–0.206 per 100 mm; p exceeds 0.05 only when dropping [2005, 2018, 2019] (worst p = 0.0952). Subperiods: 1996–2013 β 0.134 (p 0.2143, n 18); 2014–24 β 0.273 (p 0.1112, n 11). Verdict: weakly supported, same sign in both periods, but dropping any one of the seasons listed above takes p above 0.05, so treat H4 as suggestive, not firm.
  - Placebo, whole Jun–Sep monsoon: β = 0.073 per 100 mm, p = 0.1117. Weaker, consistent with late rain mattering more.
- Real-time use (1 Nov re-plan with the rain signal; β estimated on earlier seasons only): value of the rain feed = Rs 0/t (C) and Rs 0/t (B).
  - Reason: the C plan enters November with 0 t (2017–19) or exactly U = 300 t (2020–24), so the handling cap leaves no choice; B holds nothing. The rain factor also scales November and December alike, so it barely changes which month is better. The binding constraint is handling capacity, not information.

## Value of loss-rate information (sensor / digital-twin question)
- Three operators, same April forecast; the store's true monthly loss δ varies. Blind = plans with the book δ and never learns. Sensor = measures δ from May and re-plans monthly. Calibrated = δ known before April from an earlier logged season. Gain = Rs/t vs harvest sale, mean 2017–24; handling cap enforced in execution.
- Using our forecast:
  - B (book δ 18.05%/month): δ 4.0% → blind 0, sensor 0, calibrated 4,691; δ 6.0% → blind 0, sensor 0, calibrated 3,172; δ 8.0% → blind 0, sensor 0, calibrated 2,200; δ 10.0% → blind 0, sensor 0, calibrated 890; δ 12.0% → blind 0, sensor 0, calibrated 191; δ 14.0% → blind 0, sensor 0, calibrated -508; δ 18.1% → blind 0, sensor 0, calibrated 0; δ 22.0% → blind 0, sensor 0, calibrated 0.
  - C (book δ 1.83%/month): δ 0.5% → blind 5,404, sensor 5,514, calibrated 5,514; δ 1.8% → blind 4,549, sensor 4,549, calibrated 4,549; δ 3.0% → blind 3,712, sensor 3,444, calibrated 3,444; δ 5.0% → blind 2,435, sensor 2,389, calibrated 2,389; δ 8.0% → blind 828, sensor 407, calibrated 374; δ 10.0% → blind -64, sensor -621, calibrated -791; δ 12.0% → blind -829, sensor -841, calibrated -616; δ 15.0% → blind -1,849, sensor -1,234, calibrated 0.
- With perfect price foresight (isolates the value of loss information):
  - B (book δ 18.05%/month): δ 4.0% → blind 4,701, sensor 6,471, calibrated 8,374; δ 6.0% → blind 3,788, sensor 5,323, calibrated 6,738; δ 8.0% → blind 3,008, sensor 4,300, calibrated 5,306; δ 10.0% → blind 2,362, sensor 3,380, calibrated 4,030; δ 12.0% → blind 1,834, sensor 2,571, calibrated 2,958; δ 14.0% → blind 1,406, sensor 1,868, calibrated 2,054; δ 18.1% → blind 790, sensor 790, calibrated 790; δ 22.0% → blind 106, sensor 144, calibrated 231.
  - C (book δ 1.83%/month): δ 0.5% → blind 9,110, sensor 9,624, calibrated 9,624; δ 1.8% → blind 8,560, sensor 8,562, calibrated 8,562; δ 3.0% → blind 7,384, sensor 7,551, calibrated 7,551; δ 5.0% → blind 5,593, sensor 5,964, calibrated 5,965; δ 8.0% → blind 3,377, sensor 3,922, calibrated 4,000; δ 10.0% → blind 2,173, sensor 2,782, calibrated 2,921; δ 12.0% → blind 1,155, sensor 1,785, calibrated 1,977; δ 15.0% → blind -194, sensor 552, calibrated 893.
- Chawl: with the book 18% the plan sells everything in April, so in-season sensing never starts (sensor = blind = 0). A chawl measured at 8%/month is worth Rs 2,200/t with our forecast (Rs 2,298/t more than blind with perfect prices). Measured 14%: Rs -508/t: above the 12.4% break-even the plan's storage loses money, so the measurement mainly tells a good chawl from a bad one.
- Cold store: with our forecast (test-season bias -17.11%) sensing is mixed, because the low-biased forecast and the true loss push the plan in opposite directions. With accurate prices sensing is never worse and worth Rs 545–746/t when the store degrades to 8–15%/month, and Rs 514/t if it runs better than book (0.5%).
- Reading: sensors pay only alongside a good price forecast; their biggest use is calibrating a store's real loss rate before the season.