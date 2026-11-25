import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core.data import (DATA, load_backtest, load_baseline, load_official_backtest, load_rain_vs_official,
                       load_validation)
from core.official import SOURCE_URL
from core.risk import K_REPORTS
from core.ui import hero, section

obt = load_official_backtest()
last = obt[obt.method == "Last season"]
years = f"{last.year.min()}–{last.year.max()}"


def pooled(m: pd.DataFrame) -> pd.Series:
    """Totals over every season-year of one method; error weighted by cells."""
    return pd.Series({"cells": m.cells.sum(), "mae_pct": (m.mae_pct * m.cells).sum() / m.cells.sum(),
                      "bad_cells": m.bad_cells.sum(), "caught": m.caught.sum(), "flagged": m.flagged.sum()})


summary = obt.groupby("method").apply(pooled, include_groups=False)
best, naive = summary.loc["Last season"], summary.loc["Every district typical"]

hero("Model & Data Quality", "How it works, how well it predicts, and its limits.",
     meta=[("verified", f"Backtested on NISR {years}")], eyebrow="About · Methodology", ic="insights")

tabs = st.tabs(["How it works", "Backtest (official tables)", "Rainfall vs yield", "Cleaned 2020–2024 files",
                "Data limitations"])
with tabs[0]:
    section("How it works")
    st.markdown(f"""
    1. **Relative Yield Index (RYI).** For every crop × season × year, each district's yield is divided by the
       *median district* that same season: `RYI = district yield / median district yield`. RYI 0.73 is shown as
       **−27% vs typical district**.
    2. **Baseline = the last official result.** For the seven priority crops (banana, beans, cassava, Irish potato,
       maize, paddy rice, sweet potato), the baseline is the district's RYI in NISR's latest official tables for the
       same season (Season A from Season A, B from B). The *Backtest* tab shows why: on every season {years} it beat
       both "every district typical" and the average of the last two seasons.
       **Tomatoes** are only published by NISR inside "vegetables", so they keep the 2020–2024 baseline from the
       cleaned SAS files. That baseline is not validated and is labelled as such everywhere.
    3. **In-season adjustment.** Field reports (condition 1–5, pests, rain problems) shift the baseline in log space,
       weighted by `n / (n + {K_REPORTS:g})` so a single report moves it only a little.
    4. **Alert levels.** 🔴 High: expected RYI ≤ 0.75 · 🟠 Watch: ≤ 0.85 · 🟢 Normal.
    """)
    st.warning("**The field-report weights are assumptions, not estimates.** Each condition step moves the estimate "
               "by 10%, pests by −10% and a rain problem by −10% (in log RYI). There are no past field reports to fit "
               "these on. Once real reports exist, they should be re-fitted against the next official NISR results.",
               icon=":material/science:")

