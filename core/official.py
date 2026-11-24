"""NISR's official SAS tables (prep_official.py) and the productivity-target analysis built on them.

Everything here uses published numbers only:
    - yearly national yield = (Season A + Season B production) / (A + B harvested area), Table 6
    - PSTA 5 / NST2 target: productivity of priority food crops +50% by 2029, from the 2024 baseline
      (the agricultural year before PSTA 5 began); a straight path to it means +20% by 2026
    - district catch-up: districts below the top-quarter (75th percentile) yield of a season reach it
    - small-scale catch-up: small-scale farmers (SSF) close part of the gap to large-scale (LSF) yield;
      SSF's share of harvested area is solved from national = s * SSF + (1 - s) * LSF (Tables 6 and 11/13)
"""
import numpy as np
import pandas as pd
import streamlit as st

from core.data import DATA

MAJOR = ["Beans", "Maize", "Irish potato", "Cassava", "Sweet potato", "Paddy rice", "Banana"]
BASE_YEAR, TARGET_YEAR, TARGET_GAIN = 2024, 2029, 0.50
LATEST_YEAR = 2026
EXPECTED_NOW = TARGET_GAIN * (LATEST_YEAR - BASE_YEAR) / (TARGET_YEAR - BASE_YEAR)  # +20% by 2026 on a straight path
SOURCE_URL = "https://statistics.gov.rw/data-sources/surveys/Seasonal-Agricultural-Survey"
PSTA5_URL = ("https://www.minagri.gov.rw/fileadmin/user_upload/Minagri/Publications/Policies_and_strategies/"
             "PSTA_5_Abridged_version_Final.pdf")


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
def yearly_yield() -> pd.DataFrame:
    """crop x year: production, harvested area and yield (MT/ha) for Season A + Season B together."""
    n = load_national()
    n = n[n.crop.isin(MAJOR)].assign(year=lambda d: d.season.str[:4].astype(int), letter=lambda d: d.season.str[-1])
    full = n.groupby(["crop", "year"]).letter.nunique().eq(2)  # only years with both seasons published
    y = n.groupby(["crop", "year"])[["production_mt", "harvested_ha"]].sum()[full].reset_index()
    y["yield_t_ha"] = y.production_mt / y.harvested_ha
    base = y[y.year == BASE_YEAR].set_index("crop").yield_t_ha
    y["index"] = 100 * y.yield_t_ha / y.crop.map(base)
    return y


@st.cache_data
def target_progress() -> pd.DataFrame:
    """One row per crop: yield in the base and latest year, change so far, what the straight path expects."""
    y = yearly_yield()
    b = y[y.year == BASE_YEAR].set_index("crop")
    l = y[y.year == LATEST_YEAR].set_index("crop")
    out = pd.DataFrame({"base_t_ha": b.yield_t_ha, "latest_t_ha": l.yield_t_ha}).dropna()
    out["change"] = out.latest_t_ha / out.base_t_ha - 1
    out["target_t_ha"] = out.base_t_ha * (1 + TARGET_GAIN)
    out["status"] = np.where(out.change >= EXPECTED_NOW, "On track",
                             np.where(out.change > 0, "Behind", "Falling back"))
    return out.reset_index().sort_values("change")


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
    for crop in MAJOR:
        parts = [_season_gains(crop, f"{year}{s}", catch_share, gap_share) for s in "AB"]
        prod = sum(p["production"] for p in parts)
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
APP_TO_OFFICIAL = {"Beans": "Beans", "Cassava": "Cassava", "Irish potatoes": "Irish potato", "Maize": "Maize"}


def latest_official_season(app_season: str) -> str | None:
    """Most recent published season of the same letter: 'SeasonA' -> '2026A'; Season C is not published."""
    letter = app_season[-1]
    have = sorted(s for s in load_district_crops().season.unique() if s.endswith(letter))
    return have[-1] if have else None


def attach_official(t: pd.DataFrame, app_season: str) -> pd.DataFrame:
    """Add the latest official yield, the median district yield, harvested area, and the tonnes a district-crop
    would fall short of a typical district's yield at its expected RYI (harvested area x median x shortfall)."""
    cols = ["off_season", "off_yield_kgha", "off_median_kgha", "off_harvested_ha", "tonnes_below"]
    season = latest_official_season(app_season)
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
