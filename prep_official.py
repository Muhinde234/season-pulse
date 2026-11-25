"""Imboni - read NISR's official Seasonal Agricultural Survey tables (2022-2026, Seasons A and B) into tidy files.

Sources (https://statistics.gov.rw/data-sources/surveys/Seasonal-Agricultural-Survey), saved in data/raw/sas_tables/:
    SAS_2022_annual.xlsx, SAS_2023_annual.xlsx   annual tables: district tables for Seasons A, B and C
    SAS_<year><A|B>.xlsx (2024A ... 2026B)       per-season tables: district tables, farmer types, inputs, Table 6
Table numbers shift between files, so every table is found by its title (and season), never by its number.
Season C is left out: it is a short season grown mainly in swamps and the volcanic highlands, and NISR publishes
it only in the annual tables, for a few crops.

How NISR produces these figures (SAS 2026 B main report, chapter 2): an area frame of 9 ha segments, stratified by
district and land cover; 1,200 segments a season (25-68 per district) plus a list of large-scale farmers. Plot
areas are measured with GPS; yields come from the production farmers report. District figures are direct survey
estimates (weighted totals and ratios), not model-based.

Run:  python prep_official.py   (after build_baseline.py: the 2026 validation reads its baseline)

Outputs (app_data/):
    official_district_crops.csv     season x district x crop: yield (all farmers and large-scale, kg/ha),
                                    production (MT), cultivated and harvested area (ha), 2022A-2026B
    official_farmer_type.csv        season x crop: national yield for all, small-scale (SSF) and large-scale (LSF)
    official_national.csv           season x crop: national area, production, yield (Table 6, 3 years per file)
    official_inputs.csv             season x district: % of farmers using improved seeds, fertilizer, pesticides,
                                    irrigation, erosion control (overall, SSF, LSF), 2024A-2026B
    out_official_baseline.csv       the alert baseline: each district x crop's latest official result per season
    out_official_backtest.csv       predict each season 2023-2026 from the official tables: error and bad cells
    out_official_backtest_cells.csv the cells behind it (previous and actual RYI)
    out_rain_vs_official.csv        CHIRPS rainfall vs the change in official RYI from the previous year
    out_cleaned_vs_official.csv     cleaned SAS files vs official tables on the years both cover (2022-2024)
    out_validation_2026A/B.csv      the 2020-2024 cleaned-data baseline vs official 2026 results
"""
import re
from pathlib import Path

import numpy as np
import pandas as pd

RAW = Path("data/raw/sas_tables")
OUT = Path("app_data")
ANNUAL = {2022: "SAS_2022_annual.xlsx", 2023: "SAS_2023_annual.xlsx"}  # Seasons A and B read from each
SEASONAL = ["2024A", "2024B", "2025A", "2025B", "2026A", "2026B"]
DISTRICTS = ["Nyarugenge", "Gasabo", "Kicukiro", "Nyanza", "Gisagara", "Nyaruguru", "Huye", "Nyamagabe", "Ruhango",
             "Muhanga", "Kamonyi", "Karongi", "Rutsiro", "Rubavu", "Nyabihu", "Ngororero", "Rusizi", "Nyamasheke",
             "Rulindo", "Gakenke", "Musanze", "Burera", "Gicumbi", "Rwamagana", "Nyagatare", "Gatsibo", "Kayonza",
             "Kirehe", "Ngoma", "Bugesera"]
SUMMARY = ["National", "SSF", "LSF"]
# table header word -> crop name (group columns such as "Cereals" and sub-types such as "Bush bean" are skipped)
CROPS = {"maize": "Maize", "sorghum": "Sorghum", "paddy rice": "Paddy rice", "wheat": "Wheat", "cassava": "Cassava",
         "sweet potato": "Sweet potato", "sweet potatoes": "Sweet potato", "irish potato": "Irish potato",
         "irish potatoes": "Irish potato", "bananas": "Banana", "banana": "Banana", "bean": "Beans", "beans": "Beans",
         "soybean": "Soybean", "soya beans": "Soybean", "groundnuts": "Groundnuts", "groundnut": "Groundnuts",
         "ground nuts": "Groundnuts", "vegetables": "Vegetables",
         "cooking banana": "Cooking banana"}  # PSTA 5 targets cooking banana, not all bananas
MAJOR = ["Beans", "Maize", "Irish potato", "Cassava", "Sweet potato", "Paddy rice", "Banana"]
APP = {"Irish potato": "Irish potatoes"}  # official crop name -> app crop name, where they differ
# column -> title phrases (any of them; matched after lower-casing and turning "-" and "_" into spaces)
DISTRICT_TABLES = {"yield_kgha": ["average yield by crop type"],
                   "yield_lsf_kgha": ["average yield of large scale farmers", "average yield on large scale farmers"],
                   "production_mt": ["crop production by crop type"],
                   "cultivated_ha": ["cultivated area by crop type"],
                   "harvested_ha": ["harvested area by crop type"]}
