"""Imboni - turn the large/raw NISR files into the small files in app_data/ that the app loads.

Run:  python prep_data.py   (official yields, validation and the alert baseline come from prep_official.py)

Inputs (data/raw/):
    establishment_census.csv       37 MB, not committed; without it the committed aggregate is kept
    eicv_historical.csv            EICV household consumption
    sas_tables/SAS_2026A.xlsx      NISR SAS 2026 Season A official tables (Table 32: irrigation methods)
    ahs/AHS_2024_Tables.xlsx       NISR Agricultural Household Survey 2024 tables (Jan-Dec 2024)
                                   https://statistics.gov.rw/data-sources/surveys/Agricultural-Household-Survey

Outputs (app_data/, committed so Streamlit Cloud never needs the raw files):
    district_cooperatives.csv        cooperatives, food processors + goods exporters per district
    district_consumption_2020.csv    EICV 2020 household consumption per district & crop
    irrigation_2026A.csv             Table 32 irrigation methods per district (% of irrigated plots)
    ahs2024_extension_types.csv      AHS Table 27: % of agricultural households with at least one member who
                                     received extension services, by type, province and sex of household head
    ahs2024_extension_sources.csv    AHS Table 29: % of households receiving each type of service, by source
"""
from pathlib import Path

import pandas as pd

RAW = Path("data/raw")
OUT = Path("app_data")
CENSUS = RAW / "establishment_census.csv"
EICV = RAW / "eicv_historical.csv"
SAS2026 = RAW / "sas_tables" / "SAS_2026A.xlsx"
AHS = RAW / "ahs" / "AHS_2024_Tables.xlsx"
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


# ---------- AHS 2024: extension services (Tables 27 and 29) ----------
def ahs_table(sheet: str, header_word: str) -> pd.DataFrame:
    """Rows = the labels in the first text column; columns = every later column, named from the header row
    containing `header_word` (or the row above it, where a label such as "Rwanda" sits one row higher)."""
    df = pd.read_excel(AHS, sheet_name=sheet, header=None).dropna(how="all").dropna(axis=1, how="all")
    hdr = next(i for i in df.index if any(str(v).strip().startswith(header_word) for v in df.loc[i]))
    above = df.index[df.index.get_loc(hdr) - 1]
    labels = df.iloc[:, 0].astype(str).str.strip()
    cols = {j: str(df.loc[hdr].iloc[j] if pd.notna(df.loc[hdr].iloc[j]) else df.loc[above].iloc[j]).strip()
            for j in range(1, df.shape[1])}
    rows = []
    for i, label in zip(df.index, labels):
        vals = {name: pd.to_numeric(df.loc[i].iloc[j], errors="coerce") for j, name in cols.items()}
        if label not in ("nan", "") and sum(pd.notna(v) for v in vals.values()) >= 3:
            rows.append({"item": label.replace("…", "...").replace("�", "..."), **vals})
    return pd.DataFrame(rows)


t27 = ahs_table("Table 27", "Kigali")
t27.columns = ["item", "Kigali", "South", "West", "North", "East", "Rwanda", "Male-headed", "Female-headed"]
t27["item"] = t27.item.replace({"Households who receive extension services (%)": "Any extension service"})
t27 = t27[t27.item != "Number of agricultural households (,000)"]
t27.round(1).to_csv(OUT / "ahs2024_extension_types.csv", index=False)

t29 = ahs_table("Table 29", "Government officials")
t29.columns = ["service"] + [c.split(" (")[0].strip() for c in t29.columns[1:]]
t29 = t29.rename(columns={t29.columns[-1]: "households_000"}).drop(columns=["Total"], errors="ignore")
t29.round(2).to_csv(OUT / "ahs2024_extension_sources.csv", index=False)

print(f"Cooperatives: {len(coops)} districts, {coops.cooperatives.sum()} cooperatives, "
      f"{coops.food_processors.sum()} food processors, {coops.exporters.sum()} goods exporters")
print(f"EICV 2020: {len(cons)} district-crop rows across {cons.DistrictName.nunique()} districts")
print(f"Irrigation (SAS 2026 A Table 32): {len(irr)} districts")
print(f"AHS 2024: {len(t27)} extension-type rows, {len(t29)} extension-source rows")
