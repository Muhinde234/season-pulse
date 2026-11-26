import html

import streamlit as st

from core.data import CROPS, DISTRICTS, SEASONS, current_season, fmt_pct
from core.db import RAIN_OPTIONS, SIM_COUNT, add_report, delete_simulated, get_reports, load_simulated
from core.i18n import CONDITION, CROP, RAIN, SEASON, YES_NO, lang_toggle, t
from core.risk import season_baseline
from core.ui import CROP_IC as CROP_ICON, hero, icon
CONDITION_COLOR = {1: "#dc2626", 2: "#ea580c", 3: "#ca8a04", 4: "#16a34a", 5: "#15803d"}

# The banner comes first (flush with the top), so it reads the language chosen on the previous run
lang = st.session_state.get("lang", "en")
hero(t("title", lang), t("intro", lang), eyebrow="Report · Web form", ic="edit_note",
     meta=[("clock", "≈1 min"), ("languages", "Kinyarwanda · English")])
note_col, lc = st.columns([3, 1], vertical_alignment="center")
with lc:
    lang = lang_toggle()
note_col.markdown(
    f'<div class="sp-note sp-note-info">{icon("science")}<span><b>Prototype:</b> this form works, but it has not '
    "been tested with real farmers yet. A pilot in 2–3 districts is the first step on our roadmap. Until then, "
    "Imboni's alerts come from NISR's official results.</span></div>", unsafe_allow_html=True)

# Each successful submit bumps the generation so every widget starts empty again
gen = st.session_state.setdefault("rep_gen", 0)
if msg := st.session_state.pop("rep_saved", None):
    st.toast(msg, icon=":material/check_circle:")


def step(n: int, label: str) -> None:
    st.markdown(f'<div class="sp-step"><b>{n}</b><span>{html.escape(label)}</span></div>', unsafe_allow_html=True)


left, right = st.columns([1.55, 1], gap="large")
with left.container(key="rep_card"):
    step(1, t("where", lang))
    district = st.selectbox(t("district", lang), DISTRICTS, index=None, placeholder=t("choose", lang),
                            key=f"r_district_{gen}")
    crop = st.pills(t("crop", lang), CROPS, key=f"r_crop_{gen}", format_func=lambda c: CROP[c][lang],
                    selection_mode="single")

    step(2, t("looks", lang))
    condition = st.pills(t("condition", lang), list(CONDITION), key=f"r_cond_{gen}", selection_mode="single",
                         format_func=lambda c: f"{c} · {CONDITION[c][lang].split(' (')[0]}")

    step(3, t("problems", lang))
    pests = st.segmented_control(t("pests", lang), [False, True], key=f"r_pests_{gen}",
                                 format_func=lambda v: YES_NO[v][lang])
    rain = st.pills(t("rain", lang), RAIN_OPTIONS, key=f"r_rain_{gen}", selection_mode="single",
                    format_func=lambda r: RAIN[r][lang])

    with st.expander(t("more", lang), icon=":material/tune:"):
        seasons = list(SEASONS)
        season = st.selectbox(t("season", lang), seasons, index=seasons.index(current_season()),
                              format_func=lambda s: SEASON[s][lang], key=f"r_season_{gen}")
        notes = st.text_area(t("notes", lang), max_chars=500, key=f"r_notes_{gen}")
        reporter = st.text_input(t("reporter", lang), max_chars=80, key=f"r_reporter_{gen}")

    answers = [district, crop, condition, pests, rain]
    if st.button(t("submit", lang), type="primary", width="stretch", icon=":material/send:"):
        if any(a is None for a in answers):
            st.error(t("missing", lang), icon=":material/error:")
        else:
            add_report(district, crop, season, condition, pests, rain, notes.strip(), reporter.strip())
            st.session_state.rep_saved = t("saved", lang, crop=CROP[crop][lang], district=district,
                                           condition=condition)
            st.session_state.rep_gen = gen + 1
            st.rerun()

