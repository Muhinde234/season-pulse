import html

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core.data import (DISTRICT_PROVINCE, DISTRICTS, SEASONS, current_season, fmt_pct, load_cooperatives,
                       load_irrigation, pct_vs_typical)
from core.db import get_reports
from core.official import (MAJOR, district_trend, district_vs_national_practices, latest_official_season,
                           load_district_crops)
from core.risk import adjusted_table, season_baseline
from core.ui import CROP_IC, LEVEL_STYLE, badge, filter_head, hero, icon, nz, rank_list, section
ACTION_TAG = {"Small-scale irrigation": ("water_drop", "#0284c7", "Irrigation"),
              "Soil testing & fertility support": ("science", "#16a34a", "Soil fertility"),
              "Post-harvest collection & storage": ("warehouse", "#b45309", "Storage"),
              "Value addition / processing": ("factory", "#7c3aed", "Value addition"),
              "Export opportunity": ("public", "#0f766e", "Export")}
SCALE = 60  # scorecard bar spans -60% ... +60% vs typical

hero("District Profile", "Everything Imboni knows about one district.", eyebrow="Monitor · District",
     ic="location_city", meta=[("location_on", "30 districts"), ("history", "2022–2026")])

seasons = list(SEASONS)
with st.container(key="toolbar"):
    st.markdown(filter_head(hint="Choose a district and season"), unsafe_allow_html=True)
    c1, c2, _ = st.columns([1, 1, 1.2], vertical_alignment="bottom")
    district = c1.selectbox("District", DISTRICTS, index=DISTRICTS.index("Bugesera"), key="dp_district")
    season = c2.selectbox("Season", seasons, index=seasons.index(current_season()), key="dp_season2",
                          format_func=lambda s: SEASONS[s].split(" (")[0])

province = DISTRICT_PROVINCE[district]
reports = get_reports(season)
t = adjusted_table(season, reports)
d = t[t.DistrictName == district].sort_values("adjusted_RYI")
coops = load_cooperatives().set_index("DistrictName").loc[district]
irr = load_irrigation().set_index("DistrictName").reindex([district]).iloc[0]
rain = d.dropna(subset=["rain_anom_pct"]).head(1)

# ---------- headline ----------
at_risk = int((d.level != "Normal").sum())
rain_txt = (f"{rain.rain_anom_pct.iloc[0]:+.0f}%", f"rain vs average · {rain.rain_period.iloc[0]}") if len(rain) \
    else ("–", "no rainfall data")
kpis = [
    ("crisis_alert", LEVEL_STYLE["High"] if at_risk else LEVEL_STYLE["Normal"],
     f"{at_risk} of {len(d)}" if at_risk else "None", "Crops at risk",
     f"High or Watch · {SEASONS[season].split(' (')[0]}" if at_risk else "every crop near or above typical"),
    ("rainy", "#0284c7", rain_txt[0], "Rainfall", rain_txt[1]),
    ("water_drop", "#0891b2", f"{irr.traditional_pct:.0f}%" if pd.notna(irr.traditional_pct) else "–",
     "Traditional irrigation", "of irrigated plots · SAS 2026 A"),
    ("groups", "#7c3aed", nz(int(coops.cooperatives)), "Cooperatives",
     " · ".join(f"{n} {k}" for n, k in [(int(coops.food_processors), "processors"), (int(coops.exporters), "exporters")]
                if n) or "no processors or exporters"),
]
st.markdown(f'<div class="sp-dhead"><b>{html.escape(district)}</b><span>{html.escape(province)}</span></div>'
            '<div class="sp-kpis">' + "".join(
                f'<div class="sp-kpi" style="--c:{c}"><div class="sp-kpi-ic">{icon(ic)}</div><div><b>{n}</b>'
                f'<span>{html.escape(label)}</span><small>{html.escape(sub)}</small></div></div>'
                for ic, c, n, label, sub in kpis) + "</div>", unsafe_allow_html=True)

# ---------- crops this season ----------
section(f"Crops this season", SEASONS[season])
if d.empty:
    st.info("No reliable survey data for this district and season.", icon=":material/info:")
