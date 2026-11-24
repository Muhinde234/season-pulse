import html

import numpy as np
import plotly.graph_objects as go
import streamlit as st

from core.data import load_geojson
from core.official import (INPUT_LABELS, LATEST_SEASONS, MAJOR, SOURCE_URL, district_practice,
                           input_gap_by_farmer_type, practice_signals, yield_gap_by_farmer_type)
from core.ui import hero, icon, section

LEAF, GOLD, FOREST, MUTED, GRID = "#1F8A43", "#E0A100", "#0E3B22", "#5E6E65", "rgba(14,59,34,.10)"
LAYOUT = dict(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#13261C"),
              hoverlabel=dict(bgcolor="white", font_size=13))
SEASON_NAME = {s: f"Season {s[-1]} {s[:4]}" for s in LATEST_SEASONS}

hero("Farming Practices", "What large-scale farmers do differently, and where small-scale farmers need support.",
     eyebrow="Plan · Farming practices", ic="eco",
     meta=[("groups", "Small- vs large-scale"), ("database", "NISR SAS 2026 A + B")])

yg = yield_gap_by_farmer_type()
ig = input_gap_by_farmer_type().set_index("metric")
maize = yg.set_index("crop").loc["Maize"]
kpis = [
    ("scale", FOREST, f"{maize.ratio:.1f}×", "Maize yield, large vs small",
     f"{maize.lsf_kgha:,.0f} vs {maize.ssf_kgha:,.0f} kg/ha"),
    ("grain", GOLD, f"{ig.loc['improved_seed', 'ssf']:.0f}% vs {ig.loc['improved_seed', 'lsf']:.0f}%",
     "Use improved seeds", "small- vs large-scale farmers"),
    ("water_drop", "#0284c7", f"{ig.loc['irrigation', 'ssf']:.0f}% vs {ig.loc['irrigation', 'lsf']:.0f}%",
     "Practise irrigation", "small- vs large-scale farmers"),
    ("bug_report", LEAF, f"{ig.loc['pesticide', 'ssf']:.0f}% vs {ig.loc['pesticide', 'lsf']:.0f}%",
     "Use pesticides", "small- vs large-scale farmers"),
]
st.markdown('<div class="sp-kpis">' + "".join(
    f'<div class="sp-kpi" style="--c:{c}"><div class="sp-kpi-ic">{icon(ic)}</div><div><b>{html.escape(n)}</b>'
    f'<span>{html.escape(label)}</span><small>{html.escape(sub)}</small></div></div>'
    for ic, c, n, label, sub in kpis) + "</div>", unsafe_allow_html=True)

# ---------- 1 + 2: yield gap and practice gap ----------
left, right = st.columns(2, gap="medium")
with left.container(border=True, key="card_practices_1"):
    section("Same crop, different results", "large-scale yield ÷ small-scale yield")
    up = yg[yg.ratio > 1]
    fig = go.Figure(go.Bar(
        y=up.crop, x=up.ratio, orientation="h", marker=dict(color=FOREST, cornerradius=4),
        text=[f"{v:.1f}×" for v in up.ratio], textposition="outside", cliponaxis=False,
        customdata=up[["ssf_kgha", "lsf_kgha"]],
        hovertemplate="<b>%{y}</b><br>Small-scale %{customdata[0]:,.0f} kg/ha<br>"
                      "Large-scale %{customdata[1]:,.0f} kg/ha<extra></extra>"))
    fig.add_vline(x=1, line=dict(color=MUTED, width=1, dash="dot"))
    fig.update_layout(**LAYOUT, height=300, margin=dict(l=90, r=40, t=10, b=0), showlegend=False, bargap=.35,
                      xaxis=dict(range=[0, up.ratio.max() * 1.2], ticksuffix="×", gridcolor=GRID),
                      yaxis=dict(showgrid=False))
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    down = yg[yg.ratio <= 1].crop.tolist()
    if down:
        st.caption(f"Not shown: {', '.join(down).lower()}, where large-scale farmers do not out-yield "
                   "small-scale ones in NISR's tables.")
