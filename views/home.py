import html

import plotly.graph_objects as go
import streamlit as st

from core.data import DISTRICTS, SEASONS, current_season, load_backtest, load_geojson, load_validation, pct_vs_typical
from core.db import get_reports
from core.risk import adjusted_table
from core.ui import LEVEL_STYLE, hero, icon, nz, rank_list, section

season = current_season()
season_name = SEASONS[season].split(" (")[0]
reports = get_reports(season)
t = adjusted_table(season, reports)
v = load_validation()
bt = load_backtest()

hero("Imboni", f"In-season crop early warning for Rwanda's 30 districts · {SEASONS[season]}",
     eyebrow="Overview", ic="visibility")

# ---------- headline numbers ----------
high, watch = t[t.level == "High"], t[t.level == "Watch"]
districts_at_risk = t[t.level != "Normal"].DistrictName.nunique()
caught, bad = int((v.actual_low & v.flagged).sum()), int(v.actual_low.sum())
n_sim = int(reports.is_simulated.sum())
kpis = [
    ("crisis_alert", LEVEL_STYLE["High"], nz(len(high)), "High alerts",
     f"{len(watch)} more on Watch" if len(watch) else "nothing on Watch"),
    ("location_on", "#ea8a0c", nz(districts_at_risk), "Districts at risk", "with a High or Watch crop"),
    ("edit_note", "#0284c7", nz(len(reports), "None yet"), "Field reports",
     (f"{n_sim} simulated" if n_sim else "all from the field") if len(reports) else "be the first to report"),
    ("verified", "#16a34a", f"{caught}/{bad}", "Bad cells caught", "official NISR 2026 Season A"),
]
st.markdown('<div class="sp-kpis">' + "".join(
    f'<div class="sp-kpi" style="--c:{c}"><div class="sp-kpi-ic">{icon(ic)}</div><div><b>{n}</b>'
    f'<span>{html.escape(label)}</span><small>{html.escape(sub)}</small></div></div>'
    for ic, c, n, label, sub in kpis) + "</div>", unsafe_allow_html=True)

# ---------- map of alerts per district + top alerts ----------
left, right = st.columns([1.6, 1], gap="medium")
with left.container(border=True):
    section(f"Alerts per district · {season_name}", "High + Watch crops")
    counts = t[t.level != "Normal"].groupby("DistrictName").size().reindex(DISTRICTS, fill_value=0)
    hover = [f"<b>{d}</b><br>" + (f"{n} crop{'s' if n > 1 else ''} at High or Watch" if n else "no crop at risk")
             for d, n in counts.items()]
    fig = go.Figure(go.Choropleth(
        geojson=load_geojson(), featureidkey="properties.shapeName", locations=counts.index, z=counts.values,
        zmin=0, zmax=max(int(counts.max()), 3), hovertext=hover, hoverinfo="text",
        colorscale=[[0, "#f1f5f2"], [0.35, "#fcd34d"], [0.7, "#f97316"], [1, "#b91c1c"]],
        marker_line_color="white", marker_line_width=1,
        colorbar=dict(title=dict(text="crops at risk", side="top"), orientation="h", x=0.5, xanchor="center",
                      y=-0.02, yanchor="top", len=0.6, thickness=10, outlinewidth=0,
                      tickvals=list(range(1, max(int(counts.max()), 3) + 1)))))
    fig.update_geos(fitbounds="locations", visible=False)
    fig.update_layout(height=430, margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor="rgba(0,0,0,0)",
                      geo_bgcolor="rgba(0,0,0,0)", dragmode=False)
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
with right.container(border=True):
    top = t[t.level != "Normal"].head(7)
    rank_list([(f"{r.DistrictName} · {r.CropName}", r.Province, pct_vs_typical(r.adjusted_RYI))
               for _, r in top.iterrows()], "Top priority alerts")
    st.page_link("views/alerts.py", label="See all alerts and actions", icon=":material/arrow_forward:")

# ---------- how it works ----------
section("How Imboni works")
steps = [
    ("history", "1 · History", "NISR survey results 2020–2024 show which districts usually do worse than the "
                               "typical district, crop by crop."),
    ("edit_note", "2 · Field reports", "Extension officers and farmers report crop condition, pests and rain "
                                       "problems during the season, on the web or by USSD."),
    ("notifications_active", "3 · Alerts", "History and reports combine into a risk level per district and "
                                           "crop, ranked by food dependence."),
    ("task_alt", "4 · Action", "Each alert comes with a recommended action and the local co-ops, processors "
                               "and exporters who can help."),
]
st.markdown('<div class="sp-steps">' + "".join(
    f'<div class="sp-stepcard"><div class="sp-stepcard-ic">{icon(ic)}</div><b>{html.escape(title)}</b>'
    f'<span>{html.escape(text)}</span></div>' for ic, title, text in steps) + "</div>", unsafe_allow_html=True)

# ---------- key findings ----------
section("Key findings")
findings = [
    ("warning", "#ea8a0c", "Yield units aren't consistent",
     "In the cleaned 2020–2024 files Irish potato yields drop from ≈13 t/ha to ≈0.8 t/ha. Imboni compares "
     "districts within the same year instead, so the error cancels out."),
    ("verified", "#16a34a", f"History caught {caught} of {bad} bad cells in 2026",
     "Checked against official NISR 2026 Season A yields, a season the model never saw. It ranks districts "
     "well for potatoes, beans and maize, not for cassava."),
    ("trending_down", "#dc2626", f"{bt['error_reduction_pct']}% less error than guessing",
     f"On the 2024 backtest, history beats assuming every district is typical, but it catches only "
     f"{bt['low_district_flags']['recall']:.0%} of bad seasons. That gap is why field reports matter."),
]
st.markdown('<div class="sp-finds">' + "".join(
    f'<div class="sp-find" style="--c:{c}"><div class="sp-find-ic">{icon(ic)}</div><b>{html.escape(title)}</b>'
    f'<span>{html.escape(text)}</span></div>' for ic, c, title, text in findings) + "</div>", unsafe_allow_html=True)

# ---------- quick links ----------
section("Explore")
links = [("views/map.py", "District Risk Map", ":material/map:"),
         ("views/district.py", "District Profile", ":material/location_city:"),
         ("views/report.py", "Submit a field report", ":material/edit_note:"),
         ("views/model.py", "Model & Data Quality", ":material/insights:")]
for col, (page, label, ic) in zip(st.columns(4), links):
    with col.container(border=True):
        st.page_link(page, label=label, icon=ic, width="stretch")
