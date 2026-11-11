# Methodology — Technical Appendix

Kanda Code · Industry 4.0 (MS4001) · IIT Madras BS

This appendix states every model exactly as `src/kandacode.py` computes it. Every result quoted here is in `docs/KEY_NUMBERS.md` and `outputs/results.json`. Prices are Rs/quintal in the data, Rs/tonne inside the LP (× 10), and Rs/kg in text (÷ 100).

**Pipeline:** data → EDA → H1 regression → price forecast → LP plan → backtest → sensitivity → Industry 4.0 value → Industry 4.0 extensions (satellite weather, value of sensor information; §9).

| Step | Course concept | Function |
|---|---|---|
| 1 Data | cleaning, validation | `clean_maharashtra`, `build_monthly`, `validate_against_lasalgaon`, `spotcheck_2020_2024` |
| 2 EDA | descriptive analytics, seasonality, volatility | `eda_stats`, `seasonal_profile` |
| 3 H1 | multiple regression: log-log, dummy variables | `h1_regressions`, `price_taker_check` |
| 4 Forecast | naive, moving average, exponential smoothing, Holt-Winters, regression | `forecast`, `evaluate_forecasts` |
| 5 LP | linear programming, shadow prices | `solve_lp`, `marginal_values` |
| 6 Backtest | inventory with perishability, out-of-sample evaluation | `backtest`, `rolling_plan`, `calendar_plan`, `paired_tests` |
| 7 Value | sensitivity analysis; IoT and smart storage; data-driven decisions | `sensitivity`, `industry40_value` |
| 8 Extensions | remote-sensing data; OLS regression (H4); LP scenario analysis and value of information | `load_power`, `weather_price_link`, `weather_replan_backtest`, `_execute_plan`, `_sensor_replan`, `value_of_loss_information` |

**Core methods vs supporting checks.** Every decision rests on syllabus methods: EDA, OLS regression with logs and dummies, moving average, exponential smoothing, Holt-Winters, regression forecasting, LP with shadow prices, and inventory with perishability. A few standard statistical checks only guard those results: the Durbin-Watson statistic and Newey-West (HAC) standard errors for the regression, paired t and Wilcoxon signed-rank tests for the backtest, a capital recovery factor for the payback, and, for the H4 extension, HC1 robust standard errors, a Spearman rank correlation and a leave-one-season-out refit. No verdict depends on them alone: H1 also passes on plain OLS (p = 0.0126), and H3 rests first on 7 of 8 seasons won and a mean gain of +Rs 4,546/t.

---

## 1. Data construction

### 1.1 Why a composite series

The proposal named Lasalgaon APMC as the case market. The planned first-week data check found **0 Lasalgaon rows** in the main dataset. We therefore build the **Maharashtra arrival-weighted modal price**, which is the price a Maharashtra seller faces on average, and validate it against official Lasalgaon data.

### 1.2 Cleaning and aggregation

Rules and counts are in `docs/DATA_DICTIONARY.md §2`. In short: keep Maharashtra (91,898 rows, 96 markets), drop 42 rows outside Rs 50–20,000/q and 58 relative outliers (outside 0.2–5× the same-day cross-market median), then collapse variety rows to one row per market-day (85,346 market-days). Collapsing matters because Agmarknet repeats a market's total arrivals on every variety row: in all 5,672 multi-row market-days the tonnage was identical, and summing would double-count 1,979,857 t.

For market-day *i* in month *m*, with modal price $P_i$ and arrivals $A_i$:

