# Kanda Code — viva script (15 min: ~10 min talk + ~5 min Q&A)

**Site:** https://23f2003700.github.io/Kanda-Code/ (also opens straight from `presentation/viva/index.html`)

**Controls:** click once → full screen · `→` / `Space` / click = next · `←` / right-click = back (every animation plays exactly backwards) · `N` = these notes on screen · `T` = timer (amber at 9:00, red at 10:00) · type a number + `Enter` = jump to slide · `F` = full screen.

**`[→]` = press next.** Each click reveals the next piece of the slide; the speaker's colour is shown at the bottom.

| # | Speaker | Slides | Clicks | Target time |
|---|---|---|---|---|
| 1 | Raghuram Devarayi | 1–4 Title, Problem, Approach, Data | 10 | 0:00 → 2:20 |
| 2 | Parashmani Datta | 5–6 Price landscape (3D), H1 | 6 | 2:20 → 3:40 |
| 3 | Kathan Desai | 7–8 Ten models, Forecast vs actual | 6 | 3:40 → 5:00 |
| 4 | Aaryan Choudhary | 9–11 LP, 2024 plan, Backtest | 11 | 5:00 → 7:20 |
| 5 | Yash Arabhavi | 12–15 All-India (3D), Value, Implications, Thanks | 8 | 7:20 → 9:30 |

Every number on the slides is generated from the project outputs by `src/build_viva.py` — nothing is typed by hand.

---

## 1 · Raghuram Devarayi — Problem & data (≈ 2:20)

**Slide 1 · Title** (≈ 0:15)
> Good morning. We are team Kanda Code — kanda is Marathi for onion. Our question is simple: when should an onion farmer sell? I'm Raghuram; with me are Parashmani, Kathan, Aaryan and Yash, and each of us presents one part.

**Slide 2 · The problem** (≈ 0:45)
> This is Maharashtra's onion price, each month as a multiple of that year's average. April, right after the rabi harvest, is at 0.55; November is at 1.55. November beat April in all 11 years, by a median 148%. Yet farmers sell in April — at Lasalgaon they have been paid ₹7–10 a kilo against a cost of ₹22–25. **[→]** Why not wait? Onions rot: a ventilated chawl loses about 55% in 120 days, a cold store 5–7%. **[→]** So the decision: an FPO, a farmer producer organisation, holds 1,000 tonnes at harvest. How many tonnes should it sell each month, April to December?

**Slide 3 · Approach** (≈ 0:35)
> How we answered it, and who did what: data, the price pattern, a forecast, a linear programme that makes the plan, a backtest on seasons the model never saw, and an all-India check. **[→]** Three hypotheses from our approved proposal: H1, price falls when arrivals rise; H2, a planned chawl beats selling at harvest; H3, low-loss storage adds real money. **[→]** The answers up front: H1 supported; H2 rejected — the chawl rots too fast; H3 supported.

**Slide 4 · Data** (≈ 0:45)
> Our data: 965,314 daily mandi records from Agmarknet, all India, 2014 to 2024, published on Mendeley; 91,898 are from Maharashtra. Our proposal targeted Lasalgaon, Asia's largest onion market — but it has zero rows in this dataset, so we built an arrival-weighted price for Maharashtra from 96 markets. **[→]** One trap: when a market reports several varieties, the same tonnage repeats in every row; summing would double-count 19.8 lakh tonnes. We keep one row per market-day: 85,346, giving 132 monthly prices, none missing. **[→]** Is it a fair stand-in? Against NHRDF's official Lasalgaon series the correlation is 0.99 over 66 months. Over to Parashmani.

---

## 2 · Parashmani Datta — Price patterns & H1 (≈ 1:20)

**Slide 5 · 11 years in 3D** (≈ 0:35)
> Each bar is one month of real price from 2014 to 2024; height and colour are rupees per kilo. **[→]** From the front the pattern is obvious: every year a valley in April and a ridge from October to December — November beat April in all 11 years. **[→]** But it is not a safe bet: December 2019 hit ₹50.6 a kilo, February 2019 was ₹4.5. A plan must handle both.

