"""NISR's official SAS tables (prep_official.py) and the productivity-target analysis built on them.

Everything here uses published numbers only:
    - PSTA 5 (MINAGRI, 2024/25-2028/29): "a 50% increase in productivity ... as outlined in the NST2 goal" (p. 14).
      Its results framework (p. 21) sets a yield target per priority food crop and year, from a 2023 baseline,
      source SAS. Those 2023 baselines equal NISR's 2023 Season A national yields for all eight crops (to one
      decimal), so progress is measured on Season A national yields. We read farming year 2024/25 as Season A 2025
      (Sep 2024 - Feb 2025) and 2025/26 as Season A 2026: our reading, PSTA 5 doesn't say.
    - district catch-up: districts below the top-quarter (75th percentile) yield of a season reach it
    - small-scale catch-up: small-scale farmers (SSF) close part of the gap to large-scale (LSF) yield;
      SSF's share of harvested area is solved from national = s * SSF + (1 - s) * LSF (Tables 6 and 11/13)
"""
import numpy as np
import pandas as pd
import streamlit as st

from core.data import DATA, SEASONS, current_season, season_year

MAJOR = ["Beans", "Maize", "Irish potato", "Cassava", "Sweet potato", "Paddy rice", "Banana"]
LATEST_YEAR = 2026
SOURCE_URL = "https://statistics.gov.rw/data-sources/surveys/Seasonal-Agricultural-Survey"
PSTA5_URL = ("https://www.minagri.gov.rw/fileadmin/user_upload/Minagri/Publications/Policies_and_strategies/"
             "PSTA_5_Abridged_version_Final.pdf")

# PSTA 5 results framework, "Productivity for the priority food crops" (p. 21), MT/ha, source SAS.
# Columns: baseline 2023, then the target for each farming year.
PSTA_YEARS = ["2023", "2024/25", "2025/26", "2026/27", "2027/28", "2028/29"]
PSTA_TARGETS = {  # NISR crop name -> yields in PSTA_YEARS order
    "Maize": [1.7, 1.87, 2.06, 2.26, 2.49, 2.74],
    "Irish potato": [8.2, 9.2, 10.1, 11.4, 13.1, 14.7],
    "Paddy rice": [4.0, 4.3, 4.5, 4.8, 5.1, 5.4],
    "Wheat": [1.2, 1.29, 1.3, 1.32, 1.34, 1.35],
    "Beans": [0.6, 0.8, 0.9, 1, 1.1, 1.1],
    "Soybean": [0.4, 0.8, 0.9, 1, 1.1, 1.2],
    "Cassava": [13.5, 15, 15.7, 16.5, 17.2, 17.9],
    "Cooking banana": [14.2, 16.3, 17.1, 17.9, 18.8, 19.7],
}
PSTA_CROPS = list(PSTA_TARGETS)
SAS_YEAR = {"2023": 2023, "2024/25": 2025, "2025/26": 2026, "2026/27": 2027, "2027/28": 2028, "2028/29": 2029}
TARGET_LABEL = PSTA_YEARS[-1]


@st.cache_data
def load_national() -> pd.DataFrame:
    return pd.read_csv(DATA / "official_national.csv")


@st.cache_data
def load_district_crops() -> pd.DataFrame:
    return pd.read_csv(DATA / "official_district_crops.csv")


@st.cache_data
def load_farmer_type() -> pd.DataFrame:
    return pd.read_csv(DATA / "official_farmer_type.csv")


@st.cache_data
def load_inputs() -> pd.DataFrame:
    return pd.read_csv(DATA / "official_inputs.csv")


@st.cache_data
def season_a_yield() -> pd.DataFrame:
    """crop x year: NISR's Season A national yield (MT/ha) for the PSTA 5 crops, 2022-2026 (yield table,
    'National' row: the figure PSTA 5's baselines come from)."""
    ft = load_farmer_type()
    ft = ft[ft.crop.isin(PSTA_CROPS) & ft.season.str.endswith("A")].dropna(subset=["national_kgha"])
    return ft.assign(year=ft.season.str[:4].astype(int), yield_t_ha=ft.national_kgha / 1000)[
        ["crop", "year", "yield_t_ha"]].sort_values(["crop", "year"])


