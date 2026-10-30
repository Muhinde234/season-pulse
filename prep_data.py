"""Season Pulse - turn the large/raw NISR files into the small files in app_data/ that the app loads.

Run after build_baseline.py (the 2026 validation needs app_data/out_district_baseline.csv):
    python prep_data.py

Inputs (data/raw/):
    establishment_census.csv     37 MB, not committed; without it the committed aggregate is kept
    eicv_historical.csv          EICV household consumption
    Tables_2026_Season_A.xlsx    NISR SAS 2026 Season A official tables (13: yield, 32: irrigation)

Outputs (app_data/, committed so Streamlit Cloud never needs the raw files):
    district_cooperatives.csv        cooperatives, food processors + goods exporters per district
    district_consumption_2020.csv    EICV 2020 household consumption per district & crop
    official_yield_2026A.csv         Table 13 yields (kg/ha) per district & crop, plus RYI vs the median district
    irrigation_2026A.csv             Table 32 irrigation methods per district (% of irrigated plots)
    out_validation_2026A.csv         historical Season A baseline vs official 2026 Season A RYI
"""
from pathlib import Path

import numpy as np
import pandas as pd

RAW = Path("data/raw")
OUT = Path("app_data")
CENSUS = RAW / "establishment_census.csv"
EICV = RAW / "eicv_historical.csv"
SAS2026 = RAW / "Tables_2026_Season_A.xlsx"
SUMMARY_ROWS = {"National", "SSF", "LSF"}  # national total, small- and large-scale farmers

# Table 13 column -> crop name used everywhere else (Tomatoes are only published inside "vegetables")
TABLE13_CROPS = {"Bean": "Beans", "Cassava": "Cassava", "Irish potato": "Irish potatoes", "Maize": "Maize"}
LOW, FLAG = 0.80, 0.85  # official RYI <= LOW counts as a bad season; baseline <= FLAG = flagged in advance

# ---------- Establishment census: cooperatives, food processors and goods exporters only ----------
if CENSUS.exists():
    c = pd.read_csv(CENSUS, low_memory=False,
                    usecols=["DistrictCode", "DistrictName", "Is_Cooperative", "Is_Food_Processing_Related",
                             "Exports_Goods"])
    # District code 28 is labelled "Unknown District" in the cleaned file; in NISR coding 28 = Kamonyi
    # (the only Southern Province district otherwise missing).
    c.loc[c.DistrictCode == 28, "DistrictName"] = "Kamonyi"
    c = c[c.DistrictName != "Unknown District"]

    c["cooperative"] = c.Is_Cooperative.eq("Yes")
    c["food_processor"] = c.Is_Food_Processing_Related.eq(1)
    c["exporter"] = c.Exports_Goods.eq("Yes")
    coops = (c.groupby("DistrictName")[["cooperative", "food_processor", "exporter"]].sum()
              .rename(columns={"cooperative": "cooperatives", "food_processor": "food_processors",
                               "exporter": "exporters"})
              .astype(int).reset_index())
    coops.to_csv(OUT / "district_cooperatives.csv", index=False)
else:
    print(f"{CENSUS} not found - keeping existing {OUT / 'district_cooperatives.csv'}")
    coops = pd.read_csv(OUT / "district_cooperatives.csv")

# ---------- EICV: 2020 only; the 2020 rows contain duplicate district/crop rows -> sum ----------
e = pd.read_csv(EICV)
e = e[e.Year == 2020]
cons = (e.groupby(["DistrictName", "CropName"], as_index=False)
         [["Total_Weighted_Consumption_Qty_Kg", "Total_Weighted_Consumption_Value_Rwf", "Num_Households_Observed"]]
         .sum()
         .rename(columns={"Total_Weighted_Consumption_Qty_Kg": "consumption_kg_2020",
                          "Total_Weighted_Consumption_Value_Rwf": "consumption_rwf_2020",
                          "Num_Households_Observed": "households_2020"}))
