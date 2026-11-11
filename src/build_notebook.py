"""Builds notebooks/KandaCode_Analysis.ipynb — the narrated, re-runnable version of the pipeline."""
from pathlib import Path
import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]
nb = nbf.v4.new_notebook()
C = []


def md(s):
    C.append(nbf.v4.new_markdown_cell(s.strip()))


def code(s):
    C.append(nbf.v4.new_code_cell(s.strip()))


md("""
# Kanda Code — When should onion farmers sell their crop?
**Industry 4.0 (MS4001) · IIT Madras BS** · Team: Raghuram Devarayi · Parashmani Datta · Kathan Desai · Yash Arabhavi · Aaryan Choudhary

One notebook, top to bottom: **data → EDA → H1 regression → price forecasting → linear programme → backtest → sensitivity → value of IoT storage → Industry 4.0 extensions (satellite weather, value of sensor information).**
Every number in the report, the deck and the viva guide comes from the functions in `src/kandacode.py`, called here.

| Step | Course concept | Function |
|---|---|---|
| 1 Data | data cleaning, validation | `clean_maharashtra`, `build_monthly`, `validate_against_lasalgaon` |
| 2 EDA | descriptive analytics, seasonality, volatility | `eda_stats`, `seasonal_profile` |
| 3 H1 | multiple regression (log-log, dummies) | `h1_regressions` |
| 4 Forecast | moving average, exponential smoothing, Holt-Winters, regression | `forecast`, `evaluate_forecasts` |
| 5 Optimise | linear programming, shadow prices | `solve_lp` |
| 6 Validate | backtest on unseen prices | `backtest`, `paired_tests` |
| 7 Industry 4.0 | value of IoT-monitored storage | `sensitivity`, `industry40_value` |
| 8 Extensions | satellite weather (H4, OLS); value of loss-rate information (LP scenarios) | `load_power`, `weather_price_link`, `value_of_loss_information` |
""")

code("""
# Reproducibility: pandas, numpy, statsmodels, scipy, matplotlib, pulp==2.9.0 (bundled CBC solver)
# !pip install -q statsmodels "pulp==2.9.0"
import sys, json
from pathlib import Path
ROOT = Path.cwd().parent if Path.cwd().name == 'notebooks' else Path.cwd()
sys.path.insert(0, str(ROOT / 'src'))
import numpy as np, pandas as pd
import kandacode as kc
from IPython.display import Image, display
pd.set_option('display.width', 160); pd.set_option('display.max_columns', 30)
print('project root:', ROOT)
""")

md("""
## 1 · Data
**Main dataset:** Shelar, Hajare & Mangarule (2025), *Spatio-temporal onion price dataset 2014–2024*, Mendeley Data, DOI 10.17632/ds9jmxp9zy.1 (CC BY 4.0), an Agmarknet compilation of 965,314 daily market records.

**Data check, as the proposal planned.** The compilation has **no Lasalgaon APMC records** (0 rows). So we use the **Maharashtra arrival-weighted modal price** across all Maharashtra APMCs and validate it against **NHRDF's official Lasalgaon monthly series** (Mendeley 10.17632/9dn4g8m97m, 1996–Jun 2019).

**Cleaning rules:**
- Keep Maharashtra rows.
- Drop modal prices outside ₹50–20,000/quintal (₹0.5–200/kg), and prices outside 0.2–5× that day's cross-market median.
- Drop non-positive arrivals and exact duplicates.
- **Collapse to one row per market-day.** Agmarknet repeats a market's total arrivals on each variety row, so summing those rows would double-count about 2 million tonnes.
""")
code("""
raw = kc.load_raw()
mh, clean_log = kc.clean_maharashtra(raw)
daily = kc.build_daily(mh)
monthly = kc.build_monthly(mh)
nasik = kc.build_market_monthly(mh, 'Nasik')
nh = kc.load_nhrdf()
kc.LONG_HISTORY = nh['lasalgaon_price_rs_qtl'].dropna().loc[:'2013-12']   # 1996-2013 Lasalgaon history, used only for seasonal indices
print(json.dumps(clean_log, indent=1))
monthly.head()
""")
code("""
val = kc.validate_against_lasalgaon(monthly, nasik, nh)
spot = kc.spotcheck_2020_2024(monthly)   # 19 independently reported Lasalgaon prices, 2020-24
print({k: v for k, v in spot.items() if k != 'rows'})
val   # levels r ≈ 0.99, monthly changes r ≈ 0.93 over 66 months
""")
code("display(Image(str(kc.FIG / 'f8_validation.png'), width=420))")