**Slide 6 · H1** (≈ 0:45)
> Why does the price move? The copper line is arrivals — tonnes reaching the markets — heavy from December to March as the crop comes in, low from August to November. **[→]** The price, in gold, is almost its mirror image. **[→]** H1 tests this: log price on log arrivals with month and year fixed effects, so season and inflation are removed, with HAC errors because months are autocorrelated. β is −0.44, p 0.007: ten percent more arrivals, about four percent lower price. H1 is supported. Honestly, it is an association — adding last month's price makes it vanish — so we use it to understand the market and let the forecast drive the plan. Kathan.

---

## 3 · Kathan Desai — Forecast (≈ 1:20)

**Slide 7 · Ten models** (≈ 0:50)
> The plan needs prices for April to December, forecast at the end of March. We compared ten syllabus methods: naive, seasonal naive, moving averages, exponential smoothing, Holt-Winters and regressions. We chose using validation seasons 2019 to 2022 only, and locked 2023 and 2024 away as the test. **[→]** Regression on trend plus month dummies won, at 36.9% error. On the test, two smoothing models did a little better — we did not switch, because choosing after seeing the test would be cheating. **[→]** It also suits the decision: the LP needs the shape of the season, and this model is exactly trend plus a monthly shape — 13 parameters, easy to explain.

**Slide 8 · Forecast vs reality** (≈ 0:30)
> Here it is against reality, in two seasons it never saw. 2023: the dashed forecast sits below the gold actual, but rises at the right time. **[→]** 2024: the same. **[→]** Average error 29.5%, and 17% too low on average — conservative, which only makes storage look less attractive. But the month-to-month direction is right 15 times out of 16, and for a storage decision direction is what matters. Aaryan.

---

## 4 · Aaryan Choudhary — Sell-or-store LP (≈ 2:20)

**Slide 9 · The LP** (≈ 0:55)
> Now the decision. 1,000 tonnes at harvest. At least 250 must be sold in April to repay crop loans. The rest can go into a 700-tonne store that loses δ per month, and the FPO can grade and truck at most 300 tonnes a month. **[→]** We maximise forecast revenue minus holding cost. **[→]** Subject to stock balance with rot, capacity, the loan sale, the handling cap, and an empty store by December. It is linear, so the solver gives a guaranteed optimum plus shadow prices — the value of relaxing each constraint. **[→]** Three scenarios: A sells everything at harvest; B is a chawl, 18% loss a month; C is cold or IoT-monitored storage, 1.8% a month but almost three times the cost.

**Slide 10 · The 2024 plan** (≈ 0:40)
> This is the 2024 plan, made with the March forecast. **[→]** With cold storage: sell 300 in April, hold, then 300 in October and 300 in November, with 79 tonnes lost to rot. **[→]** With the chawl, the optimum is to store nothing and sell all 1,000 in April — 18% a month eats the price rise. **[→]** The shadow prices tell the FPO where to invest: one more tonne of storage is worth ₹4,028, one more tonne of monthly handling ₹6,526; the loan rule costs nothing.

**Slide 11 · Backtest** (≈ 0:45)
> Does it work on prices it never saw? For every season 2017 to 2024 we forecast in March from past data only, made the LP plan, and paid the actual prices. **[→]** Cold storage beat harvest sale in 7 of 8 seasons, by ₹4,546 a tonne on average; paired t-test p = 0.006. The chawl plan never stores, so it equals harvest sale — H2 rejected. **[→]** And the model protects the farmer: a simple "store and sell in October–November" rule with a chawl loses ₹1,149 a tonne. Yash.

---

## 5 · Yash Arabhavi — All-India & Industry 4.0 (≈ 2:10)

**Slide 12 · All-India in 3D** (≈ 0:45)
> Does this only work in Maharashtra? Every dot is an onion market in the dataset. **[→]** We ran the same model, unchanged, on all 118 markets in 15 states with near-complete data. Each column is one market: green where cold storage beat harvest sale, red where it lost. **[→]** 114 of 118, plus ₹3,692 a tonne, positive in 6 of 8 seasons, p = 0.04, and the chawl stored in only 4 markets. With market fees and quality loss added, 105 still win, but no longer significantly — we report that honestly.

**Slide 13 · Value of the loss rate** (≈ 0:35)
> What is smart storage worth? This curve is the backtest gain as the monthly loss rate changes. Storage pays only below about 12% a month; the chawl sits at 18%, so it never stores. Cold, sensor-monitored storage at 1.8% earns the gain. **[→]** That is the Industry 4.0 value: ₹4,546 a tonne, ₹4.55 a kilo; the extra capital pays back in 1.49 seasons; for a 1,000-tonne FPO, about ₹45.5 lakh a year.

