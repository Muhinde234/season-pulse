import html

import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from core.official import (LATEST_YEAR, PSTA5_URL, PSTA_CROPS, PSTA_YEARS, SOURCE_URL, TARGET_LABEL,
                           district_priorities, psta_targets, season_a_yield, target_progress)
from core.ui import hero, icon, section

LEAF, GOLD, FOREST, MUTED, GRID = "#1F8A43", "#E0A100", "#0E3B22", "#5E6E65", "rgba(14,59,34,.10)"
RED = "#dc2626"
LAYOUT = dict(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#13261C"),
              hoverlabel=dict(bgcolor="white", font_size=13))

hero("Road to +50%", "Priority crop yields against the PSTA 5 targets, from NISR's official survey tables.",
     eyebrow="Plan · Productivity target", ic="target",
     meta=[("calendar", f"2023 → {TARGET_LABEL}"), ("database", "NISR SAS · PSTA 5")])

prog = target_progress()
now = prog.psta_now.iloc[0]
on_track = prog[prog.status == "On track"]

st.markdown(
    f'<div class="sp-note sp-note-info">{icon("info")}<span>PSTA 5 (MINAGRI) aims for "a 50% increase in '
    f'productivity" (the NST2 goal). In practice it sets a <b>different yield target for each crop and year</b>, from '
    f'a 2023 baseline: from +12% for wheat to +200% for soybean by {TARGET_LABEL}. This page uses those targets.'
    '</span></div>', unsafe_allow_html=True)

kpis = [
    ("target", LEAF if len(on_track) else RED, f"{len(on_track)} of {len(prog)}", "Crops on target",
     f"{now} target met: {', '.join(on_track.crop) or 'none'}"),
    ("trending_down", RED, prog.iloc[0].crop, "Furthest behind",
     f"{prog.iloc[0].vs_target_now:+.0%} vs its {now} target"),
]
st.markdown('<div class="sp-kpis">' + "".join(
    f'<div class="sp-kpi" style="--c:{c}"><div class="sp-kpi-ic">{icon(ic)}</div><div><b>{html.escape(str(n))}</b>'
    f'<span>{html.escape(label)}</span><small>{html.escape(sub)}</small></div></div>'
    for ic, c, n, label, sub in kpis) + "</div>", unsafe_allow_html=True)

# ---------- 1. where each crop stands ----------
section("Where each crop stands", f"Season A {LATEST_YEAR} yield vs the PSTA 5 target for {now}")
p = prog.sort_values("vs_target_now")
fig = go.Figure()
fig.add_bar(y=p.crop, x=100 * p.vs_target_now, orientation="h",
            marker=dict(color=[LEAF if v >= 0 else RED for v in p.vs_target_now], cornerradius=4),
            text=[f"{v:+.0%}" for v in p.vs_target_now], textposition="outside", cliponaxis=False,
            customdata=p[["latest_t_ha", "target_now", "base_t_ha", "target_t_ha"]],
            hovertemplate="<b>%{y}</b><br>Season A " + str(LATEST_YEAR) + ": %{customdata[0]:.2f} t/ha"
                          f"<br>PSTA 5 target {now}: " + "%{customdata[1]:.2f} t/ha (%{x:+.0f}%)"
                          "<br>2023 baseline %{customdata[2]:.2f} · " + TARGET_LABEL +
                          " target %{customdata[3]:.2f}<extra></extra>")
fig.add_vline(x=0, line=dict(color=FOREST, width=2))
fig.add_annotation(x=0, y=1.02, yref="paper", text=f"on target ({now})", showarrow=False,
                   font=dict(size=12, color=FOREST), xanchor="center", yanchor="bottom")
lo = min(-50, 100 * p.vs_target_now.min() * 1.25)
fig.update_layout(**LAYOUT, height=360, margin=dict(l=0, r=40, t=36, b=10), showlegend=False, bargap=.35,
                  xaxis=dict(range=[lo, 25], ticksuffix="%", gridcolor=GRID, zeroline=False),
                  yaxis=dict(showgrid=False))
st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
behind = prog[prog.status != "On track"]
st.caption(f"{len(on_track)} of {len(prog)} PSTA 5 priority crops met their {now} target"
           + (f" ({', '.join(on_track.crop)})" if len(on_track) else "") + ". "
           + f"Furthest behind: {', '.join(behind.head(3).crop.str.lower())}.")