with right.container(border=True, key="card_practices_2"):
    section("What they do differently", "% of farmers using each practice")
    g = input_gap_by_farmer_type()
    figd = go.Figure()
    for _, r in g.iterrows():
        figd.add_shape(type="line", x0=r.ssf, x1=r.lsf, y0=r.label, y1=r.label, line=dict(color=MUTED, width=2))
    figd.add_scatter(x=g.ssf, y=g.label, mode="markers+text", name="Small-scale farmers",
                     marker=dict(color=GOLD, size=12, line=dict(color="white", width=2)),
                     text=[f"{v:.0f}%" for v in g.ssf], textfont=dict(color=MUTED),
                     textposition=["middle left" if a <= b else "middle right" for a, b in zip(g.ssf, g.lsf)],
                     hovertemplate="<b>%{y}</b><br>Small-scale: %{x:.0f}%<extra></extra>")
    figd.add_scatter(x=g.lsf, y=g.label, mode="markers+text", name="Large-scale farmers",
                     marker=dict(color=FOREST, size=12, line=dict(color="white", width=2)),
                     text=[f"{v:.0f}%" for v in g.lsf], textfont=dict(color=MUTED),
                     textposition=["middle right" if b >= a else "middle left" for a, b in zip(g.ssf, g.lsf)],
                     hovertemplate="<b>%{y}</b><br>Large-scale: %{x:.0f}%<extra></extra>")
    figd.update_layout(**LAYOUT, height=310, margin=dict(l=125, r=10, t=10, b=0),
                       legend=dict(orientation="h", y=-0.14, x=-0.3, entrywidth=170),
                       xaxis=dict(range=[-12, 112], ticksuffix="%", gridcolor=GRID, zeroline=False),
                       yaxis=dict(showgrid=False))
    st.plotly_chart(figd, width="stretch", config={"displayModeBar": False})
st.markdown(f'<div class="sp-note sp-note-info">{icon("insights")}<span>Large-scale farmers use improved seeds, '
            'pesticides and irrigation about <b>2–4 times as often</b> as small-scale farmers, and harvest up to '
            f'<b>{yg.ratio.max():.1f}×</b> more {yg.sort_values("ratio").crop.iloc[-1].lower()} per hectare. '
            'Small-scale farmers grow most of Rwanda\'s food, so closing this gap is the biggest lever for the '
            '+50% target.</span></div>', unsafe_allow_html=True)

# ---------- 3 + 4: districts ----------
section("Where support is needed", "district use of a practice, and how it lines up with yield")
with st.container(key="toolbar"):
    c1, c2, c3 = st.columns(3)
    metric = c1.selectbox("Practice", list(INPUT_LABELS), format_func=INPUT_LABELS.get, key="pr_metric",
                          index=list(INPUT_LABELS).index("inorganic_fert"))
    crop = c2.selectbox("Crop", MAJOR, key="pr_crop")
    season = c3.selectbox("Season", LATEST_SEASONS[::-1], format_func=SEASON_NAME.get, key="pr_season")
dp = district_practice(season, metric, crop)
label = INPUT_LABELS[metric].lower()

left, right = st.columns([1, 1.15], gap="medium")
with left.container(border=True, key="card_practices_3"):
    section(f"Farmers using {label}", SEASON_NAME[season])
    figm = go.Figure(go.Choropleth(
        geojson=load_geojson(), featureidkey="properties.shapeName", locations=dp.DistrictName, z=dp.overall,
        zmin=0, zmax=100, colorscale=[[0, "#EEF6F0"], [.5, "#6DBB86"], [1, FOREST]], marker_line_color="white",
        marker_line_width=1, customdata=dp[["ssf", "lsf"]],
        hovertemplate="<b>%{location}</b><br>All farmers: %{z:.0f}%<br>Small-scale: %{customdata[0]:.0f}%"
                      "<extra></extra>",
        colorbar=dict(title=dict(text="% of farmers", side="top"), orientation="h", x=.5, xanchor="center",
                      y=-0.02, yanchor="top", len=.7, thickness=10, outlinewidth=0, ticksuffix="%")))
    figm.update_geos(fitbounds="locations", visible=False)
    figm.update_layout(**LAYOUT, height=420, margin=dict(l=0, r=0, t=0, b=0), geo_bgcolor="rgba(0,0,0,0)",
                       dragmode=False)
    st.plotly_chart(figm, width="stretch", config={"displayModeBar": False})
