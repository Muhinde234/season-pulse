"""Imboni - in-season crop early warning for Rwanda's 30 districts.

Run locally:  streamlit run streamlit_app.py
"""
from pathlib import Path

import streamlit as st

from core.ui import apply_theme, footer, sidebar_brand, sidebar_note

st.set_page_config(page_title="Imboni", page_icon=str(Path(__file__).parent / "assets" / "imboni_icon.png"),
                   layout="wide")
apply_theme()

pages = {
    "Monitor": [
        st.Page("views/home.py", title="Overview", icon=":material/dashboard:", default=True),
        st.Page("views/map.py", title="District Risk Map", icon=":material/map:"),
        st.Page("views/alerts.py", title="Alerts & Recommended Actions", icon=":material/notifications_active:"),
        st.Page("views/district.py", title="District Profile", icon=":material/location_city:"),
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
footer()
sidebar_note()
