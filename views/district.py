import html

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core.data import (DISTRICT_PROVINCE, DISTRICTS, SEASONS, current_season, fmt_pct, load_baseline,
                       load_cooperatives, load_irrigation, load_official_2026, pct_vs_typical)
from core.db import get_reports
from core.risk import adjusted_table
from core.ui import LEVEL_STYLE, badge, hero, icon, nz, rank_list, section

# Crop and action icons for the scorecard (names resolved to Lucide in core.ui.icon)
CROP_IC = {"Beans": "grain", "Cassava": "nutrition", "Irish potatoes": "egg", "Maize": "grass",
           "Tomatoes": "local_florist"}
ACTION_TAG = {"Small-scale irrigation": ("water_drop", "#0284c7", "Irrigation"),
              "Soil testing & fertility support": ("science", "#16a34a", "Soil fertility"),
              "Post-harvest collection & storage": ("warehouse", "#b45309", "Storage"),
              "Value addition / processing": ("factory", "#7c3aed", "Value addition"),
              "Export opportunity": ("public", "#0f766e", "Export")}
SCALE = 60  # scorecard bar spans -60% ... +60% vs typical

hero("District Profile", "Everything Imboni knows about one district.", eyebrow="Monitor · District",
     ic="location_city")

seasons = list(SEASONS)
with st.container(key="toolbar"):
    c1, c2 = st.columns([1, 1.3], vertical_alignment="bottom")
    district = c1.selectbox("District", DISTRICTS, index=DISTRICTS.index("Bugesera"), key="dp_district")
    season = c2.segmented_control("Season", seasons, default=current_season(), key="dp_season",
                                  format_func=lambda s: SEASONS[s].split(" (")[0]) or current_season()

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
            f'<div class="sp-scale" title="Bar: expected this season · tick: 2020–2024 baseline ({fmt_pct(r.baseline_RYI)})">'
            f'<span class="sp-scale-0"></span><i style="{fill}"></i><em style="left:{base:.1f}%"></em></div>'
            f'<div class="sp-row-v">{fmt_pct(r.adjusted_RYI)}</div>'
            f'<div class="sp-tags">{tags}</div></div>')
    st.markdown('<div class="sp-rows"><div class="sp-row sp-row-h"><span>Crop</span><span>Status</span>'
                f'<span title="Bar: expected this season, from typical (centre line). Tick: 2020–2024 baseline. '
                f'Scale −{SCALE}% to +{SCALE}%.">vs typical district</span>'
                f'<span>Expected</span><span>Recommended action</span></div>{"".join(rows)}</div>',
                unsafe_allow_html=True)
    st.page_link("views/alerts.py", label="Open in Alerts & Recommended Actions", icon=":material/arrow_forward:")

# ---------- history + official 2026 ----------
left, right = st.columns([1.5, 1], gap="medium")
with left.container(border=True):
    section("History by season", "2020–2024 baseline, % vs typical district")
    b = load_baseline()
    b = b[b.DistrictName == district]
    fig = go.Figure()
    for s, color in zip(seasons, ["#16a34a", "#0284c7", "#ea8a0c"]):
        g = b[b.Season == s]
        fig.add_bar(x=g.CropName, y=pct_vs_typical(g.baseline_RYI), name=SEASONS[s].split(" (")[0], marker_color=color,
                    marker_line_width=0, hovertemplate="%{x}<br>%{y:+.0f}% vs typical<extra>" + s[-1] + "</extra>")
    fig.add_hline(y=0, line_color="rgba(128,128,128,.6)", line_width=1)
    fig.update_layout(barmode="group", height=330, margin=dict(l=0, r=0, t=10, b=0), bargap=0.3,
                      legend=dict(orientation="h", y=1.12, x=0), plot_bgcolor="rgba(0,0,0,0)",
                      paper_bgcolor="rgba(0,0,0,0)",
                      yaxis=dict(ticksuffix="%", gridcolor="rgba(128,128,128,.15)", zeroline=False))
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
with right.container(border=True):
    o = load_official_2026()
    o = o.assign(med_kg=o.groupby("CropName").yield_kg_ha.transform("median"))
    od = o[o.DistrictName == district]
    if od.empty:
        st.caption("No official 2026 Season A yields for this district.")
    else:
        rank_list([(r.CropName, f"{r.yield_kg_ha:,.0f} kg/ha · median {r.med_kg:,.0f}", pct_vs_typical(r.official_RYI))
                   for _, r in od.sort_values("official_RYI").iterrows()], "Official 2026 Season A yields")
        st.caption("NISR SAS 2026 Season A, Table 13.")

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
                 season=r.season.map(lambda s: SEASONS[s].split(" (")[0]))
         [["created_at", "crop", "season", "condition", "pests", "rain_problem", "source"]]
         .rename(columns={"created_at": "Submitted", "crop": "Crop", "season": "Season", "condition": "Condition",
                          "pests": "Pests", "rain_problem": "Rain problem", "source": "Source"}),
        hide_index=True, width="stretch", height=min(38 + 35 * len(r), 320))
