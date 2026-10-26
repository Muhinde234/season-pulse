import streamlit as st

from core.data import CROPS, SEASONS, current_season, fmt_pct, pct_vs_typical
from core.db import get_reports
from core.risk import HIGH, LEVELS, WATCH, adjusted_table

st.title("🚨 Alerts")
st.caption(f"Historical baseline adjusted by this season's field reports, ranked by risk. "
           f"🔴 **High**: expected ≥{round((1 - HIGH) * 100)}% below typical district · "
           f"🟠 **Watch**: ≥{round((1 - WATCH) * 100)}% below · 🟢 **Normal**.")

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
    if r.n_reports:
        bits = [f"avg condition {r.mean_condition:.1f}/5"]
        if r.rain_share:
            bits.append(f"{r.rain_share:.0%} report rain problems")
        if r.pest_share:
            bits.append(f"{r.pest_share:.0%} report pests")
        out.append(f"{int(r.n_reports)} report(s){' (🧪 ' + str(int(r.n_simulated)) + ' simulated)' if r.n_simulated else ''}: "
                   + ", ".join(bits))
    return " · ".join(out)


st.subheader("Top alerts")
top = t[t.level != "Normal"].head(6)
if top.empty:
    st.success("No district-crop combinations at Watch or High level.")
for i in range(0, len(top), 3):
    cols = st.columns(3)
    for col, (_, r) in zip(cols, top.iloc[i:i + 3].iterrows()):
        with col.container(border=True):
            st.markdown(f"**{LEVELS[r.level][1]} {r.level} · {r.DistrictName}, {r.CropName}**")
            st.markdown(f"Expected **{fmt_pct(r.adjusted_RYI)}** vs typical district")
            st.caption(reasons(r))
            st.markdown(f"🤝 **{int(r.cooperatives)}** cooperatives · 🏭 **{int(r.food_processors)}** food processors "
                        f"in {r.DistrictName}")

st.subheader("Full ranking")
table = t.assign(
    Level=t.level.map(lambda l: f"{LEVELS[l][1]} {l}"),
    Baseline=pct_vs_typical(t.baseline_RYI),
    Expected=pct_vs_typical(t.adjusted_RYI),
    Shift=(pct_vs_typical(t.adjusted_RYI) - pct_vs_typical(t.baseline_RYI)),
)
st.dataframe(
    table[["Level", "DistrictName", "Province", "CropName", "Baseline", "n_reports", "Shift", "Expected",
           "cooperatives", "food_processors", "consumption_rwf_2020"]],
    hide_index=True, width="stretch", height=480,
    column_config={
        "DistrictName": "District", "CropName": "Crop",
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
st.caption("Cooperative and food processor counts come from the NISR Establishment Census and are district "
           "totals across all sectors: names and contacts are not in the published data.")