md("## 2 · Exploratory data analysis — seasonality and volatility")
code("""
eda = kc.eda_stats(monthly, daily)
{k: v for k, v in eda.items() if k not in ('season_rise', 'yearly')}
""")
code("pd.DataFrame(eda['season_rise'])   # April price vs best later month, each year")
code("kc.seasonal_profile(monthly).round(3)")
code("display(Image(str(kc.FIG / 'f1_price_history.png'))); display(Image(str(kc.FIG / 'f2_seasonality.png'), width=420))")

md("""
## 3 · H1 — do arrivals drive price?
Model: $\\ln P_t = \\alpha + \\beta \\ln A_t + \\text{month dummies} + \\text{year dummies} + \\varepsilon_t$.
β is an **elasticity**: the % change in price for a 1% change in arrivals (arrivals per reporting market-day, so changes in market coverage do not count as supply).
Standard errors: OLS and Newey–West HAC (robust to autocorrelation).
""")
code("""
h1 = kc.h1_regressions(monthly, daily)
pd.DataFrame({k: v for k, v in h1.items() if k[:1] in 'MD'}).T[['n','elasticity','se_ols','p_ols','se_hac','p_hac','adj_r2','durbin_watson']]
""")
code("h1['headline'], h1['robust_normalisation'], h1['reverse_causality_lnA_on_lagged_price']")
code("display(Image(str(kc.FIG / 'f3_price_arrivals.png'), width=420))")
code("""
base = kc.LPParams()
kc.price_taker_check(monthly, base.Q, base.U, h1['headline']['elasticity'], nh)   # FPO is a price-taker (order of magnitude)
""")

md("""
## 4 · Forecasting the price path
The decision is taken at the **end of March**, so each model forecasts **April–December (1–9 months ahead)** from that origin.
- Expanding window: only data up to the origin is used.
- **Selection:** the model with the lowest MAPE on the validation seasons 2019–2022.
- **Test:** 2023 and 2024, never used for selection.
- We also report rolling 1-month-ahead accuracy.
""")
code("""
series = monthly['price_rs_qtl'].dropna()
fe = kc.evaluate_forecasts(series)
tab = (pd.DataFrame(fe['validation_horizon']).T[['MAPE']].rename(columns={'MAPE': 'VALID_2019_22_MAPE'})
       .join(pd.DataFrame(fe['decision_horizon']).T.add_prefix('TEST_'))
       .join(pd.DataFrame(fe['one_step']).T[['MAPE']].rename(columns={'MAPE': '1step_MAPE'})))
tab.index = [kc.FORECAST_LABELS[i] for i in tab.index]
tab.sort_values('VALID_2019_22_MAPE')
""")
code("best = fe['best_method']; print('chosen model:', kc.FORECAST_LABELS[best])")
code("display(Image(str(kc.FIG / 'f4_forecast_test.png')))")

