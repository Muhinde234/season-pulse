"""Cached loaders for the small pre-built files in data/ (never the raw NISR files)."""
import json
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

DATA = Path(__file__).resolve().parent.parent / "app_data"  # small processed files only; raw sources live in data/

CROPS = ["Beans", "Cassava", "Irish potatoes", "Maize", "Tomatoes"]
SEASONS = {"SeasonA": "Season A (Sep–Feb)", "SeasonB": "Season B (Mar–Jun)", "SeasonC": "Season C (Jul–Aug)"}

PROVINCES = {
    "Kigali City": ["Gasabo", "Kicukiro", "Nyarugenge"],
    "Southern Province": ["Gisagara", "Huye", "Kamonyi", "Muhanga", "Nyamagabe", "Nyanza", "Nyaruguru", "Ruhango"],
    "Western Province": ["Karongi", "Ngororero", "Nyabihu", "Nyamasheke", "Rubavu", "Rusizi", "Rutsiro"],
    "Northern Province": ["Burera", "Gakenke", "Gicumbi", "Musanze", "Rulindo"],
    "Eastern Province": ["Bugesera", "Gatsibo", "Kayonza", "Kirehe", "Ngoma", "Nyagatare", "Rwamagana"],
}
DISTRICT_PROVINCE = {d: p for p, ds in PROVINCES.items() for d in ds}
DISTRICTS = sorted(DISTRICT_PROVINCE)


def current_season(today: date | None = None) -> str:
    """Rwanda's agricultural calendar: A = Sep–Feb, B = Mar–Jun, C = Jul–Aug."""
    m = (today or date.today()).month
    if m >= 9 or m <= 2:
        return "SeasonA"
    return "SeasonB" if m <= 6 else "SeasonC"


def pct_vs_typical(ryi):
    """RYI 0.73 -> -27 (percent vs the typical district). Works on scalars and Series."""
    return np.round((ryi - 1) * 100)


def fmt_pct(ryi) -> str:
    if pd.isna(ryi):
        return "no data"
    p = int(pct_vs_typical(ryi))
    return "typical" if p == 0 else f"{p:+d}%"


@st.cache_data
def load_baseline() -> pd.DataFrame:
    return pd.read_csv(DATA / "out_district_baseline.csv")


@st.cache_data
def load_backtest() -> dict:
    return json.loads((DATA / "out_backtest.json").read_text())


@st.cache_data
def load_cooperatives() -> pd.DataFrame:
    return pd.read_csv(DATA / "district_cooperatives.csv")


@st.cache_data
def load_consumption() -> pd.DataFrame:
    return pd.read_csv(DATA / "district_consumption_2020.csv")


@st.cache_data
def load_official_2026() -> pd.DataFrame:
    """NISR SAS 2026 Season A Table 13: official yield (kg/ha) and RYI per district & crop (prep_data.py)."""
    return pd.read_csv(DATA / "official_yield_2026A.csv")


@st.cache_data
def load_irrigation() -> pd.DataFrame:
    """NISR SAS 2026 Season A Table 32: % of irrigated plots using modern vs traditional methods."""
    return pd.read_csv(DATA / "irrigation_2026A.csv")


@st.cache_data
def load_validation() -> pd.DataFrame:
    """Historical Season A baseline vs official 2026 Season A RYI (prep_data.py)."""
    return pd.read_csv(DATA / "out_validation_2026A.csv")


@st.cache_data
def load_rainfall() -> pd.DataFrame:
    """CHIRPS seasonal rainfall per district (fetch_rainfall.py); empty if the file hasn't been built."""
    path = DATA / "district_rainfall.csv"
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


@st.cache_data
def load_rain_vs_ryi() -> pd.DataFrame:
    path = DATA / "out_rain_vs_ryi.csv"
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def rain_period(r) -> str:
    """'Sep–Dec 2025' style label for a district_rainfall row (Season A falls in the previous calendar year)."""
    m = r.months.split("-")
    span = m[0] if len(m) == 1 else f"{m[0]}–{m[-1]}"
    return f"{span} {r.Year - 1 if r.Season == 'SeasonA' else r.Year}"


@st.cache_data
def load_geojson() -> dict:
    """District polygons with rings rewound clockwise. The file follows RFC 7946 (counter-clockwise outer rings),
    but Plotly's geo projection (d3-geo) reads those as "everything except the district" and floods the map."""
    gj = json.loads((DATA / "rwa_adm2.geojson").read_text())
    for f in gj["features"]:
        g = f["geometry"]
        polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        for poly in polys:
            for i, ring in enumerate(poly):
                ccw = sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(ring, ring[1:])) > 0
                if ccw == (i == 0):  # outer ring must be clockwise, holes counter-clockwise
                    ring.reverse()
    return gj
