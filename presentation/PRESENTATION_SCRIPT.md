# Kanda Code — Presentation Script (15-minute slot)

Team Kanda Code · Industry 4.0 (MS4001) · IIT Madras BS in Data Science

**Target running time: 14:30** (hard limit 15:00; this leaves a 0:30 buffer for slide changes and one breath per hand-off). Times assume about 150 words a minute. Every number below is taken from `docs/KEY_NUMBERS.md`; do not round differently on the day.

## Running order

| # | Slide id | Presenter | Words | Target | Cumulative |
|---|---|---|---|---|---|
| 1 | `cover` | Raghuram | 47 | 0:20 | 0:20 |
| 2 | `problem` | Raghuram | 91 | 0:35 | 0:55 |
| 3 | `why` | Raghuram | 86 | 0:35 | 1:30 |
| 4 | `questions` | Raghuram | 104 | 0:40 | 2:10 |
| 5 | `data` | Raghuram | 117 | 0:45 | 2:55 |
| 6 | `eda` | Parashmani | 129 | 0:50 | 3:45 |
| 7 | `seasonality` | Parashmani | 134 | 0:55 | 4:40 |
| 8 | `h1` | Parashmani | 181 | 1:10 | 5:50 |
| 9 | `forecast-models` | Kathan | 217 | 1:25 | 7:15 |
| 10 | `forecast-test` | Kathan | 216 | 1:25 | 8:40 |
| 11 | `lp-model` | Aaryan | 142 | 0:55 | 9:35 |
| 12 | `plan-2024` | Aaryan | 133 | 0:55 | 10:30 |
| 13 | `backtest` | Aaryan | 167 | 1:05 | 11:35 |
| 14 | `smart-storage` | Yash | 98 | 0:40 | 12:15 |
| 15 | `weather-sensors` | Yash | 116 | 0:45 | 13:00 |
| 16 | `sensitivity` | Yash | 79 | 0:30 | 13:30 |
| 17 | `implications` | Yash | 61 | 0:25 | 13:55 |
| 18 | `limitations` | Yash | 45 | 0:20 | 14:15 |
| 19 | `close` | Yash | 43 | 0:15 | 14:30 |

| Presenter | Slides | Speaking time |
|---|---|---|
| Raghuram Devarayi | cover, problem, why, questions, data | 2:55 |
| Parashmani Datta | eda, seasonality, h1 | 2:55 |
| Kathan Desai | forecast-models, forecast-test | 2:50 |
| Aaryan Choudhary | lp-model, plan-2024, backtest | 2:55 |
| Yash Arabhavi | smart-storage, weather-sensors, sensitivity, implications, limitations, close | 2:55 |

Each member speaks for about the same time (equal 20% contribution). Hand-offs are written into the last line of each section.

## Script, slide by slide

### Raghuram Devarayi

**1. When should onion farmers sell their crop?** · `cover` · 0:20 (ends at 0:20)

> Good morning. We are Kanda Code. Kanda is Marathi for onion. Every April, an onion farmer faces one question: sell now, or store and sell later? I'm Raghuram, and with Parashmani, Kathan, Aaryan and Yash, I'll show you how data, forecasting and a linear programme answer it.

**2. Farmers sell at the year’s lowest price** · `problem` · 0:35 (ends at 0:55)

> Start with the farmer. In May this year, farmers sold onions at five to seven rupees a kilo while retail averaged over twenty-five. At Lasalgaon, farmers have been paid seven to ten rupees against a cultivation cost of twenty-two to twenty-five. It is the calendar: in our data, April's price is only 0.55 times the year's average, and November's is 1.55 times. So why not wait? Because stored onions rot: a ventilated chawl loses about 55 percent in 120 days. Every month stored bets that the price rise beats the rot.

**3. A yearly, costly, data-rich decision** · `why` · 0:35 (ends at 1:30)

