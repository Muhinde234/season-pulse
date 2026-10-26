"""Cached loaders for the small pre-built files in data/ (never the raw NISR files)."""
import json
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

DATA = Path(__file__).resolve().parent.parent / "data"

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
def load_geojson() -> dict:
    return json.loads((DATA / "rwa_adm2.geojson").read_text())
