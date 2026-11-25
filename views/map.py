from datetime import date

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core.data import CROPS, DISTRICT_PROVINCE, DISTRICTS, SEASONS, current_season, fmt_pct, load_geojson, pct_vs_typical
from core.db import get_reports
from core.official import APP_TO_OFFICIAL, attach_official, load_district_crops
from core.risk import adjusted_table
from core.ui import filter_head, hero, nz, rank_list, section

# Diverging: red (below typical) <-> neutral gray <-> blue (above typical)
DIVERGING = [[0.0, "#a32626"], [0.25, "#e34948"], [0.5, "#f0efec"], [0.75, "#5598e7"], [1.0, "#1c5cab"]]
SEQUENTIAL = [[0.0, "#f2f7ef"], [0.5, "#7cc47f"], [1.0, "#1f6b35"]]  # yield: light = low, dark green = high
NO_DATA = "#d9d8d4"
CLIP = 50  # colour saturates at ±50%
SHOW = ["% vs typical district", "Yield (kg/ha)"]


def season_year(today: date | None = None) -> int:
    """Harvest year of the current season: Season A runs Sep-Feb, so Sep-Dec belong to next year's Season A."""
    today = today or date.today()
    return today.year + 1 if today.month >= 7 else today.year


NOW_SEASON, NOW_YEAR = current_season(), season_year()
official = load_district_crops()
official_years = sorted({int(s[:4]) for s in official.season}, reverse=True)
YEARS = [NOW_YEAR] + [y for y in official_years if y != NOW_YEAR]


def year_label(y: int) -> str:
    return f"{y} · this season (expected)" if y == NOW_YEAR else f"{y} · official NISR results"


hero("District Risk Map", "Yield vs the typical district. **Red** = below, **blue** = above.",
     eyebrow="Monitor · Map", ic="map", meta=[("location_on", "30 districts")])

