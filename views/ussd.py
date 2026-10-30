"""USSD prototype: a farmer with a basic phone dials *XXX# and reports in Kinyarwanda, one screen at a time.

Nothing here talks to a telco. A real service would sit behind a USSD gateway (e.g. Africa's Talking) that
POSTs each reply to an endpoint running the same state machine. Submissions are saved to the normal reports
table with source = "USSD (simulated)".
"""
import streamlit as st

from core.data import CROPS, PROVINCES, current_season
from core.db import RAIN_OPTIONS, add_report, get_reports
from core.i18n import CONDITION, CROP, RAIN, YES_NO, lang_toggle
from core.ui import hero, section

CODE = "*XXX#"
MAX_CHARS = 160  # typical USSD screen limit (182 on some networks)
SOURCE = "USSD (simulated)"

PROVINCE = {  # short names that fit on a USSD line
    "Kigali City": {"en": "Kigali", "rw": "Kigali"},
    "Southern Province": {"en": "South", "rw": "Amajyepfo"},
    "Western Province": {"en": "West", "rw": "Iburengerazuba"},
    "Northern Province": {"en": "North", "rw": "Amajyaruguru"},
    "Eastern Province": {"en": "East", "rw": "Iburasirazuba"},
}
UI = {
    "welcome": {"en": "Season Pulse\n1. Report my crop\n2. Exit",
                "rw": "Season Pulse\n1. Tanga raporo y'igihingwa\n2. Sohoka"},
    "province": {"en": "Province:", "rw": "Intara:"},
    "district": {"en": "District:", "rw": "Akarere:"},
    "crop": {"en": "Crop:", "rw": "Igihingwa:"},
    "condition": {"en": "How does the crop look?", "rw": "Igihingwa kimeze gute?"},
    "pests": {"en": "Pests or disease?", "rw": "Ibyonnyi cyangwa indwara?"},
    "rain": {"en": "Rain:", "rw": "Imvura:"},
    "confirm": {"en": "Confirm:\n{crop}, {district}\nState {condition}/5, pests {pests}\n{rain}\n1. Send\n2. Cancel",
                "rw": "Emeza:\n{crop}, {district}\nUko kimeze {condition}/5, ibyonnyi {pests}\n{rain}\n1. Ohereza\n2. Hagarika"},
    "done": {"en": "Thank you! Your report was received.", "rw": "Murakoze! Raporo yanyu yakiriwe."},
    "bye": {"en": "Goodbye.", "rw": "Murabeho."},
    "cancelled": {"en": "Report cancelled.", "rw": "Raporo yahagaritswe."},
    "invalid": {"en": "Invalid choice.", "rw": "Igisubizo ntikimenyekanye."},
    "back": {"en": "0. Back", "rw": "0. Subira inyuma"},
    "dial_hint": {"en": f"Dial {CODE} and press Call", "rw": f"Kanda {CODE} hanyuma uhamagare"},
}
STEPS = ["province", "district", "crop", "condition", "pests", "rain", "confirm"]


def options(step: str, a: dict, lang: str) -> list[tuple[str, str]]:
    """(stored value, label) pairs for a menu step, in the order they're numbered on screen."""
    if step == "province":
        return [(p, PROVINCE[p][lang]) for p in PROVINCES]
    if step == "district":
        return [(d, d) for d in PROVINCES[a["province"]]]
    if step == "crop":
        return [(c, CROP[c][lang]) for c in CROPS]
    if step == "condition":
        return [(c, CONDITION[c][lang].split(" (")[0]) for c in CONDITION]
    if step == "pests":
        return [(True, YES_NO[True][lang]), (False, YES_NO[False][lang])]
    if step == "rain":
        return [(r, RAIN[r][lang]) for r in RAIN_OPTIONS]
    return []


def screen(s: dict, lang: str) -> str:
    step, a = s["step"], s["answers"]
    if step == "welcome":
        return UI["welcome"][lang]
    if step == "confirm":
        return UI["confirm"][lang].format(crop=CROP[a["crop"]][lang], district=a["district"],
                                          condition=a["condition"], pests=YES_NO[a["pests"]][lang],
                                          rain=RAIN[a["rain"]][lang])
    lines = [UI[step][lang]] + [f"{i}. {label}" for i, (_, label) in enumerate(options(step, a, lang), 1)]
    return "\n".join(lines + [UI["back"][lang]])


