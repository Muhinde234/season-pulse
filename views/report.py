import streamlit as st

from core.data import CROPS, DISTRICTS, SEASONS, current_season
from core.db import RAIN_OPTIONS, SIM_COUNT, add_report, delete_simulated, get_reports, load_simulated

CONDITIONS = {1: "1 – Very poor (crop failing)", 2: "2 – Poor", 3: "3 – Average", 4: "4 – Good", 5: "5 – Excellent"}

st.title("📝 Field report")
st.caption("Extension officers and farmer promoters report what they see in the field. "
           "Reports shift the district's risk on the Alerts page.")

seasons = list(SEASONS)
with st.form("report", clear_on_submit=True):
    c1, c2, c3 = st.columns(3)
    district = c1.selectbox("District", DISTRICTS)
    crop = c2.selectbox("Crop", CROPS)
    season = c3.selectbox("Season", seasons, index=seasons.index(current_season()), format_func=SEASONS.get)
    condition = st.select_slider("Crop condition", options=list(CONDITIONS), value=3, format_func=CONDITIONS.get)
    c4, c5 = st.columns(2)
    pests = c4.radio("Pests or disease seen?", ["No", "Yes"], horizontal=True) == "Yes"
    rain = c5.selectbox("Rain problem", RAIN_OPTIONS)
    notes = st.text_area("Notes (optional)", max_chars=500)
    reporter = st.text_input("Your name or role (optional)", max_chars=80)
    if st.form_submit_button("Submit report", type="primary"):
        add_report(district, crop, season, condition, pests, rain, notes.strip(), reporter.strip())
        st.success(f"Saved: {crop} in {district}, condition {condition}.")

st.divider()
st.subheader("Demo data")
st.info("Simulated reports are **not real observations**. They are stored with a `SIMULATED` flag, "
        "labelled everywhere they appear, and can be removed at any time. Scenario: a dry spell in "
        "Eastern Province and a fall armyworm outbreak on maize in Western Province.", icon="🧪")
d1, d2, _ = st.columns([1, 1, 2])
if d1.button(f"Load {SIM_COUNT} simulated reports ({SEASONS[current_season()].split(' (')[0]})"):
    delete_simulated()  # keep it idempotent: reloading replaces, never doubles
    load_simulated(current_season())
    st.success(f"Loaded {SIM_COUNT} simulated reports.")
if d2.button("Remove simulated reports"):
    st.success(f"Removed {delete_simulated()} simulated reports.")

st.divider()
r = get_reports()
real, sim = int((r.is_simulated == 0).sum()), int(r.is_simulated.sum())
st.subheader(f"Recent reports · {real} real, {sim} simulated")
if r.empty:
    st.caption("No reports yet.")
else:
    st.dataframe(
        r.assign(source=r.is_simulated.map({0: "Real", 1: "🧪 SIMULATED"}),
                 pests=r.pests.map({0: "No", 1: "Yes"}), season=r.season.map(lambda s: SEASONS[s].split(" (")[0]))
         [["source", "created_at", "district", "crop", "season", "condition", "pests", "rain_problem", "notes"]]
         .rename(columns=str.capitalize).rename(columns={"Created_at": "Submitted", "Rain_problem": "Rain problem"}),
        hide_index=True, width="stretch", height=360)