> Why this problem? It recurs every year at scale: the government procured about 6.4 lakh tonnes for its onion buffer in 2023-24. Storage is where value is lost: in 2019, NAFED lost almost 53 percent of a 57,000-tonne buffer in traditional storage. Onion is the hardest case: grain stores well, tomato not at all, and onion stores for months but rots fast. And the gap between 55 and 7 percent loss lets us put a rupee value on smart storage. That is our Industry 4.0 link.

**4. Three questions, plus one extension** · `questions` · 0:40 (ends at 2:10)

> So we asked three questions, each with a hypothesis and a test. One: do heavier market arrivals push the price down? We test that with a log-log regression. Two: does an optimised plan in an ordinary ventilated chawl beat selling everything at harvest? Three: how much more is low-loss, cold or IoT-monitored, storage worth? For two and three, a linear programme makes the plan from a March forecast, and we score it on actual prices it never saw. Beyond the proposal we added H4: does late-monsoon rain from NASA satellites predict a bigger autumn price rise? The strip is our method, layer by layer.

**5. Lasalgaon was missing. We rebuilt it.** · `data` · 0:45 (ends at 2:55)

> Now the data and a surprise. The main dataset has 965,314 daily Agmarknet records, but zero rows for Lasalgaon. So we built a Maharashtra benchmark: the arrival-weighted monthly modal price across 96 markets, 132 months, none missing. It tracks Lasalgaon closely: 0.99 correlation on levels and 0.93 on monthly changes against NHRDF's official series, and 0.90 against 19 reported prices from 2020 to 24, running about 10 percent lower because Lasalgaon is the premium market. One fix: variety rows repeated the same arrivals, so summing would double-count about two million tonnes; we keep one row per market-day. For weather, NASA POWER gives free satellite-based monthly rain, temperature and humidity at Lasalgaon since 1996. Parashmani, over to you.

*Hand-off:* “Parashmani, over to you.”

### Parashmani Datta

**6. Prices swing four-fold within a year** · `eda` · 0:50 (ends at 3:45)

> Thanks, Raghuram. Here are eleven years of monthly prices. The average is about fifteen rupees a kilo, but in 2019 alone it went from four and a half rupees in February to over fifty in December. Prices vary by 61 percent around their mean, and within a single year the dearest month is on average 4.6 times the cheapest. Month to month, the price moves with a standard deviation of about 33 percent, roughly 100 percent volatility a year. The pink bands are the April-May harvest: the price sits near its low in every one. The dashed copper line is NHRDF's official Lasalgaon series, which our benchmark follows closely until 2019. The grey lines are export bans and duties: real shocks in the data that no model can forecast.

**7. Crash in April, peak in November** · `seasonality` · 0:55 (ends at 4:40)

> To see the pattern, we divide each month's price by that year's average. That is a seasonal index. April averages 0.55 and November 1.55, almost three times higher. November beat April in all eleven years, with a median rise of 148 percent. The shaded band is the range across years: the height of the peak varies, but its timing is reliable. In hindsight, the single best month was November in five of the eleven years and October in two. And this is not a quirk of our composite: NHRDF's Lasalgaon data from 1996 to 2013 shows the same shape, 0.61 in April and 1.42 in November, with its peak a month earlier, 1.49 in October. So the price is lowest exactly when the harvest floods the markets. Is that link real? That is H1.

**8. Heavier arrivals go with lower prices** · `h1` · 1:10 (ends at 5:50)

> H1 says prices fall when arrivals rise. We regress log price on log arrivals per market-day, with month and year dummies, so we compare heavy and light months after removing the normal season and each year's level. The slope is an elasticity: minus 0.44, with p equal to 0.013, the same with ordinary standard errors and with Newey-West errors that allow for autocorrelation. In words: a month with 10 percent heavier arrivals has prices about 4.4 percent lower. H1 is supported, but as an association, not a causal effect. It weakens to p of 0.06 to 0.08 with other arrival measures, it disappears once we control for last month's price, and last month's price itself predicts this month's arrivals, so prices and arrivals are decided together. One practical check: an FPO selling 1,000 tonnes in April is only 3.6 percent of Lasalgaon's April arrivals, so it is a price-taker. The same OLS tests our extension, H4, late rain against the autumn price rise: positive, but one season can flip it, so it is only suggestive. Kathan will now forecast the season.

