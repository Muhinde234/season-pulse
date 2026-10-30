import pandas as pd
import streamlit as st

from core.data import CROPS, SEASONS, current_season, fmt_pct, pct_vs_typical
from core.db import get_reports
from core.risk import DRY_PCT, HIGH, LEVELS, TRADITIONAL_PCT, WATCH, adjusted_table
from core.ui import badge, hero, section

hero("Alerts & Recommended Actions",
     f"Historical baseline adjusted by this season's field reports, ranked by risk and food dependence. "
     f"**High**: expected ≥{round((1 - HIGH) * 100)}% below the typical district · "
     f"**Watch**: ≥{round((1 - WATCH) * 100)}% below · **Normal**: otherwise.", eyebrow="Monitor · Alerts")

seasons = list(SEASONS)
c1, c2, c3 = st.columns([1, 2, 1])
season = c1.selectbox("Season", seasons, index=seasons.index(current_season()), format_func=SEASONS.get)
crops = c2.multiselect("Crops", CROPS, default=CROPS)
include_sim = c3.toggle("Include simulated reports", value=True)

reports = get_reports(season, include_simulated=include_sim)
t = adjusted_table(season, reports)
t = t[t.CropName.isin(crops)]

n_sim = int(reports.is_simulated.sum())
if n_sim:
    st.warning(f"🧪 {n_sim} of {len(reports)} reports this season are **SIMULATED** demo data. "
               "Alerts below are partly driven by them.")
elif reports.empty:
    st.info("No field reports for this season yet: alerts reflect the historical baseline only. "
            "Add reports on the Field report page.")

m = st.columns(4)
for col, lvl in zip(m, LEVELS):
    col.metric(f"{LEVELS[lvl][1]} {lvl}", int((t.level == lvl).sum()))
m[3].metric("Field reports used", len(reports))


def reasons(r) -> str:
    out = [f"historically {fmt_pct(r.baseline_RYI)} vs typical ({int(r.n_years)} yr)"]
    if pd.notna(r.rain_anom_pct):
        out.append(f"rain {r.rain_anom_pct:+.0f}% vs district average ({r.rain_period}"
                   f"{', partial season' if r.rain_partial else ''})")
    if pd.notna(r.traditional_pct):
        out.append(f"{r.traditional_pct:.0f}% of irrigated plots use traditional methods (SAS 2026 A)")
    if r.n_reports:
        bits = [f"avg condition {r.mean_condition:.1f}/5"]
        if r.rain_share:
            bits.append(f"{r.rain_share:.0%} report rain problems")
        if r.pest_share:
            bits.append(f"{r.pest_share:.0%} report pests")
        out.append(f"{int(r.n_reports)} report(s){' (🧪 ' + str(int(r.n_simulated)) + ' simulated)' if r.n_simulated else ''}: "
                   + ", ".join(bits))
    return " · ".join(out)


section("Top alerts", "highest risk first; equal risk → higher household food dependence first")
top = t[t.level != "Normal"].head(6)
if top.empty:
    st.success("No district-crop combinations at Watch or High level.")
for i in range(0, len(top), 3):
    cols = st.columns(3)
    for col, (_, r) in zip(cols, top.iloc[i:i + 3].iterrows()):
        with col.container(border=True, key=f"alert-{r.level.lower()}-{i}-{r.name}"):
            st.markdown(f'{badge(r.level)}<div class="sp-card-title">{r.DistrictName} · {r.CropName}</div>'
                        f'<div class="sp-card-sub">{r.Province}</div>'
                        f'<div class="sp-big">{fmt_pct(r.adjusted_RYI)} <small>expected vs typical district</small>'
                        f'</div>', unsafe_allow_html=True)
            st.caption(reasons(r))
            st.markdown(f"**Recommended action:** {r.action}")
            st.markdown(f'<div class="sp-chips"><span class="sp-chip">🤝 {int(r.cooperatives)} cooperatives</span>'
                        f'<span class="sp-chip">🏭 {int(r.food_processors)} food processors</span>'
                        f'<span class="sp-chip">🚢 {int(r.exporters)} exporters</span>'
                        f'<span class="sp-chip">🍲 {r.food_level} food dependence</span></div>',
                        unsafe_allow_html=True)

