"""Imboni - build district baselines from NISR SAS (2020-2024) and backtest.

Unit consistency in the cleaned SAS file varies by year/crop (e.g. Irish potato
yields ~13 t/ha in 2020-21 vs ~0.8 t/ha from 2022). We therefore never compare
absolute yields across years. Instead we use a Relative Yield Index (RYI):

    RYI = district yield / median district yield for the same crop, season, year

Any year-wide unit or scale factor cancels out. RYI = 0.7 means the district is
30% below the typical district that season.
"""
import json
import numpy as np
import pandas as pd

SAS = "data/raw/sas_historical.csv"
MIN_OBS = 10  # cells with fewer farm observations are flagged low-confidence

d = pd.read_csv(SAS)
d = d[(d.Season != "Annual") & d.DistrictName.notna() & (d.ProvinceName != "Unknown Province")].copy()
d["Total_Area_ha"] = d.Avg_Area_ha * d.Num_Observations
d = d[d.Total_Area_ha > 0]
d["Yield"] = d.Total_Production_Kg / d.Total_Area_ha  # area-weighted, not mean of ratios
d["LowConfidence"] = d.Num_Observations < MIN_OBS

key = ["CropName", "Season", "Year"]
d["NationalMedian"] = d.groupby(key).Yield.transform("median")
d["RYI"] = d.Yield / d.NationalMedian
d["logRYI"] = np.log(d.RYI.clip(0.05, 20))

# ---------- Backtest: predict 2024 RYI from 2020-2023 history ----------
train = d[(d.Year < 2024) & ~d.LowConfidence]
test = d[(d.Year == 2024) & ~d.LowConfidence].copy()
grp = ["DistrictName", "CropName", "Season"]
hist = train.groupby(grp).agg(hist_logRYI=("logRYI", "mean"), n_years=("Year", "nunique")).reset_index()
test = test.merge(hist, on=grp, how="inner")

# Shrink toward 0 (national typical) by years of evidence
k = 1.0
test["pred_logRYI"] = test.hist_logRYI * test.n_years / (test.n_years + k)

def mae(a, b):
    return float(np.mean(np.abs(a - b)))

naive = mae(test.logRYI, 0.0)          # "every district is typical"
model = mae(test.pred_logRYI, test.logRYI)

# Classification: can we flag districts that end up >=25% below typical?
thr = np.log(0.75)
actual_low = test.logRYI <= thr
pred_low = test.pred_logRYI <= np.log(0.85)
tp = int((actual_low & pred_low).sum())
precision = tp / max(int(pred_low.sum()), 1)
recall = tp / max(int(actual_low.sum()), 1)

results = {
    "test_cells_2024": int(len(test)),
    "mae_log_naive": round(naive, 3),
    "mae_log_model": round(model, 3),
    "error_reduction_pct": round(100 * (1 - model / naive), 1),
    "low_district_flags": {"actual_low": int(actual_low.sum()), "flagged": int(pred_low.sum()),
                           "precision": round(precision, 2), "recall": round(recall, 2)},
    "by_crop_mae": test.assign(err=(test.pred_logRYI - test.logRYI).abs(),
                               nerr=test.logRYI.abs()).groupby("CropName")[["nerr", "err"]].mean().round(3)
                       .rename(columns={"nerr": "naive", "err": "model"}).to_dict("index"),
}

# ---------- Final baseline using all years, for the app ----------
full = d[~d.LowConfidence].groupby(grp).agg(
    baseline_logRYI=("logRYI", "mean"), sd_logRYI=("logRYI", "std"), n_years=("Year", "nunique"),
    last_year=("Year", "max")).reset_index()
full["baseline_RYI"] = np.exp(full.baseline_logRYI * full.n_years / (full.n_years + k)).round(3)
full["persistently_low"] = (full.baseline_RYI < 0.8) & (full.n_years >= 3)

d.to_csv("data/out_sas_clean_ryi.csv", index=False)
full.to_csv("app_data/out_district_baseline.csv", index=False)
json.dump(results, open("app_data/out_backtest.json", "w"), indent=2)
print(json.dumps(results, indent=2))
print("\nPersistently low (>=3 yrs, RYI<0.8):")
print(full[full.persistently_low].sort_values("baseline_RYI")[grp + ["baseline_RYI", "n_years"]].to_string(index=False))
