"""Season Pulse - in-season crop early warning for Rwanda's 30 districts.

Run locally:  streamlit run app.py
"""
import streamlit as st

from core.ui import apply_theme, sidebar_brand, sidebar_note

st.set_page_config(page_title="Season Pulse", page_icon="🌱", layout="wide")
apply_theme()

pages = {
    "Monitor": [
        st.Page("views/map.py", title="District Risk Map", icon=":material/map:", default=True),
        st.Page("views/alerts.py", title="Alerts & Recommended Actions", icon=":material/notifications_active:"),
    ],
    "Report": [
        st.Page("views/report.py", title="Submit Field Report", icon=":material/edit_note:"),
        st.Page("views/ussd.py", title="USSD prototype", icon=":material/dialpad:"),
    ],
    "About": [
        st.Page("views/model.py", title="Model & Data Quality", icon=":material/insights:"),
    ],
}

sidebar_brand()
st.navigation(pages).run()
sidebar_note()