md("""
## 5 · The linear programme (sell-or-store plan)
**Decision variables:** $x_t$ = tonnes sold in month $t$; $s_t$ = tonnes in storage at the end of month $t$ ($t=1$ April … $9$ December).

**Objective:** maximise $Z=\\sum_t \\hat p_t x_t - h\\sum_t s_t$

**Constraints:**

| Constraint | Formula | Meaning |
|---|---|---|
| Harvest balance | $s_1 = Q - x_1$ | Whatever is not sold in April goes into storage |
| Stock balance | $s_t = (1-\\delta)s_{t-1} - x_t$ | Last month's stock, minus rot, minus sales |
| Capacity | $s_t \\le C$ | Stock never exceeds storage space |
| Loan repayment | $x_1 \\ge L$ | Minimum sale at harvest |
| Handling capacity | $x_t \\le U$ for $t\\ge2$ | Monthly grading and trucking limit |
| Clear by December | $s_9 = 0$ | Season ends with no stock |
| Non-negativity | $x, s \\ge 0$ | No negative sales or stock |

**Scenarios:**
- **A:** no storage ($C=0$).
- **B:** ventilated kanda chawl, δ = 1−(1−0.5489)^{1/4} ≈ 18.0%/month (ICAR: 54.89% loss in 120 days).
- **C:** cold / IoT-monitored storage, δ ≈ 1.83%/month (ICAR-DOGR: 7.14% in 120 days).

**Solvers:** PuLP + CBC, cross-checked with SciPy (HiGHS), which also returns shadow prices.
""")
code("""
from dataclasses import asdict
print(asdict(base)); print({k: {kk: round(vv, 4) if isinstance(vv, float) else vv for kk, vv in v.items()} for k, v in kc.SCENARIOS.items()})
tr = series[series.index <= pd.Period('2024-03', 'M')]
fc = kc.forecast(tr, 9, best) * 10       # Rs/quintal -> Rs/tonne
plans = {k: kc.solve_lp(fc, kc.scenario_params(base, k)) for k in 'ABC'}
pd.DataFrame({k: np.round(v['x'], 1) for k, v in plans.items()}, index=kc.SEASON)
""")
code("""
pd.DataFrame({k: {'objective_Rs_lakh': v['objective']/1e5, 'scipy_cross_check': v['objective_match'],
                  'tonnes_lost_to_rot': v['lost_total']} for k, v in plans.items()}).T
""")
code("""
# Shadow prices VERIFIED by re-solving with each right-hand side moved +/- 1 tonne (scenario C, 2024 forecast)
kc.marginal_values(fc, kc.scenario_params(base, 'C'))
""")
code("display(Image(str(kc.FIG / 'f5_lp_plan_2024.png')))")

md("## 6 · Backtest on prices the model never saw (H2, H3)")
code("""
bt = kc.backtest(series, [2023, 2024], base, best)
bt[['year','scenario','strategy','net_per_t','gain_vs_harvest_per_t','oracle_net_per_t','sold_t']].round(0)
""")
code("""
bt_rob = kc.backtest(series, list(range(2017, 2025)), base, best)
bt_rob.pivot_table(index='year', columns=['scenario','strategy'], values='gain_vs_harvest_per_t').round(0)
""")
code("kc.paired_tests(bt_rob)")
code("display(Image(str(kc.FIG / 'f6_backtest.png')))")

md("## 7 · Sensitivity and the rupee value of IoT-monitored storage (Industry 4.0)")
code("""
sens = kc.sensitivity(series, list(range(2017, 2025)), base, best)
pd.DataFrame(sens['grid_delta_h']).T   # rows: monthly loss δ ; cols: storage cost h ; value = avg gain Rs/t vs harvest sale
""")
code("print('break-even monthly loss for chawl storage:', sens['breakeven_delta_B'])")
code("kc.industry40_value(bt_rob, base)")
code("display(Image(str(kc.FIG / 'f7_sensitivity.png'), width=420))")

md("""
## 8 · Industry 4.0 extensions: satellite weather (H4) and the value of sensor information
Added on 10 Nov 2026, **after the approved proposal**. H1–H3 above are unchanged. Two additions, both with syllabus methods only (OLS as in H1; LP scenario analysis on the same backtest):
1. **A real remote-sensing feed.** NASA POWER (NASA Langley Research Center), monthly point API, at Lasalgaon 20.15°N 74.23°E, 1996–2024: T2M (2 m air temperature, °C), RH2M (relative humidity, %), PRECTOTCORR (bias-corrected rain, mm/day, converted to mm per month). Satellite-derived and reanalysis estimates on a ~0.5° grid; free, no key. Downloaded by `src/fetch_nasa_power.py`.
2. **What sensor information is worth in rupees**: blind vs sensor vs calibrated stores.

Details: `docs/METHODOLOGY.md` §9 and `docs/EXTENSION_BRIEF.md`.
""")
code("""
wx = kc.load_power()                                            # adds rain_mm = rain_mm_per_day x days in month
price_long = pd.concat([kc.LONG_HISTORY, series]).sort_index()  # NHRDF Lasalgaon 1996-2013 + our composite 2014-24
R = json.loads((kc.OUT / 'results.json').read_text(encoding='utf-8'))   # pipeline results, for checks and the slow grids
print(len(wx), 'months:', wx.index.min(), 'to', wx.index.max())
wx.head()
""")
code("""
# Climate at Lasalgaon, 2014-24: RH is 82-85% in Jul-Sep, exactly when rabi onion sits in a chawl
w14 = wx[wx.index >= pd.Period('2014-01', 'M')]
clim = w14.groupby(w14.index.month)[['t2m_c', 'rh2m_pct', 'rain_mm']].mean()
clim.index = kc.MONTHS
clim.round({'t2m_c': 1, 'rh2m_pct': 1, 'rain_mm': 0})
""")

