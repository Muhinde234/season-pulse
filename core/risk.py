"""Combine the baseline with in-season field reports into a risk ranking.

Baseline (RYI = district yield / median district yield, same crop and season):
    - seven priority crops: the district's latest official NISR result for the same season (prep_official.py).
      Backtested on every season 2023-2026, it beats every alternative we tried (see the Model page).
    - tomatoes: NISR publishes them only inside "vegetables", so they keep the 2020-2024 baseline from the cleaned
      SAS files (build_baseline.py). It is not validated and is labelled as such.
Everything is in log-RYI space so reports compose with the baseline.

Per-report signal (log RYI shift). These weights are ASSUMPTIONS, not estimates: there are no past field reports
to fit them on. They should be re-fitted once real reports can be compared with the next official results.
    condition: (condition - 3) * 0.10      -> 1 = -0.20 ... 5 = +0.20
    pests:     -0.10
    rain problem (any): -0.10
Reports for a district/crop/season are averaged, then shrunk by n / (n + K_REPORTS) so one report
moves the estimate a little and many consistent reports move it a lot.

Alert levels reuse the backtest thresholds: actual "low" = RYI <= 0.75, model flag = RYI <= 0.85.

Ranking (risk and food dependence): rows are ordered by alert level, then by priority =
    shortfall below typical (1 - expected RYI, floored at 0) x (0.5 + food dependence)
where food dependence is the district's percentile (0-1), among the 30 districts, of the crop's share of household
food spending on the five EICV 2020 crops (beans, cassava, Irish potatoes, maize, tomatoes). A share, not a total,
so large districts don't rank high just for being large. Crops EICV doesn't cover get 0.5 (neutral).
Two districts equally far below typical: the one whose households rely more on the crop comes first.

Recommended actions (simple rules on the adjusted table; a row can get several):
    below typical + (rain problem reported, latest CHIRPS
        rainfall >= 10% below avg, or mostly traditional
        irrigation in SAS 2026 A Table 32)            -> small-scale irrigation
    persistently low (< 0.8 in each of the last 3
        official years; cleaned data: mean over 3+ yrs)
        and no rainfall problem                       -> soil testing and fertility support
    above typical                                     -> post-harvest collection and storage
    surplus + cooperatives or processors >= median    -> value addition / processing
    surplus + goods exporters >= median               -> export opportunity
Surplus = expected RYI >= SURPLUS. Every district has some cooperatives and exporters, so district counts
are compared with the median district.
"""
import numpy as np
import pandas as pd

from core.data import (DISTRICT_PROVINCE, load_baseline, load_consumption, load_cooperatives, load_irrigation,
                       load_official_baseline, load_rainfall, rain_period)

K_REPORTS = 2.0
HIGH, WATCH = 0.75, 0.85
SURPLUS = 1.15  # mirror of WATCH: expected >= 15% above typical district
DRY_PCT = -10   # latest season's rainfall this far below the district's 2020-2024 average counts as dry
TRADITIONAL_PCT = 50  # "mostly traditional irrigation": at least this % of irrigated plots use traditional methods
LEVEL_ORDER = {"High": 0, "Watch": 1, "Normal": 2}

LEVELS = {  # status colour + icon + label; colour never carries meaning alone
    "High": ("#d03b3b", "🔴"),
    "Watch": ("#fab219", "🟠"),
    "Normal": ("#0ca30c", "🟢"),
}


def report_signal(r: pd.DataFrame) -> pd.Series:
    return (r.condition - 3) * 0.10 - 0.10 * r.pests - 0.10 * (r.rain_problem != "None")


def level(ryi: float) -> str:
    return "High" if ryi <= HIGH else "Watch" if ryi <= WATCH else "Normal"


CLEANED = "Cleaned SAS 2020–2024 (not validated)"


def season_baseline(season: str) -> pd.DataFrame:
    """Baseline per district x crop: the latest official NISR result, or the cleaned-data baseline for crops NISR
    doesn't publish (tomatoes). `baseline_source` says which."""
    o = load_official_baseline()
    o = o[o.Season == season].assign(baseline_source=lambda d: "NISR official " + d.source_season.str[:4]
                                     + " Season " + d.source_season.str[-1])
    old = load_baseline()
    old = old[(old.Season == season) & ~old.CropName.isin(set(o.CropName))].assign(
        baseline_source=CLEANED, source_season=np.nan, prev_RYI=np.nan)
    cols = ["DistrictName", "CropName", "Season", "baseline_RYI", "prev_RYI", "n_years", "persistently_low",
            "source_season", "baseline_source"]
    return pd.concat([o[cols], old[cols]], ignore_index=True).assign(
        persistently_low=lambda d: d.persistently_low.astype(bool))