INPUT_TABLES = {"Use of seeds by farmer type": ["improved_seed"],
                "Use of organic fertilizer by farmer type": ["organic_fert"],
                "Use of Inorganic fertilizer by farmer type": ["inorganic_fert"],
                "Use of pesticides by farmer type": ["pesticide"],
                "farmers who practiced agricultural practices": ["erosion_control", "mechanization", "irrigation",
                                                                 "agroforestry"]}
LOW, FLAG = 0.80, 0.85  # official RYI <= LOW = a bad cell; prediction <= FLAG = flagged in advance
MOVED = 0.10            # a cell "moved" when its log RYI changed by more than this from the previous year


def norm(s: str) -> str:
    return " ".join(re.sub(r"[-_]", " ", s.lower()).split())


def find_sheet(book: pd.ExcelFile, phrases: list[str], season: str | None = None) -> pd.DataFrame:
    """The sheet whose title (first rows) contains one of `phrases` and, if given, the season ('2023A')."""
    for sh in book.sheet_names:
        head = book.parse(sh, header=None, nrows=4)
        title = norm(" ".join(str(v) for v in head.values.ravel() if isinstance(v, str)))
        if season and not (f"season {season[-1].lower()}" in title and season[:4] in title):
            continue
        if any(norm(p) in title for p in phrases):
            return book.parse(sh, header=None)
    raise LookupError(f"no table titled {phrases} {season or ''} in {book.io}")


def num(v):
    v = pd.to_numeric(v, errors="coerce")
    return None if pd.isna(v) else float(v)


def district_crop_table(df: pd.DataFrame) -> pd.DataFrame:
    """District x crop table -> long rows (district or National/SSF/LSF, crop, value).
    Header row = the first row naming 3+ crops; district column = the column holding district names."""
    hdr = next(i for i in range(len(df)) if sum(str(v).strip().lower() in CROPS for v in df.iloc[i]) >= 3)
    dcol = max(range(df.shape[1]), key=lambda j: df.iloc[:, j].astype(str).str.strip().isin(DISTRICTS).sum())
    cols = {}
    for j, v in enumerate(df.iloc[hdr]):
        crop = CROPS.get(str(v).strip().lower())
        if crop and crop not in cols.values():  # first column of a crop wins
            cols[j] = crop
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