$$P_m = \frac{\sum_{i \in m} A_i P_i}{\sum_{i \in m} A_i}, \qquad A_m^{\text{md}} = \frac{\sum_{i \in m} A_i}{\#\{\text{market-days in } m\}}$$

$P_m$ is the analysis price (132 months, none missing). $A_m^{\text{md}}$, arrivals per market-day, is the H1 regressor. We use it because the number of reporting markets roughly doubles over the decade (34.0 a month in 2014, 63.8 in 2024), which would inflate raw totals.

### 1.3 Validation

| Check | Method | Result |
|---|---|---|
| vs NHRDF official Lasalgaon, 66 months 2014-01 to 2019-06 | Pearson r on levels and on monthly log changes; mean ratio; mean absolute % gap; sign agreement of month-on-month changes | r = 0.9896 (levels), 0.9254 (changes); ratio 0.973; gap 8.78%; direction agreement 87.7% |
| Season shape, 2014–18 | April → best later month rise, composite vs Lasalgaon | Same direction every year (e.g. 2017: +426.6% vs +602.0%) |
| vs 19 reported Lasalgaon prices, 2020–24 | Ratio of our monthly price to the reported price | r = 0.90; median gap −10.2%; ours lower in 84% of points |
| Robustness market | Nasik APMC alone, same pipeline | Nasik vs Lasalgaon r = 0.9724; composite vs Nasik 2023–24 r = 0.9805 |

The level gap (Lasalgaon is the premium market) scales rupee values; it barely changes *when* to sell, which is what the LP decides.

---

## 2. Exploratory analysis

- **Seasonal index** (EDA version, `seasonal_profile`): $I_{m,y} = P_{m,y} / \bar{P}_y$, the month's price divided by that calendar year's mean, averaged over 2014–24 for each month. April 0.553, May 0.577, November 1.546 (peak).
- **Volatility**: coefficient of variation (SD ÷ mean) overall 60.9% and within year 48.8% on average; month-on-month % change SD 32.5%; annualised volatility $\sigma(\Delta \ln P)\sqrt{12}$ = 101.5%; within-year max ÷ min averages 4.58×.
- **Season rise**: the November price beat April in 11 of 11 years (median rise 148.3%). The hindsight April → best-month rise has median 218.3%, an upper bound no seller could plan for.

---

## 3. H1 — do arrivals push prices down?

**Hypothesis.** H1: months with heavier arrivals have lower prices (β < 0).

**Specification (headline M3):** OLS on 132 months,

$$\ln P_m = \alpha + \beta \ln A_m^{\text{md}} + \sum_{k=2}^{12}\gamma_k\,\text{Month}_{k,m} + \sum_{y=2015}^{2024}\tau_y\,\text{Year}_{y,m} + \varepsilon_m$$

In a log-log model, β is the price flexibility with respect to arrivals: a 1% rise in arrivals goes with a β% change in price. Month dummies remove the harvest calendar, which drives both arrivals and prices. Year dummies remove the level of each year (crop size, inflation, export policy).

**Inference.** Durbin-Watson is low (0.52), so residuals are autocorrelated. We therefore report **Newey-West HAC** standard errors (max lag 3) alongside OLS. Decision rule, fixed in advance: H1 is supported if β < 0 and the two-sided HAC p < 0.05. We also report the one-sided p (= two-sided p ÷ 2), because H1 is directional.

| Model | Regressors | β | p (HAC) | adj R² | n |
|---|---|---|---|---|---|
| M1 | ln A | −0.7565 | 0.0082 | 0.126 | 132 |
| M2 | ln A + month | −0.6701 | 0.0025 | 0.358 | 132 |
| **M3 (headline)** | **ln A + month + year** | **−0.442** | **0.0131** (one-sided 0.0066) | **0.529** | **132** |
| M4 | ln A lagged 1 month + month + year | −0.1338 | 0.5220 | 0.504 | 131 |
| M5 | ln A + ln P lagged + month + year | −0.0144 | 0.9151 | 0.831 | 131 |
| D1 | daily ln A + month + year + day-of-week (HAC lag 30) | −0.0769 | 0.0129 | 0.55 | 3,972 |

M3 95% CI (OLS): −0.787 to −0.097. Reading: months with 10% heavier arrivals have prices about 4.4% lower, holding month and year fixed.

**Robustness and honesty checks.**
- Other arrival normalisations: per market reporting β = −0.2717 (p = 0.058); total arrivals β = −0.2471 (p = 0.079); excluding the April–May 2020 COVID lockdown β = −0.5717 (p = 0.0005).
- With last month's price included (M5), β vanishes (lagged-price coefficient 0.811): prices are highly persistent.
- Reverse direction: $\ln A_m$ on $\ln P_{m-1}$ + month + year gives −0.1548 (p = 0.011). Prices and arrivals are jointly determined.
- **Conclusion: H1 is supported as an association, not as a causal demand elasticity.** We do not use H1 for forecasting; it explains *why* the harvest price is low.

**Price-taker check** (`price_taker_check`). The LP treats the FPO's prices as given. Share of market = FPO sale ÷ mean Lasalgaon arrivals (NHRDF, 2014–19); implied price impact ≈ |β| × share.
- 1,000 t in April is 3.6% of 27,752 t, giving an impact of about 1.59%.
- 300 t in Oct–Nov is 1.79% of 16,800 t, giving an impact of about 0.79%.
- This is an order-of-magnitude check: β comes from the composite and is applied to one market.

---

## 4. Price forecasting

**Set-up.** Let $y_t$ be the monthly price and *T* the **end-of-March origin** of season *Y*. We forecast $\hat y_{T+h}$ for h = 1..9 (April to December) using only data up to *T* (expanding window). One forecast is made per season, because that is when the FPO decides how much to store (the rolling re-plan in §6 re-forecasts each month as a benchmark).

**Seasonal indices** (`_seasonal_indices`, classical ratio-to-moving-average). Let $\text{CMA}_t$ be the 2×12 centred moving average. Then

$$S_k = \frac{\overline{(y_t/\text{CMA}_t)}_{\,t \in \text{month } k}}{\tfrac{1}{12}\sum_{j=1}^{12}\overline{(y_t/\text{CMA}_t)}_{\,t \in \text{month } j}}$$

The indices are normalised to mean 1. The deseasonalised series is $d_t = y_t / S_{m(t)}$.

**The ten candidates** (all in the syllabus: naive benchmarks, moving average, exponential smoothing, Holt-Winters, regression):

| # | Model | Forecast equation |
|---|---|---|
| 1 | Naive | $\hat y_{T+h} = y_T$ |
| 2 | Seasonal naive | $\hat y_{T+h} = y_{T+h-12}$ |
| 3 | 12-month moving average | $\hat y_{T+h} = \tfrac{1}{12}\sum_{i=0}^{11} y_{T-i}$ |
| 4 | Seasonal index × moving average | $\hat y_{T+h} = \big(\tfrac{1}{12}\sum_{i=0}^{11} d_{T-i}\big)\, S_{m(T+h)}$ |
| 5 | Seasonal index × exponential smoothing | $\ell_t = \alpha \ln d_t + (1-\alpha)\ell_{t-1}$; $\hat y_{T+h} = e^{\ell_T} S_{m(T+h)}$; α estimated |
| 6 | Holt-Winters, damped | Additive damped trend + additive seasonality (period 12) on $\ln y_t$; $\hat y_{T+h} = \exp\big(\ell_T + (\phi + \dots + \phi^h) b_T + s_{T+h-12}\big)$ |
| **7** | **Regression: trend + month dummies (chosen)** | OLS $\ln y_t = a + b\,t + \sum_{k=2}^{12}\gamma_k D_{k,t} + e_t$; $\hat y_{T+h} = \exp\big(a + b(T+h) + \gamma_{m(T+h)}\big)$ |
| 8 | Regression: level + month effects | $\text{dev}_t = \ln y_t - \tfrac{1}{12}\sum_{i=1}^{12}\ln y_{t-i}$; $\mu_k$ = mean dev in month k; $\hat y_{T+h} = \exp\big(\tfrac{1}{12}\sum_{i=0}^{11}\ln y_{T-i} + \mu_{m(T+h)}\big)$ |
| 9 | 28-yr seasonal index × moving average | As 4, with $S_k$ estimated on NHRDF Lasalgaon 1996–2013 joined to the training series |
| 10 | 28-yr seasonal index × exponential smoothing | As 5, with the 28-year $S_k$ |

Fitting tools: statsmodels `SimpleExpSmoothing` and `ExponentialSmoothing` (estimated initial values), and NumPy least squares for the regressions. Working in logs makes seasonality multiplicative, so a November premium scales with the price level. The SES-type models fit α = 1.0 at every origin 2017–24: the latest month carries the whole level, close to a random walk.

**Error metrics** over all forecast months (actual $a$, forecast $p$):
- $\text{MAPE} = \tfrac{100}{n}\sum |p-a|/a$
- $\text{bias} = \tfrac{100}{n}\sum (p-a)/a$
- RMSE and MAE in Rs/q
- direction hit rate: the share of month-to-month moves whose sign the forecast got right, counted **within** each season only.

**Selection rule (fixed before looking at the test seasons):** choose the lowest Apr–Dec MAPE on the **validation seasons 2019–2022**, then score that one model on the **test seasons 2023–2024**. A rolling 1-step-ahead MAPE over the 24 test months is reported as a secondary check.

| Model | Validation MAPE | Test MAPE | Test bias | Direction hits |
|---|---|---|---|---|
| **Regression: trend + month dummies** | **36.94%** | **29.5%** | **−17.11%** | **93.75%** |
| Seasonal naive | 42.06% | 34.84% | −25.89% | 87.5% |
| Naive | 44.44% | 45.62% | −41.37% | 0.0% |
| 28-yr seasonal index × MA | 47.35% | 29.49% | −27.11% | 81.25% |
| Regression: level + month effects | 48.6% | 30.45% | −29.11% | 87.5% |
| Seasonal index × MA | 50.68% | 29.32% | −28.21% | 93.75% |
| Holt-Winters (damped) | 57.36% | 23.85% | −23.21% | 93.75% |
| 28-yr seasonal index × SES | 58.02% | 19.55% | −18.17% | 81.25% |
| Seasonal index × SES | 58.23% | 22.45% | −22.2% | 93.75% |
| 12-month moving average | 62.27% | 43.87% | −17.93% | 0.0% |

**Why this model, beyond accuracy.**
1. It won under the pre-registered rule on seasons it was not scored on.
2. It is transparent: a trend plus twelve month effects, the two features the EDA showed.
3. It reproduces the seasonal **shape** that drives the LP: 93.75% direction hits on the test seasons.

The best *test* MAPE belongs to the 28-yr SI × SES model (19.55%). Picking it after seeing the test seasons would be selection on test data, so we report it for reference only. The same rule applies to decision value: some candidates earn more in the backtest (28-yr SI × MA: Rs 6,182/t in scenario C), and we do not switch to them post hoc.

**Known weakness.** Forecasts are biased low (−17.11% on test). One contributor: exponentiating a log-scale fit estimates the median, not the mean, and we apply no retransformation correction. The LP's decision depends mostly on relative month-to-month prices, not on the level.

---

## 5. Linear programme — the sell-or-store plan

**Decision-maker:** an FPO holding Q tonnes of rabi onion in April. Months t = 1..9 = April..December.

**Decision variables:** $x_t \ge 0$, tonnes sold in month t; $s_t \ge 0$, tonnes in storage at the end of month t.

**Objective** (forecast prices $\hat p_t$ in Rs/t):

$$\max Z = \sum_{t=1}^{9} \hat p_t\, x_t \;-\; h \sum_{t=1}^{9} s_t$$

**Constraints:**

| # | Constraint | Equation | Meaning |
|---|---|---|---|
| 1 | Harvest balance | $s_1 = Q - x_1$ | What is not sold in April goes into store |
| 2 | Stock balance with perishability | $s_t = (1-\delta)\, s_{t-1} - x_t,\; t = 2..9$ | A share δ of last month's stock is lost, then this month's sale leaves |
| 3 | Storage capacity | $s_t \le C,\; t = 1..9$ | Stock never exceeds capacity |
| 4 | Loan-repayment sale | $x_1 \ge L$ | Sell at least L tonnes in April to repay crop loans |
| 5 | Handling cap | $x_t \le U,\; t = 2..9$ | Grading, bagging and trucking capacity, May–Dec. April's harvest sale goes field-run to traders, so it is uncapped |
| 6 | Clear by December | $s_9 = 0$ | The season ends with an empty store |
| 7 | Non-negativity | $x_t, s_t \ge 0$ | |

Constraints 1 and 2 are the inventory balance with perishability. The loss is geometric, so the LP stays linear. Tonnes lost to rot = $Q - \sum_t x_t$.

**Scenarios** (same LP, different parameters):

| Scenario | C (t) | δ (per month) | h (Rs/t/month) | L (t) | Effect |
|---|---|---|---|---|---|
| A — no storage | 0 | 0 | 0 | Q = 1,000 | Forces $x_1 = Q$: today's practice |
| B — ventilated kanda chawl | 700 | 0.18046 | 250 | 250 | |
| C — cold / IoT-monitored | 700 | 0.01835 | 700 | 250 | |

**Delta conversion.** ICAR reports the loss over 120 days (≈ 4 months), $L_{120}$. With a constant monthly loss rate, $(1-\delta)^4 = 1 - L_{120}$, so

$$\delta = 1 - (1 - L_{120})^{1/4}$$

- B: $1 - (1 - 0.5489)^{1/4} = 0.18046$ (18.05% a month).
- C: $1 - (1 - 0.0714)^{1/4} = 0.01835$ (1.83% a month).

**Solvers.** PuLP 2.9.0 (CBC) solves the LP. SciPy `linprog` (HiGHS) solves the identical standard-form model for the 2024 decision-time plans, to cross-check the objective and to read dual values; the largest difference is Rs 0.0081 (scenario C). The backtest and sensitivity runs use PuLP alone. Excel Solver (Simplex LP) holds the same model, pre-configured in `excel/KandaCode_LP_Model.xlsx`; an automated run reproduced the Python objective exactly for 2023 scenarios A and B (corner solutions), and 2024 / C is re-solved by hand as a review task.

**Shadow prices — verified, not just read.** At a degenerate vertex a solver's dual is only one of several valid values. So for each right-hand side (C, L, Q, U) we re-solve with it moved +1 t and −1 t and report both changes in Z. In scenario C, 2024 forecast, the two sides agree:

| Resource | +1 unit | Binding? |
|---|---|---|
| Storage capacity C | +Rs 4,028 | Yes, in April ($s_1$ = 700) |
| Handling cap U | +Rs 6,526 per t/month | Yes, in Oct and Nov (HiGHS duals Rs 3,050.84 and 3,474.79; raising U by 1 t lifts both months, and the two sum to the re-solve value) |
| Harvest Q | +Rs 8,474 (= April forecast price, the marginal tonne is sold in April) | – |
| Loan sale L | Rs 0 | No: capacity already forces $x_1 \ge Q - C$ = 300 > 250 |

Scenario A has no shadow prices because C = 0 and L = Q fix every decision. L = 250 ≠ Q − C = 300 deliberately, so the capacity and loan constraints do not bind at the same point, which would make the duals degenerate.

**2024 plan** (forecast made end-March 2024):
- A and B: sell all 1,000 t in April (Z = Rs 84.7 lakh). At 18% a month, rot beats the forecast price rise, so the optimiser refuses to store.
- C: x = [300, 0, 0, 0, 0, 21.2, 300, 300, 0], i.e. 300 t in April, then sales in Sep, Oct and Nov. Z = Rs 132.5 lakh at forecast prices; 78.8 t lost to rot.

---

## 6. Backtest — plans judged on prices the model never saw

For each season Y = 2017..2024: forecast from end-March Y, decide, then **evaluate at actual prices** $a_t$:

$$\text{net} = \sum_t a_t x_t - h\sum_t s_t, \qquad \text{gain vs harvest} = \frac{\text{net} - Q\,a_1}{Q} \;\;(\text{Rs per tonne harvested})$$

Because δ is applied deterministically, the stock path of every plan is feasible under actual prices; only the revenue changes.

| Strategy | Rule | Role |
|---|---|---|
| `forecast_plan` | Solve the LP once at end-March with $\hat p$; follow it | **The model** |
| `rolling_replan` | At the start of each month t, re-forecast the remaining months from data up to month t−1, re-solve from the current stock, implement only this month's sale; December clears the store | Does updating help? |
| `calendar_rule_exante` | Sell $x_1 = \max(L, Q-C)$ = 300 t in April, then up to U a month in the 3 months (May–Dec) with the highest seasonal index known at the origin (NHRDF 1996–2013 + training data); clear the rest in December. Picked Oct, Nov, Sep every year | Simple rule a farmer could follow |
| `calendar_rule_hindsight_OctNov` | Same, selling in Oct and Nov, months chosen knowing the full 2014–24 profile | Labelled hindsight; not a fair competitor |
| `perfect_foresight` | Solve the LP with actual prices | Ceiling; not achievable |

**Results, 2017–24 mean gain vs harvest sale (Rs/t harvested):**

| Scenario | Strategy | Mean | Median | Min | Max | Wins / 8 |
|---|---|---|---|---|---|---|
| C | forecast plan | 4,546 | 3,840 | −1,181 | 10,733 | 7 |
| C | rolling re-plan | 4,511 | 3,826 | −1,181 | 10,733 | 7 |
| C | calendar rule (ex-ante) | 5,508 | 6,336 | −1,324 | 10,734 | 7 |
| C | calendar rule (hindsight Oct–Nov) | 7,110 | 8,571 | −1,507 | 13,190 | 7 |
| C | perfect foresight | 8,558 | 9,828 | 532 | 19,439 | 8 |
| B | forecast plan | 0 | 0 | 0 | 0 | 0 |
| B | calendar rule (ex-ante) | −1,149 | −1,165 | −3,381 | 1,764 | 2 (6 losses) |
| B | perfect foresight | 791 | 675 | 0 | 1,764 | 5 |

Pre-registered test seasons 2023–24, means: C forecast plan Rs 9,980/t; C perfect foresight Rs 10,981/t; B forecast plan Rs 0.

**Paired tests** (`paired_tests`, n = 8 seasons). For each season, $d_Y = \text{net}_{C,Y} - \text{net}_{A,Y}$. We run a one-sided paired t-test ($H_a$: mean d > 0) and a one-sided Wilcoxon signed-rank test, which does not assume normality and suits n = 8.
- C vs A: mean +4,546, paired t p = 0.0062, Wilcoxon p = 0.0078.
- H3, C vs B: identical numbers, because the B plan never stores and therefore equals harvest sale.
- H2, B vs A: not testable; all 8 differences are 0.
- With n = 2 test seasons, results are reported descriptively only. Tests run only when n ≥ 5.

**Hypothesis verdicts.**
- **H2 (an optimised plan beats selling everything at harvest, even with ventilated-storage losses): not supported** at ICAR's 18%-a-month loss. The optimiser correctly refuses to store, and a naive chawl calendar rule loses money in 6 of 8 seasons.
- **H3 (low-loss storage raises net revenue per tonne by a material margin over ventilated storage): supported.** +Rs 4,546/t (Rs 4.55/kg), 7 of 8 seasons; one-sided paired t p = 0.0062, Wilcoxon p = 0.0078.

**Nasik robustness.** Same pipeline and model on Nasik APMC prices (complete from 2016-01), 2023–24. Scenario C gains +Rs 11,510/t (2023) and +Rs 13,377/t (2024); B again never stores.

---

## 7. Sensitivity analysis

Each value is the mean realised gain vs harvest sale over 2017–24 (forecast plan evaluated at actual prices) as **one parameter** moves, the others held at base (`sensitivity`).

| Parameter | Grid → mean gain (Rs/t) |
|---|---|
| δ_B | 0.06 → 3,172 · 0.10 → 890 · 0.14 → −508 · 0.18 → 0 · 0.22 → 0 · 0.26 → 0 |
| δ_C | 0.005 → 5,514 · 0.018 → 4,568 · 0.030 → 3,444 · 0.050 → 2,389 · 0.080 → 374 |
| h_B | 0 → −734 · 125 → −238 · 250 → 0 · 500 → 0 · 750 → 0 · 1,000 → 0 |
| h_C | 0 → 7,971 · 350 → 6,301 · 700 → 4,546 · 1,050 → 3,041 · 1,400 → 1,069 · 2,000 → 0 |
| C (scenario C) | 300 → 1,770 · 500 → 3,161 · 700 → 4,546 · 900 → 4,797 · 1,000 → 4,797 |
| L (scenario C) | 100 → 4,546 · 300 → 4,546 · 500 → 3,161 · 700 → 1,770 |
| U (scenario C) | 150 → 4,132 · 300 → 4,546 · 500 → 4,314 · 1,000 (no cap) → 4,131 |
| B-type storage at any δ, h | full 6 × 5 grid of δ ∈ {0.02 … 0.22} × h ∈ {0 … 1,000} in `results.json → sensitivity_2017_2024.grid_delta_h` and figure f7 |

- **Break-even monthly loss** for B-type storage at h = Rs 250: bisection on [0, 0.6], 30 steps, for the δ at which the mean gain falls to Rs 1/t. Result: **δ ≈ 0.1243 (12.4%/month)**. Ventilated storage pays only if its loss is cut below about 12% a month. ICAR's chawl rate is 18%.
- **Mixed signs at mid losses** (δ_B = 0.14: −508; h_B = 0: −734). When storage is marginal, the LP stores on the strength of a forecast rise that sometimes does not arrive. Low-loss storage stays positive even at δ_C = 8%/month (+374).
- **U = 300** gives the highest mean in its grid, so we disclose it. The conclusion (C gains, B does not) holds at every U, including no cap (+4,131). A cap spreads sales over several months, which hedges forecast error.

---

## 8. Industry 4.0 value of low-loss storage

$h$ is treated as the **operating** cost of an owned facility (labour, power, sensors, monitoring). Capital is handled separately, so it is not double-counted.

- **Uplift per tonne harvested:** $\bar u = \overline{(\text{net}_C - \text{net}_B)}_{2017-24}$ = **Rs 4,546/t** (Rs 4.55/kg).
- **Per tonne of capacity per season:** $\bar u\, Q / C$ = 4,546 × 1,000 / 700 = **Rs 6,495**.
- **Extra capital:** $\Delta K = K_C - K_B$ = 16,667 − 7,000 = **Rs 9,667 per t of capacity**.
  - $K_B$: MIDH, Rs 1.75 lakh per 25 t.
  - $K_C$: ICAR multi-module, Rs 1.5 lakh per 9 t.
- **Simple payback:** ΔK ÷ 6,495 = **1.49 seasons**.
- **Capital recovery factor** (10 years at 10%): $\text{CRF} = \dfrac{r(1+r)^n}{(1+r)^n - 1} = 0.1627$.
  - Annualised extra capital: ΔK × CRF = Rs 1,573/t.
  - **Net annual benefit:** 6,495 − 1,573 ≈ **Rs 4,921 per t of capacity** (computed from unrounded inputs).
- **Capex range:**

| Capex $K_C$ (Rs/t) | Source | Payback (seasons) | Net annual benefit (Rs/t) |
|---|---|---|---|
| 8,000 | MIDH cold storage type 1 | 0.15 | 6,332 |
| 16,667 | ICAR multi-module (base) | 1.49 | 4,921 |
| 50,000 | small modular cold room (assumed upper bound) | 6.62 | −503 |

- **For a 1,000 t FPO:** about **Rs 45.5 lakh a year**. The 2023–24 test seasons alone give Rs 9,980/t.
- **Season by season** (Rs/t): 2017 2,929 · 2018 −1,181 · 2019 3,069 · 2020 4,865 · 2021 4,610 · 2022 2,118 · 2023 10,733 · 2024 9,226.

---

## 9. Industry 4.0 extensions: satellite weather (H4) and the value of sensor information

Added on 10 Nov 2026, **after the approved proposal** (deviation 14 in §12). H1–H3 and every number in §1–§8 are unchanged. The code is section 8 of `src/kandacode.py`, run by step 8 of `src/run_all.py`; results are in `results.json → weather` and `results.json → value_of_loss_information`; figures f10 and f11. Background and ownership: `docs/EXTENSION_BRIEF.md`.

### 9.1 Satellite weather data — NASA POWER (`load_power`)

- **Source:** NASA Langley Research Center, POWER (Prediction Of Worldwide Energy Resources), monthly point API v2, downloaded by `src/fetch_nasa_power.py`. Point 20.15°N 74.23°E (Lasalgaon APMC, Niphad taluka, Nashik), January 1996 to December 2024. Free, no key or registration.
- **Parameters:** T2M (2 m air temperature, °C), RH2M (2 m relative humidity, %), PRECTOTCORR (bias-corrected precipitation, mm/day). These are satellite-derived and reanalysis estimates (MERRA-2 for temperature and humidity, IMERG-corrected for rain) on a ~0.5° grid, not a rain-gauge reading.
- **Processing:** the API's annual rows (month code 13) are dropped; `load_power` adds the monthly total `rain_mm = rain_mm_per_day × days in the month`.
- **Why not ISRO (Bhuvan, MOSDAC):** they need registration and add nothing for a single point at this scale. **Why not the main dataset's weather columns:** they start in 2014, and H4 needs the 1996–2013 seasons too.
- **Climate at Lasalgaon, 2014–24** (`climatology_2014_2024`): RH is highest exactly when rabi onion sits in a chawl, Jul 82.4%, Aug 84.4%, Sep 85.0%, against 29.4% in April. This is the physical reason ventilated storage rots fast (ICAR: 54.89% in 120 days, 18.05%/month).

### 9.2 H4 — does late-monsoon rain raise the post-harvest price rise? (`weather_price_link`)

One season is one observation, y = 1996..2024 (n = 29):

$$r_y = \ln\frac{\tfrac13\,(P_{\text{Oct},y}+P_{\text{Nov},y}+P_{\text{Dec},y})}{P_{\text{Apr},y}}, \qquad R_y = \text{rain}_{\text{Sep},y} + \text{rain}_{\text{Oct},y}\ \text{(mm)}$$

$$r_y = a + b\,R_y + \varepsilon_y \quad \text{(OLS)}$$

- **Prices:** NHRDF Lasalgaon for 1996–2013, our Maharashtra composite for 2014–24. $r_y$ is a ratio inside one season, so the level gap between the two series cancels.
- **Why Sep–Oct:** the window was chosen on crop-calendar (agronomic) grounds, not by searching over windows: it is when the kharif crop is maturing and stored rabi onion is still in the chawl. H4 was added after the approved proposal, so it is not a pre-registered test; its fragility is reported below.
- **Mechanism:** Sep–Oct rain damages the kharif crop in the field and raises rot in stored rabi onion, so the autumn supply is thinner. The 2019 and 2020 autumn spikes followed heavy Sep–Oct rain.
- **Result:** $b$ = 0.181 log points per 100 mm. $e^{0.181}$ = 1.198, so each extra 100 mm goes with an Oct–Dec ÷ April price ratio about **20% higher**. OLS p = 0.0361; robust (HC1) p = 0.0025; R² = 0.153; OLS 95% CI [0.013, 0.349] per 100 mm. Spearman ρ = 0.46 (p = 0.012). Mean Sep+Oct rain 237 mm.
- **Terciles:** seasons at or above the upper tercile of rain (n = 10, mean 338 mm) have a median rise of 208%; seasons at or below the lower tercile (n = 10, mean 137 mm) 123%.
- **Placebo:** the whole Jun–Sep monsoon gives β = 0.073 per 100 mm, p = 0.1117. Weaker, consistent with *late* rain mattering more than the monsoon as a whole.
- **Fragility:**
  - Leave-one-season-out: β stays between 0.145 and 0.206 per 100 mm, but p rises above 0.05 when 2005, 2018 or 2019 is dropped (worst p = 0.0952, dropping 2019).
  - Subperiods: 1996–2013 β = 0.134 (p = 0.2143, n = 18); 2014–24 β = 0.273 (p = 0.1112, n = 11). Same sign in both, neither significant alone.
- **Verdict: weakly supported, suggestive, not firm.** It is an association across 29 seasons, not causation, and one season can move it across p = 0.05.

### 9.3 Real-time use of the rain feed (`weather_replan_backtest`)

On 1 November the Sep+Oct rain is already known (NASA POWER publishes within days). For each season 2017–24 and scenarios B and C:

1. Solve the April LP on the April forecast and follow it April–October (identical to `forecast_plan`).
2. Stock entering November = $(1-\delta)\,s_{\text{Oct}}$.
3. **Price-only arm:** re-forecast Nov and Dec with the chosen model from data up to end-October, and re-solve a 2-month LP (Q = stock, L = 0, handling cap U, clear by December).
4. **Price + rain arm:** the same forecast multiplied by $m_y = \exp\big(\hat b_{<y}\,(R_y - \bar R_{<y})\big)$, where $\hat b_{<y}$ and $\bar R_{<y}$ come from the H4 regression on seasons **before** y only, so there is no look-ahead. $m_y$ ranges from 0.796 (2018, dry) to 1.332 (2020, wet).
5. Evaluate both arms at actual prices; value of the feed = mean difference in gain vs harvest sale.

**Result: Rs 0/t for C and Rs 0/t for B**, in every season. The price-only arm reproduces the C forecast plan exactly (mean +Rs 4,546/t). Why:
- B holds nothing by November.
- C enters November with 0 t (2017–19) or exactly U = 300 t (2020–24). With at most U tonnes left, both arms sell the whole stock in November. The rain multiplier also scales the November and December forecasts by the same factor, so it barely changes which month is better.

**Reading.** Handling and logistics capacity, not information, is the binding constraint late in the season. This matches the verified shadow price of U: +Rs 6,526 per tonne of monthly handling capacity in the 2024 plan (§5). It is a finding, not a failure.

### 9.4 Value of loss-rate information — the sensor / digital-twin question (`value_of_loss_information`)

"Smart storage" in §5–§8 is one assumed loss rate. Here the store's **true** monthly loss δ* varies over a grid while the plan may or may not know it. Three operators face the **same April price forecast** $\hat p$, so only loss information differs:

| Operator | Plans with | Learns δ*? | Code |
|---|---|---|---|
| **blind** | the book rate δ₀ (B 18.05%, C 1.83%) | never | `solve_lp` once, then `_execute_plan` |
| **sensor** | δ₀ in April (nothing measured yet), δ* from May | monthly from May (weighing / IoT logs) | `_sensor_replan` |
| **calibrated** | δ* from April | before the season (logged in an earlier season) | `solve_lp` with δ*, then `_execute_plan` |

- **Execution in the real store** (`_execute_plan`): start with Q; each month sell the planned $x_t$, but never more than the stock actually present and, in May–December, never more than U; in December sell what can be handled (at most U) and count anything beyond as unsold; carry $(1-\delta^*)\,s_t$ into the next month; money at actual prices minus $h\sum_t s_t$.
- **Sensor re-plan** (`_sensor_replan`): at the start of each month t, re-solve the LP for the remaining months with Q = the actual stock, the April forecast for those months (prices are **not** re-forecast), L only in April, and δ₀ in April then δ* from May. Only month t's sale is implemented, with the same caps.
- **Metric:** gain = (net − Q × actual April price) ÷ Q, Rs per tonne harvested, mean over 2017–24. Value of information (VoI) = sensor − blind, and calibrated − blind.
- **Grids of δ*:** B {4, 6, 8, 10, 12, 14, 18.05, 22}%/month; C {0.5, 1.83, 3, 5, 8, 10, 12, 15}%/month.
- **Run twice:** with our forecast, and with perfect price foresight ($\hat p$ = actual prices). Perfect foresight is not a strategy; it isolates the pure value of loss information.

**Results** (mean gain vs harvest sale, Rs/t, 2017–24; each cell is blind / sensor / calibrated):

| True δ*, chawl B | B, our forecast | B, perfect prices | True δ*, cold store C | C, our forecast | C, perfect prices |
|---|---|---|---|---|---|
| 4% | 0 / 0 / 4,691 | 4,701 / 6,471 / 8,374 | 0.5% | 5,404 / 5,514 / 5,514 | 9,110 / 9,624 / 9,624 |
| 6% | 0 / 0 / 3,172 | 3,788 / 5,323 / 6,738 | 1.83% (book) | 4,549 / 4,549 / 4,549 | 8,560 / 8,562 / 8,562 |
| 8% | 0 / 0 / 2,200 | 3,008 / 4,300 / 5,306 | 3% | 3,712 / 3,444 / 3,444 | 7,384 / 7,551 / 7,551 |
| 10% | 0 / 0 / 890 | 2,362 / 3,380 / 4,030 | 5% | 2,435 / 2,389 / 2,389 | 5,593 / 5,964 / 5,965 |
| 12% | 0 / 0 / 191 | 1,834 / 2,571 / 2,958 | 8% | 828 / 407 / 374 | 3,377 / 3,922 / 4,000 |
| 14% | 0 / 0 / −508 | 1,406 / 1,868 / 2,054 | 10% | −64 / −621 / −791 | 2,173 / 2,782 / 2,921 |
| 18.05% (book) | 0 / 0 / 0 | 790 / 790 / 790 | 12% | −829 / −841 / −616 | 1,155 / 1,785 / 1,977 |
| 22% | 0 / 0 / 0 | 106 / 144 / 231 | 15% | −1,849 / −1,234 / 0 | −194 / 552 / 893 |

The calibrated column with our forecast equals the one-at-a-time δ sensitivity of §7 where the grids overlap (e.g. B 6% 3,172, 14% −508; C 0.5% 5,514, 8% 374), a consistency check.

**Reading.**
- **Chawl.** With the book 18% the April plan sells everything in April, so there is no stock left to measure: in-season sensing never starts (sensor = blind = 0 at every δ*). Measuring the store *before* the season is what turns storage on: a chawl measured at 8%/month earns Rs 2,200/t with our forecast (Rs 2,298/t more than blind with perfect prices). Above the 12.4% break-even (§7) storing loses money (14%: −Rs 508/t), so the measurement mainly tells a good chawl from a bad one.
- **Cold store, our forecast: mixed.** The forecast is biased low (test bias −17.11%), which on its own makes the plan sell too early. A blind store that ignores a higher real loss holds too long, so its two errors partly cancel; correcting only the loss error can make things worse (8%: sensor 407 vs blind 828).
- **Cold store, accurate prices:** sensing is never worse than blind (no season worse at any δ*) and is worth Rs 545–746/t when the store degrades to 8–15%/month, and Rs 514/t if it runs better than book (0.5%).
- **Managerial reading.** Sensors pay only together with a good price forecast. Their biggest use is calibrating a store's real loss rate before the season. A digital twin here is forecast + LP + measured δ.

---

## 10. Parameter table

| Symbol | Value | Meaning | Source |
|---|---|---|---|
| Q | 1,000 t | Harvest held by the FPO in April | Assumption (FPO scale); price-taker check above |
| C | 700 t | Storage capacity (B and C) | Assumption; varied 300–1,000 |
| L | 250 t | Minimum April sale (crop-loan repayment) | Assumption; varied 100–700 |
| U | 300 t/month | Handling cap, May–Dec | Assumption (grading, bagging, trucking); varied 150–1,000 |
| T | 9 | Months, April–December | Proposal |
| δ_B | 0.18046 /month | Ventilated chawl loss | ICAR: 54.89% over 120 days |
| δ_C | 0.01835 /month | Cold-store loss | ICAR-DOGR cold storage: 7.14% over 120 days |
| h_B | Rs 250 /t/month | Chawl operating cost | Stated assumption. Khapte et al. (2023) give about Rs 167/q per season for an own structure and Rs 140/q for Nashik rent, i.e. Rs 1,400–1,670/t per season; our Rs 250 over at most 8 storage months (s₉ = 0) is up to Rs 2,000/t a season, slightly conservative; varied 0–1,000 |
| h_C | Rs 700 /t/month | Cold / IoT storage operating cost | Stated assumption; varied 0–2,000 |
| K_B | Rs 7,000 /t capacity | Chawl capital cost | MIDH 2023-24: Rs 1.75 lakh per 25 MT |
| K_C | Rs 16,667 /t capacity | Low-loss storage capital cost | ICAR multi-module: Rs 1.5 lakh per 9 t; range 8,000 (MIDH cold storage type 1) to 50,000 |
| r, n | 10%, 10 years | Discount rate and asset life for the CRF | Assumption |
| Price band | Rs 50–20,000/q | Cleaning plausibility band | Assumption (Rs 0.5–200/kg) |
| Outlier band | 0.2–5× same-day median | Relative outlier rule | Assumption |
| HAC lags | 3 (monthly), 30 (daily) | Newey-West max lags | Assumption |
| Weather point | 20.15°N 74.23°E, 1996–2024 | NASA POWER grid point for Lasalgaon (§9.1) | NASA POWER monthly point API |
| H4 window | Sep + Oct rain; Oct–Dec mean vs April price; n = 29 seasons | H4 regressor and outcome (§9.2) | Window chosen on crop-calendar (agronomic) grounds, not by searching; added after the proposal; placebo Jun–Sep |
| δ* grid, B | 4, 6, 8, 10, 12, 14, 18.05, 22 %/month | True chawl loss in the value-of-information test (§9.4) | Brackets the 12.4% break-even and the ICAR rate |
| δ* grid, C | 0.5, 1.83, 3, 5, 8, 10, 12, 15 %/month | True cold-store loss in the value-of-information test (§9.4) | From better than book to a badly degraded store |

---

## 11. Leakage controls

1. **Forecast information set.** Each season's forecast uses only data up to end-March of that year (expanding window). The rolling re-plan uses only data up to the month before each decision.
2. **Model selection on validation, not test.** Chosen on 2019–22, then scored once on 2023–24. Better-scoring test models are reported, not adopted.
3. **Long seasonal history is strictly earlier.** NHRDF 1996–2013 precedes our series and every forecast origin. The 2014–19 NHRDF overlap is used only for validation and, through its arrivals, for the price-taker check; it never enters a forecast.
4. **Ex-ante calendar rule** uses seasonal indices available at each origin. The Oct–Nov rule is labelled *hindsight* and is never used as evidence.
5. **Evaluation at actual prices** with plans fixed in advance. Perfect foresight is shown only as a ceiling.
6. **Cleaning rules use no future prices.** The relative-outlier rule compares a record with the same day's cross-market median.
7. **Disclosed residual overlap.** The 8-season backtest (2017–24) includes the validation seasons 2019–22 that chose the forecast model. Only 2023–24 is fully clean on model choice: C +Rs 9,980/t there.
8. **Parameters are not tuned on outcomes.** δ comes from ICAR and capex from published norms. Q, C, L, U and h are stated assumptions with sensitivity grids. Where a base value happens to score best (U = 300), we say so.
9. **Real-time rain feed has no look-ahead.** In `weather_replan_backtest` the rain multiplier for season y uses β and mean Sep+Oct rain estimated only on seasons before y; Sep+Oct rain itself is known by 1 November.
10. **H4 itself is an in-sample association** over all 29 seasons, reported with its leave-one-out and subperiod fragility. It is not used as a forecast input anywhere except, refitted on earlier seasons only, in the real-time test.
11. **Value-of-information operators share one April forecast.** Blind, sensor and calibrated differ only in what they know about the loss rate; the perfect-price run only isolates that value and is never a strategy.

---

## 12. Deviations from the approved proposal

| # | Proposal said | We did | Why |
|---|---|---|---|
| 1 | Forecast Lasalgaon prices from the main dataset | Maharashtra arrival-weighted composite, validated against NHRDF Lasalgaon (r = 0.9896), 19 reported 2020–24 prices (r = 0.90) and Nasik APMC | Lasalgaon has 0 rows in the main dataset, found in the planned first-week check |
| 2 | Spot-check against Agmarknet | Checked against official Lasalgaon series instead: NHRDF monthly and MSAMB weekly reports | With Lasalgaon missing, the meaningful test is against Lasalgaon's own published prices |
| 3 | Aggregate daily prices and arrivals | Collapse variety rows to one per market-day before aggregating | Agmarknet repeats each market's arrivals on every variety row; summing would double-count 1,979,857 t |
| 4 | H1 on daily arrivals | Headline on monthly data (132 months) with month and year dummies; daily model D1 kept as a sign check | The forecast and LP are monthly; daily residuals are extremely autocorrelated (DW 0.1) |
| 5 | Train 2014–2022, test 2023–24, choose by MAPE | Choose by MAPE on validation seasons 2019–22 (expanding window, March origin), then test on 2023–24 | Choosing on the test set would leak; MAPE is kept as the criterion |
| 6 | MA, exponential smoothing and regression candidates | Added naive benchmarks, Holt-Winters and 28-year seasonal indices (10 candidates) | Benchmarks show whether a model adds value; all are in the syllabus |
| 7 | Excel Solver, cross-checked in PuLP | PuLP primary, SciPy HiGHS for duals and cross-check, Excel Solver pre-configured | Scripting runs 88 backtest plans (8 seasons × 3 scenarios × up to 5 strategies) plus the sensitivity grids reproducibly |
| 8 | Constraints: balance, capacity, loan sale, clear by December | Added handling cap U = 300 t/month (May–Dec); set L = 250 t | Real logistics limit; avoids a degenerate vertex where loan and capacity bind together; no-cap case reported |
| 9 | Shadow prices (implied) | Reported only after ±1 t re-solve verification; none for scenario A | Solver duals can be non-unique at degenerate vertices |
| 10 | Backtest 2023 and 2024 vs sell-at-harvest | Also 2017–24 (8 seasons), rolling re-plan, calendar rules and perfect foresight; paired t and Wilcoxon tests | Two seasons cannot support a test; benchmarks show where the value comes from |
| 11 | Value of low-loss storage in Rs/t | Also capital cost, payback and CRF-annualised net benefit, with a capex range | An investor needs the capital case, not only operating gain |
| 12 | Price-taker assumption, to be checked | Checked: 3.6% of Lasalgaon April arrivals, implied impact about 1.6% | Done as planned |
| 13 | Rerun on potato "if time allows" | Not done | Time; the model needs only a price series and a loss rate, so it transfers |
| 14 | Not in the proposal | **Extension (10 Nov 2026):** NASA POWER satellite weather; new hypothesis H4 (late rain vs post-harvest price rise); a 1 November rain re-plan; value of loss-rate information (blind / sensor / calibrated) | Deepens the Industry 4.0 layer, where smart storage was one assumed loss rate; uses only syllabus methods (OLS as in H1; LP scenario and sensitivity analysis on the existing backtest). H1–H3 results unchanged |

---

## 13. Limitations

- **Composite, not Lasalgaon.** The series is about 10% below Lasalgaon in level. Arrival weights are Ahmednagar 38.5%, Pune 18.4% and Sholapur 15.2%.
- **H1 is an association.** It is sensitive to normalisation and disappears with lagged price.
- **Forecast error is large.** Test MAPE 29.5%, bias −17.11%. In cold storage the ex-ante Sep–Nov calendar rule does as well or better: mean +Rs 5,508/t vs +Rs 4,546/t over 2017–24, though the LP plan leads in the 2023–24 test seasons (+Rs 9,980/t vs +Rs 9,117/t). The LP's value is that it:
  - adapts to storage physics (it refuses chawl storage, where the same calendar rule loses Rs 1,149/t),
  - gives verified shadow prices,
  - supports sensitivity analysis.
- **Constant geometric loss rates** come from 120-day trials, extrapolated to 8 months; monsoon sprouting and rot would raise them. The gain stays positive at δ_C = 8%/month.
- **Deterministic LP.** It plans on a point forecast; risk aversion and price uncertainty enter only through the rolling re-plan and the sensitivity grid.
- **Not modelled:**
  - quality grading;
  - price impact;
  - credit and cash flow beyond L;
  - export-policy shocks (bans in 2019, 2020 and 2023), which are in the prices but not forecast.
- **Small sample.** 8 seasons; 2018 was a losing year for low-loss storage (−Rs 1,181/t).
- **H4 is fragile.** n = 29 seasons, R² = 0.153; dropping 2005, 2018 or 2019 lifts p above 0.05, and neither subperiod is significant alone. It is suggestive, not firm, and an association, not causation.
- **Satellite weather is a grid estimate.** NASA POWER gives satellite-derived and reanalysis values on a ~0.5° grid at one point, not a rain gauge, and not the whole onion belt.
- **Value-of-information test is stylised.** The true loss rate is constant through the season, the sensor measures it exactly from May, and the sensor operator re-plans on the April forecast rather than re-forecasting prices.