*Hand-off:* “Kathan will now forecast the season.”

### Kathan Desai

**9. Choose on validation, score on test** · `forecast-models` · 1:25 (ends at 7:15)

> Thanks, Parashmani. The plan needs one thing from a forecast: the whole April-to-December price path, made at the end of March. So every model makes exactly that: a nine-month forecast from a March origin, with an expanding window. We compared ten candidates, all from the syllabus: naive, seasonal naive, moving averages, exponential smoothing with seasonal indices, Holt-Winters, and two regressions. The rule was fixed in advance: pick the lowest April-to-December MAPE, the criterion in our approved proposal, on the validation seasons 2019 to 2022, then score it once on 2023 and 2024. MAPE is the average percentage gap between forecast and actual, so it is comparable across cheap and expensive years. Bars show validation error, dots test error. The winner is a regression of log price on a time trend and eleven month dummies, with 36.9 percent validation MAPE. Why does it win? The month dummies carry the seasonal shape and the trend sets the level, so the path is stable over nine months. The simple exponential-smoothing models fit alpha equal to one: they carry the latest month forward, which helps one month ahead but not nine. And yes, five models score better on test, the best a smoothing model at 19.55 percent. We did not switch, because choosing on test data would make the test meaningless.

**10. Right shape, level biased low** · `forecast-test` · 1:25 (ends at 8:40)

> Here is the chosen model on the two test seasons, in purple, against actual prices in black. Test MAPE is 29.5 percent, and the bias is minus 17 percent: on average the forecast sat 17 percent below the actual price. It under-predicts most in 2024, when prices ran far above history. The error is large; we report it openly. But look at the shape. Across the two seasons there are 16 month-to-month moves, and it calls the direction of 15 of them, up or down, correctly. It also places the high season, September to November, in the right place. For a sell-or-store decision, the timing of the peak matters more than its height: a forecast that is low everywhere still says October and November are the best months to sell. A biased-low forecast also makes the plan cautious: in the backtest, the plan's own estimate of its value was below what it actually earned in 6 of 8 seasons. This low bias is also why store sensors pay reliably only with accurate prices. The green dashed line is the smoothing model that did best on test. The grey line, a 12-month moving average, shows what a flat forecast would tell the farmer: no reason to wait. Aaryan will now turn this forecast into a selling plan.

*Hand-off:* “Aaryan will now turn this forecast into a selling plan.”

### Aaryan Choudhary

**11. The sell-or-store linear programme** · `lp-model` · 0:55 (ends at 9:35)

> Thanks, Kathan. This is the decision model: a linear programme for one farmer producer organisation with 1,000 tonnes in April. Each month, April to December, it chooses x, tonnes sold, and s, tonnes left in store, to maximise forecast revenue minus storage cost. The key constraint is the stock balance: this month's stock is last month's, minus the rot rate delta, minus what we sell. That is inventory with perishability. Then: 700 tonnes of capacity, a 250-tonne April sale to repay crop loans, a 300-tonne monthly grading and trucking limit, and an empty store by December. Three scenarios differ only in storage: A, none; B, a ventilated chawl losing 18 percent a month; C, cold or IoT-monitored storage losing 1.8 percent, both from ICAR trials. For 2024, B refuses to store, so it equals A, while C plans 47.8 lakh rupees more.

**12. The 2024 plan and its shadow prices** · `plan-2024` · 0:55 (ends at 10:30)

> Here is the 2024 plan. A and B sell all 1,000 tonnes in April. C sells 300 tonnes in April, the minimum a 700-tonne store allows, then holds and sells 21 tonnes in September and 300 in each of October and November. On the right, the shaded area is the stock in C and the dashed line is the March forecast, which turned out far below actual prices. Because this is an LP, we also get shadow prices, and we verified each one by re-solving with one tonne more and one tonne less. One more tonne of storage capacity is worth 4,028 rupees. One more tonne a month of handling capacity is worth 6,526, because the 300-tonne cap binds in October and November. The loan sale is slack, so its value is zero.