else:
    def pos(ryi):  # % position of an RYI on the -SCALE..+SCALE bar
        return (max(min(float(pct_vs_typical(ryi)), SCALE), -SCALE) + SCALE) / (2 * SCALE) * 100

    rows = []
    for _, r in d.iterrows():
        exp, base = pos(r.adjusted_RYI), pos(r.baseline_RYI)
        fill = f"left:{min(exp, 50):.1f}%;width:{abs(exp - 50):.1f}%"
        tags = "".join(
            f'<span class="sp-tag" style="--c:{c}">{icon(ic)} {name}</span>'
            for a in r.action.split(" · ") if " " in a and a.split(" ", 1)[1] in ACTION_TAG
            for ic, c, name in [ACTION_TAG[a.split(" ", 1)[1]]]) \
            or f'<span class="sp-tag" style="--c:#64748b">{icon("visibility")} Monitor</span>'
        meta = f"{int(r.n_years)} yrs" + (" · persistently low" if r.persistently_low else "") \
            + (f" · {int(r.n_reports)} report{'s' if r.n_reports != 1 else ''}" if r.n_reports else "")
        tone = "#dc2626" if r.adjusted_RYI < 1 else "#16a34a"
        rows.append(
            f'<div class="sp-row" style="--c:{LEVEL_STYLE[r.level]};--t:{tone}">'
            f'<div class="sp-row-crop"><span class="sp-row-ic">{icon(CROP_IC[r.CropName])}</span>'
            f'<div><b>{html.escape(r.CropName)}</b><small>{meta}</small></div></div>'
            f'<div>{badge(r.level)}</div>'
            f'<div class="sp-scale" title="Bar: expected this season · tick: baseline ({fmt_pct(r.baseline_RYI)}, {r.baseline_source})">'
            f'<span class="sp-scale-0"></span><i style="{fill}"></i><em style="left:{base:.1f}%"></em></div>'
            f'<div class="sp-row-v">{fmt_pct(r.adjusted_RYI)}</div>'
            f'<div class="sp-tags">{tags}</div></div>')
    st.markdown('<div class="sp-rows"><div class="sp-row sp-row-h"><span>Crop</span><span>Status</span>'
                f'<span title="Bar: expected this season, from typical (centre line). Tick: baseline (last official result). '
                f'Scale −{SCALE}% to +{SCALE}%.">vs typical district</span>'
                f'<span>Expected</span><span>Recommended action</span></div>{"".join(rows)}</div>',
                unsafe_allow_html=True)
    st.page_link("views/alerts.py", label="Open in Alerts & Recommended Actions", icon=":material/arrow_forward:")

# ---------- history + official 2026 ----------
left, right = st.columns([1.5, 1], gap="medium")
with left.container(border=True, key="card_district_1"):
    section("Both seasons", "Baseline: last official result, % vs typical district")
    fig = go.Figure()
    for s, color in zip(seasons, ["#16a34a", "#0284c7"]):
        g = season_baseline(s).query("DistrictName == @district").sort_values("CropName")
        fig.add_bar(x=g.CropName, y=pct_vs_typical(g.baseline_RYI), name=SEASONS[s].split(" (")[0], marker_color=color,
                    marker_line_width=0, customdata=g.baseline_source,
                    hovertemplate="%{x}<br>%{y:+.0f}% vs typical<br>%{customdata}<extra>" + s[-1] + "</extra>")
    fig.add_hline(y=0, line_color="rgba(128,128,128,.6)", line_width=1)
    fig.update_layout(barmode="group", height=330, margin=dict(l=0, r=0, t=10, b=0), bargap=0.3,
                      legend=dict(orientation="h", y=1.12, x=0), plot_bgcolor="rgba(0,0,0,0)",
                      paper_bgcolor="rgba(0,0,0,0)",
                      yaxis=dict(ticksuffix="%", gridcolor="rgba(128,128,128,.15)", zeroline=False))
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
off_season = latest_official_season(season)
with right.container(border=True, key="card_district_2"):
    if off_season is None:
        st.caption("No official NISR yields for this season.")
    else:
        o = load_district_crops().query("season == @off_season and crop in @MAJOR").dropna(subset=["yield_kgha"])
        o = o.assign(med=o.groupby("crop").yield_kgha.transform("median"))
        od = o[o.DistrictName == district].assign(ryi=lambda x: x.yield_kgha / x.med)
        off_name = f"{off_season[:4]} Season {off_season[-1]}"
        if od.empty:
            st.caption(f"No official {off_name} yields for this district.")
        else:
            rank_list([(r.crop, f"{r.yield_kgha:,.0f} kg/ha · median {r.med:,.0f}", pct_vs_typical(r.ryi))
                       for _, r in od.sort_values("ryi").iterrows()], f"Official {off_name} yields")
            st.caption(f"NISR SAS {off_name}, official tables: yield by crop and district.")