with st.container(key="toolbar"):
    st.markdown(filter_head(hint="Pick a crop, then a year and season, then what to show"), unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns([1, 1.3, 0.9, 1.1])
    crop = c1.selectbox("Crop", CROPS, key="m_crop")
    year = c2.selectbox("Year", YEARS, format_func=year_label, key="m_year")
    if year == NOW_YEAR:
        seasons = [NOW_SEASON]
    else:
        seasons = [s for s in SEASONS if f"{year}{s[-1]}" in set(official.season)]
    season = c3.selectbox("Season", seasons, format_func=lambda s: SEASONS[s].split(" (")[0], key=f"m_season_{year}")
    show = c4.selectbox("Show", SHOW, key="m_show")
current = year == NOW_YEAR
season_name = f"{SEASONS[season].split(' (')[0]} {year}"

# ---------- one row per district: ryi (vs typical) and yield (kg/ha), plus what the hover needs ----------
if current:
    t = attach_official(adjusted_table(season, get_reports(season)), season)
    t = t[t.CropName == crop].copy()
    t["ryi"] = t.adjusted_RYI
    # expected kg/ha = last official yield, moved by the same % as the field reports moved the baseline
    t["yield_kgha"] = t.off_yield_kgha * t.adjusted_RYI / t.baseline_RYI
    source = t.baseline_source.iloc[0] if len(t) else ""
    subtitle = f"Expected this season: last official result ({source}) adjusted by field reports"
else:
    off_crop = APP_TO_OFFICIAL.get(crop)
    d = official[(official.season == f"{year}{season[-1]}") & (official.crop == off_crop)].dropna(subset=["yield_kgha"])
    t = d.assign(CropName=crop, Province=d.DistrictName.map(DISTRICT_PROVINCE),
                 ryi=d.yield_kgha / d.yield_kgha.median())
    subtitle = f"Official NISR results, {season_name} (Seasonal Agricultural Survey)"

if t.empty:
    why = (" NISR publishes tomatoes only inside 'vegetables', so there are no official tomato yields by district."
           if crop == "Tomatoes" and not current else "")
    st.warning(f"No data for {crop} in {season_name}.{why}", icon=":material/warning:")
    st.stop()

by_yield = show == "Yield (kg/ha)"
if by_yield and t.yield_kgha.isna().all():
    st.info(f"No kg/ha figures for {crop}: NISR doesn't publish them. Showing % vs typical district instead.",
            icon=":material/info:")
    by_yield = False

t = t.assign(pct=pct_vs_typical(t.ryi).clip(-CLIP, CLIP))
median_kgha = t.yield_kgha.median() if t.yield_kgha.notna().any() else np.nan


def hover(r) -> str:
    kg = f"<br>{r.yield_kgha:,.0f} kg/ha" if pd.notna(r.yield_kgha) else ""
    if not current:
        return (f"<b>{r.DistrictName}</b><br>{fmt_pct(r.ryi)} vs typical district{kg}"
                f"<br>{r.harvested_ha:,.0f} ha harvested · {r.production_mt:,.0f} t")
    return (f"<b>{r.DistrictName}</b><br>{fmt_pct(r.ryi)} vs typical district (expected){kg}"
            f"<br>Last official: {fmt_pct(r.baseline_RYI)} ({r.baseline_source})"
            f"{' · persistently low' if r.persistently_low else ''}"
            f"<br>{int(r.n_reports)} field report(s) this season"
            + (f"<br>Rain {r.rain_anom_pct:+.0f}% vs district avg ({r.rain_period})" if pd.notna(r.rain_anom_pct)
               else ""))


missing = [d for d in DISTRICTS if d not in set(t.DistrictName)]
gj = load_geojson()
fig = go.Figure()
if missing:
    fig.add_trace(go.Choropleth(
        geojson=gj, featureidkey="properties.shapeName", locations=missing, z=[0] * len(missing),
        colorscale=[[0, NO_DATA], [1, NO_DATA]], showscale=False, marker_line_color="white", marker_line_width=1,
        hovertext=[f"<b>{d}</b><br>no data" for d in missing], hoverinfo="text"))
bar = dict(orientation="h", x=0.5, xanchor="center", y=-0.02, yanchor="top", len=0.75, thickness=10, outlinewidth=0)
if by_yield:
    plotted = t.dropna(subset=["yield_kgha"])
    fig.add_trace(go.Choropleth(
        geojson=gj, featureidkey="properties.shapeName", locations=plotted.DistrictName, z=plotted.yield_kgha,
        colorscale=SEQUENTIAL, marker_line_color="white", marker_line_width=1,
        hovertext=[hover(r) for _, r in plotted.iterrows()], hoverinfo="text",
        colorbar=dict(title=dict(text="kg per hectare", side="top"), **bar)))
else:
    fig.add_trace(go.Choropleth(
        geojson=gj, featureidkey="properties.shapeName", locations=t.DistrictName, z=t.pct,
        zmin=-CLIP, zmax=CLIP, colorscale=DIVERGING, marker_line_color="white", marker_line_width=1,
        hovertext=[hover(r) for _, r in t.iterrows()], hoverinfo="text",
        colorbar=dict(title=dict(text="% vs typical district", side="top"), ticksuffix="%",
                      tickvals=[-50, -25, 0, 25, 50], **bar)))
fig.update_geos(fitbounds="locations", visible=False)
fig.update_layout(height=520, margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor="rgba(0,0,0,0)",
                  geo_bgcolor="rgba(0,0,0,0)", dragmode=False, font_family="Inter, sans-serif",
                  hoverlabel=dict(font_family="Inter, sans-serif", font_size=13))

m1, m2, m3, m4 = st.columns(4)
m1.metric("Districts with data", f"{len(t)} / 30")
m2.metric("≥25% below typical", nz(int((t.ryi <= 0.75).sum())))
m3.metric("Typical district", f"{median_kgha:,.0f} kg/ha" if pd.notna(median_kgha) else "–",
          help="The median district: half the districts are above it, half below")
if current:
    m4.metric("Field reports", nz(int(t.n_reports.sum()), "None yet"), help="Reports for this crop and season")
else:
    m4.metric("Production", f"{t.production_mt.sum():,.0f} t", help="All districts with data, this season")

left, right = st.columns([2.3, 1])
with left.container(border=True, key="card_map_1"):
    section(f"{crop} · {season_name}", subtitle)
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
with right.container(border=True, key="card_map_2"):
    ranked = t.sort_values("ryi")
    rows = lambda d: [(r.DistrictName, r.Province, pct_vs_typical(r.ryi)) for _, r in d.iterrows()]
    rank_list(rows(ranked.head(6)), "Most at risk" if current else "Lowest yields")
    st.markdown("")
    rank_list(rows(ranked.tail(4).iloc[::-1]), "Strongest districts")

with st.expander("Table view"):
    cols = {"DistrictName": "District", "Province": "Province", "pct_txt": "% vs typical", "yield_kgha": "kg/ha"}
    if current:
        cols |= {"baseline_source": "Baseline", "persistently_low": "Persistently low", "n_reports": "Field reports"}
    else:
        cols |= {"harvested_ha": "Harvested (ha)", "production_mt": "Production (t)"}
    table = (t.sort_values("ryi").assign(pct_txt=t.ryi.map(fmt_pct), yield_kgha=t.yield_kgha.round(0))
             [list(cols)].rename(columns=cols))
    st.dataframe(table, hide_index=True, width="stretch")
    st.download_button("Download table (CSV)", table.to_csv(index=False), icon=":material/download:",
                       file_name=f"imboni_map_{crop.replace(' ', '_')}_{year}{season[-1]}.csv", mime="text/csv")