def adjusted_table(season: str, reports: pd.DataFrame) -> pd.DataFrame:
    """One row per district x crop with baseline, report adjustment, adjusted RYI and alert level."""
    b = season_baseline(season)
    b["baseline_log"] = np.log(b.baseline_RYI)

    r = reports[reports.season == season].copy()
    if len(r):
        r["signal"] = report_signal(r)
        agg = r.groupby(["district", "crop"]).agg(
            n_reports=("signal", "size"), mean_signal=("signal", "mean"),
            n_simulated=("is_simulated", "sum"), mean_condition=("condition", "mean"), pest_share=("pests", "mean"),
            rain_share=("rain_problem", lambda s: (s != "None").mean()),
        ).reset_index().rename(columns={"district": "DistrictName", "crop": "CropName"})
        b = b.merge(agg, on=["DistrictName", "CropName"], how="left")
    for col in ["n_reports", "mean_signal", "n_simulated", "mean_condition", "pest_share", "rain_share"]:
        if col not in b:
            b[col] = 0.0
        b[col] = b[col].fillna(0)

    b["report_shift"] = b.mean_signal * b.n_reports / (b.n_reports + K_REPORTS)
    b["adjusted_RYI"] = np.exp(b.baseline_log + b.report_shift)
    b["level"] = b.adjusted_RYI.apply(level)
    b["Province"] = b.DistrictName.map(DISTRICT_PROVINCE)

    b = b.merge(load_cooperatives(), on="DistrictName", how="left")
    cons = load_consumption()
    cons = cons.assign(food_share=cons.consumption_rwf_2020
                       / cons.groupby("DistrictName").consumption_rwf_2020.transform("sum"))
    b = b.merge(cons[["DistrictName", "CropName", "food_share"]], on=["DistrictName", "CropName"], how="left")
    b = b.merge(latest_rainfall(season), on="DistrictName", how="left")
    b = b.merge(load_irrigation()[["DistrictName", "modern_pct", "traditional_pct"]], on="DistrictName", how="left")
    b["action"] = recommended_actions(b, load_cooperatives())

    # Food dependence: percentile among districts of the crop's share of household food spending (0 = least)
    b["food_dependence"] = b.groupby("CropName").food_share.rank(pct=True)
    b["food_level"] = pd.cut(b.food_dependence, [0, 1 / 3, 2 / 3, 1], labels=["Low", "Medium", "High"],
                             include_lowest=True).astype(str).where(b.food_dependence.notna(), "No data")
    b["food_dependence"] = b.food_dependence.fillna(0.5)
    b["priority"] = ((1 - b.adjusted_RYI).clip(lower=0) * (0.5 + b.food_dependence)).round(3)
    b["level_order"] = b.level.map(LEVEL_ORDER)
    return (b.sort_values(["level_order", "priority", "adjusted_RYI"], ascending=[True, False, True])
             .drop(columns="level_order").reset_index(drop=True))


def latest_rainfall(season: str) -> pd.DataFrame:
    """Most recent CHIRPS rainfall for this season type per district (may be partial: only months published)."""
    cols = ["DistrictName", "rain_mm", "avg_mm", "rain_anom_pct", "rain_partial", "rain_period"]
    rain = load_rainfall()
    if rain.empty:
        return pd.DataFrame(columns=cols)
    rain = rain[rain.Season == season]
    rain = rain[rain.Year == rain.Year.max()]
    return rain.assign(rain_partial=rain.partial, rain_period=rain.apply(rain_period, axis=1))[cols]


def recommended_actions(b: pd.DataFrame, coops: pd.DataFrame) -> pd.Series:
    """Rule-based actions per row, joined with ' · ' ('-' when no rule fires)."""
    below, above = b.adjusted_RYI < 1, b.adjusted_RYI > 1
    surplus = b.adjusted_RYI >= SURPLUS
    has_buyers = ((b.cooperatives >= coops.cooperatives.median())
                  | (b.food_processors >= coops.food_processors.median()))
    rain_problem = (b.rain_share > 0) | (b.rain_anom_pct <= DRY_PCT).fillna(False)
    traditional = (b.traditional_pct >= TRADITIONAL_PCT).fillna(False)
    rules = [
        ("💧 Small-scale irrigation", below & (rain_problem | traditional)),
        ("🌱 Soil testing & fertility support", b.persistently_low.astype(bool) & ~rain_problem),
        ("🏚️ Post-harvest collection & storage", above),
        ("🏭 Value addition / processing", surplus & has_buyers),
        ("🚢 Export opportunity", surplus & (b.exporters >= coops.exporters.median())),
    ]
    out = pd.Series([[] for _ in range(len(b))], index=b.index)
    for label, mask in rules:
        for i in b.index[mask.fillna(False)]:
            out[i].append(label)
    return out.map(lambda a: " · ".join(a) or "-")
