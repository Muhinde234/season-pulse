"""Combine the historical RYI baseline with in-season field reports into a risk ranking.

Everything is in log-RYI space so it composes with the baseline built in build_baseline.py.

Per-report signal (log RYI shift):
    condition: (condition - 3) * 0.10      -> 1 = -0.20 ... 5 = +0.20
    pests:     -0.10
    rain problem (any): -0.10
Reports for a district/crop/season are averaged, then shrunk by n / (n + K_REPORTS) so one report
moves the estimate a little and many consistent reports move it a lot.

Alert levels reuse the backtest thresholds: actual "low" = RYI <= 0.75, model flag = RYI <= 0.85.
"""
import numpy as np
import pandas as pd

from core.data import DISTRICT_PROVINCE, load_baseline, load_consumption, load_cooperatives

K_REPORTS = 2.0
HIGH, WATCH = 0.75, 0.85

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
    return b.sort_values("adjusted_RYI").reset_index(drop=True)
