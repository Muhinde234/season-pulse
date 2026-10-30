"""English / Kinyarwanda labels for the farmer-facing screens (field report form, USSD prototype).

Stored values stay in English (crop names, rain options) so the database and risk model are unchanged;
only what the user sees is translated. Kinyarwanda wording should be reviewed by a native speaker
(e.g. a RAB extension officer) before real use.
"""
import streamlit as st

LANGS = {"en": "English", "rw": "Kinyarwanda"}

CROP = {
    "Beans": {"en": "Beans", "rw": "Ibishyimbo"},
    "Cassava": {"en": "Cassava", "rw": "Imyumbati"},
    "Irish potatoes": {"en": "Irish potatoes", "rw": "Ibirayi"},
    "Maize": {"en": "Maize", "rw": "Ibigori"},
    "Tomatoes": {"en": "Tomatoes", "rw": "Inyanya"},
}
CONDITION = {
    1: {"en": "Very poor (crop failing)", "rw": "Kibi cyane (kirimo kwangirika)"},
    2: {"en": "Poor", "rw": "Kibi"},
    3: {"en": "Average", "rw": "Biringaniye"},
    4: {"en": "Good", "rw": "Byiza"},
    5: {"en": "Excellent", "rw": "Byiza cyane"},
}
RAIN = {
    "None": {"en": "No problem", "rw": "Nta kibazo"},
    "Too little rain / dry spell": {"en": "Too little rain / dry spell", "rw": "Imvura nke / izuba ryinshi"},
    "Too much rain / flooding": {"en": "Too much rain / flooding", "rw": "Imvura nyinshi / imyuzure"},
    "Late onset of rains": {"en": "Rains came late", "rw": "Imvura yatinze kugwa"},
}
YES_NO = {True: {"en": "Yes", "rw": "Yego"}, False: {"en": "No", "rw": "Oya"}}
SEASON = {
    "SeasonA": {"en": "Season A (Sep–Feb)", "rw": "Igihembwe A (Nzeri–Gashyantare)"},
    "SeasonB": {"en": "Season B (Mar–Jun)", "rw": "Igihembwe B (Werurwe–Kamena)"},
    "SeasonC": {"en": "Season C (Jul–Aug)", "rw": "Igihembwe C (Nyakanga–Kanama)"},
}

TEXT = {
    "language": {"en": "Language", "rw": "Ururimi"},
    "title": {"en": "Submit Field Report", "rw": "Tanga raporo yo mu murima"},
    "intro": {"en": "Tell us how the crop looks in your area. Five quick questions.",
              "rw": "Tubwire uko igihingwa kimeze iwanyu. Ibibazo bitanu byihuse."},
    "district": {"en": "District", "rw": "Akarere"},
    "crop": {"en": "Crop", "rw": "Igihingwa"},
    "condition": {"en": "How does the crop look?", "rw": "Igihingwa kimeze gute?"},
    "pests": {"en": "Pests or disease seen?", "rw": "Hari ibyonnyi cyangwa indwara mwabonye?"},
    "rain": {"en": "Rain problem", "rw": "Ikibazo cy'imvura"},
    "more": {"en": "More details (optional)", "rw": "Ibindi bisobanuro (si ngombwa)"},
    "season": {"en": "Season", "rw": "Igihembwe"},
    "notes": {"en": "Notes", "rw": "Ibisobanuro"},
    "reporter": {"en": "Your name or role", "rw": "Izina ryawe cyangwa icyo ukora"},
    "submit": {"en": "Send report", "rw": "Ohereza raporo"},
    "saved": {"en": "Thank you! Report saved: {crop} in {district}, condition {condition}/5.",
              "rw": "Murakoze! Raporo yakiriwe: {crop} mu karere ka {district}, uko kimeze {condition}/5."},
    "choose": {"en": "Choose…", "rw": "Hitamo…"},
    "missing": {"en": "Please answer every question.", "rw": "Subiza ibibazo byose, ubishoboye."},
}


def lang_toggle(default: str = "en") -> str:
    """English/Kinyarwanda switch. The choice lives in st.session_state.lang so it survives page changes
    (Streamlit drops a widget's own state when you navigate away from its page)."""
    st.session_state.setdefault("lang", default)
    st.session_state["lang_widget"] = st.session_state.lang
    st.radio(f"{TEXT['language']['en']} / {TEXT['language']['rw']}", list(LANGS), format_func=LANGS.get,
             horizontal=True, key="lang_widget",
             on_change=lambda: st.session_state.update(lang=st.session_state.lang_widget))
    return st.session_state.lang


def t(key: str, lang: str, **kw) -> str:
    return TEXT[key][lang].format(**kw)
