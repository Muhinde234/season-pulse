import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core.data import (CROPS, DISTRICTS, SEASONS, current_season, fmt_pct, load_geojson, load_official_2026,
                       pct_vs_typical)
from core.db import get_reports
from core.risk import adjusted_table
from core.ui import hero, section

# Diverging: red (below typical) <-> neutral gray <-> blue (above typical)
DIVERGING = [[0.0, "#a32626"], [0.25, "#e34948"], [0.5, "#f0efec"], [0.75, "#5598e7"], [1.0, "#1c5cab"]]
NO_DATA = "#d9d8d4"
CLIP = 50  # colour saturates at ±50%
OFFICIAL = "Official 2026 Season A"
VIEWS = {"Historical baseline": "baseline_RYI", "Adjusted by field reports": "adjusted_RYI", OFFICIAL: "official_RYI"}

hero("District Risk Map",
     "How each district's yield compares with the **typical district** for the same crop and season "
     "(Relative Yield Index): the 2020–2024 baseline, the baseline adjusted by field reports, or the official "
     "NISR 2026 Season A results. Red = below typical, blue = above.", eyebrow="Monitor · Map")

seasons = list(SEASONS)
c1, c2, c3 = st.columns([1, 1, 1.4])
crop = c1.selectbox("Crop", CROPS)
season = c2.selectbox("Season", seasons, index=seasons.index(current_season()), format_func=SEASONS.get)
view = c3.radio("Show", list(VIEWS), horizontal=True)

t = adjusted_table(season, get_reports(season))
t = t[t.CropName == crop]
col = VIEWS[view]
if view == OFFICIAL:
    official = load_official_2026()
    if season != "SeasonA" or crop not in set(official.CropName):
        st.info(f"Official 2026 yields are published for **Season A** only, for "
                f"{', '.join(sorted(official.CropName.unique()))} (NISR SAS 2026 Season A, Table 13). Tomatoes are "
                "only published inside \"vegetables\". Pick Season A and one of those crops.")
        st.stop()
    t = t.merge(official[["DistrictName", "CropName", "yield_kg_ha", "official_RYI"]], on=["DistrictName", "CropName"])

if t.empty:
    st.warning(f"No SAS data for {crop} in {SEASONS[season]}. Try another season.")
    st.stop()

t = t.assign(pct=pct_vs_typical(t[col]).clip(-CLIP, CLIP))
hover = [
    f"<b>{r.DistrictName}</b><br>{fmt_pct(r[col])} vs typical district<br>"
    f"{int(r.n_years)} year(s) of data{' · persistently low' if r.persistently_low else ''}"
    f"<br>{int(r.n_reports)} field report(s) this season"
    + (f"<br>Official 2026 A: {r.yield_kg_ha:,.0f} kg/ha · baseline {fmt_pct(r.baseline_RYI)}" if view == OFFICIAL
       else "")
    + (f"<br>Rain {r.rain_anom_pct:+.0f}% vs district avg ({r.rain_period})" if pd.notna(r.rain_anom_pct) else "")
    for _, r in t.iterrows()
]
missing = [d for d in DISTRICTS if d not in set(t.DistrictName)]
gj = load_geojson()

fig = go.Figure()
if missing:
    fig.add_trace(go.Choropleth(
        geojson=gj, featureidkey="properties.shapeName", locations=missing, z=[0] * len(missing),
        colorscale=[[0, NO_DATA], [1, NO_DATA]], showscale=False, marker_line_color="white", marker_line_width=1,
        hovertext=[f"<b>{d}</b><br>no reliable data" for d in missing], hoverinfo="text"))
fig.add_trace(go.Choropleth(
    geojson=gj, featureidkey="properties.shapeName", locations=t.DistrictName, z=t.pct,
    zmin=-CLIP, zmax=CLIP, colorscale=DIVERGING, marker_line_color="white", marker_line_width=1,
    hovertext=hover, hoverinfo="text",
    colorbar=dict(title="% vs typical", ticksuffix="%", tickvals=[-50, -25, 0, 25, 50], len=0.8, thickness=12)))
fig.update_geos(fitbounds="locations", visible=False)
fig.update_layout(height=560, margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor="rgba(0,0,0,0)",
                  geo_bgcolor="rgba(0,0,0,0)", dragmode=False, font_family="Inter, sans-serif",
                  hoverlabel=dict(font_family="Inter, sans-serif", font_size=13))

m1, m2, m3, m4 = st.columns(4)
m1.metric("Districts with data", f"{len(t)} / 30")
m2.metric("≥25% below typical", int((t[col] <= 0.75).sum()))
m3.metric("Persistently low", int(t.persistently_low.sum()), help="Below typical in 3+ years of data")
m4.metric("Field reports", int(t.n_reports.sum()), help="Reports for this crop and season")

with st.container(border=True):
    section(f"{crop} · {SEASONS[season]}", view)
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

with st.expander("Table view"):
    st.dataframe(
        t.sort_values(col).assign(**{"% vs typical": t[col].map(fmt_pct)})
         [["DistrictName", "Province", "% vs typical", "n_years", "persistently_low", "n_reports"]]
         .rename(columns={"DistrictName": "District", "n_years": "Years of data",
                          "persistently_low": "Persistently low", "n_reports": "Field reports"}),
        hide_index=True, width="stretch")
