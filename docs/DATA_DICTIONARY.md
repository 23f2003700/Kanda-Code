# Data Dictionary — Kanda Code

Every file, every column, its unit and exactly how it is derived. Code references point to `src/kandacode.py` (functions) and `src/run_all.py` (file writes). Numbers come from `outputs/results.json → data_quality` (and `→ weather` for the NASA POWER extension) and are listed in `docs/KEY_NUMBERS.md`.

## Units — read this first

| Quantity | Unit in data files | Unit in the LP | Unit in text and slides |
|---|---|---|---|
| Price | Rs per quintal (Rs/q; 1 quintal = 100 kg) | Rs per tonne (= Rs/q × 10) | Rs per kg (= Rs/q ÷ 100 = Rs/t ÷ 1,000) |
| Arrivals | tonnes (t) | tonnes | tonnes |
| Period | `ym` = calendar month `YYYY-MM`; `date` = `YYYY-MM-DD` | t = 1..9 = Apr..Dec | month names |
| Weather (NASA POWER) | temperature °C; relative humidity %; rain mm/day (raw) and mm per month (processed) | not in the LP | °C, %, mm |

Example: Rs 1,488/q = Rs 14,880/t = Rs 14.88/kg (the 2014–24 mean price).

---

## 1. Raw inputs (`data/raw/`)

### 1.1 `onion_2014_2024.parquet` — main dataset

Onion records of Shelar, Hajare & Mangarule (2025), *A Comprehensive Spatio-Temporal Dataset for Agricultural Price Forecasting (2014–2024)*, Mendeley Data V1, doi:10.17632/ds9jmxp9zy.1, CC BY 4.0. Compiled from Agmarknet (Directorate of Marketing and Inspection).

- **965,314** daily market records, all India, 2014-01-01 to 2024-12-31, **56 columns**.
- SHA-256 `392da11330e7d3166df07e7b4e154c64934bfd450221afa8b4024e2cf1124006`.

**Columns we use** (read by `load_raw`; the other 46 columns are not used):

| Column | Type | Unit | Meaning | How we use it |
|---|---|---|---|---|
| `date` | date | day | Trading date | Grouping key (day, month) |
| `state` | text | – | State | Filter `== "Maharashtra"` |
| `district` | text | – | District | Arrival weights by district; kept on market-days |
| `market` | text | – | APMC market name | Grouping key; Lasalgaon search; Nasik robustness series |
| `variety` | text | – | Variety label (Maharashtra: Other, Red, Local, White, 1st Sort, 2nd Sort, Pole, Hybrid) | Duplicate key; reveals repeated-arrival rows |
| `grade` | text | – | Grade (Maharashtra: FAQ on every row) | Duplicate key |
| `arrivals_tonnes` | float | t | Quantity arriving at the market that day | Weights and the H1 regressor |
| `min_price_rs_qtl` | float | Rs/q | Day's minimum price | Consistency flag only |
| `max_price_rs_qtl` | float | Rs/q | Day's maximum price | Consistency flag only |
| `modal_price_rs_qtl` | float | Rs/q | Most frequent transaction price that day | **The price we model** |

**Columns not used, and why.** Weather (`rain`, `tmax`, `tmin`, `temp_*`, `*_5m`, `cum_rain_*`), location (`lat`, `lon`, `grid_*`), calendar helpers (`year`, `month`, `week`, `dayofweek`, `is_weekend`, `season`, `crop_season_onion`), engineered lags and rolling means (`*_lag_1/7/30`, `*_pctchg_*`, `*_7d_mean`, `*_30d_mean`), flags (`price_spike`, `arrival_zero`), events (`festival_name`, `is_festival`), and `group`, `market_key`. Our models work on monthly aggregates and compute their own lags, so the pre-built daily features are unnecessary. Festivals are outside the decision we model. The dataset's weather columns start in 2014 and are attached to individual markets; the weather extension (H4) needs the 1996–2013 seasons too, so it uses NASA POWER at Lasalgaon instead (§1.3).

### 1.2 `nhrdf/LasalgaonOnionData_NHRDF.csv` — official Lasalgaon series

NHRDF Lasalgaon onion monthly prices and arrivals, Mendeley Data, doi:10.17632/9dn4g8m97m.1. **282 months, 1996-01 to 2019-06**, no missing values. SHA-256 `26781af1e0fd6679336c5d2349804e46b077103f5d964e3d3e9a0593eb4b7914`.