with right.container(border=True, key="card_practices_4"):
    section(f"{INPUT_LABELS[metric]} and {crop.lower()} yield", "each dot is a district · size = harvested area")
    s = dp.dropna(subset=["yield_kgha", "overall"])
    if s.empty:
        st.info(f"No {crop.lower()} yield data for this season.", icon=":material/info:")
        prio = s
    else:
        mx, my = s.overall.median(), s.yield_kgha.median()
        prio = s[(s.overall < mx) & (s.yield_kgha < my)].sort_values("harvested_ha", ascending=False)
        size = 10 + 30 * np.sqrt(s.harvested_ha / s.harvested_ha.max())
        is_p = s.DistrictName.isin(prio.DistrictName)
        figs = go.Figure(go.Scatter(
            x=s.overall, y=s.yield_kgha, mode="markers+text",
            text=np.where(s.DistrictName.isin(prio.DistrictName.head(5)), s.DistrictName, ""),
            textposition="top center", textfont=dict(size=11, color=MUTED),
            marker=dict(size=size, color=np.where(is_p, GOLD, LEAF), opacity=.85, line=dict(color="white", width=2)),
            customdata=s[["DistrictName", "harvested_ha"]],
            hovertemplate="<b>%{customdata[0]}</b><br>" + INPUT_LABELS[metric] + ": %{x:.0f}% of farmers<br>"
                          "Yield: %{y:,.0f} kg/ha<br>Harvested: %{customdata[1]:,.0f} ha<extra></extra>"))
        figs.add_hline(y=my, line=dict(color=MUTED, width=1, dash="dot"))
        figs.add_vline(x=mx, line=dict(color=MUTED, width=1, dash="dot"))
        figs.add_annotation(x=s.overall.min(), y=s.yield_kgha.min(), text="low use · low yield", showarrow=False,
                            xanchor="left", yanchor="bottom", font=dict(size=11, color="#8A6400"))
        figs.update_layout(**LAYOUT, height=420, margin=dict(l=0, r=10, t=10, b=0), showlegend=False,
                           xaxis=dict(title=f"% of farmers using {label}", ticksuffix="%", gridcolor=GRID),
                           yaxis=dict(title="Yield (kg/ha)", gridcolor=GRID))
        st.plotly_chart(figs, width="stretch", config={"displayModeBar": False})

sig = practice_signals(metric).set_index("crop")
r = float(sig.loc[crop, "r"]) if crop in sig.index else float("nan")
strength = ("no clear link" if abs(r) < .2 else "a weak link" if abs(r) < .4 else
            "a moderate link" if abs(r) < .6 else "a strong link")
direction = "higher" if r > 0 else "lower"
names = ", ".join(prio.DistrictName.head(5)) if len(prio) else ""
st.markdown(
    f'<div class="sp-note sp-note-info">{icon("insights")}<span>Across districts and seasons there is <b>{strength}</b> '
    f'between {label} and {crop.lower()} yield (r = {r:+.2f})'
    + (f": districts where more farmers use it tend to have {direction} yields. " if abs(r) >= .2 else ". ")
    + (f"<b>Priority districts</b> (low use, low yield, ranked by area): {html.escape(names)}." if names else "")
    + "</span></div>", unsafe_allow_html=True)
st.caption("A link across districts is an association, not proof of cause: soils, altitude and rainfall also differ "
           "between districts. NISR publishes practice use for all crops together, not per crop.")

with st.expander("Table view and sources", icon=":material/table_rows:"):
    st.dataframe(dp.rename(columns={"DistrictName": "District", "overall": "% all farmers", "ssf": "% small-scale",
                                    "lsf": "% large-scale", "yield_kgha": f"{crop} yield (kg/ha)",
                                    "harvested_ha": "Harvested (ha)", "production_mt": "Production (t)"}).round(1),
                 hide_index=True, width="stretch")
    st.markdown(f"Source: NISR Seasonal Agricultural Survey, official tables "
                f"([NISR SAS releases]({SOURCE_URL})): yield by district and by farmer type, use of seeds, "
                "fertilizer and pesticides by farmer type, and agricultural practices per district.")