with tabs[1]:
    section("Backtest: predict each season from NISR's earlier official tables")
    st.caption(f"Every Season A and B from {years}, seven priority crops, all districts with data in both years. "
               f"Source: [NISR SAS official tables]({SOURCE_URL}), 2022–2026.")
    c = st.columns(4)
    c[0].metric("Cell-seasons tested", f"{int(best.cells):,}")
    c[1].metric("Average error", f"{best.mae_pct:.1f}%",
                help=f"Mean absolute error in log RYI ×100, last season's official result. "
                     f"Every district typical: {naive.mae_pct:.1f}%")
    c[2].metric("Bad cells caught", f"{int(best.caught)} of {int(best.bad_cells)}",
                help="Cells ≥20% below the median district, flagged in advance (last season ≤ 0.85)")
    c[3].metric("Precision of flags", f"{best.caught / best.flagged:.0%}",
                help=f"{int(best.flagged)} cells flagged; share that really came in ≥20% below the median")

    obt["label"] = obt.year.astype(str) + obt.season
    fig = go.Figure()
    for name, color in [("Every district typical", "#eb6834"), ("Average of last two seasons", "#9b59b6"),
                        ("Last season", "#2a78d6")]:
        g = obt[obt.method == name].sort_values(["year", "season"])
        fig.add_scatter(x=g.label, y=g.mae_pct, mode="lines+markers", name=name, line=dict(color=color, width=2),
                        hovertemplate="%{x}: %{y:.1f}% error<extra>" + name + "</extra>")
    fig.update_layout(height=340, margin=dict(l=0, r=0, t=30, b=0), legend=dict(orientation="h", y=1.12, x=0),
                      yaxis=dict(title="Average error (%) · lower is better", rangemode="tozero",
                                 gridcolor="rgba(128,128,128,0.15)"),
                      xaxis=dict(title="Season predicted"), plot_bgcolor="rgba(0,0,0,0)",
                      paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

    table = last.assign(**{"Season": last.year.astype(str) + last.season,
                           "Bad cells caught": last.caught.astype(str) + " of " + last.bad_cells.astype(str),
                           "Moved >10%": last.moved.astype(str) + " of " + last.cells.astype(str)})
    first_year = int(last.year.min())
    first_err = (lambda m: (m.mae_pct * m.cells).sum() / m.cells.sum())(last[last.year == first_year])
    recent = last[last.year >= last.year.max() - 1]
    recent_err = (recent.mae_pct * recent.cells).sum() / recent.cells.sum()
    recent_years = f"{recent.year.min()}–{recent.year.max()}"
    t1, t2 = st.columns([1.3, 1])
    t1.dataframe(table[["Season", "cells", "mae_pct", "rank_r", "Bad cells caught", "flagged", "Moved >10%"]]
                 .rename(columns={"cells": "Cells", "mae_pct": "Error (%)", "rank_r": "Rank r", "flagged": "Flagged"}),
                 hide_index=True, width="stretch")
    t2.markdown(f"""
    **Reading it honestly**

    - A district's last official result for the same season is the best predictor we found: **{best.mae_pct:.1f}%**
      average error vs {naive.mae_pct:.1f}% for "every district typical", catching
      **{best.caught / best.bad_cells:.0%}** of bad cells.
    - Its error fell from **{first_err:.0f}%** in {first_year} to **{recent_err:.1f}%** on average in
      {recent_years}, because district positions became much steadier: the cells that moved more than 10% from
      the year before dropped sharply (last column).
    - That stability is a feature of the survey results, not forecasting skill. NISR's district figures are
      **direct survey estimates** (25–68 sampled segments per district, GPS-measured areas, farmer-reported
      production), so we can't tell how much of it comes from the farms and how much from the sample.
    - Last season **cannot see a district that breaks its pattern**, and rainfall did not explain the ones that did
      (next tab). That is the gap field reports are for.
    """)

    cells = pd.read_csv(DATA / "out_official_backtest_cells.csv")
    pick = st.segmented_control("Season to plot", sorted((cells.year.astype(str) + cells.season).unique()),
                                default=f"{last.year.max()}A", key="bt_pick") or f"{last.year.max()}A"
    g = cells[(cells.year == int(pick[:4])) & (cells.season == pick[-1])]
    figc = go.Figure()
    for bad, (name, color) in {False: ("Other cells", "#1F8A43"), True: ("Ended ≥20% below median", "#E0A100")}.items():
        cc = g[(g.ryi_now <= 0.8) == bad]
        figc.add_scatter(x=100 * (cc.ryi_prev - 1), y=100 * (cc.ryi_now - 1), mode="markers", name=name,
                         marker=dict(size=9 if bad else 7, color=color, opacity=.9 if bad else .55,
                                     line=dict(width=1.5, color="white")),
                         customdata=cc[["DistrictName", "crop"]],
                         hovertemplate="<b>%{customdata[0]}</b> · %{customdata[1]}"
                                       "<br>Year before: %{x:+.0f}%<br>Actual: %{y:+.0f}%<extra></extra>")
    figc.add_hline(y=-20, line=dict(color="#E0A100", width=1, dash="dash"))
    figc.add_vline(x=-15, line=dict(color="#5E6E65", width=1, dash="dash"))
    figc.add_shape(type="line", x0=-80, y0=-80, x1=160, y1=160, line=dict(color="rgba(128,128,128,0.45)", dash="dot"))
    figc.update_layout(height=420, margin=dict(l=0, r=0, t=30, b=0), legend=dict(orientation="h", y=1.1, x=0),
                       xaxis=dict(title="Same season, year before: % vs median district", ticksuffix="%",
                                  gridcolor="rgba(128,128,128,0.15)", zeroline=False),
                       yaxis=dict(title=f"Official {pick}: % vs median district", ticksuffix="%",
                                  gridcolor="rgba(128,128,128,0.15)", zeroline=False),
                       plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(figc, width="stretch", config={"displayModeBar": False})
    st.caption("Dots on the diagonal kept their position. Left of the grey line = flagged in advance; "
               "gold = ended ≥20% below the median district.")

with tabs[2]:
    section("Does rainfall explain the cells that moved?")
    rv = load_rain_vs_official()
    if rv.empty:
        st.info("No rainfall data yet: run `python fetch_rainfall.py`, then `python prep_official.py`.")
    else:
        covered = ", ".join(sorted((rv.Year.astype(str) + rv.Season.str[-1]).unique()))
        st.caption("CHIRPS seasonal rainfall per district vs the change in official RYI from the same season a year "
                   f"earlier, both relative to the typical district. Seasons with rainfall data: {covered} "
                   "(the stored rainfall skips 2025A, 2025B and 2026A; re-run fetch_rainfall.py with more years "
                   "to add them).",
                   help="A = Sep–Dec of the previous year, B = Mar–May. Rainfall is log(rain / district average) "
                        "minus the median across districts that season, so a countrywide drought cancels out, "
                        "as it does in RYI.")
        x = 100 * (np.exp(rv.rain_rel) - 1)
        y = 100 * (np.exp(rv.ryi_dev) - 1)
        r_all = rv.ryi_dev.corr(rv.rain_rel)
        rho = rv.ryi_dev.rank().corr(rv.rain_rel.rank())  # Spearman = Pearson on ranks (no scipy needed)
        dry, drop = x <= -10, y <= -20
        c = st.columns(4)
        c[0].metric("Correlation (Pearson r)", f"{r_all:+.2f}", help=f"Spearman ρ = {rho:+.2f}. n = {len(rv)}.")
        c[1].metric("Cell-seasons", f"{len(rv):,}")
        c[2].metric("Dropped ≥20% in relatively dry seasons", f"{drop[dry].mean():.0%}",
                    help="Share of cells whose RYI fell ≥20% from the year before, when the district was ≥10% drier "
                         "than the typical district that season")
        c[3].metric("Dropped ≥20% in other seasons", f"{drop[~dry].mean():.0%}")
        fig = go.Figure(go.Scattergl(
            x=x, y=y, mode="markers",
            marker=dict(size=7, color="#2a78d6", opacity=0.5, line=dict(width=1, color="rgba(255,255,255,0.8)")),
            customdata=rv[["DistrictName", "CropName", "Season", "Year"]],
            hovertemplate="<b>%{customdata[0]}</b> · %{customdata[1]}<br>%{customdata[2]} %{customdata[3]}"
                          "<br>Rain vs typical district: %{x:+.0f}%<br>RYI change: %{y:+.0f}%<extra></extra>"))
        fig.add_hline(y=0, line_color="rgba(128,128,128,0.5)", line_width=1)
        fig.add_vline(x=0, line_color="rgba(128,128,128,0.5)", line_width=1)
        fig.update_layout(height=380, margin=dict(l=0, r=0, t=10, b=0), showlegend=False,
                          xaxis=dict(title="Season rainfall vs typical district (relative %)", ticksuffix="%",
                                     gridcolor="rgba(128,128,128,0.15)", zeroline=False),
                          yaxis=dict(title="Change in RYI from the year before", ticksuffix="%",
                                     gridcolor="rgba(128,128,128,0.15)", zeroline=False),
                          plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
        by = lambda col: (rv.groupby(col).apply(lambda g: pd.Series({"Pearson r": round(g.ryi_dev.corr(g.rain_rel), 2),
                                                                      "Cell-seasons": len(g)}), include_groups=False)
                            .reset_index())
        t1, t2 = st.columns(2)
        t1.dataframe(by("CropName").rename(columns={"CropName": "Crop"}), hide_index=True, width="stretch")
        t2.dataframe(by("Season"), hide_index=True, width="stretch")
        strength = ("essentially no" if abs(r_all) < 0.1 else "a weak" if abs(r_all) < 0.3
                    else "a moderate" if abs(r_all) < 0.5 else "a strong")
        st.markdown(f"**Reading it:** there is **{strength} link** (r = {r_all:+.2f}) between a district being "
                    "relatively dry and its yield falling against the typical district that season. Rainfall "
                    "differences between districts don't explain which cells moved: soils, pests, inputs and survey "
                    "noise matter more at this scale. So Imboni uses rainfall only as one trigger for the irrigation "
                    "recommendation and never to move the yield estimate. The field-report weights for rain "
                    "problems are therefore an assumption too.")

with tabs[3]:
    section("The cleaned 2020–2024 files")
    st.caption("The first version of Imboni was built on cleaned, aggregated SAS files. They are now used only for "
               "tomatoes, which NISR doesn't publish separately.")
    cv = pd.read_csv(DATA / "out_cleaned_vs_official.csv")
    st.markdown("**Same years, same districts: do the cleaned files agree with the official tables?** "
                "Rank correlation of district positions (RYI), 2022–2024, Seasons A and B together.")
    c1, c2 = st.columns([1.2, 1])
    c1.dataframe(cv.pivot(index="CropName", columns="Year", values="rank_r").round(2).reset_index()
                 .rename(columns={"CropName": "Crop"}), hide_index=True, width="stretch")
    c2.markdown("Agreement is weak to moderate for beans, maize and Irish potatoes, and **none for cassava**. Median "
                "yields are also in different units (e.g. beans ≈ 6,200 vs 700 kg/ha). The official tables add up "
                "exactly to NISR's national totals, so Imboni treats them as the reference.")
    with st.expander("Table view (out_cleaned_vs_official.csv)"):
        st.dataframe(cv, hide_index=True, width="stretch")

    bt = load_backtest()
    flags = bt["low_district_flags"]
    st.markdown("**The cleaned-data baseline, for reference**")
    c = st.columns(4)
    c[0].metric("2024 backtest: error reduction", f"{bt['error_reduction_pct']}%",
                help=f"vs every district typical, mean abs. error in log RYI: {bt['mae_log_model']} vs "
                     f"{bt['mae_log_naive']}")
    c[1].metric("2024 backtest: recall", f"{flags['recall']:.0%}")
    for i, vs in enumerate(["2026A", "2026B"]):
        v = load_validation(vs)
        err = 100 * np.abs(np.log(v.predicted_RYI) - np.log(v.official_RYI)).mean()
        c[2 + i].metric(f"Official {vs}: bad cells caught", f"{int((v.actual_low & v.flagged).sum())} of "
                                                            f"{int(v.actual_low.sum())}",
                        help=f"Average error {err:.1f}% on {len(v)} cells (beans, cassava, Irish potatoes, maize)")
    st.caption("On official 2026 results this baseline had a larger error than assuming every district is typical, "
               "which is why the alerts no longer use it for the crops NISR publishes.")

with tabs[4]:
    section("Data limitations")
    b = load_baseline()
    st.markdown(f"""
    - **Official district figures are survey estimates.** About 25–68 sampled segments per district; yields come from
      the production farmers report, not crop cuts. Small districts and minor crops are the least precise.
    - **The baseline can't see a new shock.** It assumes a district repeats its last official position. Only field
      reports can show a season breaking the pattern.
    - **Seasons A and B only.** Season C (Jul–Aug, swamps and volcanic highlands) is published only in NISR's annual
      tables, for a few crops, and is left out.
    - **Tomatoes** rely on the cleaned 2020–2024 files ({int((b.CropName == 'Tomatoes').sum())} district-season cells),
      which don't match the official tables for the crops we could check. Treat tomato alerts as indicative only.
    - **Report weights are assumptions**, not estimated: there are no past field reports to fit them on.
    - **Simulated reports** are clearly labelled demo data and must not be interpreted as observations.
    - **EICV** consumption uses the 2020 round and covers only beans, cassava, Irish potatoes, maize and tomatoes.
      Food dependence for banana, paddy rice and sweet potato is unknown and set to neutral.
    - **Establishment Census** gives counts of cooperatives and food processors per district, not names or contacts.
      The cleaned file labels district code 28 as "Unknown District"; it is mapped to Kamonyi (NISR code 28).
    - **Storage:** reports are kept in SQLite. On Streamlit Community Cloud the disk resets when the app restarts,
      so real reports are lost unless downloaded; production use needs a hosted database.
    - **Rainfall:** CHIRPS v2.0 is satellite + station rainfall at ~5 km; small districts (e.g. Nyarugenge) cover only
      a few pixels. The latest season can be partial (only the months published so far).
    - **Boundaries:** geoBoundaries RWA ADM2 (2012 boundaries, CC BY 4.0).
    """)