def psta_targets() -> pd.DataFrame:
    """Long table: crop, PSTA farming year, the Season A year it is compared with, target MT/ha."""
    return pd.DataFrame([{"crop": c, "psta_year": y, "year": SAS_YEAR[y], "target_t_ha": v}
                         for c, vals in PSTA_TARGETS.items() for y, v in zip(PSTA_YEARS, vals)])


@st.cache_data
def target_progress() -> pd.DataFrame:
    """One row per PSTA crop: baseline, latest Season A yield, that year's PSTA target, and the final target."""
    y = season_a_yield().set_index(["crop", "year"]).yield_t_ha
    t = psta_targets()
    latest = max(yr for yr in SAS_YEAR.values() if yr <= LATEST_YEAR)
    psta_now = next(k for k, v in SAS_YEAR.items() if v == latest)
    rows = []
    for crop in PSTA_CROPS:
        tt = t[t.crop == crop].set_index("psta_year").target_t_ha
        rows.append({"crop": crop, "base_t_ha": tt["2023"], "nisr_2023A": y.get((crop, 2023), np.nan),
                     "latest_t_ha": y.get((crop, latest), np.nan), "psta_now": psta_now,
                     "target_now": tt[psta_now], "target_t_ha": tt[TARGET_LABEL]})
    out = pd.DataFrame(rows)
    out["change"] = out.latest_t_ha / out.base_t_ha - 1                 # since the PSTA 5 baseline
    out["vs_target_now"] = out.latest_t_ha / out.target_now - 1          # vs this year's PSTA target
    out["needed"] = out.target_t_ha / out.latest_t_ha - 1                # still to gain by 2028/29
    out["status"] = np.where(out.vs_target_now >= 0, "On track",
                             np.where(out.change > 0, "Behind", "Below baseline"))
    return out.sort_values("vs_target_now")


def _season_gains(crop: str, season: str, catch_share: float, gap_share: float) -> dict:
    """Extra tonnes in one season from the two levers (see module docstring)."""
    dc = load_district_crops()
    d = dc[(dc.season == season) & (dc.crop == crop)].dropna(subset=["yield_kgha", "harvested_ha"])
    nat = load_national().query("season == @season and crop == @crop")
    ft = load_farmer_type().query("season == @season and crop == @crop")
    production = float(nat.production_mt.iloc[0]) if len(nat) else float((d.yield_kgha * d.harvested_ha).sum() / 1e3)
    p75 = d.yield_kgha.quantile(.75) if len(d) else np.nan
    catch_t = float(((p75 - d.yield_kgha).clip(lower=0) * d.harvested_ha).sum() / 1e3 * catch_share) if len(d) else 0.0
    gap_t = 0.0
    if len(ft) and len(nat):
        n, s_y, l_y = ft.national_kgha.iloc[0], ft.ssf_kgha.iloc[0], ft.lsf_kgha.iloc[0]
        if pd.notna(l_y) and pd.notna(s_y) and l_y > s_y > 0:
            ssf_area_share = float(np.clip((l_y - n) / (l_y - s_y), 0, 1))
            gap_t = ssf_area_share * float(nat.harvested_ha.iloc[0]) * (l_y - s_y) / 1e3 * gap_share
    return {"production": production, "catch_t": catch_t, "gap_t": gap_t}


@st.cache_data
def scenario(catch_share: float, gap_share: float, year: int = LATEST_YEAR) -> pd.DataFrame:
    """Per crop: % more production from district catch-up and from small-scale catch-up, Seasons A + B."""
    rows = []
    for crop in PSTA_CROPS:
        parts = [_season_gains(crop, f"{year}{s}", catch_share, gap_share) for s in "AB"]
        prod = sum(p["production"] for p in parts)
        if not prod > 0:  # no official production for this crop and year: leave it out rather than divide by 0
            continue
        catch, gap = sum(p["catch_t"] for p in parts), sum(p["gap_t"] for p in parts)
        rows.append({"crop": crop, "production_t": prod, "catch_t": catch, "gap_t": gap,
                     "catch_pct": 100 * catch / prod, "gap_pct": 100 * gap / prod,
                     "total_pct": 100 * (catch + gap) / prod})
    return pd.DataFrame(rows)


