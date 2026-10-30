"""Shared look and feel: global CSS, page header, status badges.

Colours are semi-transparent overlays where possible so the same CSS reads well in Streamlit's light and
dark themes. Brand green matches primaryColor in .streamlit/config.toml.
"""
import html
from pathlib import Path

import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

ASSETS = Path(__file__).resolve().parent.parent / "assets"
BRAND = "#16a34a"
LEVEL_STYLE = {  # accent colour per alert level; icon + text always accompany the colour
    "High": "#dc2626",
    "Watch": "#ea8a0c",
    "Normal": "#16a34a",
}

CSS = """
<style>
/* ---------- layout ---------- */
.block-container { padding-top: 2.2rem; padding-bottom: 4rem; max-width: 1280px; }
h1, h2, h3 { letter-spacing: -0.02em; }
[data-testid="stHeader"] { background: transparent; }

/* ---------- hero header ---------- */
.sp-hero { position: relative; overflow: hidden; border-radius: 18px; padding: 1.6rem 1.8rem 1.5rem;
           margin-bottom: 1.4rem; color: #f2fbf5;
           background: radial-gradient(120% 140% at 100% 0%, #22c55e55 0%, transparent 55%),
                       linear-gradient(135deg, #0c2a1e 0%, #14532d 60%, #166534 100%);
           box-shadow: 0 10px 30px -12px rgba(12, 42, 30, 0.55); }
.sp-hero::after { content: ""; position: absolute; right: -40px; bottom: -60px; width: 220px; height: 220px;
                  border-radius: 50%; border: 36px solid rgba(255,255,255,0.05); }
.sp-hero .sp-eyebrow { display: inline-flex; align-items: center; gap: .4rem; font-size: .72rem; font-weight: 700;
                       letter-spacing: .12em; text-transform: uppercase; color: #86efac;
                       background: rgba(134,239,172,.12); border: 1px solid rgba(134,239,172,.25);
                       padding: .22rem .6rem; border-radius: 999px; }
.sp-hero h1 { color: #ffffff; font-size: 2.05rem; font-weight: 800; margin: .55rem 0 .3rem; padding: 0;
              line-height: 1.15; }
.sp-hero p { color: rgba(242,251,245,.82); font-size: 1rem; margin: 0; max-width: 820px; line-height: 1.5; }
.sp-hero p strong { color: #fff; }

/* ---------- section headings ---------- */
.sp-section { display: flex; align-items: baseline; gap: .6rem; margin: 1.6rem 0 .6rem; }
.sp-section .sp-h { font-size: 1.3rem; font-weight: 750; letter-spacing: -0.02em; line-height: 1.3; }
.sp-section span { font-size: .85rem; opacity: .6; }

/* ---------- metrics as cards ---------- */
[data-testid="stMetric"] { background: rgba(22,163,74,0.04); border: 1px solid rgba(128,128,128,0.18);
                           border-radius: 14px; padding: .9rem 1.1rem; height: 100%;
                           transition: transform .15s ease, box-shadow .15s ease; }
[data-testid="stMetric"]:hover { transform: translateY(-2px); box-shadow: 0 8px 22px -14px rgba(0,0,0,.45); }
[data-testid="stMetricLabel"] p { font-size: .84rem; font-weight: 600; opacity: .72; }
[data-testid="stMetricLabel"], [data-testid="stMetricLabel"] * { white-space: normal !important;
                                                                  overflow: visible !important;
                                                                  text-overflow: clip !important; }
[data-testid="stMetricValue"] { font-size: 1.9rem; font-weight: 800; letter-spacing: -0.02em; }

/* ---------- bordered containers / cards ---------- */
[data-testid="stVerticalBlockBorderWrapper"] { border-radius: 14px; }
[class*="st-key-alert-"] { border-left: 5px solid var(--sp-accent) !important; border-radius: 14px !important;
                          background: linear-gradient(90deg, color-mix(in srgb, var(--sp-accent) 9%, transparent),
                                      transparent 55%);
                          transition: transform .15s ease, box-shadow .15s ease; }
[class*="st-key-alert-"]:hover { transform: translateY(-2px); box-shadow: 0 10px 24px -16px rgba(0,0,0,.5); }
[class*="st-key-alert-high"] { --sp-accent: #dc2626; }
[class*="st-key-alert-watch"] { --sp-accent: #ea8a0c; }
[class*="st-key-alert-normal"] { --sp-accent: #16a34a; }
.sp-card-title { font-size: 1.08rem; font-weight: 700; margin: .35rem 0 .1rem; line-height: 1.3; }
.sp-card-sub { font-size: .82rem; opacity: .65; margin-bottom: .5rem; }
.sp-big { font-size: 1.7rem; font-weight: 800; letter-spacing: -0.02em; line-height: 1.1; }
.sp-big small { font-size: .8rem; font-weight: 500; opacity: .65; letter-spacing: 0; }
.sp-chips { display: flex; flex-wrap: wrap; gap: .35rem; margin-top: .5rem; }
.sp-chip { font-size: .76rem; font-weight: 600; padding: .2rem .55rem; border-radius: 999px;
           background: rgba(128,128,128,.12); border: 1px solid rgba(128,128,128,.18); white-space: nowrap; }

/* ---------- badges ---------- */
.sp-badge { display: inline-flex; align-items: center; gap: .35rem; font-size: .72rem; font-weight: 700;
            letter-spacing: .06em; text-transform: uppercase; padding: .2rem .6rem; border-radius: 999px;
            color: var(--c); background: color-mix(in srgb, var(--c) 14%, transparent);
            border: 1px solid color-mix(in srgb, var(--c) 35%, transparent); }
.sp-badge::before { content: ""; width: .5rem; height: .5rem; border-radius: 50%; background: var(--c); }

/* ---------- buttons, inputs, tables ---------- */
.stButton button, .stDownloadButton button, [data-testid="stFormSubmitButton"] button {
    font-weight: 600; border-radius: 10px; transition: transform .1s ease, box-shadow .15s ease; }
.stButton button:hover, .stDownloadButton button:hover, [data-testid="stFormSubmitButton"] button:hover {
    transform: translateY(-1px); box-shadow: 0 6px 16px -10px rgba(22,163,74,.8); }
[data-testid="stDataFrame"] { border-radius: 12px; overflow: hidden; border: 1px solid rgba(128,128,128,.18); }
[data-testid="stExpander"] details { border-radius: 12px; }
[data-testid="stAlert"] { border-radius: 12px; }

/* ---------- sidebar ---------- */
[data-testid="stSidebar"] { border-right: 1px solid rgba(255,255,255,.06); }
[data-testid="stSidebarNav"] a { border-radius: 10px; margin: 1px 0; }
[data-testid="stSidebarLogo"], [data-testid="stSidebarHeader"] img { height: 2.6rem !important; }
[data-testid="stSidebarHeader"] { padding-top: 1.4rem; padding-bottom: .4rem; }
.sp-side-note { font-size: .76rem; line-height: 1.5; color: rgba(220,239,228,.7);
                border-top: 1px solid rgba(255,255,255,.08); padding-top: .9rem; margin-top: .5rem; }
.sp-side-note b { color: #dcefe4; }

@media (max-width: 640px) {
  .block-container { padding-top: 3.6rem; }
  .sp-hero { padding: 1.2rem 1.1rem; border-radius: 14px; }
  .sp-hero h1 { font-size: 1.55rem; }
}
</style>
"""