section("Full ranking", "by alert level, then shortfall × food dependence")
periods = t.rain_period.dropna()
rain_label = (periods.iloc[0] + (" (partial: months published so far)" if t.rain_partial.any() else "")
              if len(periods) else "this season (no rainfall data: run fetch_rainfall.py)")
table = t.assign(
    Level=t.level.map(lambda l: f"{LEVELS[l][1]} {l}"),
    Baseline=pct_vs_typical(t.baseline_RYI),
    Expected=pct_vs_typical(t.adjusted_RYI),
    Shift=(pct_vs_typical(t.adjusted_RYI) - pct_vs_typical(t.baseline_RYI)),
    Food=t.food_level,
)
st.dataframe(
    table[["Level", "DistrictName", "Province", "CropName", "Baseline", "n_reports", "Shift", "Expected", "Food",
           "priority", "action", "rain_anom_pct", "traditional_pct", "cooperatives", "food_processors", "exporters",
           "consumption_rwf_2020"]],
    hide_index=True, width="stretch", height=480,
    column_config={
        "DistrictName": "District", "CropName": "Crop",
        "action": st.column_config.TextColumn(
            "Recommended action", width="large",
            help=f"Rules: below typical + (rain problems reported, rainfall ≥{-DRY_PCT}% below the district "
                 f"average, or ≥{TRADITIONAL_PCT}% of irrigated plots on traditional methods) → small-scale irrigation · "
                 "persistently low (3+ yrs) with no rainfall problem → soil testing & fertility support · above "
                 "typical → post-harvest collection & storage · surplus (≥15% above typical) + cooperatives or food "
                 "processors at/above the median district → value addition · surplus + goods exporters at/above "
                 "the median district → export opportunity."),
        "Food": st.column_config.TextColumn(
            "Food dependence", help="District's EICV 2020 household consumption of this crop compared with the "
                                    "other districts: top third = High, middle = Medium, bottom = Low."),
        "priority": st.column_config.NumberColumn(
            "Priority", format="%.2f", help="Shortfall below typical × (0.5 + food dependence percentile). "
                                            "Orders rows within the same alert level."),
        "traditional_pct": st.column_config.NumberColumn(
            "Traditional irrigation", format="%.0f%%",
            help="SAS 2026 Season A Table 32: share of irrigated plots using traditional techniques "
                 "(the rest use surface, flood, drip, sprinkler or pivot irrigation)."),
        "rain_anom_pct": st.column_config.NumberColumn(
            "Rain vs district avg", format="%+.0f%%",
            help=f"CHIRPS rainfall for {rain_label} compared with the district's 2020–2024 average for the same months."),
        "exporters": st.column_config.NumberColumn("Goods exporters", format="%d"),
        "Baseline": st.column_config.NumberColumn("Baseline % vs typical", format="%+d%%"),
        "n_reports": st.column_config.NumberColumn("Reports", format="%d"),
        "Shift": st.column_config.NumberColumn("Shift from reports", format="%+d pts"),
        "Expected": st.column_config.NumberColumn("Expected % vs typical", format="%+d%%"),
        "cooperatives": st.column_config.NumberColumn("Cooperatives", format="%d"),
        "food_processors": st.column_config.NumberColumn("Food processors", format="%d"),
        "consumption_rwf_2020": st.column_config.NumberColumn(
            "Household consumption 2020 (RWF)", format="localized",
            help="EICV 2020 weighted household consumption value of this crop in the district: who is exposed "
                 "if supply drops."),
    },
)
st.download_button("Download ranking (CSV)", table.drop(columns=["baseline_logRYI", "baseline_log"]).to_csv(index=False),
                   file_name=f"season_pulse_alerts_{season}.csv", mime="text/csv")
st.caption("Cooperative, food processor and goods exporter counts come from the NISR Establishment Census and are "
           "district totals across all sectors: names and contacts are not in the published data. Recommended "
           "actions are simple rules, not calibrated advice.")
