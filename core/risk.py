"""Combine the historical RYI baseline with in-season field reports into a risk ranking.

Everything is in log-RYI space so it composes with the baseline built in build_baseline.py.

Per-report signal (log RYI shift):
    condition: (condition - 3) * 0.10      -> 1 = -0.20 ... 5 = +0.20
    pests:     -0.10
    rain problem (any): -0.10
Reports for a district/crop/season are averaged, then shrunk by n / (n + K_REPORTS) so one report
moves the estimate a little and many consistent reports move it a lot.

Alert levels reuse the backtest thresholds: actual "low" = RYI <= 0.75, model flag = RYI <= 0.85.

Ranking (risk and food dependence): rows are ordered by alert level, then by priority =
    shortfall below typical (1 - expected RYI, floored at 0) x (0.5 + food dependence)
where food dependence is the district's percentile (0-1) of EICV 2020 household consumption of that crop among
the 30 districts. Two districts equally far below typical: the one whose households eat more of the crop comes first.

Recommended actions (simple rules on the adjusted table; a row can get several):
    below typical + (rain problem reported, latest CHIRPS
        rainfall >= 10% below avg, or mostly traditional
        irrigation in SAS 2026 A Table 32)            -> small-scale irrigation
    persistently low (baseline < 0.8 over 3+ yrs)
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
                       load_rainfall, rain_period)

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


def adjusted_table(season: str, reports: pd.DataFrame) -> pd.DataFrame:
    """One row per district x crop with baseline, report adjustment, adjusted RYI and alert level."""
    b = load_baseline()
    b = b[b.Season == season].copy()
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
    b = b.merge(cons[["DistrictName", "CropName", "consumption_rwf_2020"]], on=["DistrictName", "CropName"],
                how="left")
    b = b.merge(latest_rainfall(season), on="DistrictName", how="left")
    b = b.merge(load_irrigation()[["DistrictName", "modern_pct", "traditional_pct"]], on="DistrictName", how="left")
    b["action"] = recommended_actions(b, load_cooperatives())

    # Food dependence: percentile of household consumption of this crop among districts (0 = least, 1 = most)
    b["food_dependence"] = b.groupby("CropName").consumption_rwf_2020.rank(pct=True).fillna(0.5)
    b["food_level"] = pd.cut(b.food_dependence, [0, 1 / 3, 2 / 3, 1], labels=["Low", "Medium", "High"],
                             include_lowest=True).astype(str)
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
