"""Season Pulse - pre-aggregate the large census and EICV files into small CSVs for the app.

Run once after build_baseline.py:
    python prepare_data.py

Outputs (committed to the repo so Streamlit Cloud never needs the raw files):
    data/district_cooperatives.csv   cooperatives + food processors per district
    data/district_consumption_2020.csv  EICV 2020 household consumption per district & crop
"""
from pathlib import Path

import pandas as pd

CENSUS = Path("data/raw/establishment_census.csv")
EICV = "data/raw/eicv_historical.csv"

# ---------- Establishment census: cooperatives and food processors only ----------
# The raw census (37 MB) is not in git; without it the committed aggregate is kept as is.
if CENSUS.exists():
    c = pd.read_csv(CENSUS, low_memory=False,
                    usecols=["DistrictCode", "DistrictName", "Is_Cooperative", "Is_Food_Processing_Related"])
    # District code 28 is labelled "Unknown District" in the cleaned file; in NISR coding 28 = Kamonyi
    # (the only Southern Province district otherwise missing).
    c.loc[c.DistrictCode == 28, "DistrictName"] = "Kamonyi"
    c = c[c.DistrictName != "Unknown District"]

    c["cooperative"] = c.Is_Cooperative.eq("Yes")
    c["food_processor"] = c.Is_Food_Processing_Related.eq(1)
    coops = (c.groupby("DistrictName")[["cooperative", "food_processor"]].sum()
              .rename(columns={"cooperative": "cooperatives", "food_processor": "food_processors"})
              .astype(int).reset_index())
    coops.to_csv("data/district_cooperatives.csv", index=False)
else:
    print(f"{CENSUS} not found - keeping existing data/district_cooperatives.csv")
    coops = pd.read_csv("data/district_cooperatives.csv")

# ---------- EICV: 2020 only; the 2020 rows contain duplicate district/crop rows -> sum ----------
e = pd.read_csv(EICV)
e = e[e.Year == 2020]
cons = (e.groupby(["DistrictName", "CropName"], as_index=False)
         [["Total_Weighted_Consumption_Qty_Kg", "Total_Weighted_Consumption_Value_Rwf", "Num_Households_Observed"]]
         .sum()
         .rename(columns={"Total_Weighted_Consumption_Qty_Kg": "consumption_kg_2020",
                          "Total_Weighted_Consumption_Value_Rwf": "consumption_rwf_2020",
                          "Num_Households_Observed": "households_2020"}))
cons.to_csv("data/district_consumption_2020.csv", index=False)

print(f"Cooperatives: {len(coops)} districts, {coops.cooperatives.sum()} cooperatives, "
      f"{coops.food_processors.sum()} food processors")
print(f"EICV 2020: {len(cons)} district-crop rows across {cons.DistrictName.nunique()} districts")