# ---------- official trend + practices ----------
if off_season is not None:
    letter = off_season[-1]
    left2, right2 = st.columns([1.5, 1], gap="medium")
    with left2.container(border=True, key="card_district_3"):
        section("Official yield trend", f"Season {letter}, 2022–2026 · kg/ha vs the median district")
        tr = district_trend(district, letter)
        crops_here = [c for c in MAJOR if c in set(tr.crop)]
        crop_pick = st.selectbox("Crop", crops_here, key="dp_trend_crop") if crops_here else None
        if crop_pick:
            g = tr[tr.crop == crop_pick].sort_values("year")
            figt = go.Figure()
            figt.add_scatter(x=g.year, y=g.median_kgha, mode="lines", name="Median district",
                             line=dict(color="#5E6E65", width=2, dash="dash"),
                             hovertemplate="%{x}: %{y:,.0f} kg/ha<extra>median district</extra>")
            figt.add_scatter(x=g.year, y=g.yield_kgha, mode="lines+markers+text", name=district,
                             line=dict(color="#1F8A43", width=2), text=[f"{v:,.0f}" for v in g.yield_kgha],
                             textposition="top center", marker=dict(size=9, line=dict(color="white", width=2)),
                             hovertemplate="%{x}: %{y:,.0f} kg/ha<extra>" + district + "</extra>")
            figt.update_layout(height=280, margin=dict(l=0, r=10, t=20, b=0), plot_bgcolor="rgba(0,0,0,0)",
                               paper_bgcolor="rgba(0,0,0,0)", legend=dict(orientation="h", y=-0.2, x=0),
                               xaxis=dict(tickvals=sorted(g.year.unique()), gridcolor="rgba(14,59,34,.08)"),
                               yaxis=dict(title="kg/ha", rangemode="tozero", gridcolor="rgba(14,59,34,.08)"))
            st.plotly_chart(figt, width="stretch", config={"displayModeBar": False})
    with right2.container(border=True, key="card_district_4"):
        pv = district_vs_national_practices(district, off_season)
        section("Farming practices", f"{district} vs national · {off_season[:4]} Season {letter}")
        figp = go.Figure()
        for _, r in pv.iterrows():
            figp.add_shape(type="line", x0=r.national, x1=r.district, y0=r.label, y1=r.label,
                           line=dict(color="#C9D3CC", width=2))
        figp.add_scatter(x=pv.national, y=pv.label, mode="markers", name="National average",
                         marker=dict(color="#5E6E65", size=10, symbol="line-ns-open", line=dict(width=3)),
                         hovertemplate="<b>%{y}</b><br>National: %{x:.0f}%<extra></extra>")
        figp.add_scatter(x=pv.district, y=pv.label, mode="markers+text", name=district,
                         marker=dict(color=["#1F8A43" if a >= b else "#E0A100" for a, b in zip(pv.district, pv.national)],
                                     size=11, line=dict(color="white", width=2)),
                         text=[f"{v:.0f}%" for v in pv.district],
                         textposition=["middle right" if a >= b else "middle left"
                                       for a, b in zip(pv.district, pv.national)],
                         textfont=dict(color="#5E6E65", size=11),
                         hovertemplate="<b>%{y}</b><br>" + district + ": %{x:.0f}%<extra></extra>")
        figp.update_layout(height=320, margin=dict(l=120, r=10, t=10, b=0), plot_bgcolor="rgba(0,0,0,0)",
                           paper_bgcolor="rgba(0,0,0,0)", legend=dict(orientation="h", y=-0.14, x=-0.4),
                           xaxis=dict(range=[0, 112], ticksuffix="%", gridcolor="rgba(14,59,34,.08)"),
                           yaxis=dict(showgrid=False))
        st.plotly_chart(figp, width="stretch", config={"displayModeBar": False})
        below = pv[pv.district < pv.national - 5].sort_values("national", ascending=False).label.tolist()
        st.caption(("Below the national average: " + ", ".join(below).lower() + ".") if below
                   else "At or above the national average on every practice.")

# ---------- recent reports ----------
r = get_reports()
r = r[r.district == district]
section("Field reports", f"{len(r)} in total" if len(r) else "")
if r.empty:
    st.caption("No field reports from this district yet.")
    st.page_link("views/report.py", label="Submit one", icon=":material/edit_note:")
else:
    st.dataframe(
        r.assign(source=r.source.where(r.is_simulated == 0, "SIMULATED"), pests=r.pests.map({0: "No", 1: "Yes"}),
                 season=r.season.map(lambda s: SEASONS.get(s, s).split(" (")[0]))
         [["created_at", "crop", "season", "condition", "pests", "rain_problem", "source"]]
         .rename(columns={"created_at": "Submitted", "crop": "Crop", "season": "Season", "condition": "Condition",
                          "pests": "Pests", "rain_problem": "Rain problem", "source": "Source"}),
        hide_index=True, width="stretch", height=min(38 + 35 * len(r), 320))