# ---------- live summary ----------
done = sum(a is not None for a in answers)
rows = [
    ("location_on", t("district", lang), district),
    (CROP_ICON.get(crop, "eco"), t("crop", lang), CROP[crop][lang] if crop else None),
    ("monitor_heart", t("looks", lang), f"{condition}/5 · {CONDITION[condition][lang].split(' (')[0]}"
     if condition else None),
    ("bug_report", t("pests", lang).rstrip("?"), YES_NO[pests][lang] if pests is not None else None),
    ("rainy", t("rain", lang), RAIN[rain][lang] if rain else None),
]
body = "".join(
    f'<div class="sp-sum-row{"" if v is not None else " todo"}">{icon(ic)}<span>{html.escape(k)}</span>'
    f'<b>{html.escape(str(v)) if v is not None else "—"}</b></div>' for ic, k, v in rows)
ctx = ""
if district and crop:
    b = season_baseline(season)
    cell = b[(b.DistrictName == district) & (b.CropName == crop)]
    n_here = len(get_reports(season).query("district == @district and crop == @crop"))
    if len(cell):
        ryi = float(cell.baseline_RYI.iloc[0])
        color = "#dc2626" if ryi <= 0.85 else "#16a34a" if ryi >= 1 else "#ca8a04"
        ctx = (f'<div class="sp-ctx" style="--c:{color}">{icon("history")}<div><b>{fmt_pct(ryi)}</b> '
               f'{html.escape(t("vs_typical", lang))}<br>'
               f'{html.escape(t("reports_here", lang, n=n_here) if n_here else t("no_reports_here", lang))}</div></div>')
right.markdown(f'<div class="sp-sum"><div class="sp-sum-h"><span>{icon("assignment")} {html.escape(t("summary", lang))}</span>'
               f'<small>{html.escape(t("answered", lang, n=done) if done else t("five_q", lang))}</small></div>'
               f'<div class="sp-sum-bar"><i style="width:{done * 20}%"></i></div>{body}{ctx}</div>',
               unsafe_allow_html=True)

# ---------- organisers ----------
st.markdown("")
with st.expander("Organisers: demo data and recent reports", icon=":material/admin_panel_settings:"):
    st.caption("Simulated reports are flagged and labelled everywhere. Scenario: dry spell in the East, "
               "fall armyworm on maize in the West.")
    d1, d2 = st.columns(2)
    if d1.button(f"Load {SIM_COUNT} simulated reports", icon=":material/science:", width="stretch"):
        delete_simulated()  # keep it idempotent: reloading replaces, never doubles
        load_simulated(current_season())
        st.toast(f"Loaded {SIM_COUNT} simulated reports", icon=":material/science:")
    if d2.button("Remove simulated reports", icon=":material/delete:", width="stretch"):
        st.toast(f"Removed {delete_simulated()} simulated reports", icon=":material/delete:")

    r = get_reports()
    real, sim = int((r.is_simulated == 0).sum()), int(r.is_simulated.sum())
    st.markdown(f"**Recent reports** · {real} real · {sim} simulated")
    st.warning("Prototype storage: reports are saved in a SQLite file on the app server. On Streamlit Community "
               "Cloud that file is wiped whenever the app restarts, so download real reports regularly. A real "
               "deployment needs a hosted database.", icon=":material/database:")
    if not r.empty:
        st.dataframe(
            r.assign(source=r.source.where(r.is_simulated == 0, "SIMULATED"),
                     pests=r.pests.map({0: "No", 1: "Yes"}),
                     season=r.season.map(lambda s: SEASONS.get(s, s).split(" (")[0]))
             [["source", "created_at", "district", "crop", "season", "condition", "pests", "rain_problem", "notes"]]
             .rename(columns=str.capitalize).rename(columns={"Created_at": "Submitted", "Rain_problem": "Rain problem"}),
            hide_index=True, width="stretch", height=320)
        st.download_button("Download all reports (CSV)", r.to_csv(index=False), file_name="imboni_field_reports.csv",
                           mime="text/csv", icon=":material/download:")