def apply_theme() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
    # Every Plotly chart inherits the app font
    if "season_pulse" not in pio.templates:
        pio.templates["season_pulse"] = go.layout.Template(layout=dict(
            font=dict(family="Inter, Segoe UI, sans-serif"), hoverlabel=dict(font_family="Inter, Segoe UI, sans-serif")))
    pio.templates.default = "plotly+season_pulse"


def hero(title: str, subtitle: str, eyebrow: str = "Season Pulse") -> None:
    """Gradient page header. `subtitle` may contain **bold** (converted) but no other markup."""
    sub = html.escape(subtitle)
    while "**" in sub:
        sub = sub.replace("**", "<strong>", 1).replace("**", "</strong>", 1)
    st.markdown(f'<div class="sp-hero"><span class="sp-eyebrow">● {html.escape(eyebrow)}</span>'
                f'<h1>{html.escape(title)}</h1><p>{sub}</p></div>', unsafe_allow_html=True)


def section(title: str, note: str = "") -> None:
    st.markdown(f'<div class="sp-section"><div class="sp-h">{html.escape(title)}</div>'
                f'<span>{html.escape(note)}</span></div>', unsafe_allow_html=True)


def badge(level: str) -> str:
    return f'<span class="sp-badge" style="--c:{LEVEL_STYLE[level]}">{level}</span>'


def sidebar_brand() -> None:
    st.logo(str(ASSETS / "logo.svg"), size="large", icon_image=str(ASSETS / "icon.svg"))


def sidebar_note() -> None:
    st.sidebar.markdown(
        '<div class="sp-side-note">Yields shown as <b>% vs typical district</b> (Relative Yield Index), never kg/ha.'
        '<br><br>Data: NISR SAS 2020–2024, SAS 2026 Season A, EICV 2020, Establishment Census, CHIRPS rainfall. Boundaries © '
        'geoBoundaries (CC BY 4.0).<br><br><b>NISR Hackathon 2026</b></div>', unsafe_allow_html=True)