@st.cache_data
def district_priorities(crop: str, year: int = LATEST_YEAR) -> pd.DataFrame:
    """Districts ranked by the tonnes they would add by reaching the top-quarter yield (Seasons A + B)."""
    dc = load_district_crops()
    out = []
    for s in "AB":
        d = dc[(dc.season == f"{year}{s}") & (dc.crop == crop)].dropna(subset=["yield_kgha", "harvested_ha"])
        if d.empty:
            continue
        p75 = d.yield_kgha.quantile(.75)
        out.append(d.assign(p75=p75, gain_t=(p75 - d.yield_kgha).clip(lower=0) * d.harvested_ha / 1e3))
    if not out:
        return pd.DataFrame()
    d = pd.concat(out)
    g = d.groupby("DistrictName").agg(gain_t=("gain_t", "sum"), harvested_ha=("harvested_ha", "sum"),
                                      production_mt=("production_mt", "sum"))
    g["yield_kgha"] = 1e3 * g.production_mt / g.harvested_ha
    g["p75_kgha"] = d.groupby("DistrictName").apply(
        lambda x: np.average(x.p75, weights=x.harvested_ha), include_groups=False)
    return g[g.gain_t > 0].sort_values("gain_t", ascending=False).reset_index()


# ---------- farming practices (inputs) ----------
INPUT_LABELS = {"improved_seed": "Improved seeds", "inorganic_fert": "Mineral fertilizer",
                "organic_fert": "Organic fertilizer", "pesticide": "Pesticides", "irrigation": "Irrigation",
                "erosion_control": "Erosion control", "mechanization": "Mechanization", "agroforestry": "Agroforestry"}
LATEST_SEASONS = [f"{LATEST_YEAR}A", f"{LATEST_YEAR}B"]


@st.cache_data
def yield_gap_by_farmer_type() -> pd.DataFrame:
    """Per crop: small- and large-scale yield (kg/ha) averaged over the latest A and B seasons where both exist."""
    ft = load_farmer_type()
    ft = ft[ft.crop.isin(MAJOR) & ft.season.isin(LATEST_SEASONS) & (ft.lsf_kgha > 0) & (ft.ssf_kgha > 0)]
    g = ft.groupby("crop")[["ssf_kgha", "lsf_kgha"]].mean()
    g["ratio"] = g.lsf_kgha / g.ssf_kgha
    return g.reset_index().sort_values("ratio")


@st.cache_data
def input_gap_by_farmer_type() -> pd.DataFrame:
    """Per input: % of small- and large-scale farmers using it, mean of districts over the latest A and B seasons."""
    i = load_inputs()
    i = i[i.season.isin(LATEST_SEASONS)].groupby("metric")[["ssf", "lsf", "overall"]].mean().reset_index()
    i["label"] = i.metric.map(INPUT_LABELS)
    return i.sort_values("lsf")


@st.cache_data
def district_practice(season: str, metric: str, crop: str) -> pd.DataFrame:
    """Per district: % of farmers using `metric` (overall) next to the crop's yield and harvested area."""
    i = load_inputs().query("season == @season and metric == @metric")[["DistrictName", "overall", "ssf", "lsf"]]
    d = load_district_crops().query("season == @season and crop == @crop")[
        ["DistrictName", "yield_kgha", "harvested_ha", "production_mt"]]
    return i.merge(d, on="DistrictName", how="left")


@st.cache_data
def practice_signals(metric: str) -> pd.DataFrame:
    """Per crop: correlation across districts between % of farmers using `metric` and yield, after removing
    season-to-season shifts (both sides centred within each season). An association, not a cause."""
    i = load_inputs().query("metric == @metric")[["season", "DistrictName", "overall"]]
    d = load_district_crops()[load_district_crops().crop.isin(MAJOR)].dropna(subset=["yield_kgha"])
    m = d.merge(i, on=["season", "DistrictName"]).dropna(subset=["overall"])
    m["ly"] = np.log(m.yield_kgha)
    rows = []
    for crop, g in m.groupby("crop"):
        y = g.ly - g.groupby("season").ly.transform("mean")
        x = g.overall - g.groupby("season").overall.transform("mean")
        rows.append({"crop": crop, "r": float(np.corrcoef(x, y)[0, 1]), "n": len(g)})
    return pd.DataFrame(rows).sort_values("r")


