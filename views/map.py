import plotly.graph_objects as go
import streamlit as st

from core.data import CROPS, DISTRICTS, SEASONS, current_season, fmt_pct, load_geojson, pct_vs_typical
from core.db import get_reports
from core.risk import adjusted_table

# Diverging: red (below typical) <-> neutral gray <-> blue (above typical)
DIVERGING = [[0.0, "#a32626"], [0.25, "#e34948"], [0.5, "#f0efec"], [0.75, "#5598e7"], [1.0, "#1c5cab"]]
NO_DATA = "#d9d8d4"
CLIP = 50  # colour saturates at ±50%

st.title("🗺️ District yield map")
st.caption("Colour = how a district's yield compares with the **typical district** for the same crop and season "
           "(Relative Yield Index, averaged over 2020–2024). Red = below typical, blue = above.")

seasons = list(SEASONS)
c1, c2, c3 = st.columns([1, 1, 1.4])
crop = c1.selectbox("Crop", CROPS)
season = c2.selectbox("Season", seasons, index=seasons.index(current_season()), format_func=SEASONS.get)
view = c3.radio("Show", ["Historical baseline", "Adjusted by field reports"], horizontal=True)

t = adjusted_table(season, get_reports(season))
t = t[t.CropName == crop]
col = "baseline_RYI" if view == "Historical baseline" else "adjusted_RYI"

if t.empty:
    st.warning(f"No SAS data for {crop} in {SEASONS[season]}. Try another season.")
    st.stop()

t = t.assign(pct=pct_vs_typical(t[col]).clip(-CLIP, CLIP))
hover = [
    f"<b>{r.DistrictName}</b><br>{fmt_pct(r[col])} vs typical district<br>"
    f"{int(r.n_years)} year(s) of data{' · persistently low' if r.persistently_low else ''}"
    f"<br>{int(r.n_reports)} field report(s) this season"
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
                  geo_bgcolor="rgba(0,0,0,0)", dragmode=False)
st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

m1, m2, m3 = st.columns(3)
m1.metric("Districts with data", f"{len(t)} / 30")
m2.metric("≥25% below typical", int((t[col] <= 0.75).sum()))
m3.metric("Persistently low (≥3 yrs)", int(t.persistently_low.sum()))

with st.expander("Table view"):
    st.dataframe(
        t.sort_values(col).assign(**{"% vs typical": t[col].map(fmt_pct)})
         [["DistrictName", "Province", "% vs typical", "n_years", "persistently_low", "n_reports"]]
         .rename(columns={"DistrictName": "District", "n_years": "Years of data",
                          "persistently_low": "Persistently low", "n_reports": "Field reports"}),
        hide_index=True, width="stretch")
