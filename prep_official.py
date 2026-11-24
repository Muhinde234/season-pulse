"""Imboni - read NISR's official Seasonal Agricultural Survey tables (6 seasons) into tidy files for the app.

Source: the "Tables_<year> Season <A|B>.xlsx" files NISR publishes with every SAS release
(https://statistics.gov.rw/data-sources/surveys/Seasonal-Agricultural-Survey), saved in data/raw/sas_tables/
as SAS_<year><season>.xlsx. Table numbers shift between seasons (Season A files carry two extra GVA tables),
so every table is found by its title, never by its number.

Run:  python prep_official.py

Outputs (app_data/):
    official_district_crops.csv  season x district x crop: yield (all farmers and large-scale, kg/ha),
                                 production (MT), cultivated and harvested area (ha)
    official_farmer_type.csv     season x crop: national yield for all, small-scale (SSF) and large-scale (LSF)
    official_national.csv        season x crop: national area, production, yield (Table 6, 3 years per file)
    official_inputs.csv          season x district: % of farmers using improved seeds, organic and inorganic
                                 fertilizer, pesticides, irrigation, erosion control (overall, SSF, LSF)
"""
import re
from pathlib import Path

import numpy as np
import pandas as pd

RAW = Path("data/raw/sas_tables")
OUT = Path("app_data")
SEASONS = ["2024A", "2024B", "2025A", "2025B", "2026A", "2026B"]
DISTRICTS = ["Nyarugenge", "Gasabo", "Kicukiro", "Nyanza", "Gisagara", "Nyaruguru", "Huye", "Nyamagabe", "Ruhango",
             "Muhanga", "Kamonyi", "Karongi", "Rutsiro", "Rubavu", "Nyabihu", "Ngororero", "Rusizi", "Nyamasheke",
             "Rulindo", "Gakenke", "Musanze", "Burera", "Gicumbi", "Rwamagana", "Nyagatare", "Gatsibo", "Kayonza",
             "Kirehe", "Ngoma", "Bugesera"]
SUMMARY = ["National", "SSF", "LSF"]
# table header word -> crop name used in the app (group columns such as "Cereals" are skipped)
CROPS = {"maize": "Maize", "sorghum": "Sorghum", "paddy rice": "Paddy rice", "wheat": "Wheat", "cassava": "Cassava",
         "sweet potato": "Sweet potato", "irish potato": "Irish potato", "bananas": "Banana", "banana": "Banana",
         "bean": "Beans", "soybean": "Soybean", "groundnuts": "Groundnuts", "groundnut": "Groundnuts",
         "vegetables": "Vegetables"}
DISTRICT_TABLES = {"yield_kgha": "Average yield by crop type and district",
                   "yield_lsf_kgha": "Average yield of large-scale farmers",
                   "production_mt": "Crop production by crop type and district",
                   "cultivated_ha": "Cultivated area by crop type and district",
                   "harvested_ha": "Harvested area by crop type and district"}
INPUT_TABLES = {"Use of seeds by farmer type": ["improved_seed"],
                "Use of organic fertilizer by farmer type": ["organic_fert"],
                "Use of Inorganic fertilizer by farmer type": ["inorganic_fert"],
                "Use of pesticides by farmer type": ["pesticide"],
                "farmers who practiced agricultural practices": ["erosion_control", "mechanization", "irrigation",
                                                                 "agroforestry"]}


def find_sheet(book: pd.ExcelFile, phrase: str) -> pd.DataFrame:
    """The sheet whose title (first rows) contains `phrase`, read without headers."""
    for sh in book.sheet_names:
        head = book.parse(sh, header=None, nrows=4)
        if phrase.lower() in " ".join(str(v) for v in head.values.ravel() if isinstance(v, str)).lower():
            return book.parse(sh, header=None)
    raise LookupError(f"no table titled '{phrase}' in {book.io}")


def num(v):
    v = pd.to_numeric(v, errors="coerce")
    return None if pd.isna(v) else float(v)


def district_crop_table(df: pd.DataFrame) -> pd.DataFrame:
    """District x crop table -> long rows (district or National/SSF/LSF, crop, value)."""
    hdr = next(i for i in range(len(df)) if any(str(v).strip().startswith("District") for v in df.iloc[i]))
    dcol = next(j for j, v in enumerate(df.iloc[hdr]) if str(v).strip().startswith("District"))
    cols = {j: CROPS[str(v).strip().lower()] for j, v in enumerate(df.iloc[hdr]) if str(v).strip().lower() in CROPS}
    rows = []
    for i in range(hdr + 1, len(df)):
        name = str(df.iat[i, dcol]).strip()
        if name in DISTRICTS or name in SUMMARY:
            rows += [(name, crop, num(df.iat[i, j])) for j, crop in cols.items()]
    return pd.DataFrame(rows, columns=["DistrictName", "crop", "value"])