| Column | Unit | Meaning | Used? |
|---|---|---|---|
| `Month Name` | – | e.g. January | No (redundant with `Time`) |
| `Year` | – | e.g. 1996 | No (redundant with `Time`) |
| `Arrival (q)` | quintals | Monthly arrivals at Lasalgaon | Yes → tonnes (÷ 10) |
| `Modal Price (Rs/q)` | Rs/q | Monthly modal price at Lasalgaon | Yes |
| `Arrival ('000q)` | thousand quintals | Same as `Arrival (q)` ÷ 1,000 | No |
| `Time` | `DD-MM-YYYY` (1st of month) | Month stamp | Yes → `ym` |

It is used for three things only (never as a forecast input after 2013):
1. **Validation** of our benchmark, on the 66 overlapping months 2014-01 to 2019-06.
2. **Long seasonality**: the 216 months 1996-01 to 2013-12 (all before our series starts, so before every forecast origin) feed the seasonal indices of the two "28-yr" forecast candidates and the ex-ante calendar rule, and give the 1996–2013 reference seasonal index shown in the EDA.
3. **Price-taker check**: mean Lasalgaon arrivals in April (27,752 t) and in Oct–Nov (16,800 t), 2014–19.

### 1.3 `nasa_power/` — satellite weather at Lasalgaon (extension, H4)