with st.expander("Table view", icon=":material/table_rows:"):
    st.dataframe(prog[["crop", "base_t_ha", "nisr_2023A", "latest_t_ha", "target_now", "vs_target_now",
                       "target_t_ha", "needed", "status"]]
                 .rename(columns={"crop": "Crop", "base_t_ha": "PSTA baseline 2023", "nisr_2023A": "NISR 2023 A",
                                  "latest_t_ha": f"NISR {LATEST_YEAR} A", "target_now": f"Target {now}",
                                  "vs_target_now": "vs target", "target_t_ha": f"Target {TARGET_LABEL}",
                                  "needed": f"Still needed by {TARGET_LABEL}", "status": "Status"})
                 .round(3), hide_index=True, width="stretch")
    st.caption("Yields in tonnes per hectare. 'NISR 2023 A' shows that PSTA 5's baselines are NISR's 2023 Season A "
               "national yields, rounded.")

# ---------- 2. trend per crop ----------
with st.expander("Yield trend per crop, 2022–2026, against the PSTA 5 targets", icon=":material/show_chart:"):
    y, t = season_a_yield(), psta_targets()
    figt = make_subplots(rows=2, cols=4, subplot_titles=PSTA_CROPS, horizontal_spacing=.06, vertical_spacing=.18)
    for i, crop in enumerate(PSTA_CROPS):
        r, c = divmod(i, 4)
        tc, d = t[t.crop == crop], y[y.crop == crop]
        figt.add_scatter(x=tc.year, y=tc.target_t_ha, mode="lines+markers", customdata=tc.psta_year,
                         line=dict(color=MUTED, width=2, dash="dash"), marker=dict(size=5), row=r + 1, col=c + 1,
                         showlegend=i == 0, name="PSTA 5 target",
                         hovertemplate="%{customdata}: %{y:.2f} t/ha<extra>PSTA 5 target</extra>")
        figt.add_scatter(x=d.year, y=d.yield_t_ha, mode="lines+markers", line=dict(color=LEAF, width=2),
                         marker=dict(size=8, line=dict(color="white", width=2)), row=r + 1, col=c + 1,
                         showlegend=i == 0, name="NISR Season A yield",
                         hovertemplate="Season A %{x}: %{y:.2f} t/ha<extra>" + crop + "</extra>")
    figt.update_xaxes(tickvals=[2023, 2026, 2029], gridcolor=GRID)
    figt.update_yaxes(gridcolor=GRID, rangemode="tozero")
    figt.update_layout(**LAYOUT, height=470, margin=dict(l=0, r=0, t=40, b=0),
                       legend=dict(orientation="h", y=-0.08, x=0))
    st.plotly_chart(figt, width="stretch", config={"displayModeBar": False})
    st.caption("Season A national yield, tonnes per hectare (NISR SAS yield table, 'National' row). Target points "
               "are placed on the Season A that falls in each farming year (2025/26 → Season A 2026).")

# ---------- 3. where to start ----------
section("Where to start", "districts that would add the most tonnes by reaching the yield the best quarter of districts already reach")
crop = st.selectbox("Crop", PSTA_CROPS, key="tg_crop")
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
- **Target:** [PSTA 5]({PSTA5_URL}) (MINAGRI, 2024/25–2028/29) states the NST2 goal of "a 50% increase in
  productivity" (p. 14). Its results framework (p. 21, "Productivity for the priority food crops") gives a yield
  target in MT/ha for eight crops and each year ({", ".join(PSTA_YEARS)}), with SAS as the source.
- **Which NISR number to compare with:** PSTA 5's 2023 baselines equal NISR's **2023 Season A** national yields for
  all eight crops, to one decimal (see the table view). So progress is measured on **Season A national yields**
  (NISR SAS yield table, "National" row). PSTA 5 doesn't say which season each farming year means; we compare
  2024/25 with Season A 2025 (Sep 2024–Feb 2025) and 2025/26 with Season A {LATEST_YEAR}.
- **Banana:** PSTA 5 targets *cooking* banana, so this page uses NISR's cooking-banana column, not all bananas.
- **Data:** [NISR SAS releases]({SOURCE_URL}), official tables 2022–2026. District tables add up exactly to NISR's
  national totals.
- **Where to start:** each district below the yield the best quarter of districts already reach, for that season and crop, is raised to it; extra tonnes = yield gap × harvested area.
""")