md("""
### 8.1 · H4 — does late-monsoon rain raise the post-harvest price rise?
One season = one observation (n = 29, 1996–2024). Outcome: $r_y = \\ln(\\overline{P}_{Oct-Dec} / P_{Apr})$. Regressor: Sep + Oct rain (mm). OLS $r_y = a + b R_y$, with HC1 robust p, Spearman ρ, wet vs dry thirds, a leave-one-season-out refit, two subperiods, and a placebo using the whole Jun–Sep monsoon.
Mechanism: late rain damages the kharif crop in the field and raises rot in stored rabi onion.
""")
code("""
h4 = kc.weather_price_link(price_long, wx)
tab4 = pd.DataFrame(h4['table']).set_index('year')
tab4[['rain_sep_oct_mm', 'rain_jun_sep_mm', 'rh_sep_oct_pct', 'rise_pct', 'rise_log', 'source']]
""")
code("""
coef = {k: h4[k] for k in ('n_seasons', 'years', 'beta_per_100mm_log', 'rise_multiplier_per_100mm', 'p_ols', 'p_robust_HC1',
                           'r2', 'ci95_ols_per_100mm', 'spearman_rho', 'spearman_p', 'mean_rain_sep_oct_mm')}
print(json.dumps(coef, indent=1))
print('wet third:', h4['wet_third'], '| dry third:', h4['dry_third'])
print('placebo (Jun-Sep monsoon):', h4['placebo_jun_sep_monsoon'])
print('leave-one-out:', h4['leave_one_out'])
print('subperiods:', h4['subperiods'])
same = all(h4[k] == R['weather']['h4_rain_price_link'][k] for k in ('beta_per_100mm_log', 'p_ols', 'p_robust_HC1', 'r2', 'n_seasons'))
print('matches outputs/results.json:', same)
""")
code("display(Image(str(kc.FIG / 'f10_rain_price.png'), width=460))")
md("""
**Verdict: weakly supported, suggestive.** About +20% bigger rise per 100 mm (p = 0.0361, robust p = 0.0025, R² = 0.153), and the wettest third of seasons rose much more than the driest third. But dropping any one of 2005, 2018 or 2019 takes p above 0.05, neither subperiod is significant alone (same sign in both), and it is an association, not causation.
""")

md("""
### 8.2 · Real-time use of the rain feed (1 November re-plan)
On 1 November the Sep+Oct rain is known. Nov–Dec is re-planned from the actual stock with (a) a price-only re-forecast and (b) the same forecast scaled by the H4 rain effect, with β estimated **only on earlier seasons** (no look-ahead). Read from `results.json` (`weather_replan_backtest`, run by `run_all.py`).
""")
code("""
rt = R['weather']['realtime_replan_nov_dec']
print({k: {kk: vv for kk, vv in v.items() if kk != 'by_season'} for k, v in rt.items()})
pd.DataFrame(rt['C']['by_season']).set_index('year')[['rain_sep_oct_mm', 'rain_multiplier', 'stock_entering_nov_t',
                                                       'price_only', 'price_plus_rain', 'price_plus_rain_nov_dec_sales']]
""")
md("""
**Value of the rain feed: ₹0/t** for both B and C. The cold-store plan enters November with at most U = 300 t, so the handling cap sends all of it to market in November in both arms; the chawl plan holds nothing. Handling capacity, not information, is the binding constraint (the U shadow price in 2024 is +₹6,526 per tonne of monthly capacity).
""")