**13. Tested on prices the model never saw (H2)** · `backtest` · 1:05 (ends at 11:35)

> For each season from 2017 to 2024, we plan from a March forecast and score the plan at actual prices against selling all in April. H2 is not supported. At 18 percent loss a month, the chawl plan never stores, so it equals harvest sale in all eight seasons; and a naive September-to-November rule in a chawl would lose 1,149 rupees a tonne. In low-loss storage, the plan beats harvest sale in 7 of 8 seasons, by 4,546 rupees a tonne on average; a one-sided paired t-test gives p of 0.006, and a rank test agrees. The one loss was 2018. Even with perfect foresight, a chawl adds only 791 rupees a tonne. A fixed September-to-November calendar rule does better on average in cold storage, 5,508 rupees a tonne, though not in the 2023-24 test seasons. So the seasonal shape does the work; the LP adds knowing when not to store, and a price on every constraint. Yash will now put a rupee value on smart storage.

*Hand-off:* “Yash will now put a rupee value on smart storage.”

### Yash Arabhavi

**14. Smart storage pays its way (H3)** · `smart-storage` · 0:40 (ends at 12:15)

> Thanks, Aaryan. This is H3, our Industry 4.0 story: a closed loop. Sensors track temperature and humidity; alerts and cooling hold the loss near ICAR's cold-store 1.8 percent a month instead of 18; the LP re-plans monthly; the FPO sells or holds. It earns 4,546 rupees per tonne over the chawl across eight seasons. Monthly re-planning earns about the same, so the value is in cutting loss. At about 16,700 rupees a tonne of space versus 7,000 for a chawl, it pays back in one and a half seasons: 45.5 lakh rupees a year for a 1,000-tonne FPO.

**15. What satellites and sensors are worth (extension: H4 and value of information)** · `weather-sensors` · 0:45 (ends at 13:00)

> Beyond the proposal: what is extra data worth? With NASA POWER satellite rain, each 100 millimetres of September-October rain goes with about a 20 percent bigger autumn rise, p of 0.036. It is fragile: drop 2005, 2018 or 2019 and p passes 0.05, so H4 is weakly supported. A live rain feed is worth zero: the handling cap already fixes November's sales. Sensors: a chawl measured at 8 percent a month earns 2,200 rupees a tonne, where the book 18 percent says never store. In a cold store, sensing earns 545 to 746 rupees a tonne if losses climb to 8 to 15 percent, but only with accurate prices. Lesson: measure the store before the season.

**16. Storage pays below 12.4% loss a month** · `sensitivity` · 0:30 (ends at 13:30)

> The grid varies the chawl's monthly loss and storage cost; purple cells gain, copper cells lose. At 250 rupees a month, storage breaks even at about 12.4 percent loss a month; the ICAR chawl, at 18, is above it. The cold store stays positive at 8 percent loss, plus 374 rupees, and at double the cost, plus 1,069. Removing the handling cap leaves the result intact. Each point of monthly loss avoided is worth about 685 rupees a tonne.

**17. What each decision-maker should do** · `implications` · 0:25 (ends at 13:55)

> FPOs: never store in a chawl on hope; with low-loss storage, sell the minimum in April, hold for September to November, and add capacity and handling first. Buffer agencies: the storage type decides whether a buffer earns or rots. Investors: payback is about 1.5 seasons at ICAR's cost, but a small cold room at 50,000 rupees a tonne does not pay.

**18. What our model does not claim** · `limitations` · 0:20 (ends at 14:15)

> Our limits, openly. The series is a composite, about 10 percent below Lasalgaon. H1 is an association, and H4 is fragile. Forecasts are biased low. Loss rates come from 120-day trials. We skip grading, credit and export bans, and eight seasons make our tests indicative.

**19. Cut the rot first, then time the sale · Questions** · `close` · 0:15 (ends at 14:30)