def input_table(df: pd.DataFrame, metrics: list[str]) -> pd.DataFrame:
    """'% of farmers' groups (Overall / SSF / LSF) per district; the first len(metrics) groups are farmer shares."""
    sub = next(i for i in range(len(df)) if any(str(v).strip() == "Overall" for v in df.iloc[i]))
    starts = [j for j, v in enumerate(df.iloc[sub]) if str(v).strip() == "Overall"][:len(metrics)]
    dcol = next(j for j in range(df.shape[1]) if any(str(df.iat[i, j]).strip() in DISTRICTS for i in range(len(df))))
    rows = []
    for i in range(sub + 1, len(df)):
        name = str(df.iat[i, dcol]).strip()
        if name in DISTRICTS:
            for m, j in zip(metrics, starts):
                rows.append((name, m, num(df.iat[i, j]), num(df.iat[i, j + 1]), num(df.iat[i, j + 2])))
    return pd.DataFrame(rows, columns=["DistrictName", "metric", "overall", "ssf", "lsf"])


def national_table(df: pd.DataFrame) -> pd.DataFrame:
    """Table 6: crop x {cultivated, harvested, production, yield} x 3 seasons of the same letter."""
    hdr = next(i for i in range(len(df)) if any(str(v).strip().startswith("Crop/Groups") for v in df.iloc[i]))
    ccol = next(j for j, v in enumerate(df.iloc[hdr]) if str(v).strip().startswith("Crop/Groups"))
    groups, current = {}, None
    for j, v in enumerate(df.iloc[hdr]):
        s = str(v).lower()
        current = ("cultivated_ha" if "cultivated" in s else "harvested_ha" if "harvested" in s else
                   "production_mt" if "production" in s else "yield_mt_ha" if "yield" in s else current)
        label = re.sub(r"\s+", "", str(df.iat[hdr + 1, j]))
        if current and re.fullmatch(r"20\d\d[ABC]", label):
            groups[j] = (current, label)
    rows = []
    for i in range(hdr + 2, len(df)):
        crop = CROPS.get(str(df.iat[i, ccol]).strip().lower())
        if crop:
            rows += [(season, crop, metric, num(df.iat[i, j])) for j, (metric, season) in groups.items()]
    long = pd.DataFrame(rows, columns=["season", "crop", "metric", "value"])
    return long.pivot_table(index=["season", "crop"], columns="metric", values="value").reset_index()


district_parts, farmer_type, national, inputs = [], [], [], []
for season in SEASONS:
    book = pd.ExcelFile(RAW / f"SAS_{season}.xlsx")
    wide = None
    for col, phrase in DISTRICT_TABLES.items():
        t = district_crop_table(find_sheet(book, phrase)).rename(columns={"value": col})
        if col == "yield_kgha":  # the National / SSF / LSF rows of the yield table = yield by farmer type
            ft = t[t.DistrictName.isin(SUMMARY)].pivot_table(index="crop", columns="DistrictName", values=col)
            farmer_type.append(ft.reset_index().assign(season=season))
        t = t[t.DistrictName.isin(DISTRICTS)]
        wide = t if wide is None else wide.merge(t, on=["DistrictName", "crop"], how="outer")
    district_parts.append(wide.assign(season=season))
    national.append(national_table(find_sheet(book, "Cultivated area, harvested area, production and yield by crop")))
    for phrase, metrics in INPUT_TABLES.items():
        inputs.append(input_table(find_sheet(book, phrase), metrics).assign(season=season))

dc = pd.concat(district_parts, ignore_index=True)
# 0 in a district table = crop not grown / not observed there: keep it as missing, not as a failed harvest
for c in DISTRICT_TABLES:
    dc.loc[dc[c] == 0, c] = None
dc = dc[["season", "DistrictName", "crop", *DISTRICT_TABLES]].sort_values(["season", "crop", "DistrictName"])
dc.to_csv(OUT / "official_district_crops.csv", index=False)

ft = pd.concat(farmer_type, ignore_index=True).rename(columns={"National": "national_kgha", "SSF": "ssf_kgha",
                                                               "LSF": "lsf_kgha"})
ft[["season", "crop", "national_kgha", "ssf_kgha", "lsf_kgha"]].to_csv(OUT / "official_farmer_type.csv", index=False)

