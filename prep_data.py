"""Imboni - turn the large/raw NISR files into the small files in app_data/ that the app loads.

Run:  python prep_data.py   (official yields, validation and the alert baseline come from prep_official.py)

Inputs (data/raw/):
    establishment_census.csv       37 MB, not committed; without it the committed aggregate is kept
    eicv_historical.csv            EICV household consumption
    sas_tables/SAS_2026A.xlsx      NISR SAS 2026 Season A official tables (Table 32: irrigation methods)

Outputs (app_data/, committed so Streamlit Cloud never needs the raw files):
    district_cooperatives.csv        cooperatives, food processors + goods exporters per district
    district_consumption_2020.csv    EICV 2020 household consumption per district & crop
    irrigation_2026A.csv             Table 32 irrigation methods per district (% of irrigated plots)
"""
from pathlib import Path

import pandas as pd

RAW = Path("data/raw")
OUT = Path("app_data")
CENSUS = RAW / "establishment_census.csv"
EICV = RAW / "eicv_historical.csv"
SAS2026 = RAW / "sas_tables" / "SAS_2026A.xlsx"
SUMMARY_ROWS = {"National", "SSF", "LSF"}  # national total, small- and large-scale farmers

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


# Table 32: % of irrigated plots by irrigation type (two header rows: modern types, then traditional)
t32 = pd.read_excel(SAS2026, sheet_name="Table 32", header=None).iloc[:, 1:]
t32.columns = ["DistrictName", "surface", "flood", "drip", "sprinkler", "pivot", "traditional"]
irr = district_rows(t32)
irr[irr.columns[1:]] = irr[irr.columns[1:]].apply(pd.to_numeric, errors="coerce")
irr = irr.assign(modern_pct=irr[["surface", "flood", "drip", "sprinkler", "pivot"]].sum(axis=1).round(1),
                 traditional_pct=irr.traditional.round(1))
irr[["DistrictName", "modern_pct", "traditional_pct", "surface", "flood", "drip", "sprinkler", "pivot"]].to_csv(
    OUT / "irrigation_2026A.csv", index=False)

print(f"Cooperatives: {len(coops)} districts, {coops.cooperatives.sum()} cooperatives, "
      f"{coops.food_processors.sum()} food processors, {coops.exporters.sum()} goods exporters")
print(f"EICV 2020: {len(cons)} district-crop rows across {cons.DistrictName.nunique()} districts")
print(f"Irrigation (SAS 2026 A Table 32): {len(irr)} districts")
