"""
Kanda Code — When should onion farmers sell their crop?
Core analysis library (data -> EDA -> H1 regression -> forecasting -> LP -> backtest -> sensitivity).

Every number in the report, slides, viva guide and Excel model is produced by this file.
Run:  python src/run_all.py      (writes outputs/ and data/processed/)

Units used throughout
  raw data       : price in Rs per quintal (1 quintal = 100 kg), arrivals in tonnes
  LP / backtest  : price in Rs per tonne  (= Rs/quintal x 10)
  reporting      : Rs per kg              (= Rs/quintal / 100)
"""
from __future__ import annotations

import json
import warnings
from dataclasses import dataclass, asdict, field
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]
RAW_PARQUET = ROOT / "data" / "raw" / "onion_2014_2024.parquet"
RAW_NHRDF = ROOT / "data" / "raw" / "nhrdf" / "LasalgaonOnionData_NHRDF.csv"
PROC = ROOT / "data" / "processed"
OUT = ROOT / "outputs"
FIG = OUT / "figures"
TAB = OUT / "tables"

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
SEASON = ["Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]  # t = 1..9

# ---------------------------------------------------------------------------
# 1. DATA
# ---------------------------------------------------------------------------
PRICE_MIN, PRICE_MAX = 50.0, 20000.0  # Rs/quintal plausibility band (Rs 0.5 - 200 per kg)


def load_raw(columns=None) -> pd.DataFrame:
    cols = columns or ["date", "state", "district", "market", "variety", "grade",
                       "arrivals_tonnes", "min_price_rs_qtl", "max_price_rs_qtl", "modal_price_rs_qtl"]
    if not RAW_PARQUET.exists():
        raise FileNotFoundError(
            f"{RAW_PARQUET} is missing. It is 113 MB, so it ships as a GitHub release asset, not in git. Download it with\n"
            "  gh release download v1.0 -R 23f2003700/Kanda-Code -p onion_2014_2024.parquet -D data/raw\n"
            "or from https://github.com/23f2003700/Kanda-Code/releases/download/v1.0/onion_2014_2024.parquet")
    return pd.read_parquet(RAW_PARQUET, columns=cols)


def clean_maharashtra(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Keep Maharashtra onion records and apply transparent quality rules. Returns (clean, log)."""
    log = {"rows_all_india": int(len(df))}
    mh = df[df["state"] == "Maharashtra"].copy()
    log["rows_maharashtra"] = int(len(mh))
    log["markets_maharashtra"] = int(mh["market"].nunique())
    log["lasalgaon_rows_in_main_dataset"] = int(mh["market"].str.contains("lasal", case=False, na=False).sum())
    bad_price = ~mh["modal_price_rs_qtl"].between(PRICE_MIN, PRICE_MAX)
    bad_arr = ~(mh["arrivals_tonnes"] > 0)
    dup = mh.duplicated(subset=["date", "market", "variety", "grade"], keep="first")
    log["dropped_price_outside_band"] = int(bad_price.sum())
    log["dropped_nonpositive_arrivals"] = int((bad_arr & ~bad_price).sum())
    log["dropped_duplicates"] = int((dup & ~bad_price & ~bad_arr).sum())
    mh = mh[~bad_price & ~bad_arr & ~dup].copy()
    # min <= modal <= max consistency (flag only; modal is what we use)
    incons = ~((mh["min_price_rs_qtl"] <= mh["modal_price_rs_qtl"]) & (mh["modal_price_rs_qtl"] <= mh["max_price_rs_qtl"]))
    log["flag_min_modal_max_inconsistent"] = int(incons.sum())
    # relative outlier rule: a modal price outside 0.2x-5x of that day's cross-market median is a likely unit/entry error
    day_med = mh.groupby("date")["modal_price_rs_qtl"].transform("median")
    rel_bad = (mh["modal_price_rs_qtl"] < 0.2 * day_med) | (mh["modal_price_rs_qtl"] > 5 * day_med)
    log["dropped_relative_price_outliers"] = int(rel_bad.sum())
    mh = mh[~rel_bad].copy()
    log["rows_clean_records"] = int(len(mh))
    # Collapse to ONE row per market-day. Agmarknet repeats a market's total arrivals on each variety/grade row
    # (e.g. Red / Local / Other on the same day) -> summing rows would double-count tonnage.
    g = mh.groupby(["date", "market"])
    n = g["arrivals_tonnes"].transform("size")
    same = g["arrivals_tonnes"].transform(lambda a: a.nunique() == 1)
    multi = n > 1
    log["market_days_with_multiple_variety_rows"] = int(mh[multi].groupby(["date", "market"]).ngroups)
    log["multi_row_market_days_with_repeated_arrivals_pct"] = round(float(
        mh[multi].groupby(["date", "market"])["arrivals_tonnes"].nunique().eq(1).mean() * 100), 1) if multi.any() else 0.0
    rep = mh[multi & same]
    log["tonnes_double_counted_if_rows_summed"] = round(float((rep["arrivals_tonnes"] * (1 - 1 / n[multi & same])).sum()), 0)

    def _collapse(x):
        a = x["arrivals_tonnes"].to_numpy(); p = x["modal_price_rs_qtl"].to_numpy()
        if len(a) == 1:
            return pd.Series({"arrivals_tonnes": a[0], "modal_price_rs_qtl": p[0], "variety_rows": 1})
        if np.unique(a).size == 1:           # repeated market total -> count once, average the variety prices
            return pd.Series({"arrivals_tonnes": a[0], "modal_price_rs_qtl": p.mean(), "variety_rows": len(a)})
        return pd.Series({"arrivals_tonnes": a.sum(), "modal_price_rs_qtl": np.average(p, weights=a), "variety_rows": len(a)})

    md = (mh.groupby(["date", "market", "district"]).apply(_collapse, include_groups=False).reset_index())
    log["market_days_clean"] = int(len(md))
    log["rows_clean"] = int(len(md))
    log["date_min"] = str(md["date"].min().date())
    log["date_max"] = str(md["date"].max().date())
    return md, log


def _wavg(g, col="modal_price_rs_qtl", w="arrivals_tonnes"):
    return float(np.average(g[col], weights=g[w]))


def build_daily(mh: pd.DataFrame) -> pd.DataFrame:
    g = mh.groupby("date")
    d = pd.DataFrame({
        "price_rs_qtl": g.apply(_wavg, include_groups=False),
        "arrivals_t": g["arrivals_tonnes"].sum(),
        "markets_reporting": g["market"].nunique(),
    })
    d["arrivals_per_market_t"] = d["arrivals_t"] / d["markets_reporting"]
    d.index.name = "date"
    return d


def build_monthly(mh: pd.DataFrame) -> pd.DataFrame:
    x = mh.copy()
    x["ym"] = x["date"].dt.to_period("M")
    g = x.groupby("ym")
    m = pd.DataFrame({
        "price_rs_qtl": g.apply(_wavg, include_groups=False),
        "price_median_rs_qtl": g["modal_price_rs_qtl"].median(),
        "arrivals_t": g["arrivals_tonnes"].sum(),
        "market_days": g.size(),              # distinct (date, market) pairs after collapsing variety rows
        "markets_reporting": g["market"].nunique(),
        "trading_days": g["date"].nunique(),
    })
    m["arrivals_per_market_day_t"] = m["arrivals_t"] / m["market_days"]
    m["arrivals_per_market_t"] = m["arrivals_t"] / m["markets_reporting"]
    full = pd.period_range("2014-01", "2024-12", freq="M")
    m = m.reindex(full)
    m.index.name = "ym"
    m["year"] = m.index.year
    m["month"] = m.index.month
    return m


def build_market_monthly(mh: pd.DataFrame, market: str) -> pd.DataFrame:
    x = mh[mh["market"] == market].copy()
    x["ym"] = x["date"].dt.to_period("M")
    g = x.groupby("ym")
    m = pd.DataFrame({"price_rs_qtl": g.apply(_wavg, include_groups=False), "arrivals_t": g["arrivals_tonnes"].sum(),
                      "trading_days": g["date"].nunique()})
    return m.reindex(pd.period_range("2014-01", "2024-12", freq="M"))


def load_nhrdf() -> pd.DataFrame:
    L = pd.read_csv(RAW_NHRDF)
    L["ym"] = pd.to_datetime(L["Time"], format="%d-%m-%Y").dt.to_period("M")
    L = L.set_index("ym").rename(columns={"Modal Price (Rs/q)": "lasalgaon_price_rs_qtl", "Arrival (q)": "lasalgaon_arrivals_q"})
    L["lasalgaon_arrivals_t"] = L["lasalgaon_arrivals_q"] / 10.0
    return L[["lasalgaon_price_rs_qtl", "lasalgaon_arrivals_t"]]


def validate_against_lasalgaon(monthly: pd.DataFrame, nasik: pd.DataFrame, nh: pd.DataFrame) -> dict:
    j = monthly[["price_rs_qtl"]].join(nh, how="inner").dropna()
    jn = nasik[["price_rs_qtl"]].rename(columns={"price_rs_qtl": "nasik"}).join(nh, how="inner").dropna()
    r = np.corrcoef(j["price_rs_qtl"], j["lasalgaon_price_rs_qtl"])[0, 1]
    rl = np.corrcoef(np.log(j["price_rs_qtl"]), np.log(j["lasalgaon_price_rs_qtl"]))[0, 1]
    ratio = (j["price_rs_qtl"] / j["lasalgaon_price_rs_qtl"])
    mape = float((ratio - 1).abs().mean() * 100)
    # month-to-month direction agreement
    dm = np.sign(j["price_rs_qtl"].diff()).iloc[1:]
    dl = np.sign(j["lasalgaon_price_rs_qtl"].diff()).iloc[1:]
    dlog_m = np.log(j["price_rs_qtl"]).diff().dropna()
    dlog_l = np.log(j["lasalgaon_price_rs_qtl"]).diff().dropna()
    # season shape: April -> best later month rise, each overlapping year (what the LP actually exploits)
    shape = []
    for y in sorted(set(j.index.year)):
        a = j[j.index.year == y]
        if 4 in a.index.month and (a.index.month > 4).sum() >= 5:
            aa = a.set_index(a.index.month)
            shape.append({"year": int(y),
                          "rise_composite_pct": round(float(aa.loc[5:, "price_rs_qtl"].max() / aa.loc[4, "price_rs_qtl"] * 100 - 100), 1),
                          "rise_lasalgaon_pct": round(float(aa.loc[5:, "lasalgaon_price_rs_qtl"].max() / aa.loc[4, "lasalgaon_price_rs_qtl"] * 100 - 100), 1)})
    # Nasik APMC (the only Nashik-district market in the main data) vs composite, test years
    jc = monthly[["price_rs_qtl"]].join(nasik[["price_rs_qtl"]].rename(columns={"price_rs_qtl": "nasik"}), how="inner").dropna()
    jt = jc[jc.index.year >= 2023]
    return {
        "overlap_months": int(len(j)), "overlap_start": str(j.index.min()), "overlap_end": str(j.index.max()),
        "pearson_r_levels": round(float(r), 4), "pearson_r_logs": round(float(rl), 4),
        "pearson_r_monthly_log_changes": round(float(np.corrcoef(dlog_m, dlog_l)[0, 1]), 4),
        "mean_ratio_mh_to_lasalgaon": round(float(ratio.mean()), 3),
        "mean_abs_pct_gap": round(mape, 2),
        "direction_agreement_pct": round(float((dm == dl).mean() * 100), 1),
        "season_shape": shape,
        "nasik_overlap_months": int(len(jn)),
        "nasik_pearson_r": round(float(np.corrcoef(jn["nasik"], jn["lasalgaon_price_rs_qtl"])[0, 1]), 4),
        "composite_vs_nasik_r_2023_2024": round(float(np.corrcoef(jt["price_rs_qtl"], jt["nasik"])[0, 1]), 4),
        "composite_over_nasik_ratio_2023_2024": round(float((jt["price_rs_qtl"] / jt["nasik"]).mean()), 3),
    }


def spotcheck_2020_2024(monthly: pd.DataFrame) -> dict:
    """Compare our monthly series with independently reported Lasalgaon prices (MSAMB weekly reports, news)."""
    p = ROOT / "data" / "validation" / "lasalgaon_reported_prices_2020_2024.csv"
    sc = pd.read_csv(p)
    sc["ym"] = pd.PeriodIndex(sc["month"], freq="M")
    sc["ours_rs_qtl"] = monthly["price_rs_qtl"].reindex(sc["ym"]).values
    sc["gap_pct"] = (sc["ours_rs_qtl"] / sc["reported_rs_qtl"] - 1) * 100
    ms = sc[sc["source_type"] == "MSAMB weekly report"]
    return {"points": int(len(sc)), "median_abs_gap_pct": round(float(sc["gap_pct"].abs().median()), 1),
            "median_signed_gap_pct": round(float(sc["gap_pct"].median()), 1),
            "share_ours_below_pct": round(float((sc["gap_pct"] < 0).mean() * 100), 0),
            "pearson_r": round(float(np.corrcoef(sc["ours_rs_qtl"], sc["reported_rs_qtl"])[0, 1]), 3),
            "msamb_points": int(len(ms)), "msamb_median_signed_gap_pct": round(float(ms["gap_pct"].median()), 1),
            "rows": sc.drop(columns=["ym"]).round(1).to_dict(orient="records")}


# ---------------------------------------------------------------------------
# 2. EDA
# ---------------------------------------------------------------------------

def seasonal_profile(monthly: pd.DataFrame) -> pd.DataFrame:
    """Seasonal price index = month price / that year's average price (ratio-to-annual-mean), averaged across years."""
    m = monthly.dropna(subset=["price_rs_qtl"]).copy()
    m["annual_mean"] = m.groupby("year")["price_rs_qtl"].transform("mean")
    m["idx"] = m["price_rs_qtl"] / m["annual_mean"]
    m["arr_share"] = m["arrivals_per_market_day_t"] / m.groupby("year")["arrivals_per_market_day_t"].transform("mean")
    prof = m.groupby("month").agg(price_index_mean=("idx", "mean"), price_index_min=("idx", "min"),
                                  price_index_max=("idx", "max"), arrivals_index_mean=("arr_share", "mean"),
                                  price_mean_rs_qtl=("price_rs_qtl", "mean"))
    prof.index = [MONTHS[i - 1] for i in prof.index]
    return prof


def eda_stats(monthly: pd.DataFrame, daily: pd.DataFrame) -> dict:
    m = monthly.dropna(subset=["price_rs_qtl"])
    yr = m.groupby("year")["price_rs_qtl"].agg(["mean", "min", "max", "std"])
    yr["cv_pct"] = yr["std"] / yr["mean"] * 100
    yr["max_over_min"] = yr["max"] / yr["min"]
    mom = m["price_rs_qtl"].pct_change().dropna() * 100
    # within-season rise: Apr price -> max of May..Dec (HINDSIGHT upper bound on what a storer could have earned)
    rows = []
    for y in range(2014, 2025):
        s = m[m["year"] == y].set_index("month")["price_rs_qtl"]
        if 4 in s.index:
            later = s.loc[[k for k in range(5, 13) if k in s.index]]
            rows.append({"year": y, "apr": s.loc[4], "best_later": later.max(),
                         "best_month": MONTHS[int(later.idxmax()) - 1], "rise_pct": (later.max() / s.loc[4] - 1) * 100,
                         "apr_to_nov_pct": (s.loc[11] / s.loc[4] - 1) * 100 if 11 in s.index else np.nan})
    rise = pd.DataFrame(rows)
    mret = np.log(m["price_rs_qtl"]).diff().dropna()
    return {
        "monthly_obs": int(len(m)),
        "price_mean_rs_kg": round(float(m["price_rs_qtl"].mean() / 100), 2),
        "price_min_rs_kg": round(float(m["price_rs_qtl"].min() / 100), 2),
        "price_min_month": str(m["price_rs_qtl"].idxmin()),
        "price_max_rs_kg": round(float(m["price_rs_qtl"].max() / 100), 2),
        "price_max_month": str(m["price_rs_qtl"].idxmax()),
        "overall_cv_pct": round(float(m["price_rs_qtl"].std() / m["price_rs_qtl"].mean() * 100), 1),
        "mean_within_year_cv_pct": round(float(yr["cv_pct"].mean()), 1),
        "mean_max_over_min_within_year": round(float(yr["max_over_min"].mean()), 2),
        "mom_change_sd_pct": round(float(mom.std()), 1),
        "share_months_abs_change_gt_20pct": round(float((mom.abs() > 20).mean() * 100), 1),
        "monthly_log_return_sd_pct": round(float(mret.std() * 100), 1),
        "annualised_vol_from_monthly_pct": round(float(mret.std() * np.sqrt(12) * 100), 1),
        "season_rise": rise.round(1).to_dict(orient="records"),
        "mean_rise_apr_to_best_pct_hindsight": round(float(rise["rise_pct"].mean()), 1),
        "median_rise_apr_to_best_pct_hindsight": round(float(rise["rise_pct"].median()), 1),
        "median_rise_apr_to_nov_pct": round(float(rise["apr_to_nov_pct"].median()), 1),
        "years_nov_above_apr": int((rise["apr_to_nov_pct"] > 0).sum()), "years": int(len(rise)),
        "years_best_month": rise["best_month"].value_counts().to_dict(),
        "yearly": yr.round(1).reset_index().to_dict(orient="records"),
    }


# ---------------------------------------------------------------------------
# 3. H1 — price vs arrivals regression
# ---------------------------------------------------------------------------

def h1_regressions(monthly: pd.DataFrame, daily: pd.DataFrame) -> dict:
    """H1: log price on log arrivals with month-of-year and year dummies (OLS; Newey-West HAC SEs as a check).
    The coefficient is the price flexibility w.r.t. arrivals: an equilibrium ASSOCIATION, not a causal demand elasticity."""
    import statsmodels.formula.api as smf

    m = monthly.dropna(subset=["price_rs_qtl"]).copy()
    m["lnP"] = np.log(m["price_rs_qtl"])
    m["lnA"] = np.log(m["arrivals_per_market_day_t"])
    m["lnA_lag1"] = m["lnA"].shift(1)
    m["lnP_lag1"] = m["lnP"].shift(1)
    m["lnA_total"] = np.log(m["arrivals_t"])
    m["lnA_per_market"] = np.log(m["arrivals_per_market_t"])
    m["mon"] = m["month"].astype(str)
    m["yr"] = m["year"].astype(str)
    m["covid"] = ((m.index >= pd.Period("2020-04", "M")) & (m.index <= pd.Period("2020-05", "M"))).astype(int)

    def fit(f, v, data, lags=3):
        ols = smf.ols(f, data=data).fit()
        hac = smf.ols(f, data=data).fit(cov_type="HAC", cov_kwds={"maxlags": lags})
        return {"formula": f, "n": int(ols.nobs), "elasticity": round(float(ols.params[v]), 4),
                "se_ols": round(float(ols.bse[v]), 4), "t_ols": round(float(ols.tvalues[v]), 2),
                "p_ols": float(ols.pvalues[v]), "se_hac": round(float(hac.bse[v]), 4), "p_hac": float(hac.pvalues[v]),
                "r2": round(float(ols.rsquared), 3), "adj_r2": round(float(ols.rsquared_adj), 3),
                "ci95_low": round(float(ols.conf_int().loc[v, 0]), 4), "ci95_high": round(float(ols.conf_int().loc[v, 1]), 4),
                "durbin_watson": round(float(__import__("statsmodels.stats.stattools", fromlist=["durbin_watson"]).durbin_watson(ols.resid)), 2)}

    out = {
        "M1_simple": fit("lnP ~ lnA", "lnA", m),
        "M2_month_FE": fit("lnP ~ lnA + C(mon)", "lnA", m),
        "M3_month_year_FE": fit("lnP ~ lnA + C(mon) + C(yr)", "lnA", m),
        "M4_lagged_arrivals": fit("lnP ~ lnA_lag1 + C(mon) + C(yr)", "lnA_lag1", m.dropna(subset=["lnA_lag1"])),
        "M5_dynamic_with_lagged_price": fit("lnP ~ lnA + lnP_lag1 + C(mon) + C(yr)", "lnA", m.dropna(subset=["lnP_lag1"])),
    }
    mm = m.dropna(subset=["lnP_lag1"])
    out["M5_dynamic_with_lagged_price"]["lagged_price_coef"] = round(float(smf.ols("lnP ~ lnA + lnP_lag1 + C(mon) + C(yr)", data=mm).fit().params["lnP_lag1"]), 3)
    # robustness to how arrivals are normalised (market coverage doubles 2014 -> 2024)
    out["robust_normalisation"] = {
        "per_market_day (headline)": {k: out["M3_month_year_FE"][k] for k in ("elasticity", "p_hac")},
        "per_market_reporting": {k: fit("lnP ~ lnA_per_market + C(mon) + C(yr)", "lnA_per_market", m)[k] for k in ("elasticity", "p_hac")},
        "total_arrivals": {k: fit("lnP ~ lnA_total + C(mon) + C(yr)", "lnA_total", m)[k] for k in ("elasticity", "p_hac")},
        "per_market_day_excl_covid_AprMay2020": {k: fit("lnP ~ lnA + C(mon) + C(yr)", "lnA", m[m["covid"] == 0])[k] for k in ("elasticity", "p_hac")},
    }
    # reverse causality check: do past prices predict arrivals? (farmers release stock when prices are high)
    rc = fit("lnA ~ lnP_lag1 + C(mon) + C(yr)", "lnP_lag1", mm)
    out["reverse_causality_lnA_on_lagged_price"] = {k: rc[k] for k in ("elasticity", "p_hac", "n")}
    # daily sign check (Maharashtra aggregate), HAC with 30 lags because daily residuals are highly autocorrelated
    d = daily.copy()
    d = d[d["arrivals_per_market_t"] > 0]
    d["lnP"] = np.log(d["price_rs_qtl"]); d["lnA"] = np.log(d["arrivals_per_market_t"])
    d["mon"] = d.index.month.astype(str); d["yr"] = d.index.year.astype(str); d["dow"] = d.index.dayofweek.astype(str)
    out["D1_daily_sign_check"] = fit("lnP ~ lnA + C(mon) + C(yr) + C(dow)", "lnA", d, lags=30)
    main = out["M3_month_year_FE"]
    out["headline"] = {
        "spec": "M3_month_year_FE",
        "elasticity": main["elasticity"],
        "interpretation": (f"Months with 10% heavier arrivals (per market-day) have prices about {abs(main['elasticity'])*10:.0f}% lower, "
                           "holding month-of-year and year constant. This is an association, not a causal elasticity."),
        "one_sided_p_hac": main["p_hac"] / 2 if main["elasticity"] < 0 else 1 - main["p_hac"] / 2,
        "H1_supported": bool(main["elasticity"] < 0 and main["p_hac"] < 0.05),
    }
    return out


def price_taker_check(monthly: pd.DataFrame, max_april_sale: float, U: float, elasticity: float, nh: pd.DataFrame) -> dict:
    """Order-of-magnitude check: FPO sales as a share of Lasalgaon's own monthly arrivals (NHRDF, 2014-19)."""
    las = nh["lasalgaon_arrivals_t"].dropna()
    las = las[las.index.year >= 2014]
    apr = float(las[las.index.month == 4].mean())
    octnov = float(las[las.index.month.isin([10, 11])].mean())
    return {
        "lasalgaon_mean_april_arrivals_t": round(apr, 0),
        "lasalgaon_mean_oct_nov_arrivals_t": round(octnov, 0),
        "fpo_max_april_sale_t": max_april_sale, "fpo_max_later_monthly_sale_t": U,
        "share_april_pct": round(max_april_sale / apr * 100, 2), "share_oct_nov_pct": round(U / octnov * 100, 2),
        "implied_price_impact_april_pct": round(abs(elasticity) * max_april_sale / apr * 100, 2),
        "implied_price_impact_oct_nov_pct": round(abs(elasticity) * U / octnov * 100, 2),
        "note": "Elasticity is from the Maharashtra composite; applying it to one APMC's tonnage is an order-of-magnitude check.",
    }


# ---------------------------------------------------------------------------
# 4. FORECASTING (monthly price, multi-step from a March origin)
# ---------------------------------------------------------------------------

def _seasonal_indices(train: pd.Series) -> pd.Series:
    """Classical ratio-to-centred-moving-average seasonal indices (multiplicative), normalised to mean 1."""
    cma = train.rolling(12, center=True).mean().rolling(2).mean().shift(-1)
    ratio = (train / cma).dropna()
    si = ratio.groupby(ratio.index.month).mean()
    si = si.reindex(range(1, 13)).fillna(1.0)
    return si / si.mean()


def forecast(train: pd.Series, h: int, method: str) -> np.ndarray:
    """train: monthly price Series with PeriodIndex (no NaN). Returns h-step forecasts (Rs/q)."""
    y = train.astype(float)
    last = y.index[-1]
    fut = pd.period_range(last + 1, periods=h, freq="M")
    fm = np.array([p.month for p in fut])
    if method == "naive":
        return np.repeat(y.iloc[-1], h)
    if method == "seasonal_naive":
        return np.array([y.loc[p - 12] if (p - 12) in y.index else y.iloc[-1] for p in fut])
    if method == "moving_average_12":
        return np.repeat(y.iloc[-12:].mean(), h)
    if method == "seasonal_moving_average":  # deseasonalised 12-m MA level x seasonal index
        si = _seasonal_indices(y)
        des = y / si.reindex(y.index.month).values
        level = des.iloc[-12:].mean()
        return level * si.reindex(fm).values
    if method == "seasonal_ses":  # simple exponential smoothing on deseasonalised series
        from statsmodels.tsa.holtwinters import SimpleExpSmoothing
        si = _seasonal_indices(y)
        des = (y / si.reindex(y.index.month).values).values
        fit = SimpleExpSmoothing(np.log(des), initialization_method="estimated").fit()
        level = np.exp(fit.forecast(1)[0])
        return level * si.reindex(fm).values
    if method in ("seasonal_ses_long", "seasonal_moving_average_long"):
        # seasonal indices estimated on 28 years: NHRDF Lasalgaon 1996-2013 (all before any forecast origin) + our series
        hist = LONG_HISTORY if LONG_HISTORY is not None else y.iloc[:0]
        si = _seasonal_indices(pd.concat([hist[hist.index < y.index[0]], y]))
        des = y / si.reindex(y.index.month).values
        if method == "seasonal_moving_average_long":
            level = des.iloc[-12:].mean()
        else:
            from statsmodels.tsa.holtwinters import SimpleExpSmoothing
            fit = SimpleExpSmoothing(np.log(des.values), initialization_method="estimated").fit()
            level = np.exp(fit.forecast(1)[0])
        return level * si.reindex(fm).values
    if method == "holt_winters":  # additive (damped) trend + additive seasonality on log price
        from statsmodels.tsa.holtwinters import ExponentialSmoothing
        fit = ExponentialSmoothing(np.log(y.values), trend="add", damped_trend=True, seasonal="add",
                                   seasonal_periods=12, initialization_method="estimated").fit()
        return np.exp(fit.forecast(h))
    if method == "regression_trend_season":  # OLS: log P = a + b*t + month dummies
        t = np.arange(len(y))
        X = np.column_stack([np.ones(len(y)), t] + [(y.index.month == k).astype(float) for k in range(2, 13)])
        beta, *_ = np.linalg.lstsq(X, np.log(y.values), rcond=None)
        tf = np.arange(len(y), len(y) + h)
        Xf = np.column_stack([np.ones(h), tf] + [(fm == k).astype(float) for k in range(2, 13)])
        return np.exp(Xf @ beta)
    if method == "regression_level_season":  # OLS: log P_t = a + c*log P_{origin} anchor via last-12m level + month dummies
        # seasonal regression on deviations from the trailing 12-month mean (level-anchored seasonality)
        ly = np.log(y)
        anchor = ly.rolling(12).mean().shift(1)
        dfr = pd.DataFrame({"dev": ly - anchor, "m": y.index.month}).dropna()
        mdev = dfr.groupby("m")["dev"].mean().reindex(range(1, 13)).fillna(0)
        base = ly.iloc[-12:].mean()
        return np.exp(base + mdev.reindex(fm).values)
    raise ValueError(method)


LONG_HISTORY = None  # set by run_all: NHRDF Lasalgaon monthly price 1996-2013 (Rs/quintal)

FORECAST_METHODS = ["naive", "seasonal_naive", "moving_average_12", "seasonal_moving_average",
                    "seasonal_ses", "holt_winters", "regression_trend_season", "regression_level_season",
                    "seasonal_moving_average_long", "seasonal_ses_long"]
FORECAST_LABELS = {
    "naive": "Naive (last month)", "seasonal_naive": "Seasonal naive (same month last year)",
    "moving_average_12": "12-month moving average", "seasonal_moving_average": "Seasonal index x moving average",
    "seasonal_ses": "Seasonal index x exponential smoothing", "holt_winters": "Holt-Winters (damped trend + seasonality)",
    "regression_trend_season": "Regression: trend + month dummies", "regression_level_season": "Regression: level + month effects",
    "seasonal_moving_average_long": "28-yr seasonal index x moving average",
    "seasonal_ses_long": "28-yr seasonal index x exponential smoothing",
}


def fitted_smoothing_params(train: pd.Series, method: str) -> dict:
    """Report the fitted smoothing constants (viva question: 'what was your alpha?')."""
    from statsmodels.tsa.holtwinters import SimpleExpSmoothing, ExponentialSmoothing
    y = train.astype(float)
    if method in ("seasonal_ses", "seasonal_ses_long"):
        hist = LONG_HISTORY if (method.endswith("long") and LONG_HISTORY is not None) else y.iloc[:0]
        si = _seasonal_indices(pd.concat([hist[hist.index < y.index[0]], y]))
        des = (y / si.reindex(y.index.month).values).values
        f = SimpleExpSmoothing(np.log(des), initialization_method="estimated").fit()
        return {"alpha": round(float(f.params["smoothing_level"]), 3),
                "seasonal_index": {MONTHS[k - 1]: round(float(v), 3) for k, v in si.items()}}
    if method == "holt_winters":
        f = ExponentialSmoothing(np.log(y.values), trend="add", damped_trend=True, seasonal="add", seasonal_periods=12,
                                 initialization_method="estimated").fit()
        return {k: round(float(f.params[n]), 3) for k, n in [("alpha", "smoothing_level"), ("beta", "smoothing_trend"),
                                                              ("gamma", "smoothing_seasonal"), ("phi", "damping_trend")]}
    return {}


def _err(actual, pred, season_len=9):
    a, p = np.asarray(actual, float), np.asarray(pred, float)
    # direction hits are counted WITHIN each season only (no Dec -> next Apr jump)
    hits = []
    for i in range(0, len(a), season_len):
        aa, pp = a[i:i + season_len], p[i:i + season_len]
        hits.extend(np.sign(np.diff(pp)) == np.sign(np.diff(aa)))
    return {"MAPE": float(np.mean(np.abs(p - a) / a) * 100), "RMSE_rs_qtl": float(np.sqrt(np.mean((p - a) ** 2))),
            "MAE_rs_qtl": float(np.mean(np.abs(p - a))), "bias_pct": float(np.mean((p - a) / a) * 100),
            "direction_hit_pct": float(np.mean(hits) * 100) if hits else np.nan}


def _horizon_errors(series, meth, years):
    A, P, paths = [], [], {}
    for yr in years:
        tr = series[series.index <= pd.Period(f"{yr}-03", "M")]
        fc = forecast(tr, 9, meth)
        act = series[(series.index >= pd.Period(f"{yr}-04", "M")) & (series.index <= pd.Period(f"{yr}-12", "M"))].values
        A.extend(act); P.extend(fc)
        paths[yr] = [round(float(v), 1) for v in fc]
    return {k: round(v, 2) for k, v in _err(A, P).items()}, paths


def evaluate_forecasts(series: pd.Series, valid_years=(2019, 2020, 2021, 2022), test_years=(2023, 2024)) -> dict:
    """Decision-horizon accuracy: origin = end-March, forecast Apr..Dec (9 steps), expanding window.
       The model is SELECTED on the validation seasons 2019-22 and only then scored on the untouched test seasons 2023-24.
       Rolling 1-step-ahead accuracy over the 24 test months is reported as a secondary check."""
    res_v, res_h, res_1, paths = {}, {}, {}, {}
    for meth in FORECAST_METHODS:
        res_v[meth], _ = _horizon_errors(series, meth, valid_years)
        res_h[meth], paths[meth] = _horizon_errors(series, meth, test_years)
        A1, P1 = [], []
        for p in series.index[(series.index.year >= test_years[0]) & (series.index.year <= test_years[-1])]:
            tr = series[series.index < p]
            P1.append(forecast(tr, 1, meth)[0]); A1.append(series.loc[p])
        e = _err(A1, P1, season_len=len(A1))
        res_1[meth] = {k: round(v, 2) for k, v in e.items()}
    best = min(res_v, key=lambda k: res_v[k]["MAPE"])
    best_test = min(res_h, key=lambda k: res_h[k]["MAPE"])
    params = {yr: fitted_smoothing_params(series[series.index <= pd.Period(f"{yr}-03", "M")], best) for yr in test_years}
    return {"validation_horizon": res_v, "decision_horizon": res_h, "one_step": res_1, "paths": paths,
            "best_method": best, "best_method_on_test_for_reference": best_test, "fitted_params_best": params,
            "selection_rule": f"lowest Apr-Dec MAPE on validation seasons {valid_years[0]}-{valid_years[-1]}; scored on {test_years[0]}-{test_years[-1]}"}


# ---------------------------------------------------------------------------
# 5. LINEAR PROGRAMME — the sell-or-store plan
# ---------------------------------------------------------------------------

@dataclass
class LPParams:
    Q: float = 1000.0     # tonnes harvested and held by the FPO in April
    C: float = 700.0      # storage capacity, tonnes
    L: float = 250.0      # minimum sale in April (crop-loan repayment), tonnes  (Q - C = 300 > L, so constraints are not degenerate)
    U: float = 300.0      # max tonnes the FPO can grade, bag and truck to market in one month
    delta: float = 0.18   # monthly storage loss rate
    h: float = 250.0      # storage cost, Rs per tonne per month
    T: int = 9            # Apr..Dec
    first_is_harvest: bool = True  # month 1 is April harvest (min-sale L applies, no handling cap)


SCENARIOS = {
    # A: no storage. With C = 0 the stock-balance forces x1 = Q (U is lifted in April so the problem stays feasible)
    "A": {"name": "No storage (sell all at harvest)", "C": 0.0, "delta": 0.0, "h": 0.0},
    "B": {"name": "Ventilated kanda chawl", "delta": 1 - (1 - 0.5489) ** (1 / 4), "h": 250.0},
    "C": {"name": "Cold / IoT-monitored storage", "delta": 1 - (1 - 0.0714) ** (1 / 4), "h": 700.0},
}


def solve_lp(prices_rs_t, p: LPParams, return_duals=True) -> dict:
    """Maximise sum_t (price_t * x_t) - h * sum_t s_t
       s_1 = Q - x_1 ; s_t = (1-delta) s_{t-1} - x_t (t>=2) ; s_t <= C ; x_1 >= L ; x_t <= U (t>=2) ; s_T = 0 ; x,s >= 0
       Solved with PuLP (CBC); duals from SciPy linprog (HiGHS) on the identical model."""
    import pulp
    T = p.T
    prices = np.asarray(prices_rs_t, float)[:T]
    m = pulp.LpProblem("kanda_sell_or_store", pulp.LpMaximize)
    x = [pulp.LpVariable(f"x{t+1}", lowBound=0) for t in range(T)]
    s = [pulp.LpVariable(f"s{t+1}", lowBound=0) for t in range(T)]
    m += pulp.lpSum(prices[t] * x[t] for t in range(T)) - p.h * pulp.lpSum(s)
    m += (s[0] == p.Q - x[0]), "harvest_balance"
    for t in range(1, T):
        m += (s[t] == (1 - p.delta) * s[t - 1] - x[t]), f"stock_balance_{t+1}"
    for t in range(T):
        m += (s[t] <= p.C), f"capacity_{t+1}"
    m += (x[0] >= min(p.L, p.Q)), "min_harvest_sale"
    for t in range(0 if not p.first_is_harvest else 1, T):
        m += (x[t] <= p.U), f"handling_cap_{t+1}"
    m += (s[T - 1] == 0), "clear_by_december"
    status = m.solve(pulp.PULP_CBC_CMD(msg=False))
    if pulp.LpStatus[m.status] != "Optimal":
        return {"status": pulp.LpStatus[m.status]}
    xs = np.array([v.value() for v in x]); ss = np.array([v.value() for v in s])
    xs[np.abs(xs) < 1e-7] = 0; ss[np.abs(ss) < 1e-7] = 0
    out = {"status": "Optimal", "x": xs.tolist(), "s": ss.tolist(),
           "objective": float(pulp.value(m.objective)), "revenue": float(prices @ xs), "storage_cost": float(p.h * ss.sum()),
           "sold_total": float(xs.sum()), "lost_total": float(p.Q - xs.sum())}
    if return_duals:
        out.update(_duals_scipy(prices, p, out["objective"]))
    return out


def _duals_scipy(prices, p: LPParams, pulp_obj: float) -> dict:
    """Same LP in standard form for SciPy/HiGHS to obtain shadow prices (cross-check of PuLP objective)."""
    from scipy.optimize import linprog
    T = p.T
    n = 2 * T  # [x1..xT, s1..sT]
    c = np.concatenate([-prices, np.full(T, p.h)])  # minimise negative profit
    Aeq, beq = [], []
    r = np.zeros(n); r[0] = 1; r[T] = 1; Aeq.append(r); beq.append(p.Q)            # x1 + s1 = Q
    for t in range(1, T):
        r = np.zeros(n); r[t] = 1; r[T + t] = 1; r[T + t - 1] = -(1 - p.delta); Aeq.append(r); beq.append(0)
    r = np.zeros(n); r[2 * T - 1] = 1; Aeq.append(r); beq.append(0)                 # s_T = 0
    first_ub = None if p.first_is_harvest else p.U
    bounds = [(min(p.L, p.Q), first_ub)] + [(0, p.U)] * (T - 1) + [(0, p.C)] * T
    res = linprog(c, A_eq=np.array(Aeq), b_eq=np.array(beq), bounds=bounds, method="highs")
    cap_duals = (-res.upper.marginals[T:]).round(2).tolist()          # Rs per extra tonne of capacity in month t
    hand_duals = (-res.upper.marginals[1:T]).round(2).tolist()
    L_dual = float(-res.lower.marginals[0])
    Q_dual = float(-res.eqlin.marginals[0])
    return {"scipy_objective": float(-res.fun), "objective_match": bool(abs(-res.fun - pulp_obj) <= 1.0),
            "objective_abs_diff_rs": round(float(abs(-res.fun - pulp_obj)), 4),
            "shadow_capacity_by_month": cap_duals, "shadow_capacity_total": round(float(sum(cap_duals)), 2),
            "shadow_handling_by_month": hand_duals, "shadow_min_harvest_sale": round(L_dual, 2),
            "shadow_extra_tonne_harvest": round(Q_dual, 2)}


def scenario_params(base: LPParams, key: str) -> LPParams:
    sp = SCENARIOS[key]
    q = LPParams(**asdict(base))
    q.delta = sp.get("delta", q.delta); q.h = sp.get("h", q.h); q.C = sp.get("C", q.C)
    if key == "A":
        q.L = q.Q
    return q


def marginal_values(prices_rs_t, p: LPParams) -> dict:
    """Shadow prices VERIFIED by re-solving with each right-hand side moved +1 and -1 tonne.
       Reports both one-sided values, because at a degenerate vertex the solver's dual is only one of several valid values."""
    if p.C <= 0 or p.L >= p.Q:
        return {"applicable": False,
                "note": "Scenario A: selling all at harvest fixes every decision (C = 0, L = Q), so there are no meaningful shadow prices."}
    base = solve_lp(prices_rs_t, p, return_duals=False)["objective"]
    out = {"applicable": True}
    for name, field in [("capacity_C", "C"), ("loan_sale_L", "L"), ("harvest_Q", "Q"), ("handling_cap_U", "U")]:
        res = {}
        for d, lab in [(+1, "plus1"), (-1, "minus1")]:
            q = LPParams(**{**asdict(p), field: getattr(p, field) + d})
            r = solve_lp(prices_rs_t, q, return_duals=False)
            res[lab] = round(r["objective"] - base, 1) if r.get("status") == "Optimal" else None
        out[name] = {"gain_if_plus_1t": res["plus1"], "loss_if_minus_1t": (None if res["minus1"] is None else round(-res["minus1"], 1))}
    out["degenerate_C_equals_Q_minus_L"] = bool(abs(p.Q - p.L - p.C) < 1e-9)
    return out


def evaluate_plan(x, s, actual_prices_rs_t, h) -> dict:
    a = np.asarray(actual_prices_rs_t, float)
    rev = float(a @ np.asarray(x)); cost = float(h * np.sum(s))
    return {"revenue": rev, "storage_cost": cost, "net": rev - cost}


# ---------------------------------------------------------------------------
# 6. BACKTEST
# ---------------------------------------------------------------------------

def season_prices(series: pd.Series, year: int) -> np.ndarray:
    idx = pd.period_range(f"{year}-04", f"{year}-12", freq="M")
    return series.reindex(idx).values * 10.0  # Rs/q -> Rs/t


def rolling_plan(series: pd.Series, year: int, p: LPParams, method: str) -> dict:
    """Rolling-horizon re-planning: at the start of each month t, re-forecast the rest of the season using data
       through month t-1, re-solve the LP from the current stock, implement only this month's sale."""
    T = p.T
    act = season_prices(series, year)
    stock = p.Q
    xs, ss = [], []
    for t in range(T):
        origin = pd.Period(f"{year}-03", "M") + t
        tr = series[series.index <= origin].dropna()
        fc = forecast(tr, T - t, method) * 10.0
        sub = LPParams(Q=stock, C=p.C + 1e-4, L=(p.L if t == 0 else 0.0), U=p.U + 1e-4, delta=p.delta, h=p.h, T=T - t,
                       first_is_harvest=(t == 0))
        sol = solve_lp(fc, sub, return_duals=False)
        if sol.get("status") != "Optimal":
            return {"status": sol.get("status"), "revenue": np.nan, "storage_cost": np.nan, "net": np.nan, "x": [], "s": []}
        x_now = min(sol["x"][0], stock)
        s_now = max(stock - x_now, 0.0)
        if t == T - 1:  # December: everything left is sold (clear-by-December)
            x_now, s_now = stock, 0.0
        xs.append(x_now); ss.append(s_now)
        stock = (1 - p.delta) * s_now
    ev = evaluate_plan(xs, ss, act, p.h)
    return {"x": np.round(xs, 3).tolist(), "s": np.round(ss, 3).tolist(), **ev}


def calendar_plan(sell_months, q: LPParams) -> tuple[list, list]:
    """A fixed calendar rule (no optimisation): sell the forced minimum in April, then up to U tonnes in each
       chosen month (in calendar order), and clear whatever is left in December."""
    x = [0.0] * q.T; s = [0.0] * q.T
    x[0] = max(q.L, q.Q - q.C); s[0] = q.Q - x[0]
    for t in range(1, q.T):
        stock = (1 - q.delta) * s[t - 1]
        if t == q.T - 1:
            x[t] = stock
        elif SEASON[t] in sell_months:
            x[t] = min(q.U, stock)
        s[t] = stock - x[t]
    return x, s


def backtest(series: pd.Series, years, base: LPParams, method: str) -> pd.DataFrame:
    rows = []
    for yr in years:
        tr = series[series.index <= pd.Period(f"{yr}-03", "M")].dropna()
        fc = forecast(tr, 9, method) * 10.0
        act = season_prices(series, yr)
        if np.isnan(act).any():
            continue
        harvest_net = base.Q * act[0]
        # ex-ante calendar rule: the 3 months (May-Dec) with the highest seasonal index known at the origin
        hist = LONG_HISTORY if LONG_HISTORY is not None else tr.iloc[:0]
        si = _seasonal_indices(pd.concat([hist[hist.index < tr.index[0]], tr]))
        top3 = [MONTHS[k - 1] for k in si.loc[5:12].sort_values(ascending=False).index[:3]]
        for key in ["B", "C"]:
            q = scenario_params(base, key)
            for strat, months in [("calendar_rule_exante", top3), ("calendar_rule_hindsight_OctNov", ["Oct", "Nov"])]:
                cx, cs = calendar_plan(months, q)
                ev = evaluate_plan(cx, cs, act, q.h)
                rows.append({"year": yr, "scenario": key, "strategy": strat, **ev, "net_per_t": ev["net"] / base.Q,
                             "gain_vs_harvest_per_t": (ev["net"] - harvest_net) / base.Q, "x": [round(v, 1) for v in cx],
                             "s": [round(v, 1) for v in cs], "sold_t": float(np.sum(cx)), "rule_months": ",".join(months)})
        for key in ["A", "B", "C"]:
            q = scenario_params(base, key)
            plan = solve_lp(fc, q, return_duals=False)
            ev = evaluate_plan(plan["x"], plan["s"], act, q.h)
            oracle = solve_lp(act, q, return_duals=False)
            row = {"year": yr, "scenario": key, "strategy": "forecast_plan", **ev,
                   "net_per_t": ev["net"] / base.Q, "gain_vs_harvest_per_t": (ev["net"] - harvest_net) / base.Q,
                   "oracle_net_per_t": oracle["objective"] / base.Q,
                   "x": [round(v, 1) for v in plan["x"]], "s": [round(v, 1) for v in plan["s"]],
                   "sold_t": float(np.sum(plan["x"])), "forecast_objective_per_t": plan["objective"] / base.Q}
            rows.append(row)
            if key != "A":
                rp = rolling_plan(series, yr, q, method)
                rows.append({"year": yr, "scenario": key, "strategy": "rolling_replan", "revenue": rp["revenue"],
                             "storage_cost": rp["storage_cost"], "net": rp["net"], "net_per_t": rp["net"] / base.Q,
                             "gain_vs_harvest_per_t": (rp["net"] - harvest_net) / base.Q,
                             "oracle_net_per_t": oracle["objective"] / base.Q, "x": [round(v, 1) for v in rp["x"]],
                             "s": [round(v, 1) for v in rp["s"]], "sold_t": float(np.sum(rp["x"]))})
                rows.append({"year": yr, "scenario": key, "strategy": "perfect_foresight", "revenue": oracle["revenue"],
                             "storage_cost": oracle["storage_cost"], "net": oracle["objective"],
                             "net_per_t": oracle["objective"] / base.Q,
                             "gain_vs_harvest_per_t": (oracle["objective"] - harvest_net) / base.Q,
                             "oracle_net_per_t": oracle["objective"] / base.Q, "x": [round(v, 1) for v in oracle["x"]],
                             "s": [round(v, 1) for v in oracle["s"]], "sold_t": float(np.sum(oracle["x"]))})
    return pd.DataFrame(rows)


def paired_tests(bt: pd.DataFrame, strategy="forecast_plan") -> dict:
    """One-sided paired tests across backtest seasons (net Rs/t of the same season under two scenarios).
       Only meaningful with several seasons (we use the 8-season backtest); with n = 2 we report numbers only."""
    from scipy import stats
    f = bt[bt["strategy"] == strategy].pivot(index="year", columns="scenario", values="net_per_t")
    out = {}
    for a, b, name in [("B", "A", "H2_B_vs_A"), ("C", "A", "C_vs_A"), ("C", "B", "H3_C_vs_B")]:
        d = (f[a] - f[b]).dropna()
        res = {"n_seasons": int(len(d)), "mean_diff_rs_per_t": round(float(d.mean()), 0),
               "median_diff_rs_per_t": round(float(d.median()), 0), "min_diff_rs_per_t": round(float(d.min()), 0),
               "max_diff_rs_per_t": round(float(d.max()), 0), "wins": int((d > 0).sum()), "ties": int((d.abs() < 0.5).sum())}
        if len(d) >= 5 and (d.abs() > 0.5).any():
            res["paired_t_one_sided_p"] = round(float(stats.ttest_rel(f[a], f[b], alternative="greater").pvalue), 4)
            res["wilcoxon_one_sided_p"] = round(float(stats.wilcoxon(d, alternative="greater").pvalue), 4)
        else:
            res["paired_t_one_sided_p"] = None
            res["wilcoxon_one_sided_p"] = None
            res["note"] = ("not testable: every season identical (the B plan never stores, so it equals harvest sale)"
                           if (d.abs() < 0.5).all() else "too few seasons for a meaningful test; numbers reported descriptively")
        out[name] = res
    return out


# ---------------------------------------------------------------------------
# 7. SENSITIVITY & INDUSTRY 4.0 VALUE
# ---------------------------------------------------------------------------

def sensitivity(series: pd.Series, years, base: LPParams, method: str) -> dict:
    """Average (over backtest seasons) realised gain vs harvest sale, Rs per tonne, as one parameter moves."""
    fcs = {}
    acts = {}
    for yr in years:
        tr = series[series.index <= pd.Period(f"{yr}-03", "M")].dropna()
        fcs[yr] = forecast(tr, 9, method) * 10.0
        acts[yr] = season_prices(series, yr)

    def avg_gain(q: LPParams):
        g = []
        for yr in years:
            plan = solve_lp(fcs[yr], q, return_duals=False)
            if plan.get("status") != "Optimal":
                return np.nan
            ev = evaluate_plan(plan["x"], plan["s"], acts[yr], q.h)
            g.append((ev["net"] - q.Q * acts[yr][0]) / q.Q)
        return float(np.mean(g))

    res = {}
    qB, qC = scenario_params(base, "B"), scenario_params(base, "C")
    res["delta_B"] = {f"{d:.2f}": round(avg_gain(LPParams(**{**asdict(qB), "delta": d})), 0) for d in [0.06, 0.10, 0.14, 0.18, 0.22, 0.26]}
    res["delta_C"] = {f"{d:.3f}": round(avg_gain(LPParams(**{**asdict(qC), "delta": d})), 0) for d in [0.005, 0.018, 0.03, 0.05, 0.08]}
    res["h_B"] = {str(h): round(avg_gain(LPParams(**{**asdict(qB), "h": h})), 0) for h in [0, 125, 250, 500, 750, 1000]}
    res["h_C"] = {str(h): round(avg_gain(LPParams(**{**asdict(qC), "h": h})), 0) for h in [0, 350, 700, 1050, 1400, 2000]}
    res["C_capacity_B"] = {str(c): round(avg_gain(LPParams(**{**asdict(qB), "C": c})), 0) for c in [300, 500, 700, 900, 1000]}
    res["C_capacity_C"] = {str(c): round(avg_gain(LPParams(**{**asdict(qC), "C": c})), 0) for c in [300, 500, 700, 900, 1000]}
    res["L_B"] = {str(l): round(avg_gain(LPParams(**{**asdict(qB), "L": l})), 0) for l in [100, 300, 500, 700]}
    res["L_C"] = {str(l): round(avg_gain(LPParams(**{**asdict(qC), "L": l})), 0) for l in [100, 300, 500, 700]}
    res["U_C"] = {str(u): round(avg_gain(LPParams(**{**asdict(qC), "U": u})), 0) for u in [150, 300, 500, 1000]}
    # 2-way grid for scenario-B style storage: delta x h  (heat map)
    grid = {}
    for d in [0.02, 0.06, 0.10, 0.14, 0.18, 0.22]:
        grid[f"{d:.2f}"] = {str(h): round(avg_gain(LPParams(**{**asdict(qB), "delta": d, "h": h})), 0) for h in [0, 250, 500, 750, 1000]}
    res["grid_delta_h"] = grid
    # break-even monthly loss rate for B-type storage at h=250 (bisection on avg gain = 0)
    lo, hi = 0.0, 0.6
    if avg_gain(LPParams(**{**asdict(qB), "delta": hi})) > 1:
        res["breakeven_delta_B"] = None
    else:
        for _ in range(30):
            mid = (lo + hi) / 2
            if avg_gain(LPParams(**{**asdict(qB), "delta": mid})) > 1:
                lo = mid
            else:
                hi = mid
        res["breakeven_delta_B"] = round((lo + hi) / 2, 4)
    return res


def industry40_value(bt: pd.DataFrame, base: LPParams, capex_B_per_t=7000.0, capex_C_per_t=16667.0, life_years=10, rate=0.10,
                     capex_C_range=(8000.0, 16667.0, 50000.0)) -> dict:
    """Rupee value of low-loss (cold / IoT-monitored) storage over the ventilated chawl.
       h (Rs/t/month) is treated as OPERATING cost of an owned facility (labour, power, sensors, monitoring);
       capital cost is handled separately here, so it is not double-counted.
       capex_B: MIDH norm Rs 1.75 lakh per 25 t unit = Rs 7,000/t.
       capex_C: ICAR multi-module storage Rs 1.5 lakh per 9 t = Rs 16,667/t (base); range Rs 8,000/t (MIDH cold storage
       type 1 norm) to Rs 50,000/t (small modular cold room)."""
    f = bt[bt["strategy"] == "forecast_plan"].pivot(index="year", columns="scenario", values="net_per_t")
    uplift_per_t_harvest = float((f["C"] - f["B"]).mean())
    uplift_per_t_capacity = uplift_per_t_harvest * base.Q / base.C
    crf = rate * (1 + rate) ** life_years / ((1 + rate) ** life_years - 1)

    def econ(cc):
        extra = cc - capex_B_per_t
        return {"capex_C_rs_per_t": cc, "extra_capex_rs_per_t_capacity": extra,
                "annualised_extra_capex_rs_per_t": round(extra * crf, 0),
                "simple_payback_seasons": round(extra / uplift_per_t_capacity, 2) if uplift_per_t_capacity > 0 else None,
                "net_annual_benefit_rs_per_t_capacity": round(uplift_per_t_capacity - extra * crf, 0)}
    return {
        "uplift_C_over_B_rs_per_t_harvest": round(uplift_per_t_harvest, 0),
        "uplift_C_over_B_rs_per_kg": round(uplift_per_t_harvest / 1000, 2),
        "uplift_C_over_B_rs_per_t_capacity_per_season": round(uplift_per_t_capacity, 0),
        "capex_B_rs_per_t_capacity": capex_B_per_t, "capital_recovery_factor_10y_10pct": round(crf, 4),
        "base_case": econ(capex_C_per_t),
        "capex_range": [econ(c) for c in capex_C_range],
        "fpo_annual_uplift_rs_lakh": round(uplift_per_t_harvest * base.Q / 1e5, 1),
        "seasons": int(len(f)), "uplift_by_season": {int(k): round(float(v), 0) for k, v in (f["C"] - f["B"]).items()},
    }


def to_jsonable(o):
    if isinstance(o, dict):
        return {str(k): to_jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [to_jsonable(v) for v in o]
    if isinstance(o, (np.floating,)):
        return None if np.isnan(o) else float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, float) and np.isnan(o):
        return None
    if isinstance(o, (pd.Period, pd.Timestamp)):
        return str(o)
    return o


# ---------------------------------------------------------------------------
# 8. INDUSTRY 4.0 EXTENSIONS: satellite weather (NASA POWER) and the value of sensor information
# ---------------------------------------------------------------------------
RAW_POWER = ROOT / "data" / "raw" / "nasa_power" / "lasalgaon_power_monthly_1996_2024.csv"


def load_power() -> pd.DataFrame:
    """NASA POWER monthly weather at Lasalgaon (20.15N, 74.23E): t2m_c, rh2m_pct, rain_mm_per_day; plus rain_mm (month total)."""
    w = pd.read_csv(RAW_POWER)
    w["ym"] = pd.PeriodIndex(w["ym"], freq="M")
    w = w.set_index("ym")
    w["rain_mm"] = w["rain_mm_per_day"] * w.index.days_in_month
    return w


def weather_price_link(price_long: pd.Series, wx: pd.DataFrame, years=range(1996, 2025)) -> dict:
    """H4 (extension added after the proposal; Sep-Oct window chosen on crop-calendar grounds): heavier late-monsoon rain (Sep+Oct total, mm) over Nashik is followed by a bigger
       post-harvest price rise, measured as ln(mean Oct-Dec price / April price). One season = one observation.
       Rationale: Sep-Oct rain damages the kharif crop in the field and raises rot in stored rabi onion."""
    import statsmodels.api as sm
    from scipy import stats
    rows = []
    for y in years:
        apr = price_long.get(pd.Period(f"{y}-04", "M"))
        od = price_long.reindex(pd.period_range(f"{y}-10", f"{y}-12", freq="M"))
        if apr is None or np.isnan(apr) or od.isna().any():
            continue
        so = float(wx.loc[pd.period_range(f"{y}-09", f"{y}-10", freq="M"), "rain_mm"].sum())
        jjas = float(wx.loc[pd.period_range(f"{y}-06", f"{y}-09", freq="M"), "rain_mm"].sum())
        rows.append({"year": y, "rise_log": float(np.log(od.mean() / apr)), "rise_pct": float((od.mean() / apr - 1) * 100),
                     "rain_sep_oct_mm": round(so, 1), "rain_jun_sep_mm": round(jjas, 1),
                     "rh_sep_oct_pct": round(float(wx.loc[pd.period_range(f"{y}-09", f"{y}-10", freq="M"), "rh2m_pct"].mean()), 1),
                     "source": "NHRDF Lasalgaon" if y < 2014 else "Maharashtra composite"})
    d = pd.DataFrame(rows)
    X = sm.add_constant(d["rain_sep_oct_mm"])
    fit = sm.OLS(d["rise_log"], X).fit()
    fit_hc = sm.OLS(d["rise_log"], X).fit(cov_type="HC1")
    jj = sm.OLS(d["rise_log"], sm.add_constant(d["rain_jun_sep_mm"])).fit()
    rho, rho_p = stats.spearmanr(d["rain_sep_oct_mm"], d["rise_log"])
    q = d["rain_sep_oct_mm"].quantile([1 / 3, 2 / 3]).values
    wet = d[d["rain_sep_oct_mm"] >= q[1]]
    dry = d[d["rain_sep_oct_mm"] <= q[0]]
    b = float(fit.params["rain_sep_oct_mm"])
    loo = []
    for y in d["year"]:
        dd = d[d["year"] != y]
        r = sm.OLS(dd["rise_log"], sm.add_constant(dd["rain_sep_oct_mm"])).fit()
        loo.append({"dropped": int(y), "beta_per_100mm_log": round(float(r.params["rain_sep_oct_mm"]) * 100, 3),
                    "p": round(float(r.pvalues["rain_sep_oct_mm"]), 4)})
    worst = max(loo, key=lambda r: r["p"])
    sub = {}
    for lab, dd in [("1996_2013", d[d["year"] < 2014]), ("2014_2024", d[d["year"] >= 2014])]:
        r = sm.OLS(dd["rise_log"], sm.add_constant(dd["rain_sep_oct_mm"])).fit()
        sub[lab] = {"n": int(len(dd)), "beta_per_100mm_log": round(float(r.params["rain_sep_oct_mm"]) * 100, 3),
                    "p": round(float(r.pvalues["rain_sep_oct_mm"]), 4)}
    return {"n_seasons": int(len(d)), "years": f"{int(d.year.min())}-{int(d.year.max())}",
            "leave_one_out": {"beta_min": min(r["beta_per_100mm_log"] for r in loo), "beta_max": max(r["beta_per_100mm_log"] for r in loo),
                              "p_max": worst["p"], "p_max_when_dropping": worst["dropped"],
                              "seasons_whose_removal_lifts_p_above_0_05": [r["dropped"] for r in loo if r["p"] > 0.05]},
            "subperiods": sub,
            "beta_per_mm": round(b, 5), "beta_per_100mm_log": round(b * 100, 3),
            "rise_multiplier_per_100mm": round(float(np.exp(b * 100)), 3),
            "se_ols": round(float(fit.bse["rain_sep_oct_mm"]), 5), "p_ols": round(float(fit.pvalues["rain_sep_oct_mm"]), 4),
            "p_robust_HC1": round(float(fit_hc.pvalues["rain_sep_oct_mm"]), 4), "r2": round(float(fit.rsquared), 3),
            "ci95_ols_per_100mm": [round(float(v) * 100, 3) for v in fit.conf_int().loc["rain_sep_oct_mm"]],
            "spearman_rho": round(float(rho), 3), "spearman_p": round(float(rho_p), 4),
            "placebo_jun_sep_monsoon": {"beta_per_100mm_log": round(float(jj.params["rain_jun_sep_mm"]) * 100, 3),
                                        "p": round(float(jj.pvalues["rain_jun_sep_mm"]), 4), "r2": round(float(jj.rsquared), 3)},
            "wet_third": {"mean_rain_mm": round(float(wet.rain_sep_oct_mm.mean()), 0),
                          "median_rise_pct": round(float(wet.rise_pct.median()), 0), "n": int(len(wet))},
            "dry_third": {"mean_rain_mm": round(float(dry.rain_sep_oct_mm.mean()), 0),
                          "median_rise_pct": round(float(dry.rise_pct.median()), 0), "n": int(len(dry))},
            "mean_rain_sep_oct_mm": round(float(d.rain_sep_oct_mm.mean()), 0),
            "table": d.round(3).to_dict(orient="records")}


def _execute_plan(x_plan, q: LPParams, delta_true: float, actual):
    """Follow a planned sales schedule in a store whose REAL monthly loss is delta_true.
       Sales are capped by the stock actually there and by the handling cap U (May-Dec); in December the store
       sells what it can handle and anything beyond U is unsold (counted as lost)."""
    stock = q.Q
    xs, ss = [], []
    for t in range(q.T):
        cap = stock if t == 0 else min(stock, q.U)      # handling cap applies May-Dec, as in the LP
        x = min(max(x_plan[t], 0.0), cap)
        if t == q.T - 1:
            x = cap                                       # December: sell what can be handled
        s = stock - x if t < q.T - 1 else 0.0              # anything beyond the cap in December is unsold (lost)
        xs.append(x); ss.append(s)
        stock = (1 - delta_true) * s
    return xs, ss, evaluate_plan(xs, ss, actual, q.h)


def _sensor_replan(fc, q: LPParams, delta_true: float, actual, measured_from_month=1):
    """Sensor store: the April decision uses the book loss rate (nothing measured yet); from month
       `measured_from_month` the loss rate is MEASURED (weight/IoT logs) and the rest of the season is re-solved
       from the actual stock with delta_true. Same April forecast throughout, so only loss information differs."""
    stock = q.Q
    xs, ss = [], []
    for t in range(q.T):
        d_plan = delta_true if t >= measured_from_month else q.delta
        sub = LPParams(Q=stock, C=q.C + 1e-4, L=(q.L if t == 0 else 0.0), U=q.U + 1e-4, delta=d_plan, h=q.h,
                       T=q.T - t, first_is_harvest=(t == 0))
        sol = solve_lp(fc[t:], sub, return_duals=False)
        cap = stock if t == 0 else min(stock, q.U)
        x = min(sol["x"][0], cap) if sol.get("status") == "Optimal" else cap
        if t == q.T - 1:
            x = cap
        s = stock - x if t < q.T - 1 else 0.0
        xs.append(x); ss.append(s)
        stock = (1 - delta_true) * s
    return xs, ss, evaluate_plan(xs, ss, actual, q.h)


def value_of_loss_information(series: pd.Series, years, base: LPParams, method: str, grids=None, price_source="forecast") -> dict:
    """Value of information from monitoring a store's REAL loss rate (the Industry 4.0 sensor question).
       For each season and each true loss rate, compare three operators facing the same April forecast:
         blind      - plans once with the book loss rate (B: 18.05%/month chawl, C: 1.83%/month cold store), never learns;
         sensor     - plans April with the book rate, then measures the real rate and re-plans monthly from May;
         calibrated - the store's rate is known before April (logged in an earlier season) - upper bound.
       Value = net revenue at actual prices minus selling everything at harvest, Rs per tonne harvested.
       VoI = sensor - blind. No price information differs between operators."""
    grids = grids or {"B": [0.04, 0.06, 0.08, 0.10, 0.12, 0.14, 0.1805, 0.22],
                      "C": [0.005, 0.0183, 0.03, 0.05, 0.08, 0.10, 0.12, 0.15]}
    out = {}
    for key, grid in grids.items():
        q = scenario_params(base, key)
        rows = []
        for yr in years:
            tr = series[series.index <= pd.Period(f"{yr}-03", "M")].dropna()
            act = season_prices(series, yr)
            fc = act.copy() if price_source == "actual" else forecast(tr, 9, method) * 10.0
            harvest = base.Q * act[0]
            blind_plan = solve_lp(fc, q, return_duals=False)
            for d in grid:
                _, _, eb = _execute_plan(blind_plan["x"], q, d, act)
                _, _, es = _sensor_replan(fc, q, d, act, measured_from_month=1)
                qc = LPParams(**{**asdict(q), "delta": d})
                cal = solve_lp(fc, qc, return_duals=False)
                _, _, ec = _execute_plan(cal["x"], q, d, act)
                rows.append({"year": yr, "delta_true": d, "blind": (eb["net"] - harvest) / base.Q,
                             "sensor": (es["net"] - harvest) / base.Q, "calibrated": (ec["net"] - harvest) / base.Q})
        df = pd.DataFrame(rows)
        g = df.groupby("delta_true")[["blind", "sensor", "calibrated"]].mean()
        g["voi_sensor"] = g["sensor"] - g["blind"]
        g["voi_calibrated"] = g["calibrated"] - g["blind"]
        diff = df.assign(w=df.sensor - df.blind)
        wins = diff.groupby("delta_true")["w"].agg(lambda v: int((v > 0.5).sum()))
        losses = diff.groupby("delta_true")["w"].agg(lambda v: int((v < -0.5).sum()))
        out[key] = {"book_delta": round(q.delta, 4), "price_source": price_source,
                    "grid": [{"delta_true": float(dlt), **{k: round(float(v), 0) for k, v in r.items()},
                              "sensor_beats_blind_seasons": int(wins[dlt]), "sensor_worse_seasons": int(losses[dlt])}
                             for dlt, r in g.iterrows()],
                    "by_season": df.round(1).to_dict(orient="records")}
    return out


def weather_replan_backtest(series: pd.Series, price_long: pd.Series, wx: pd.DataFrame, years, base: LPParams,
                            method: str) -> dict:
    """Real-time use of the satellite feed: on 1 November the FPO knows Sep+Oct rain (NASA POWER, ~days latency).
       Re-plan Nov-Dec from the actual stock with (a) a price-only re-forecast from end-October and
       (b) the same forecast scaled by the H4 rain effect estimated ONLY on earlier seasons (no look-ahead).
       Apr-Oct follow the April LP plan in both arms. Gains in Rs per tonne harvested vs harvest sale."""
    import statsmodels.api as sm
    link = weather_price_link(price_long, wx)
    tab = pd.DataFrame(link["table"]).set_index("year")
    res = {}
    for key in ["B", "C"]:
        q = scenario_params(base, key)
        rows = []
        for yr in years:
            tr = series[series.index <= pd.Period(f"{yr}-03", "M")].dropna()
            fc = forecast(tr, 9, method) * 10.0
            act = season_prices(series, yr)
            harvest = base.Q * act[0]
            plan = solve_lp(fc, q, return_duals=False)
            x = list(plan["x"]); s = list(plan["s"])
            stock_nov = (1 - q.delta) * s[6]          # stock entering November (t = 7)
            tr_oct = series[series.index <= pd.Period(f"{yr}-10", "M")].dropna()
            fc2 = forecast(tr_oct, 2, method) * 10.0
            prior = tab[tab.index < yr]
            fitp = sm.OLS(prior["rise_log"], sm.add_constant(prior["rain_sep_oct_mm"])).fit()
            anom = tab.loc[yr, "rain_sep_oct_mm"] - prior["rain_sep_oct_mm"].mean()
            mult = float(np.exp(fitp.params["rain_sep_oct_mm"] * anom))
            arms = {}
            for arm, f in [("price_only", fc2), ("price_plus_rain", fc2 * mult)]:
                sub = LPParams(Q=stock_nov, C=q.C + 1e-4, L=0.0, U=q.U + 1e-4, delta=q.delta, h=q.h, T=2,
                               first_is_harvest=False)
                sol = solve_lp(f, sub, return_duals=False)
                xx = x[:7] + list(sol["x"]); ss = s[:7] + list(sol["s"])
                arms[arm] = round((evaluate_plan(xx, ss, act, q.h)["net"] - harvest) / base.Q, 1)
                arms[arm + "_nov_dec_sales"] = [round(v, 1) for v in sol["x"]]
            rows.append({"year": yr, "rain_sep_oct_mm": float(tab.loc[yr, "rain_sep_oct_mm"]), "rain_multiplier": round(mult, 3),
                         "stock_entering_nov_t": round(stock_nov, 1), **arms})
        df = pd.DataFrame(rows)
        dv = df.price_plus_rain - df.price_only
        res[key] = {"mean_price_only": round(float(df.price_only.mean()), 0),
                    "mean_price_plus_rain": round(float(df.price_plus_rain.mean()), 0),
                    "mean_value_of_rain_feed": round(float(dv.mean()), 0),
                    "seasons_rain_helps": int((dv > 0.5).sum()), "seasons_rain_hurts": int((dv < -0.5).sum()),
                    "by_season": df.to_dict(orient="records")}
    return res
