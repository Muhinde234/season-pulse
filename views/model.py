import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core.data import load_backtest, load_baseline, load_rain_vs_ryi, load_validation
from core.risk import K_REPORTS
from core.ui import hero, section

bt = load_backtest()
flags = bt["low_district_flags"]

hero("Model & Data Quality", "How the Relative Yield Index and the field-report adjustment work, how well "
     "they did on unseen 2024 data, and what the data can't tell you.", eyebrow="About · Methodology")

section("How it works")
st.markdown("""
1. **Relative Yield Index (RYI).** For every crop × season × year, each district's yield is divided by the
   *median district* that same season: `RYI = district yield / median district yield`. Because SAS yield units
   differ across years, absolute kg/ha are never compared or shown, and any year-wide unit factor cancels out.
   RYI 0.73 is shown as **−27% vs typical district**.
2. **Baseline.** The mean log-RYI over 2020–2024 for each district × crop × season, shrunk toward "typical"
   by `n_years / (n_years + 1)` so districts with little history aren't over-confident. Cells with fewer than
   10 farm observations are excluded.
3. **In-season adjustment.** Field reports (condition 1–5, pests, rain problems) shift the baseline in log space,
   weighted by `n / (n + {k:g})` so a single report moves it only a little.
4. **Alert levels.** 🔴 High: expected RYI ≤ 0.75 · 🟠 Watch: ≤ 0.85 (the backtest flag threshold) · 🟢 Normal.
""".format(k=K_REPORTS))

section("Backtest: predict 2024 from 2020–2023")
st.caption("Trained on 2020–2023 only, then scored on 2024 district results the model never saw. "
           "The naive benchmark assumes every district is typical (RYI = 1).")
c = st.columns(4)
c[0].metric("2024 test cells", bt["test_cells_2024"])
c[1].metric("Error reduction vs naive", f"{bt['error_reduction_pct']}%",
            help=f"Mean absolute error in log-RYI: model {bt['mae_log_model']} vs naive {bt['mae_log_naive']}")
c[2].metric("Precision of low flags", f"{flags['precision']:.0%}",
            help=f"{flags['flagged']} cells flagged (predicted RYI ≤ 0.85); share that really ended ≥25% below typical")
c[3].metric("Recall of low districts", f"{flags['recall']:.0%}",
            help=f"Of {flags['actual_low']} cells that ended ≥25% below typical, share flagged in advance")

crop = pd.DataFrame(bt["by_crop_mae"]).T.rename_axis("Crop").reset_index()
fig = go.Figure()
for col, name, color in [("naive", "Naive (every district typical)", "#eb6834"),
                         ("model", "Season Pulse baseline", "#2a78d6")]:
    fig.add_bar(x=crop.Crop, y=crop[col], name=name, marker_color=color, marker_line_width=0,
                text=crop[col].round(2), textposition="outside", textfont_color="gray",
                hovertemplate="%{x}<br>" + name + ": %{y:.3f}<extra></extra>")
