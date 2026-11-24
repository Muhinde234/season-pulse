import html

import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from core.official import (BASE_YEAR, EXPECTED_NOW, LATEST_YEAR, MAJOR, PSTA5_URL, SOURCE_URL, TARGET_GAIN,
                           TARGET_YEAR, district_priorities, scenario, target_progress, yearly_yield)
from core.ui import hero, icon, section

LEAF, GOLD, FOREST, MUTED, GRID = "#1F8A43", "#E0A100", "#0E3B22", "#5E6E65", "rgba(14,59,34,.10)"
LAYOUT = dict(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#13261C"),
              hoverlabel=dict(bgcolor="white", font_size=13))

hero("Road to +50%", "Priority crop yields against Rwanda's PSTA 5 target, from NISR's official survey tables.",
     eyebrow="Plan · Productivity target", ic="target",
     meta=[("calendar", f"{BASE_YEAR} → {TARGET_YEAR}"), ("database", "NISR SAS 2023–2026")])

prog = target_progress()
on_track = int((prog.status == "On track").sum())
best = prog.sort_values("change").iloc[-1]
sc_default = scenario(1.0, 0.5)
reach = sc_default[sc_default.total_pct >= 100 * TARGET_GAIN].crop.tolist()
kpis = [
    ("target", "#dc2626" if not on_track else LEAF, f"{on_track} of {len(prog)}" if on_track else "None",
     "Crops on track", f"a straight path needs +{EXPECTED_NOW:.0%} by {LATEST_YEAR}"),
    ("trending_down", LEAF, f"{best.change:+.1%}", "Best progress", f"{best.crop}, {BASE_YEAR} → {LATEST_YEAR}"),
    ("scale", GOLD, f"{sc_default.set_index('crop').total_pct.max():.0f}%", "Largest possible gain",
     f"{sc_default.set_index('crop').total_pct.idxmax()}: both levers below"),
    ("verified", FOREST, ", ".join(reach) if reach else "None", "Can pass +50%",
     "with both levers set as below"),
]
st.markdown('<div class="sp-kpis">' + "".join(
    f'<div class="sp-kpi" style="--c:{c}"><div class="sp-kpi-ic">{icon(ic)}</div><div><b>{html.escape(str(n))}</b>'
    f'<span>{html.escape(label)}</span><small>{html.escape(sub)}</small></div></div>'
    for ic, c, n, label, sub in kpis) + "</div>", unsafe_allow_html=True)

# ---------- 1. where each crop stands ----------
section("Where each crop stands", f"yield change since {BASE_YEAR}, Seasons A + B")
p = prog.sort_values("change")
fig = go.Figure()
fig.add_bar(y=p.crop, x=100 * p.change, orientation="h",
            marker=dict(color=[LEAF if v >= 0 else "#dc2626" for v in p.change], cornerradius=4),
            text=[f"{v:+.1%}" for v in p.change], textposition="outside", cliponaxis=False,
            customdata=p[["base_t_ha", "latest_t_ha", "target_t_ha", "status"]],
            hovertemplate="<b>%{y}</b><br>%{customdata[0]:.2f} → %{customdata[1]:.2f} t/ha (%{x:+.1f}%)"
                          f"<br>{TARGET_YEAR} target: %{{customdata[2]:.2f}} t/ha<br>%{{customdata[3]}}<extra></extra>",
            name="Change so far")
fig.add_vline(x=100 * EXPECTED_NOW, line=dict(color=FOREST, width=2, dash="dot"))
fig.add_vline(x=100 * TARGET_GAIN, line=dict(color=FOREST, width=2))
fig.add_vline(x=0, line=dict(color=MUTED, width=1))
fig.add_annotation(x=100 * EXPECTED_NOW, y=1.02, yref="paper", text=f"expected by {LATEST_YEAR}: +{EXPECTED_NOW:.0%}",
                   showarrow=False, font=dict(size=12, color=FOREST), xanchor="center", yanchor="bottom")
fig.add_annotation(x=100 * TARGET_GAIN, y=1.02, yref="paper", text=f"{TARGET_YEAR} target: +{TARGET_GAIN:.0%}",
                   showarrow=False, font=dict(size=12, color=FOREST), xanchor="center", yanchor="bottom")
fig.update_layout(**LAYOUT, height=330, margin=dict(l=0, r=30, t=36, b=10), showlegend=False, bargap=.35,
                  xaxis=dict(range=[-8, 56], ticksuffix="%", gridcolor=GRID, zeroline=False),
                  yaxis=dict(showgrid=False))