def reply(s: dict, text: str, lang: str) -> None:
    """Advance the USSD session state machine by one user reply."""
    step, text = s["step"], text.strip()
    s["error"] = False
    if step == "welcome":
        if text == "1":
            s["step"] = "province"
        elif text == "2":
            s.update(step="end", message=UI["bye"][lang])
        else:
            s["error"] = True
        return
    if step == "confirm":
        if text == "1":
            a = s["answers"]
            add_report(a["district"], a["crop"], current_season(), a["condition"], a["pests"], a["rain"],
                       notes=f"Submitted via {CODE} prototype", reporter="USSD", source=SOURCE)
            s.update(step="end", message=UI["done"][lang])
        elif text == "2":
            s.update(step="end", message=UI["cancelled"][lang])
        elif text == "0":
            s["step"] = "rain"
        else:
            s["error"] = True
        return
    if text == "0":  # back one screen
        i = STEPS.index(step)
        s["step"] = STEPS[i - 1] if i else "welcome"
        return
    opts = options(step, s["answers"], lang)
    if text.isdigit() and 1 <= int(text) <= len(opts):
        s["answers"][step] = opts[int(text) - 1][0]
        s["step"] = STEPS[STEPS.index(step) + 1]
    else:
        s["error"] = True


def new_session() -> dict:
    return {"step": "dial", "answers": {}, "error": False, "message": ""}


st.markdown("""
<style>
.st-key-phone { max-width: 340px; margin: 0 auto; background: #1f1f1f; border-radius: 28px !important;
                padding: 18px 16px 22px !important; border: none !important; }
.st-key-phone p, .st-key-phone label p { color: #e8e8e8; }
.ussd-screen { background: #c8d7b4; color: #10220a; font-family: "Courier New", monospace; font-size: 1.05rem;
               line-height: 1.35; white-space: pre-wrap; border-radius: 6px; padding: 12px 14px; min-height: 210px; }
.ussd-meta { color: #9a9a9a; font-size: 0.75rem; text-align: right; margin-top: 4px; }
</style>
""", unsafe_allow_html=True)

hero("USSD prototype", "What a farmer without a smartphone sees after dialling a short code, one screen at a "
     "time, in Kinyarwanda by default.", eyebrow="Report · Basic phones")
st.warning(f"**PROTOTYPE, not a live service.** This page *simulates* what a farmer without a smartphone would see "
           f"after dialling {CODE} (placeholder code). No phone network is involved. Reports sent here are saved "
           f"with source **“{SOURCE}”** so they can be told apart from web-form reports.", icon="🧪")

lang = lang_toggle(default="rw")
s = st.session_state.setdefault("ussd", new_session())

with st.container(key="phone"):
    if s["step"] == "dial":
        text = UI["dial_hint"][lang]
    elif s["step"] == "end":
        text = s["message"]
    else:
        text = (UI["invalid"][lang] + "\n" if s["error"] else "") + screen(s, lang)
    st.markdown(f'<div class="ussd-screen">{text}</div>'
                f'<div class="ussd-meta">{len(text)}/{MAX_CHARS} chars</div>', unsafe_allow_html=True)
    if len(text) > MAX_CHARS:
        st.caption(f"⚠️ Screen longer than {MAX_CHARS} characters: would be cut on some networks.")

    with st.form("ussd_input", clear_on_submit=True, border=False):
        if s["step"] in ("dial", "end"):
            entry = st.text_input("Dial", value=CODE if s["step"] == "dial" else "", label_visibility="collapsed")
            pressed = st.form_submit_button("📞 Call" if s["step"] == "dial" else "📞 Dial again", width="stretch",
                                            type="primary")
        else:
            entry = st.text_input("Reply", placeholder="1, 2, 3…", label_visibility="collapsed")
            c1, c2 = st.columns(2)
            pressed = c1.form_submit_button("Send", width="stretch", type="primary")
            if c2.form_submit_button("Cancel", width="stretch"):
                st.session_state.ussd = new_session()
                st.rerun()
    if pressed:
        if s["step"] in ("dial", "end"):
            if entry.strip() == CODE or s["step"] == "end":
                st.session_state.ussd = s = new_session() | {"step": "welcome"}
        else:
            reply(s, entry, lang)
        st.rerun()

st.divider()
section("Reports received via USSD")
r = get_reports()
r = r[r.source == SOURCE]
if r.empty:
    st.caption("None yet. Dial the code above and complete a report.")
else:
    st.dataframe(r[["created_at", "district", "crop", "season", "condition", "pests", "rain_problem"]]
                 .assign(pests=r.pests.map({0: "No", 1: "Yes"}))
                 .rename(columns={"created_at": "Submitted", "district": "District", "crop": "Crop",
                                  "season": "Season", "condition": "Condition", "pests": "Pests",
                                  "rain_problem": "Rain problem"}),
                 hide_index=True, width="stretch")
st.caption("These reports feed the Map and Alerts pages like any other field report. In production, a USSD "
           "gateway would forward each reply to a server running this same menu logic.")