cons.to_csv(OUT / "district_consumption_2020.csv", index=False)


# ---------- SAS 2026 Season A official tables ----------
def district_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Keep the 30 district rows of an official table (drop titles, totals and the source note)."""
    df = df.rename(columns={df.columns[0]: "DistrictName"})
    df["DistrictName"] = df.DistrictName.astype(str).str.strip()
    return df[df.DistrictName.isin(cons.DistrictName.unique()) & ~df.DistrictName.isin(SUMMARY_ROWS)]


# Table 13: average yield (kg/ha). Row 3 holds the headers; column A is empty. 0 = crop not grown there.
t13 = district_rows(pd.read_excel(SAS2026, sheet_name="Table 13", header=2).iloc[:, 1:])
official = (t13.melt(id_vars="DistrictName", value_vars=list(TABLE13_CROPS), var_name="col", value_name="yield_kg_ha")
               .assign(CropName=lambda d: d.col.map(TABLE13_CROPS)).drop(columns="col"))
official["yield_kg_ha"] = pd.to_numeric(official.yield_kg_ha, errors="coerce")
official = official[official.yield_kg_ha > 0].copy()
official["official_RYI"] = official.yield_kg_ha / official.groupby("CropName").yield_kg_ha.transform("median")
official = official.round({"yield_kg_ha": 0, "official_RYI": 3})
official.to_csv(OUT / "official_yield_2026A.csv", index=False)

# Table 32: % of irrigated plots by irrigation type (two header rows: modern types, then traditional)
t32 = pd.read_excel(SAS2026, sheet_name="Table 32", header=None).iloc[:, 1:]
t32.columns = ["DistrictName", "surface", "flood", "drip", "sprinkler", "pivot", "traditional"]
irr = district_rows(t32)
irr[irr.columns[1:]] = irr[irr.columns[1:]].apply(pd.to_numeric, errors="coerce")
irr = irr.assign(modern_pct=irr[["surface", "flood", "drip", "sprinkler", "pivot"]].sum(axis=1).round(1),
                 traditional_pct=irr.traditional.round(1))
irr[["DistrictName", "modern_pct", "traditional_pct", "surface", "flood", "drip", "sprinkler", "pivot"]].to_csv(
    OUT / "irrigation_2026A.csv", index=False)

# Validation: the Season A baseline (built from 2020-2024 only) vs what NISR actually measured in 2026 A
base = pd.read_csv(OUT / "out_district_baseline.csv")
base = base[base.Season == "SeasonA"][["DistrictName", "CropName", "baseline_RYI", "n_years"]]
val = official.merge(base, on=["DistrictName", "CropName"], how="inner").rename(columns={"baseline_RYI": "predicted_RYI"})
val["error_log"] = (np.log(val.predicted_RYI) - np.log(val.official_RYI)).round(3)
val["actual_low"] = val.official_RYI <= LOW
val["flagged"] = val.predicted_RYI <= FLAG
val.sort_values(["CropName", "DistrictName"]).to_csv(OUT / "out_validation_2026A.csv", index=False)

print(f"Cooperatives: {len(coops)} districts, {coops.cooperatives.sum()} cooperatives, "
      f"{coops.food_processors.sum()} food processors, {coops.exporters.sum()} goods exporters")
print(f"EICV 2020: {len(cons)} district-crop rows across {cons.DistrictName.nunique()} districts")
print(f"2026 A official yields: {len(official)} district-crop rows · irrigation: {len(irr)} districts")
print(f"2026 A validation: {len(val)} cells, caught {int((val.actual_low & val.flagged).sum())} of "
      f"{int(val.actual_low.sum())} bad cells")
for crop, g in val.groupby("CropName"):
    print(f"  {crop:15s} r = {np.log(g.official_RYI).corr(np.log(g.predicted_RYI)):+.2f}  (n = {len(g)})")