# ---------- official numbers next to the early-warning alerts ----------
# app crop name (cleaned SAS) -> crop name in NISR's official tables; tomatoes are only published as "vegetables"
APP_TO_OFFICIAL = {"Banana": "Banana", "Beans": "Beans", "Cassava": "Cassava", "Irish potatoes": "Irish potato",
                   "Maize": "Maize", "Paddy rice": "Paddy rice", "Sweet potato": "Sweet potato"}


def latest_official_season(app_season: str) -> str | None:
    """Most recent published season of the same letter: 'SeasonA' -> '2026A'."""
    letter = app_season[-1]
    have = sorted(s for s in load_district_crops().season.unique() if s.endswith(letter))
    return have[-1] if have else None


def year_options() -> list[int]:
    """Year filter: the current season's harvest year first (expected values), then every official year, newest
    first."""
    now = season_year()
    return [now] + sorted({int(s[:4]) for s in load_district_crops().season} - {now}, reverse=True)


def seasons_for(year: int) -> list[str]:
    """Season filter for a year: the current season only for this year, else the seasons NISR published."""
    if year == season_year():
        return [current_season()]
    have = set(load_district_crops().season)
    return [s for s in SEASONS if f"{year}{s[-1]}" in have]


def year_label(year: int) -> str:
    return f"{year} · this season (expected)" if year == season_year() else f"{year} · official NISR results"


def attach_official(t: pd.DataFrame, app_season: str, year: int | None = None) -> pd.DataFrame:
    """Add the official yield (latest season of that letter, or the given year's), the median district yield,
    harvested area, and the tonnes a district-crop falls short of a typical district's yield at its RYI
    (harvested area x median x shortfall)."""
    cols = ["off_season", "off_yield_kgha", "off_median_kgha", "off_harvested_ha", "tonnes_below"]
    season = latest_official_season(app_season) if year is None else f"{year}{app_season[-1]}"
    if season not in set(load_district_crops().season):
        season = None
    if season is None:
        return t.assign(**{c: np.nan for c in cols})
    d = load_district_crops().query("season == @season").dropna(subset=["yield_kgha"])
    d = d.assign(off_median_kgha=d.groupby("crop").yield_kgha.transform("median"))
    m = t.assign(_crop=t.CropName.map(APP_TO_OFFICIAL)).merge(
        d.rename(columns={"crop": "_crop", "yield_kgha": "off_yield_kgha", "harvested_ha": "off_harvested_ha"})
         [["DistrictName", "_crop", "off_yield_kgha", "off_median_kgha", "off_harvested_ha"]],
        on=["DistrictName", "_crop"], how="left").drop(columns="_crop")
    m.index = t.index
    m["off_season"] = season
    m["tonnes_below"] = (m.off_harvested_ha * m.off_median_kgha * (1 - m.adjusted_RYI).clip(lower=0) / 1e3)
    return m


@st.cache_data
def district_trend(district: str, letter: str) -> pd.DataFrame:
    """Official yield per crop and season (one letter) for a district, next to the median district."""
    d = load_district_crops()
    d = d[d.season.str.endswith(letter) & d.crop.isin(MAJOR)].dropna(subset=["yield_kgha"])
    d = d.assign(median_kgha=d.groupby(["season", "crop"]).yield_kgha.transform("median"))
    return d[d.DistrictName == district].assign(year=lambda x: x.season.str[:4].astype(int))


@st.cache_data
def district_vs_national_practices(district: str, season: str) -> pd.DataFrame:
    """% of farmers using each practice in the district vs the mean of all districts, one season."""
    i = load_inputs().query("season == @season")
    nat = i.groupby("metric").overall.mean().rename("national")
    dis = i[i.DistrictName == district].set_index("metric").overall.rename("district")
    out = pd.concat([dis, nat], axis=1).dropna().reset_index()
    out["label"] = out.metric.map(INPUT_LABELS)
    return out.sort_values("national")