# each Season file repeats the two previous years: keep the most recent publication of each season
nat = pd.concat(national, ignore_index=True).drop_duplicates(["season", "crop"], keep="last")
nat = nat[["season", "crop", "cultivated_ha", "harvested_ha", "production_mt", "yield_mt_ha"]]
nat.sort_values(["crop", "season"]).to_csv(OUT / "official_national.csv", index=False)

inp = pd.concat(inputs, ignore_index=True)[["season", "DistrictName", "metric", "overall", "ssf", "lsf"]]
inp.to_csv(OUT / "official_inputs.csv", index=False)

# ---------- checks ----------
print(f"district x crop rows: {len(dc)} ({dc.season.nunique()} seasons, {dc.DistrictName.nunique()} districts, "
      f"{dc.crop.nunique()} crops)")
print(f"national rows: {len(nat)} seasons {sorted(nat.season.unique())}")
print(f"input rows: {len(inp)} metrics {sorted(inp.metric.unique())}")
# the district table's production should add up to Table 6's national production
chk = dc.groupby(["season", "crop"]).production_mt.sum().reset_index().merge(nat, on=["season", "crop"])
chk["ratio"] = chk.production_mt_x / chk.production_mt_y
print("district production / national production (should be ~1):",
      chk.ratio.describe()[["min", "50%", "max"]].round(3).to_dict())

# ---------- validation of the early-warning baseline on official 2026 Seasons A and B ----------
APP = {"Beans": "Beans", "Cassava": "Cassava", "Irish potatoes": "Irish potato", "Maize": "Maize"}
LOW, FLAG = 0.80, 0.85  # official RYI <= LOW = a bad cell; baseline <= FLAG = flagged in advance
base = pd.read_csv(OUT / "out_district_baseline.csv")


def official_ryi(season: str) -> pd.DataFrame:
    d = dc[dc.season == season].dropna(subset=["yield_kgha"]).copy()
    d["official_RYI"] = d.yield_kgha / d.groupby("crop").yield_kgha.transform("median")
    return d


for season in ["2026A", "2026B"]:
    b = base[base.Season == f"Season{season[-1]}"].assign(crop=lambda x: x.CropName.map(APP)).dropna(subset=["crop"])
    v = official_ryi(season).merge(b[["DistrictName", "crop", "CropName", "baseline_RYI", "n_years"]],
                                   on=["DistrictName", "crop"]).rename(columns={"baseline_RYI": "predicted_RYI"})
    v["error_log"] = (np.log(v.predicted_RYI) - np.log(v.official_RYI)).round(3)
    v["actual_low"], v["flagged"] = v.official_RYI <= LOW, v.predicted_RYI <= FLAG
    v[["DistrictName", "yield_kgha", "CropName", "official_RYI", "predicted_RYI", "n_years", "error_log",
       "actual_low", "flagged"]].round(3).sort_values(["CropName", "DistrictName"]).to_csv(
        OUT / f"out_validation_{season}.csv", index=False)
    print(f"validation {season}: {len(v)} cells, caught {int((v.actual_low & v.flagged).sum())} of "
          f"{int(v.actual_low.sum())}")

# ---------- next-season forecast from official tables only: predict 2026 from 2024 and 2025 (same season) ----------
MAJOR = ["Beans", "Maize", "Irish potato", "Cassava", "Sweet potato", "Paddy rice", "Banana"]
methods, cells = [], []
for letter in "AB":
    r = {y: official_ryi(f"{y}{letter}").set_index(["DistrictName", "crop"]).official_RYI for y in (2024, 2025, 2026)}
    df = pd.concat(r, axis=1).dropna()
    df = df[df.index.get_level_values("crop").isin(MAJOR)]
    lt = np.log(df)
    preds = {"Every district typical": 0 * lt[2025], "Last season (2025)": lt[2025],
             "Average of 2024 and 2025": (lt[2024] + lt[2025]) / 2}
    for name, p in preds.items():
        low, fl = df[2026] <= LOW, np.exp(p) <= FLAG
        methods.append({"season": letter, "method": name, "cells": len(df),
                        "mae_pct": round(100 * float((p - lt[2026]).abs().mean()), 1),
                        "bad_cells": int(low.sum()), "caught": int((low & fl).sum()), "flagged": int(fl.sum())})
    cells.append(df.reset_index().rename(columns={2024: "ryi_2024", 2025: "ryi_2025", 2026: "ryi_2026"})
                 .assign(season=letter))
pd.DataFrame(methods).to_csv(OUT / "out_official_forecast.csv", index=False)
pd.concat(cells).round(4).to_csv(OUT / "out_official_forecast_cells.csv", index=False)
print(pd.DataFrame(methods).to_string(index=False))