> Our answer: cut the rot first, then time the sale. Low-loss storage adds about four and a half rupees a kilo and pays back in a season and a half. Measure the store first. Thank you. We are happy to take your questions.

*Hand-off:* “We are happy to take your questions.”

---

## Rehearsal checklist (one page)

**Two full run-throughs with a stopwatch, then one with a mock Q&A.**

Timing
- [ ] Each presenter finishes within ±10 s of their total in the table above; whole deck at or under 14:30.
- [ ] Practise the five hand-off lines word for word; the next speaker starts on the next slide without a pause.
- [ ] If running long, cut the second sentence of each figure description, never a number or a limitation.
- [ ] One person (Aaryan, coordination) keeps time with a silent phone timer and signals at 10:00 and 13:30.

Numbers to say exactly (from KEY_NUMBERS.md)
- [ ] Seasonal index: April 0.55×, November 1.55× (1.546). November beat April in 11 of 11 years; median rise 148.3%.
- [ ] Data: 965,314 records, 0 Lasalgaon rows, 96 Maharashtra markets, 85,346 market-days, 132 months; validation r 0.99 / 0.93 / 0.90.
- [ ] H1: β = −0.44, p = 0.013 with OLS and with HAC errors (one-sided 0.0066), n = 132, adj R² 0.53. Say “association, not causation”.
- [ ] Forecast: regression trend + month dummies; validation MAPE 36.94%, test MAPE 29.5%, bias −17.1%, 15 of 16 directions.
- [ ] LP 2024: C sells 300 / 21 / 300 / 300 t (Apr, Sep, Oct, Nov); shadow prices +Rs 4,028 (capacity), +Rs 6,526 (handling), Rs 0 (loan).
- [ ] Backtest: chawl stores in 0 of 8 seasons (H2 not supported); cold store +Rs 4,546/t, wins 7 of 8, paired t p = 0.006 (Wilcoxon 0.008); calendar rule +Rs 5,508/t; chawl with perfect foresight only +Rs 791/t.
- [ ] Value: payback 1.5 seasons (Rs 9,667/t extra capex ÷ Rs 6,495/t capacity a season); Rs 45.5 lakh a year for 1,000 t; break-even loss 12.4%/month.
- [ ] Extension: H4 β ≈ +20% rise per 100 mm of Sep+Oct rain (NASA POWER), p = 0.036, n = 29 seasons, R² 0.15; live rain feed Rs 0/t (handling cap U binds); chawl measured at 8% Rs 2,200/t; cold-store sensing Rs 545–746/t at 8–15% loss with accurate prices.

Honesty lines everyone must be able to say
- [ ] Lasalgaon is not in the main dataset; our Maharashtra composite runs about 10% below it, so rupee gains for a Lasalgaon seller would be somewhat higher (Nasik: +Rs 11,510 and +Rs 13,377/t in 2023–24).
- [ ] We chose the forecaster on 2019–22 and only then scored 2023–24; five models did better on test (best 19.55%) and we did not switch.
- [ ] The forecast is biased low; value comes from the seasonal shape. A fixed Sep–Nov rule does better on average in cold storage (+Rs 5,508 vs +Rs 4,546/t); the LP adds knowing when not to store, verified shadow prices and sensitivity. Monthly re-planning earns about the same (+Rs 4,511/t).
- [ ] Eight seasons, two of them test seasons: our tests are indicative; 2018 lost Rs 1,181/t.
- [ ] H4 is an extension beyond the approved proposal and only weakly supported: dropping 2005, 2018 or 2019 lifts p above 0.05, and neither subperiod is significant alone. It is an association, not causation. NASA POWER, not ISRO: Bhuvan and MOSDAC need registration and add nothing at point scale.

Logistics
- [ ] Open the deck in presenter view; speaker notes match this script.
- [ ] All five members present and on camera; each knows the slide numbers of the others in case of a dropped connection.
- [ ] Keep the Excel Solver model and the notebook open in background tabs for Q&A demonstrations.
- [ ] Q&A: the person asked answers first; others may add one sentence only. Any member must be able to explain every slide.