st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
st.caption(f"No priority crop is on the straight path to +50%. A straight path from {BASE_YEAR} to {TARGET_YEAR} "
           f"means +{EXPECTED_NOW:.0%} by {LATEST_YEAR}.")

# ---------- 2. trend per crop ----------
with st.expander("Yield trend per crop, 2023–2026, with the target path", icon=":material/show_chart:"):
    y = yearly_yield()
    figt = make_subplots(rows=2, cols=4, subplot_titles=MAJOR, horizontal_spacing=.06, vertical_spacing=.18)
    for i, crop in enumerate(MAJOR):
        r, c = divmod(i, 4)
        d = y[y.crop == crop]
        base = float(d[d.year == BASE_YEAR].yield_t_ha.iloc[0])
        figt.add_scatter(x=[BASE_YEAR, TARGET_YEAR], y=[base, base * (1 + TARGET_GAIN)], mode="lines",
                         line=dict(color=MUTED, width=2, dash="dash"), row=r + 1, col=c + 1, showlegend=i == 0,
                         name="Path to +50%", hovertemplate="%{x}: %{y:.2f} t/ha<extra>target path</extra>")
        figt.add_scatter(x=d.year, y=d.yield_t_ha, mode="lines+markers", line=dict(color=LEAF, width=2),
                         marker=dict(size=8, line=dict(color="white", width=2)), row=r + 1, col=c + 1,
                         showlegend=i == 0, name="Official yield",
                         hovertemplate="%{x}: %{y:.2f} t/ha<extra>" + crop + "</extra>")
    figt.update_xaxes(tickvals=[2023, 2026, 2029], gridcolor=GRID)
    figt.update_yaxes(gridcolor=GRID, rangemode="tozero")
    figt.update_layout(**LAYOUT, height=470, margin=dict(l=0, r=0, t=40, b=0),
                       legend=dict(orientation="h", y=-0.08, x=0))
    st.plotly_chart(figt, width="stretch", config={"displayModeBar": False})
    st.caption("Yield in tonnes per hectare: Season A + Season B production ÷ harvested area (NISR SAS, Table 6).")

# ---------- 3. scenario ----------
section("Where can +50% come from?", f"extra production on the same land, {LATEST_YEAR} Seasons A + B")
c1, c2 = st.columns(2)
catch = c1.slider("Districts below the top quarter catch up by", 0, 100, 100, 10, format="%d%%",
                  help="Every district whose yield is below the top-quarter (75th percentile) district yield of "
                       "that season closes this share of the gap. The top quarter is already reached in Rwanda.")
gap = c2.slider("Small-scale farmers close their gap to large-scale yields by", 0, 100, 50, 10, format="%d%%",
                help="NISR publishes yields for small-scale (SSF) and large-scale farmers (LSF). Large-scale farmers "
                     "use far more improved seed, fertilizer and irrigation.")
sc = scenario(catch / 100, gap / 100).sort_values("total_pct")
figs = go.Figure()
figs.add_bar(y=sc.crop, x=sc.catch_pct, orientation="h", name="Districts catch up", marker=dict(color=LEAF),
             customdata=sc.catch_t, hovertemplate="<b>%{y}</b><br>Districts catch up: +%{x:.1f}% "
                                                  "(%{customdata:,.0f} t)<extra></extra>")
figs.add_bar(y=sc.crop, x=sc.gap_pct, orientation="h", name="Small-scale farmers catch up",
             marker=dict(color=GOLD, cornerradius=4), customdata=sc.gap_t,
             text=[f"+{v:.0f}%" for v in sc.total_pct], textposition="outside", cliponaxis=False,
             hovertemplate="<b>%{y}</b><br>Small-scale catch up: +%{x:.1f}% (%{customdata:,.0f} t)<extra></extra>")
figs.add_vline(x=100 * TARGET_GAIN, line=dict(color=FOREST, width=2))
figs.add_annotation(x=100 * TARGET_GAIN, y=1.02, yref="paper", text="+50% target", showarrow=False,
                    font=dict(size=12, color=FOREST), yanchor="bottom")
figs.update_layout(**LAYOUT, barmode="stack", height=340, margin=dict(l=0, r=40, t=36, b=0), bargap=.35,
                   legend=dict(orientation="h", y=-0.12, x=0, traceorder="normal"),
                   xaxis=dict(ticksuffix="%", gridcolor=GRID, range=[0, max(60, sc.total_pct.max() * 1.15)]),
                   yaxis=dict(showgrid=False))
