import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core.data import load_backtest, load_baseline
from core.risk import K_REPORTS

bt = load_backtest()
flags = bt["low_district_flags"]

st.title("📊 Model & limitations")

st.subheader("How it works")
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

st.subheader("Backtest: predict 2024 from 2020–2023")
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

st.subheader("Data limitations")
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
- **Boundaries:** geoBoundaries RWA ADM2 (2012 boundaries, CC BY 4.0).
""")
