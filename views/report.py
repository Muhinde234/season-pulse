import streamlit as st

from core.data import CROPS, DISTRICTS, SEASONS, current_season
from core.db import RAIN_OPTIONS, SIM_COUNT, add_report, delete_simulated, get_reports, load_simulated
from core.i18n import CONDITION, CROP, RAIN, SEASON, YES_NO, lang_toggle, t
from core.ui import hero

# Mobile-first: one narrow column, large text and tap targets (Streamlit stacks everything on a phone anyway)
st.markdown("""
<style>
[data-testid="stForm"] { max-width: 560px; margin: 0 auto; }
[data-testid="stForm"] [data-testid="stWidgetLabel"] p { font-size: 1.15rem; font-weight: 600; }
[data-testid="stForm"] [data-testid="stRadio"] label { padding: 0.45rem 0; }
[data-testid="stForm"] [data-testid="stRadio"] label p,
[data-testid="stForm"] [data-baseweb="select"] div { font-size: 1.1rem; }
[data-testid="stForm"] [data-baseweb="select"] > div { min-height: 3rem; }
[data-testid="stForm"] button[kind="primaryFormSubmit"] { min-height: 3.4rem; }
[data-testid="stForm"] button[kind="primaryFormSubmit"] p { font-size: 1.2rem; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

lang = lang_toggle()
hero(t("title", lang), t("intro", lang), eyebrow="Report · Web form")

seasons = list(SEASONS)
with st.form("report"):
    district = st.selectbox(t("district", lang), DISTRICTS, index=None, placeholder=t("choose", lang))
    crop = st.radio(t("crop", lang), CROPS, index=None, format_func=lambda c: CROP[c][lang])
    condition = st.radio(t("condition", lang), list(CONDITION), index=None,
                         format_func=lambda c: f"{c} – {CONDITION[c][lang]}")
    pests = st.radio(t("pests", lang), [False, True], index=None, horizontal=True,
                     format_func=lambda v: YES_NO[v][lang])
    rain = st.radio(t("rain", lang), RAIN_OPTIONS, index=None, format_func=lambda r: RAIN[r][lang])
    with st.expander(t("more", lang)):
        season = st.selectbox(t("season", lang), seasons, index=seasons.index(current_season()),
                              format_func=lambda s: SEASON[s][lang])
        notes = st.text_area(t("notes", lang), max_chars=500)
        reporter = st.text_input(t("reporter", lang), max_chars=80)
    if st.form_submit_button(t("submit", lang), type="primary", width="stretch"):
        if None in (district, crop, condition, pests, rain):
            st.error(t("missing", lang))
        else:
            add_report(district, crop, season, condition, pests, rain, notes.strip(), reporter.strip())
            st.success(t("saved", lang, crop=CROP[crop][lang], district=district, condition=condition))

st.divider()
with st.expander("Demo data and recent reports (for organisers)"):
    st.info("Simulated reports are **not real observations**. They are stored with a `SIMULATED` flag, "
            "labelled everywhere they appear, and can be removed at any time. Scenario: a dry spell in "
            "Eastern Province and a fall armyworm outbreak on maize in Western Province.", icon="🧪")
    d1, d2 = st.columns(2)
    if d1.button(f"Load {SIM_COUNT} simulated reports ({SEASONS[current_season()].split(' (')[0]})"):
        delete_simulated()  # keep it idempotent: reloading replaces, never doubles
        load_simulated(current_season())
        st.success(f"Loaded {SIM_COUNT} simulated reports.")
    if d2.button("Remove simulated reports"):
        st.success(f"Removed {delete_simulated()} simulated reports.")

    r = get_reports()
    real, sim = int((r.is_simulated == 0).sum()), int(r.is_simulated.sum())
    st.markdown(f"**Recent reports · {real} real, {sim} simulated**")
    if r.empty:
        st.caption("No reports yet.")
    else:
        st.dataframe(
            r.assign(source=r.source.where(r.is_simulated == 0, "🧪 SIMULATED"),
                     pests=r.pests.map({0: "No", 1: "Yes"}), season=r.season.map(lambda s: SEASONS[s].split(" (")[0]))
             [["source", "created_at", "district", "crop", "season", "condition", "pests", "rain_problem", "notes"]]
             .rename(columns=str.capitalize).rename(columns={"Created_at": "Submitted", "Rain_problem": "Rain problem"}),
            hide_index=True, width="stretch", height=360)