figs.update_traces(marker_line_color="white", marker_line_width=2)
st.plotly_chart(figs, width="stretch", config={"displayModeBar": False})
passing = sc[sc.total_pct >= 100 * TARGET_GAIN].crop.tolist()
short = sc[sc.total_pct < 100 * TARGET_GAIN].sort_values("total_pct", ascending=False)
st.markdown(
    f'<div class="sp-note sp-note-info">{icon("insights")}<span>'
    + (f"<b>{', '.join(passing)}</b> can pass +50% with these levers. " if passing else
       "No crop passes +50% with these levers alone. ")
    + (f"<b>{short.crop.iloc[0]}</b> gets closest of the rest (+{short.total_pct.iloc[0]:.0f}%); "
       "crops where large-scale farmers do not out-yield small-scale ones (cassava, sweet potato) need other "
       "levers such as irrigation and better varieties." if len(short) else "")
    + "</span></div>", unsafe_allow_html=True)
with st.expander("Table view", icon=":material/table_rows:"):
    st.dataframe(sc.sort_values("total_pct", ascending=False).rename(columns={
        "crop": "Crop", "production_t": f"Production {LATEST_YEAR} (t)", "catch_t": "Districts catch up (t)",
        "gap_t": "Small-scale catch up (t)", "catch_pct": "Districts (%)", "gap_pct": "Small-scale (%)",
        "total_pct": "Total (%)"}).round(1), hide_index=True, width="stretch")

# ---------- 4. where to start ----------
section("Where to start", "districts that would add the most tonnes by reaching the top-quarter yield")
crop = st.selectbox("Crop", MAJOR, key="tg_crop")
pr = district_priorities(crop).head(10).iloc[::-1]
if pr.empty:
    st.info("No district data for this crop.", icon=":material/info:")
else:
    figp = go.Figure(go.Bar(
        y=pr.DistrictName, x=pr.gain_t, orientation="h", marker=dict(color=LEAF, cornerradius=4),
        text=[f"+{v:,.0f} t" for v in pr.gain_t], textposition="outside", cliponaxis=False,
        customdata=pr[["yield_kgha", "p75_kgha", "harvested_ha"]],
        hovertemplate="<b>%{y}</b><br>Yield %{customdata[0]:,.0f} kg/ha vs top quarter %{customdata[1]:,.0f}"
                      "<br>Harvested %{customdata[2]:,.0f} ha<br>Extra: %{x:,.0f} t<extra></extra>"))
    figp.update_layout(**LAYOUT, height=380, margin=dict(l=0, r=60, t=10, b=0), showlegend=False, bargap=.3,
                       xaxis=dict(gridcolor=GRID, title="Extra tonnes per year (Seasons A + B)"),
                       yaxis=dict(showgrid=False))
    st.plotly_chart(figp, width="stretch", config={"displayModeBar": False})
    top = pr.iloc[-1]
    st.caption(f"{top.DistrictName} alone would add about {top.gain_t:,.0f} t of {crop.lower()} a year by moving from "
               f"{top.yield_kgha:,.0f} to {top.p75_kgha:,.0f} kg/ha, a yield other districts already achieve.")

with st.expander("Method and sources", icon=":material/menu_book:"):
    st.markdown(f"""
- **Data:** NISR Seasonal Agricultural Survey, official tables for Seasons A and B, 2023–2026
  ([NISR SAS releases]({SOURCE_URL})). District tables add up exactly to NISR's national totals.
- **Target:** PSTA 5 / NST2 aims to raise the productivity of priority food crops by more than 50% by {TARGET_YEAR}
  ([PSTA 5]({PSTA5_URL})). Baseline = {BASE_YEAR} (Seasons A + B), the agricultural year before PSTA 5 began.
- **Yield** = (Season A + Season B production) ÷ (A + B harvested area). Season C is not published per crop.
- **Districts catch up:** each district below the top-quarter yield of that season and crop closes the chosen share
  of its gap; extra tonnes = gap × harvested area.
- **Small-scale catch up:** small-scale farmers' share of harvested area is solved from NISR's national, small-scale
  and large-scale yields; extra tonnes = that area × (large-scale − small-scale yield) × the chosen share.
- The two levers are added, so the total is approximate. More production on the same land = higher yield.
""")