def district_tables(book: pd.ExcelFile, season: str, tag: str | None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """All district x crop tables of one season, side by side, plus the National/SSF/LSF yield rows."""
    wide, ft = None, None
    for col, phrases in DISTRICT_TABLES.items():
        t = district_crop_table(find_sheet(book, phrases, tag)).rename(columns={"value": col})
        if col == "yield_kgha":  # the National / SSF / LSF rows of the yield table = yield by farmer type
            ft = t[t.DistrictName.isin(SUMMARY)].pivot_table(index="crop", columns="DistrictName", values=col)
            ft = ft.reset_index().assign(season=season)
        t = t[t.DistrictName.isin(DISTRICTS)]
        wide = t if wide is None else wide.merge(t, on=["DistrictName", "crop"], how="outer")
    return wide.assign(season=season), ft


district_parts, farmer_type, national, inputs = [], [], [], []
for year, fname in ANNUAL.items():
    book = pd.ExcelFile(RAW / fname)
    for letter in "AB":
        wide, ft = district_tables(book, f"{year}{letter}", f"{year}{letter}")
        district_parts.append(wide)
        farmer_type.append(ft)
for season in SEASONAL:
    book = pd.ExcelFile(RAW / f"SAS_{season}.xlsx")
    wide, ft = district_tables(book, season, None)
    district_parts.append(wide)
    farmer_type.append(ft)
    national.append(national_table(find_sheet(book, ["Cultivated area, harvested area, production and yield by crop"])))
    for phrase, metrics in INPUT_TABLES.items():
        inputs.append(input_table(find_sheet(book, [phrase]), metrics).assign(season=season))

dc = pd.concat(district_parts, ignore_index=True)
# 0 in a district table = crop not grown / not observed there: keep it as missing, not as a failed harvest
for c in DISTRICT_TABLES:
    dc.loc[dc[c] == 0, c] = None
dc = dc[["season", "DistrictName", "crop", *DISTRICT_TABLES]].sort_values(["season", "crop", "DistrictName"])
dc.to_csv(OUT / "official_district_crops.csv", index=False)

ft = pd.concat(farmer_type, ignore_index=True).rename(columns={"National": "national_kgha", "SSF": "ssf_kgha",
                                                               "LSF": "lsf_kgha"})
for c in ["national_kgha", "ssf_kgha", "lsf_kgha"]:
    if c not in ft:
        ft[c] = np.nan
ft[["season", "crop", "national_kgha", "ssf_kgha", "lsf_kgha"]].to_csv(OUT / "official_farmer_type.csv", index=False)

# each Season file repeats the two previous years: keep the most recent publication of each season
nat = pd.concat(national, ignore_index=True).drop_duplicates(["season", "crop"], keep="last")
nat = nat[["season", "crop", "cultivated_ha", "harvested_ha", "production_mt", "yield_mt_ha"]]
nat.sort_values(["crop", "season"]).to_csv(OUT / "official_national.csv", index=False)

inp = pd.concat(inputs, ignore_index=True)[["season", "DistrictName", "metric", "overall", "ssf", "lsf"]]
inp.to_csv(OUT / "official_inputs.csv", index=False)

# ---------- checks ----------
print(f"district x crop rows: {len(dc)} ({dc.season.nunique()} seasons {sorted(dc.season.unique())}, "
      f"{dc.DistrictName.nunique()} districts, {dc.crop.nunique()} crops)")
print(f"national rows: {len(nat)} seasons {sorted(nat.season.unique())}")
print(f"input rows: {len(inp)} metrics {sorted(inp.metric.unique())}")
# the district table's production should add up to Table 6's national production (2022-2026 are all in Table 6)
chk = dc.groupby(["season", "crop"]).production_mt.sum().reset_index().merge(nat, on=["season", "crop"])
chk["ratio"] = chk.production_mt_x / chk.production_mt_y
print("district production / national production (should be ~1), by season:")
print(chk[chk.crop.isin(MAJOR)].groupby("season").ratio.agg(["min", "median", "max"]).round(3).to_string())


def official_ryi(season: str) -> pd.DataFrame:
    d = dc[dc.season == season].dropna(subset=["yield_kgha"]).copy()
    d["official_RYI"] = d.yield_kgha / d.groupby("crop").yield_kgha.transform("median")
    return d


def app_crop(c: str) -> str:
    return APP.get(c, c)


# RYI per (letter, year) for the major crops: one column per year
YEARS = sorted({int(s[:4]) for s in dc.season})
ryi = {letter: pd.concat({y: official_ryi(f"{y}{letter}").set_index(["DistrictName", "crop"]).official_RYI
                          for y in YEARS}, axis=1)
       for letter in "AB"}
for letter in ryi:
    ryi[letter] = ryi[letter][ryi[letter].index.get_level_values("crop").isin(MAJOR)]

# ---------- validation of the 2020-2024 cleaned-data baseline on official 2026 Seasons A and B ----------
base = pd.read_csv(OUT / "out_district_baseline.csv")
for season in ["2026A", "2026B"]:
    b = base[base.Season == f"Season{season[-1]}"].assign(crop=lambda x: x.CropName.replace({v: k for k, v in APP.items()}))
    v = official_ryi(season).merge(b[["DistrictName", "crop", "CropName", "baseline_RYI", "n_years"]],
                                   on=["DistrictName", "crop"]).rename(columns={"baseline_RYI": "predicted_RYI"})
    v["error_log"] = (np.log(v.predicted_RYI) - np.log(v.official_RYI)).round(3)
    v["actual_low"], v["flagged"] = v.official_RYI <= LOW, v.predicted_RYI <= FLAG
    v[["DistrictName", "yield_kgha", "CropName", "official_RYI", "predicted_RYI", "n_years", "error_log",
       "actual_low", "flagged"]].round(3).sort_values(["CropName", "DistrictName"]).to_csv(
        OUT / f"out_validation_{season}.csv", index=False)
    print(f"cleaned-data baseline vs official {season}: {len(v)} cells, caught {int((v.actual_low & v.flagged).sum())} "
          f"of {int(v.actual_low.sum())}")

# ---------- backtest: predict every season 2023-2026 from the official tables of earlier years ----------
methods, cells = [], []
for letter, r in ryi.items():
    lr = np.log(r)
    for y in YEARS[1:]:
        ok = lr[y].notna() & lr[y - 1].notna()
        now, prev = lr.loc[ok, y], lr.loc[ok, y - 1]
        two = lr.loc[ok, [c for c in (y - 1, y - 2) if c in lr]].mean(axis=1)  # mean of the years available
        preds = {"Every district typical": 0 * now, "Last season": prev, "Average of last two seasons": two}
        low = now <= np.log(LOW)
        for name, p in preds.items():
            fl = p <= np.log(FLAG)
            methods.append({"season": letter, "year": y, "method": name, "cells": int(ok.sum()),
                            "mae_pct": round(100 * float((p - now).abs().mean()), 1),
                            "rank_r": round(float(p.rank().corr(now.rank())), 3) if name != "Every district typical"
                            else np.nan,
                            "bad_cells": int(low.sum()), "caught": int((low & fl).sum()), "flagged": int(fl.sum()),
                            "moved": int(((now - prev).abs() > MOVED).sum())})
        cells.append(pd.DataFrame({"season": letter, "year": y, "ryi_prev": np.exp(prev), "ryi_now": np.exp(now)})
                     .reset_index())
bt = pd.DataFrame(methods)
bt.to_csv(OUT / "out_official_backtest.csv", index=False)
pd.concat(cells).round(4).to_csv(OUT / "out_official_backtest_cells.csv", index=False)
print(bt[bt.method == "Last season"].to_string(index=False))

# ---------- the alert baseline: latest official result of the same season, per district x crop ----------
rows = []
for letter, r in ryi.items():
    latest = max(y for y in YEARS if r[y].notna().any())
    last3 = [y for y in YEARS if y > latest - 3]
    for (district, crop), row in r.iterrows():
        if pd.isna(row[latest]):
            continue
        rows.append({"Season": f"Season{letter}", "DistrictName": district, "CropName": app_crop(crop),
                     "baseline_RYI": round(float(row[latest]), 3), "source_season": f"{latest}{letter}",
                     "prev_RYI": round(float(row[latest - 1]), 3) if pd.notna(row.get(latest - 1)) else np.nan,
                     "n_years": int(row.notna().sum()),
                     "persistently_low": bool(row[last3].notna().all() and (row[last3] < LOW).all())})
ob = pd.DataFrame(rows)
ob.to_csv(OUT / "out_official_baseline.csv", index=False)
print(f"official baseline: {len(ob)} rows, {int(ob.persistently_low.sum())} persistently low "
      f"(< {LOW} in each of the last 3 years)")

# ---------- rainfall: does a relatively dry season explain the cells that moved away from last season? ----------
# Rainfall is made relative like RYI: log(rain / district average) minus the median of that across districts.
rain = pd.read_csv(OUT / "district_rainfall.csv")
rain = rain[~rain.partial & rain.Season.isin(["SeasonA", "SeasonB"])].copy()
rain["log_rain_anom"] = np.log(rain.rain_mm / rain.avg_mm)
rain["rain_rel"] = rain.log_rain_anom - rain.groupby(["Season", "Year"]).log_rain_anom.transform("median")
bc = pd.concat(cells)
bc = bc.assign(Season="Season" + bc.season, Year=bc.year, CropName=bc.crop.map(app_crop),
               ryi_dev=np.log(bc.ryi_now / bc.ryi_prev))
rv = bc.merge(rain[["DistrictName", "Season", "Year", "rain_mm", "rain_anom_pct", "rain_rel"]],
              on=["DistrictName", "Season", "Year"])
rv[["DistrictName", "CropName", "Season", "Year", "ryi_prev", "ryi_now", "ryi_dev", "rain_mm", "rain_anom_pct",
    "rain_rel"]].round(4).to_csv(OUT / "out_rain_vs_official.csv", index=False)
print(f"rain vs official RYI change: {len(rv)} cell-years, r = {rv.ryi_dev.corr(rv.rain_rel):+.3f}")

# ---------- cleaned SAS files vs official tables, on the years both cover ----------
sas = pd.read_csv("data/raw/sas_historical.csv")
sas = sas[sas.Season.isin(["SeasonA", "SeasonB"]) & sas.DistrictName.notna() & (sas.Num_Observations >= 10)]
sas = sas.assign(area=sas.Avg_Area_ha * sas.Num_Observations)
sas = sas[sas.area > 0].assign(yield_=lambda d: d.Total_Production_Kg / d.area)
sas["clean_RYI"] = sas.yield_ / sas.groupby(["CropName", "Season", "Year"]).yield_.transform("median")
off = pd.concat([official_ryi(f"{y}{l}").assign(Year=y, Season=f"Season{l}") for y in YEARS for l in "AB"])
off["CropName"] = off.crop.map(app_crop)
both = sas.merge(off[["DistrictName", "CropName", "Season", "Year", "yield_kgha", "official_RYI"]],
                 on=["DistrictName", "CropName", "Season", "Year"])
cmp_rows = []
for (crop, year), g in both.groupby(["CropName", "Year"]):
    cmp_rows.append({"CropName": crop, "Year": year, "cells": len(g),
                     "rank_r": round(float(g.clean_RYI.rank().corr(g.official_RYI.rank())), 3),
                     "clean_median_yield": round(float(g.yield_.median()), 1),
                     "official_median_kgha": round(float(g.yield_kgha.median()), 1)})
cv = pd.DataFrame(cmp_rows)
cv.to_csv(OUT / "out_cleaned_vs_official.csv", index=False)
print("cleaned vs official (rank r per crop and year):")
print(cv.to_string(index=False))