md("""
### 8.3 · Value of loss-rate information (the sensor / digital-twin question)
Same April forecast; the store's **true** monthly loss δ varies over a grid. Three operators:
- **blind**: plans with the book δ (B 18.05%, C 1.83%) and never learns (`solve_lp` then `_execute_plan`);
- **sensor**: measures δ from May (weighing / IoT logs) and re-plans monthly on the April forecast (`_sensor_replan`);
- **calibrated**: δ known before April from an earlier logged season (`solve_lp` with the true δ, then `_execute_plan`).

Execution enforces the real stock and the handling cap U. Gain = Rs/t vs harvest sale, mean 2017–24, with our forecast and with perfect price foresight (which isolates the pure value of loss information). The grids take a few minutes to solve, so they are read from `results.json` (`value_of_loss_information`); the cell after the tables re-solves one season to show the functions.
""")
code("""
voi = R['value_of_loss_information']
cols = ['delta_true', 'blind', 'sensor', 'calibrated', 'voi_sensor', 'voi_calibrated', 'sensor_beats_blind_seasons', 'sensor_worse_seasons']
for src in ('with_forecast_prices', 'with_perfect_price_foresight'):
    for k in ('B', 'C'):
        g = pd.DataFrame(voi[src][k]['grid'])[cols]
        print(f"{src} | scenario {k} | book delta {voi[src][k]['book_delta']}")
        display(g.set_index('delta_true'))
""")
code("""
# One season re-solved live (2024, cold store C, true loss 8%/month, our April forecast) to show the three operators
q = kc.scenario_params(base, 'C'); act = kc.season_prices(series, 2024)
fc24 = kc.forecast(series[series.index <= pd.Period('2024-03', 'M')], 9, best) * 10
harvest = base.Q * act[0]
blind_plan = kc.solve_lp(fc24, q, return_duals=False)
_, _, e_blind = kc._execute_plan(blind_plan['x'], q, 0.08, act)
xs_sensor, _, e_sensor = kc._sensor_replan(fc24, q, 0.08, act)
cal_plan = kc.solve_lp(fc24, kc.LPParams(**{**asdict(q), 'delta': 0.08}), return_duals=False)
_, _, e_cal = kc._execute_plan(cal_plan['x'], q, 0.08, act)
live = pd.DataFrame({'blind': e_blind, 'sensor': e_sensor, 'calibrated': e_cal}).T
live['gain_vs_harvest_per_t'] = (live['net'] - harvest) / base.Q
# (results.json keeps only the 2017-24 means per grid point at full precision; by_season rounds delta_true to 1 decimal)
live.round(0)
""")
code("display(Image(str(kc.FIG / 'f11_value_of_information.png')))")
md("""
**Reading.**
- **Chawl:** with the book 18% the plan sells everything in April, so in-season sensing never starts (sensor = blind = 0). A chawl *measured* at 8%/month before the season earns ₹2,200/t with our forecast; above the 12.4% break-even storing loses money (14% → −₹508/t).
- **Cold store:** with our low-biased forecast (test bias −17.11%) sensing is mixed. With accurate prices sensing is never worse and is worth ₹545–746/t when the store degrades to 8–15%/month.
- **Lesson:** sensors pay only together with a good price forecast; their biggest use is calibrating the store's real loss rate before the season. A digital twin is the forecast + LP + measured δ.
""")

md("""
## 9 · Conclusions
- **H1 supported (as an association).** Months with heavier arrivals have lower prices: β ≈ −0.44 with month and year effects, p ≈ 0.01. It weakens with other arrival measures, and it disappears once last month's price is controlled for.
- **H2 not supported at ICAR's ventilated-storage loss.** At ≈18%/month the optimiser never stores, so the B plan equals harvest sale. A fixed calendar rule in a chawl loses money. Storage pays only below the break-even δ ≈ 12%/month.
- **H3 supported.** Low-loss (cold / IoT-monitored) storage beats harvest sale in 7 of 8 seasons: mean +₹4,546/t, Wilcoxon p = 0.008. Its extra capital cost pays back in about 1.5 seasons in the base case.
- **H4 (extension) weakly supported.** Heavier Sep+Oct rain (NASA POWER) goes with a bigger post-harvest price rise, but the link is fragile under leave-one-out. The real-time rain feed is worth ₹0/t because the handling cap binds; measuring the store's real loss rate is worth most before the season and with a good price forecast.

Limitations (quality grading, credit, price impact, forecast bias, H4 fragility) are listed in the report.
""")

nb["cells"] = C
nb["metadata"]["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
out = ROOT / "notebooks" / "KandaCode_Analysis.ipynb"
out.parent.mkdir(exist_ok=True)
nbf.write(nb, out)
print("wrote", out)