NASA Langley Research Center, **POWER** (Prediction Of Worldwide Energy Resources) project, monthly point API v2 (the file header reports API v2.10.0), https://power.larc.nasa.gov. Free, no key or registration. Downloaded by `src/fetch_nasa_power.py` (accessed 10 Nov 2026).
- **Point:** 20.15°N, 74.23°E (Lasalgaon APMC, Niphad taluka, Nashik); the file records an elevation of 581.1 m.
- **Period:** 1996-01 to 2024-12, **348 months**, no fill values (POWER's fill value is −999).
- **What the values are:** satellite-derived and reanalysis estimates (MERRA-2 for temperature and humidity, IMERG-corrected for rain) on a ~0.5° grid. They describe a grid cell, not a rain gauge.

**`lasalgaon_power_monthly_1996_2024.json`** — the API response exactly as downloaded (GeoJSON `Feature`). `properties.parameter` holds one dictionary per parameter keyed `YYYYMM`; keys ending in `13` are the annual value and are dropped. SHA-256 `e2c98e9ca1acafa061d0f3545ca8dc5a561d96b6d5a13f3cc523f52fad3b3b7b`.

**`lasalgaon_power_monthly_1996_2024.csv`** — the same values, tidied by `fetch_nasa_power.py`, one row per month (348 rows). This is the file `load_power` reads. SHA-256 `f346499cd076cc37576eb81bc0377b9e936e87cc39ec23bf0ab98634946f90d2`.

| Column | Unit | POWER parameter | Meaning | Range in file |
|---|---|---|---|---|
| `ym` | `YYYY-MM` | – | Month | 1996-01 … 2024-12 |
| `t2m_c` | °C | T2M | Mean air temperature at 2 m | 17.96 … 32.63 |
| `rh2m_pct` | % | RH2M | Mean relative humidity at 2 m | 16.34 … 88.79 |
| `rain_mm_per_day` | mm/day | PRECTOTCORR | Bias-corrected precipitation, mean per day of the month | 0.0 … 12.91 |

---

## 2. Cleaning log (`clean_maharashtra`, results.json → `data_quality`)

Applied in this order:

| Step | Rule | Rows / result |
|---|---|---|
| 0 | All-India onion records | 965,314 |
| 1 | Keep `state == "Maharashtra"` | **91,898** rows, **96** markets |
| 2 | Search for Lasalgaon (`market` contains "lasal", any case) | **0 rows** — the reason we build a composite |
| 3 | Drop modal price outside the plausibility band Rs 50–20,000/q (Rs 0.5–200/kg) | 42 dropped |
| 4 | Drop arrivals ≤ 0 | 0 dropped |
| 5 | Drop exact duplicates on (date, market, variety, grade) | 0 dropped |
| 6 | Flag rows where min ≤ modal ≤ max fails | 0 flagged (flag only; modal is what we use) |
| 7 | Drop relative outliers: modal price < 0.2× or > 5× the same day's cross-market median (likely unit or entry errors) | 58 dropped |
| – | Clean records | **91,798** |
| 8 | Detect repeated arrivals: market-days with several variety rows | **5,672** market-days; **100.0%** of them repeat the same tonnage on every row |
| – | Tonnes that would be double-counted if rows were summed | **1,979,857 t** |
| 9 | Collapse to one row per (date, market, district) | **85,346** clean market-days |
| – | Date range after cleaning | 2014-01-01 to 2024-12-31 |
| – | Trading days with at least one market | 3,972; median 22 markets reporting per day |
| – | Monthly series | 132 months, **none missing** |
| – | Mean markets reporting per month | 34.0 (2014) → 63.8 (2024) |

**Collapse rule (step 9), per market-day:**
- One row: keep it.
- Several rows with **identical** arrivals (the Agmarknet pattern; 100% of cases here): count the tonnage **once**; price = simple mean of the variety modal prices.
- Several rows with **different** arrivals: sum the arrivals; price = arrival-weighted mean of the variety modal prices. (Coded for completeness; it did not occur in the Maharashtra data.)

**Arrival weight by district** (share of clean arrivals, top 6): Ahmednagar 38.5%, Pune 18.4%, Sholapur 15.2%, Mumbai 9.3%, Chattrapati Sambhajinagar 4.2%, Kolhapur 3.7%.

**Top markets by clean arrivals (t):** Solapur 5,225,972; Pune 3,720,233; Ahmednagar 3,044,270; Newasa (Ghodegaon) 2,879,666; Vashi New Mumbai 2,611,785; Rahuri 1,500,349; Sangamner 1,479,319; Kolhapur 1,320,823; Parner 1,006,692; Junnar (Alephata) 978,144.

---

## 3. Processed files (`data/processed/`, written by `run_all.py`)

### 3.1 `maharashtra_onion_monthly.csv` — the analysis series (`build_monthly`)

132 rows (2014-01 … 2024-12), one per month. Every model in the project reads `price_rs_qtl` from this file (as a `PeriodIndex` series).

| Column | Unit | Derivation | Range in file |
|---|---|---|---|
| `ym` | `YYYY-MM` | Calendar month | 2014-01 … 2024-12 |
| `price_rs_qtl` | Rs/q | **Arrival-weighted mean of market-day modal prices** in the month: Σ(Aᵢ·Pᵢ) / ΣAᵢ over all market-days *i* | 451.1 … 5,055.7 (mean 1,488.1) |
| `price_median_rs_qtl` | Rs/q | Unweighted median of market-day modal prices (robustness view) | 425 … 5,500 |
| `arrivals_t` | t | Sum of market-day arrivals | 25,703 … 655,947 |
| `market_days` | count | Distinct (date, market) pairs after the collapse | 143 … 1,006 |
| `markets_reporting` | count | Distinct markets with at least one market-day | 26 … 67 |
| `trading_days` | count | Distinct dates with at least one market | 19 … 31 |
| `arrivals_per_market_day_t` | t | `arrivals_t / market_days` — **the H1 regressor** (removes the doubling of market coverage over time) | 161.4 … 848.8 |
| `arrivals_per_market_t` | t | `arrivals_t / markets_reporting` — robustness normalisation | 714.0 … 10,753.2 |
| `year` | – | Calendar year | 2014 … 2024 |
| `month` | 1–12 | Calendar month | 1 … 12 |

Price extremes: minimum Rs 4.51/kg (2019-02), maximum Rs 50.56/kg (2019-12).

### 3.2 `maharashtra_onion_daily.csv` — daily series (`build_daily`)

3,972 rows, one per trading date, 2014-01-01 … 2024-12-31. Used only for the H1 daily sign-check (model D1).

| Column | Unit | Derivation |
|---|---|---|
| `date` | `YYYY-MM-DD` | Trading date |
| `price_rs_qtl` | Rs/q | Arrival-weighted mean of that day's market modal prices (374.6 … 8,142.3) |
| `arrivals_t` | t | Sum of that day's market arrivals (0.5 … 42,294) |
| `markets_reporting` | count | Markets reporting that day (1 … 45; median 22) |
| `arrivals_per_market_t` | t | `arrivals_t / markets_reporting` (D1 regressor) |

### 3.3 `nasik_apmc_monthly.csv` — robustness market (`build_market_monthly`)

132 rows; "Nasik" is the only Nashik-district market in the main data. Built from the same clean market-days with the same weighting.

| Column | Unit | Derivation |
|---|---|---|
| `ym` | `YYYY-MM` | Month |
| `price_rs_qtl` | Rs/q | Arrival-weighted modal price at Nasik APMC (397.8 … 5,160.3) |
| `arrivals_t` | t | Monthly Nasik arrivals |
| `trading_days` | count | Days with a Nasik record (1 … 27) |

Missing months (blank rows): 13 — 2014-01 to 2014-06, 2014-10, 2015-05 to 2015-10. **Complete from 2016-01**, so the Nasik backtest uses 2016-01 onwards.

Correlations: Nasik vs NHRDF Lasalgaon r = 0.9724; composite vs Nasik in 2023–24 r = 0.9805, composite ÷ Nasik level ratio 0.948.

### 3.4 `lasalgaon_nhrdf_monthly.csv` — tidied NHRDF series (`load_nhrdf`)

282 rows, 1996-01 … 2019-06.

| Column | Unit | Derivation |
|---|---|---|
| `ym` | `YYYY-MM` | From `Time` |
| `lasalgaon_price_rs_qtl` | Rs/q | `Modal Price (Rs/q)` unchanged (140 … 4,593) |
| `lasalgaon_arrivals_t` | t | `Arrival (q)` ÷ 10 (3,053.2 … 77,440.5) |

### 3.5 `lasalgaon_nasa_power_monthly.csv` — weather for H4 (`load_power`)

348 rows (1996-01 … 2024-12), written by step 8 of `run_all.py`. The raw CSV of §1.3 plus one derived column.

| Column | Unit | Derivation | Range in file |
|---|---|---|---|
| `ym` | `YYYY-MM` | Month | 1996-01 … 2024-12 |
| `t2m_c` | °C | T2M, unchanged | 17.96 … 32.63 |
| `rh2m_pct` | % | RH2M, unchanged | 16.34 … 88.79 |
| `rain_mm_per_day` | mm/day | PRECTOTCORR, unchanged | 0.0 … 12.91 |
| `rain_mm` | mm per month | `rain_mm_per_day` × days in the month | 0.0 … 400.21 |

Used for: the H4 regressor (Sep + Oct `rain_mm`), the placebo (Jun–Sep `rain_mm`), Sep–Oct mean RH, and the 2014–24 monthly climatology (`results.json → weather.climatology_2014_2024`; RH 82.4–85.0% in Jul–Sep).

---

## 4. Validation file (`data/validation/lasalgaon_reported_prices_2020_2024.csv`)

19 independently reported Lasalgaon prices for 2020–24, the period NHRDF does not cover: **8 MSAMB weekly reports** and **11 dated news reports**. Hand-compiled; each row carries its source and URL. SHA-256 `87f090fb3a7c7f4e990fdd472aec53e86e48d397458f88dca10edede9664d5bb`.

| Column | Unit | Meaning |
|---|---|---|
| `month` | `YYYY-MM` | Month the reported price falls in (matched to our monthly series) |
| `reported_rs_qtl` | Rs/q | Reported Lasalgaon price (weekly average or single-day average; where two prices are reported in a month, their mean) |
| `source_type` | – | `MSAMB weekly report` or `news report` |
| `what` | text | Exactly what the figure is (date, day or week, grade) |
| `source` | text | Publication and date |
| `url` | text | Link to the source |

Result (`spotcheck_2020_2024`): r = 0.90; median absolute gap 17.7%; our series lower in 84% of points (median signed gap −10.2%; MSAMB points only −19.0%). Lasalgaon is the premium market, so a lower composite level is expected. A level gap scales rupee values but barely moves the timing decision.

---

## 5. Derived tables (`outputs/tables/`)

### 5.1 `seasonal_profile.csv` (`seasonal_profile`)

12 rows (Jan … Dec). Index = month price ÷ that calendar year's mean price, then averaged over 2014–24.

| Column | Meaning |
|---|---|
| (index) | Month name |
| `price_index_mean` | Mean seasonal price index (Apr 0.553 … Nov 1.546) |
| `price_index_min` / `price_index_max` | Lowest / highest index for that month across the 11 years |
| `arrivals_index_mean` | Mean of `arrivals_per_market_day_t` ÷ that year's mean (0.81 … 1.27) |
| `price_mean_rs_qtl` | Mean price for that month across years, Rs/q |

### 5.2 `backtest_2017_2024.csv` (88 rows) and `backtest_2023_2024.csv` (22 rows) (`backtest`)

One row per season × scenario × strategy. Strategies: `forecast_plan` (A, B, C), `rolling_replan`, `perfect_foresight`, `calendar_rule_exante`, `calendar_rule_hindsight_OctNov` (B, C). All money is evaluated at **actual** prices.

| Column | Unit | Meaning |
|---|---|---|
| `year` | – | Season (Apr–Dec of that year) |
| `scenario` | A/B/C | Storage scenario |
| `strategy` | – | How the sales were decided (see METHODOLOGY §6) |
| `revenue` | Rs | Σₜ actual priceₜ × xₜ |
| `storage_cost` | Rs | h × Σₜ sₜ |
| `net` | Rs | revenue − storage_cost |
| `net_per_t` | Rs/t harvested | net ÷ Q (Q = 1,000 t) |
| `gain_vs_harvest_per_t` | Rs/t harvested | (net − Q × actual April price) ÷ Q — **the headline metric** |
| `x` | t, list of 9 | Tonnes sold Apr … Dec |
| `s` | t, list of 9 | End-of-month stock Apr … Dec |
| `sold_t` | t | Σ x (less than 1,000 when stock is lost to rot) |
| `rule_months` | – | Calendar-rule rows only: months sold (ex-ante rule picked Oct, Nov, Sep in every year) |
| `oracle_net_per_t` | Rs/t | Perfect-foresight optimum for the same season and scenario (blank for calendar rules) |
| `forecast_objective_per_t` | Rs/t | `forecast_plan` rows only: what the LP *expected* to earn at forecast prices |

### 5.3 Extension tables kept in `results.json` (no CSV)

**`weather.h4_rain_price_link.table`** (`weather_price_link`) — one row per season, 29 rows, 1996–2024:

| Field | Unit | Meaning |
|---|---|---|
| `year` | – | Season |
| `rise_log` | log points | ln(mean Oct–Dec price ÷ April price) — the H4 outcome |
| `rise_pct` | % | (mean Oct–Dec price ÷ April price − 1) × 100 |
| `rain_sep_oct_mm` | mm | Sep + Oct rain at Lasalgaon (NASA POWER) — the H4 regressor |
| `rain_jun_sep_mm` | mm | Jun–Sep rain — the placebo regressor |
| `rh_sep_oct_pct` | % | Mean RH2M over Sep and Oct |
| `source` | – | Price series used: `NHRDF Lasalgaon` (1996–2013) or `Maharashtra composite` (2014–24) |

**`weather.realtime_replan_nov_dec.{B,C}.by_season`** (`weather_replan_backtest`) — 8 rows each, 2017–24: `rain_sep_oct_mm`; `rain_multiplier` (the rain adjustment applied to the Nov–Dec forecast, from a regression on earlier seasons only); `stock_entering_nov_t` (t); `price_only` and `price_plus_rain` (gain vs harvest sale, Rs/t harvested, in each arm); and the Nov–Dec sales (t) in each arm.

**`value_of_loss_information.{with_forecast_prices, with_perfect_price_foresight}.{B,C}`** (`value_of_loss_information`) — `book_delta` (the loss rate the blind operator plans with); `grid` (one row per true loss rate δ*: mean `blind`, `sensor`, `calibrated` gain in Rs/t, `voi_sensor` = sensor − blind, `voi_calibrated` = calibrated − blind, and the number of seasons in which the sensor beats or loses to blind); `by_season` (the same per season, 2017–24).

---

## 6. Glossary

| Term | Meaning |
|---|---|
| APMC | Agricultural Produce Market Committee — a regulated wholesale market (mandi) |
| Arrivals | Tonnes of produce brought to a market for sale |
| Modal price | The price at which most of the day's trade happened |
| Market-day | One market on one date, after collapsing variety rows |
| Composite / benchmark | Our Maharashtra arrival-weighted monthly modal price |
| FPO | Farmer producer organisation — the decision-maker in the LP |
| Kanda chawl | Traditional naturally ventilated onion store (scenario B) |
| Rabi | Winter-sown crop, harvested March–May; the crop that is stored |
| FAQ | Fair Average Quality grade |
| Kharif | Monsoon-sown crop, harvested from about October; late rain damages it in the field |
| NASA POWER | NASA's free satellite and reanalysis weather service, used here for Lasalgaon temperature, humidity and rain |
| Reanalysis | A weather model run that assimilates observations to give consistent gridded values for past months |
| Value of information | Gain of a decision made with a piece of information minus the gain of the same decision made without it (here: knowing the store's real loss rate, or the Sep+Oct rain) |
