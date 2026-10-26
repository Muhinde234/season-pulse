"""Season Pulse - in-season crop early warning for Rwanda's 30 districts.

Run locally:  streamlit run app.py
"""
import streamlit as st

st.set_page_config(page_title="Season Pulse", page_icon="🌱", layout="wide")

pages = [
    st.Page("views/map.py", title="District map", icon="🗺️", default=True),
    st.Page("views/report.py", title="Field report", icon="📝"),
    st.Page("views/alerts.py", title="Alerts", icon="🚨"),
    st.Page("views/model.py", title="Model & limitations", icon="📊"),
]

with st.sidebar:
    st.markdown("### 🌱 Season Pulse")
    st.caption("In-season crop early warning · NISR Hackathon 2026")

st.navigation(pages).run()

st.sidebar.caption("Yields shown as **% vs typical district** (Relative Yield Index), never kg/ha. "
                   "Data: NISR SAS 2020–2024, EICV 2020, Establishment Census; boundaries © geoBoundaries (CC BY 4.0).")