**Slide 14 · Implications** (≈ 0:40)
> Three takeaways. FPOs: store in cold or monitored storage and sell September to November, not at the April low. Buffer stocks: don't hold them in chawls — NAFED lost about 53% of its 2019 buffer. Industry 4.0: sensors that measure the loss rate turn storage from a gamble into a plan. **[→]** Limitations: our price is a composite about 10% below Lasalgaon; H1 is an association; we assume the FPO is a price-taker — 1,000 tonnes is 3.6% of Lasalgaon's April arrivals; eight seasons is a small sample; and the all-India gain is not significant once extra costs are added.

**Slide 15 · Thank you** (≈ 0:10)
> Thank you. Everything — data, code, report and this deck — is reproducible from the repository on the QR code. We are happy to take your questions.

---

## Likely questions — short answers (whoever owns the part answers)

**Raghuram — data**
- *Why not use Lasalgaon prices directly?* Lasalgaon APMC has zero rows in the Agmarknet/Mendeley dataset. We built an arrival-weighted Maharashtra composite from 96 markets and checked it against NHRDF's official Lasalgaon series: r = 0.99 over 66 months. It runs about 10% below Lasalgaon in level, so absolute rupee gains are conservative.
- *How did you clean it?* One row per market-day (varieties repeat the same tonnage — summing would double-count 19.8 lakh t), arrival-weighted modal price, 132 monthly prices with none missing.

**Parashmani — H1**
- *Is β = −0.44 causal?* No. It is an association with month and year fixed effects and HAC errors. Adding last month's price shrinks it to about −0.01, so price momentum explains much of it. We use H1 to understand the market, not to drive the plan.
- *Why logs?* β is then an elasticity: 10% more arrivals ↔ about 4% lower price.

**Kathan — forecast**
- *Why regression and not Holt-Winters?* We picked on validation seasons 2019–22 only (regression 36.9% MAPE, best). On the locked 2023–24 test two smoothing models did slightly better; switching after seeing the test would be data snooping.
- *29.5% error is high — does the plan still work?* The LP needs the season's shape, not exact levels. Direction was right in 15 of 16 months, the bias is −17% (too low, so storage is understated), and the backtest pays the plan at actual prices: +₹4,546/t.

**Aaryan — LP**
- *Where do δ = 18% and 1.8% come from?* ICAR storage losses over 120 days: 54.89% in a chawl, 5–7.14% in cold storage, converted to a monthly rate (1 − 0.5489)^(1/4) → 18.05%/month; cold → 1.83%/month.
- *Why an LP and not dynamic programming / stochastic?* Prices are taken from the March forecast (one scenario), all constraints are linear, and an LP gives a guaranteed optimum plus shadow prices that the FPO can act on. Re-planning each month with a fresh forecast is a natural extension.
- *Doesn't selling 1,000 t move the price?* 1,000 t is 3.6% of Lasalgaon's average April arrivals; with β = −0.44 that is about a 1.6% price effect, so the price-taker assumption is reasonable.
- *What do the shadow prices mean?* +1 t of storage capacity is worth ₹4,028; +1 t/month of handling ₹6,526; the April loan sale (250 t) is not binding, so it costs ₹0.

**Yash — all-India & Industry 4.0**
- *Is the all-India result significant?* Base case: 114 of 118 markets gain, mean +₹3,692/t, 6 of 8 seasons positive, p = 0.04. With a 1% fee, ₹500/t selling cost and 1%/month quality discount, 105 still gain but p = 0.11 — we say so on the slide.
- *Where is the Industry 4.0 part?* The value is entirely in the loss rate δ: storage only pays below about 12.4%/month. Sensor-monitored cold storage (temperature, humidity, gas) is what keeps δ near 1.8% and lets the FPO plan around it. Uplift ₹4,546/t over the chawl, payback 1.49 seasons on ₹16,667/t vs ₹7,000/t capital.
- *Which markets lose?* Four, all with small losses: Pehowa (Haryana, −₹731/t), Shahjahanpur (UP), Dehradoon and Vikasnagar (Uttarakhand); every other market gains.