fig.update_layout(barmode="group", bargap=0.35, bargroupgap=0.08, height=360,
                  margin=dict(l=0, r=0, t=30, b=0), legend=dict(orientation="h", y=1.12, x=0),
                  yaxis=dict(title="Mean abs. error (log RYI) · lower is better", gridcolor="rgba(128,128,128,0.15)",
                             zeroline=False),
                  plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
worse = crop[crop.model > crop.naive].Crop.tolist()
if worse:
    st.warning(f"For **{', '.join(worse)}** the historical baseline did *worse* than assuming every district is "
               "typical. District rankings for that crop are unstable year to year; treat its alerts as "
               "driven mainly by field reports.")
with st.expander("Table view"):
    st.dataframe(crop.rename(columns={"naive": "Naive MAE", "model": "Model MAE"}), hide_index=True)

st.markdown(f"""
**Reading the results honestly:** history alone explains part of next season. The baseline cuts error by
{bt['error_reduction_pct']}%, but only about {flags['recall']:.0%} of the districts that ended badly were flagged
from history alone, and {flags['precision']:.0%} of flags were correct. That gap is why Season Pulse
collects in-season field reports: the baseline says *where to look*, reports say *what is happening now*.
""")

section("Validation: official NISR 2026 Season A yields")
v = load_validation()
caught = int((v.actual_low & v.flagged).sum())
st.caption("A season the model never saw. The Season A baseline (built from 2020–2024 only) is compared with "
           "the official district yields NISR published for 2026 Season A (SAS 2026, Table 13), converted to RYI "
           "the same way (district ÷ median district). Tomatoes aren't published separately, so they're not included.")
r_by_crop = (v.groupby("CropName")
               .apply(lambda g: pd.Series({"r": np.log(g.official_RYI).corr(np.log(g.predicted_RYI)),
                                           "Districts": len(g)}), include_groups=False)
               .reset_index())
vc = st.columns(4)
vc[0].metric("2026 A cells", len(v), help="District × crop pairs with both a baseline and an official 2026 yield")
vc[1].metric("Bad cells caught", f"{caught} of {int(v.actual_low.sum())}",
             help="Cells that came in ≥20% below typical in 2026 A and were flagged in advance (baseline ≤ 0.85)")
vc[2].metric("Precision of flags", f"{caught / max(int(v.flagged.sum()), 1):.0%}",
             help=f"{int(v.flagged.sum())} cells flagged; share that really came in ≥20% below typical")
best = r_by_crop.sort_values("r", ascending=False).iloc[0]
vc[3].metric("Best ranking (Pearson r)", f"{best.r:+.2f}", help=f"{best.CropName}; see the per-crop table")

fig = go.Figure()
for i, (crop_name, g) in enumerate(v.groupby("CropName")):
    fig.add_scatter(x=100 * (g.predicted_RYI - 1), y=100 * (g.official_RYI - 1), mode="markers", name=crop_name,
                    marker=dict(size=9, opacity=0.8, color=["#2a78d6", "#eb6834", "#16a34a", "#9b59b6"][i % 4],
                                line=dict(width=1, color="rgba(255,255,255,0.8)")),
                    customdata=g[["DistrictName", "yield_kg_ha"]],
                    hovertemplate="<b>%{customdata[0]}</b> · " + crop_name + "<br>Baseline: %{x:+.0f}%"
                                  "<br>Official 2026 A: %{y:+.0f}% (%{customdata[1]:,.0f} kg/ha)<extra></extra>")
fig.add_shape(type="line", x0=-70, y0=-70, x1=150, y1=150, line=dict(color="rgba(128,128,128,0.45)", dash="dot"))
fig.add_hline(y=-20, line_color="rgba(220,38,38,0.4)", line_dash="dash",
              annotation_text="20% below typical", annotation_position="bottom right")
fig.update_layout(height=420, margin=dict(l=0, r=0, t=30, b=0), legend=dict(orientation="h", y=1.1, x=0),
                  xaxis=dict(title="Historical baseline: % vs typical district", ticksuffix="%",
                             gridcolor="rgba(128,128,128,0.15)", zeroline=False),
                  yaxis=dict(title="Official 2026 Season A: % vs typical district", ticksuffix="%",
                             gridcolor="rgba(128,128,128,0.15)", zeroline=False),
                  plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
v1, v2 = st.columns([2.2, 1])
v1.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
v2.dataframe(r_by_crop.rename(columns={"CropName": "Crop", "r": "Pearson r"}).round(2), hide_index=True,
             width="stretch")
v2.caption("r = correlation between the baseline and the official 2026 result (log RYI). Positive = history "
           "ranks districts in the right order.")
spread = np.log(v.predicted_RYI).std() / np.log(v.official_RYI).std()
st.markdown(f"**Reading it:** history ranks districts in the right order for Irish potatoes, beans and maize, but "
            f"not for cassava. Baseline values are about {spread:.1f}× as spread out as the official results: it "
            "overstates how far from typical a district will be, so Season Pulse uses it as a **risk ranking**, "
            "not an exact forecast, and relies on field reports for what is happening this season.")
with st.expander("Table view (out_validation_2026A.csv)"):
    st.dataframe(v.rename(columns={"DistrictName": "District", "CropName": "Crop", "yield_kg_ha": "Official kg/ha",
                                   "official_RYI": "Official RYI", "predicted_RYI": "Baseline RYI",
                                   "n_years": "Years of history", "actual_low": "≥20% below typical",
                                   "flagged": "Flagged in advance"}),
                 hide_index=True, width="stretch")
    st.download_button("Download validation (CSV)", v.to_csv(index=False), file_name="out_validation_2026A.csv",
                       mime="text/csv")

section("Do bad yield years match dry seasons?")
rv = load_rain_vs_ryi()
if rv.empty:
    st.info("No rainfall data yet: run `python fetch_rainfall.py` to build it from CHIRPS.")
else:
    st.caption("CHIRPS v2.0 monthly rainfall averaged over each district, summed per season (A = Sep–Dec of the "
               "previous year, B = Mar–May, C = Jun–Aug), joined with SAS 2020–2024 for district × crop × season "
               "cells with at least 3 years. Both sides are relative: RYI compares a district with the typical "
               "district that year, so rainfall is likewise compared with the typical district's anomaly that "
               "season. A countrywide drought cancels out of both.")
    x = 100 * (np.exp(rv.rain_rel) - 1)  # % wetter/drier than the typical district's anomaly
    y = 100 * (np.exp(rv.ryi_dev) - 1)   # % above/below this cell's own average RYI
    r_all = rv.ryi_dev.corr(rv.rain_rel)
    rho = rv.ryi_dev.corr(rv.rain_rel, method="spearman")
    dry = x <= -10
    bad = y <= -20
    c = st.columns(4)
    c[0].metric("Correlation (Pearson r)", f"{r_all:+.2f}", help=f"Spearman ρ = {rho:+.2f}. n = {len(rv)} cell-years.")
    c[1].metric("Cell-years", len(rv))
    c[2].metric("Bad years in relatively dry seasons", f"{bad[dry].mean():.0%}",
                help="Share of cell-years ≥20% below the cell's own average RYI, when the district was ≥10% "
                     "drier than the typical district that season")
    c[3].metric("Bad years in other seasons", f"{bad[~dry].mean():.0%}")

    fig = go.Figure(go.Scattergl(
        x=x, y=y, mode="markers",
        marker=dict(size=8, color="#2a78d6", opacity=0.55, line=dict(width=1, color="rgba(255,255,255,0.8)")),
        customdata=rv[["DistrictName", "CropName", "Season", "Year"]],
        hovertemplate="<b>%{customdata[0]}</b> · %{customdata[1]}<br>%{customdata[2]} %{customdata[3]}"
                      "<br>Rain vs typical district: %{x:+.0f}%<br>Yield vs own average: %{y:+.0f}%<extra></extra>"))
    fig.add_hline(y=0, line_color="rgba(128,128,128,0.5)", line_width=1)
    fig.add_vline(x=0, line_color="rgba(128,128,128,0.5)", line_width=1)
    fig.update_layout(height=380, margin=dict(l=0, r=0, t=10, b=0), showlegend=False,
                      xaxis=dict(title="Season rainfall vs typical district (relative %)", ticksuffix="%",
                                 gridcolor="rgba(128,128,128,0.15)", zeroline=False),
                      yaxis=dict(title="RYI vs the cell's own average", ticksuffix="%",
                                 gridcolor="rgba(128,128,128,0.15)", zeroline=False),
                      plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

    by_crop = (rv.groupby("CropName")
                 .apply(lambda g: pd.Series({"Pearson r": round(g.ryi_dev.corr(g.rain_rel), 2),
                                             "Cell-years": len(g)}), include_groups=False)
                 .reset_index().rename(columns={"CropName": "Crop"}))
    by_season = (rv.groupby("Season")
                   .apply(lambda g: pd.Series({"Pearson r": round(g.ryi_dev.corr(g.rain_rel), 2),
                                               "Cell-years": len(g)}), include_groups=False)
                   .reset_index())
    t1, t2 = st.columns(2)
    t1.dataframe(by_crop, hide_index=True, width="stretch")
    t2.dataframe(by_season, hide_index=True, width="stretch")
    strength = ("essentially no" if abs(r_all) < 0.1 else "a weak" if abs(r_all) < 0.3
                else "a moderate" if abs(r_all) < 0.5 else "a strong")
    st.markdown(f"**Reading it:** there is **{strength} link** (r = {r_all:+.2f}) between a district being "
                "relatively dry in a season and that season being a bad year for it. A positive r would mean drier "
                "seasons go with worse yields. In 2020–2024 rainfall differences between districts did not explain "
                "which district-crop cells had bad years: soils, pests, inputs and survey noise matter more at "
                "this scale. That is why Season Pulse uses rainfall only as one trigger for the irrigation "
                "recommendation and never to move the yield estimate.")
    with st.expander("Table view"):
        st.dataframe(rv.assign(**{"Rain vs typical %": x.round(0), "Yield vs own avg %": y.round(0)})
                     [["DistrictName", "CropName", "Season", "Year", "rain_mm", "Rain vs typical %",
                       "Yield vs own avg %"]], hide_index=True, width="stretch")

section("Data limitations")
b = load_baseline()
st.markdown(f"""
- **SAS yield units are inconsistent across years** (e.g. Irish potato values drop roughly 20–30× from 2022 onward).
  Only within-year relative comparisons (RYI) are used; kg/ha are never shown.
- **Short history:** 2020–2024 at most, and only 3 years for Maize and Tomatoes.
  {int((b.n_years < 3).sum())} of {len(b)} baseline cells have fewer than 3 years.
- **Coverage gaps:** Season C has few crops; some district × crop cells are missing or excluded for having
  < 10 observations. These appear grey on the map.
- **Report weights are expert judgement, not estimated.** Condition, pest and rain effects (±0.10 log-RYI per step)
  have not been calibrated against outcomes: there are no historical field reports to calibrate on.
- **Simulated reports** are clearly labelled demo data and must not be interpreted as observations.
- **EICV** consumption uses the 2020 round only; duplicate district rows in the source are summed.
- **Establishment Census** gives counts of cooperatives and food processors per district, not names or contacts.
  The cleaned file labels district code 28 as "Unknown District"; it is mapped to Kamonyi (NISR code 28).
- **Storage:** reports are kept in SQLite. On Streamlit Community Cloud the disk resets when the app restarts,
  so production use needs a hosted database.
- **Rainfall:** CHIRPS v2.0 is satellite + station rainfall at ~5 km; small districts (e.g. Nyarugenge) cover only
  a few pixels. The latest season can be partial (only the months published so far), and is then compared with
  the average for the same months.
- **Boundaries:** geoBoundaries RWA ADM2 (2012 boundaries, CC BY 4.0).
""")
