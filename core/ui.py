"""Shared look and feel: global CSS, page header, status badges.

Colours are semi-transparent overlays where possible so the same CSS reads well in Streamlit's light and
dark themes. Brand green matches primaryColor in .streamlit/config.toml.
"""
import functools
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
.block-container { padding: 0 2.75rem 4rem !important; max-width: 100%; }
/* Streamlit's top controls (menu, Deploy, run status) float in a small pill over the banner */
[data-testid="stHeader"] { background: transparent !important; pointer-events: none; }
[data-testid="stHeader"] * { pointer-events: auto; }
[data-testid="stStatusWidget"], [data-testid="stAppDeployButton"], [data-testid="stMainMenu"] { display: none !important; }
[data-testid="stHeader"] { z-index: 70 !important; }
/* the zero-height blocks that load the app's CSS would otherwise add a 16px gap above the banner */
.block-container [data-testid="stElementContainer"]:has(> [data-testid="stMarkdown"] style) { display: none; }
[data-testid="stExpandSidebarButton"] { background: rgba(255,255,255,.92); border-radius: 10px; }
h1, h2, h3 { letter-spacing: -0.02em; }
[data-testid="stHeader"] { background: transparent; }

/* ---------- palette (from the Imboni logo) ---------- */
:root { --forest: #0E3B22; --leaf: #1F8A43; --gold: #F5B700; --gold-ink: #8A6400; --mint: #E9F5ED;
        --ink: #13261C; --muted: #5E6E65; --line: rgba(14,59,34,.12); --surface: #ffffff; }

/* ---------- page header (light) ---------- */
.sp-hero { position: relative; overflow: hidden; display: flex; align-items: center; flex-wrap: wrap;
           gap: .8rem 1.1rem; margin: 0 -2.75rem 1.3rem; padding: 1.15rem 2.75rem 1.05rem; border-radius: 0;
           background: var(--surface); border: none; border-bottom: 1px solid var(--line);
           box-shadow: 0 8px 20px -16px rgba(14,59,34,.35); }
/* the banner stays at the top while the page scrolls */
.block-container [data-testid="stElementContainer"]:has(> [data-testid="stMarkdown"] .sp-hero) {
    position: sticky; top: 0; z-index: 60; }
/* sidebar closed: Streamlit shows the logo and the "»" button in the top-left corner, so make room for them */
body:has([data-testid="stSidebar"][aria-expanded="false"]) .sp-hero { padding-left: 7.2rem; }
.sp-hero::before { content: ""; position: absolute; inset: 0 0 auto 0; height: 4px;
                   background: linear-gradient(90deg, var(--forest), var(--leaf)); }
.sp-hero::after { content: ""; position: absolute; right: -90px; top: -110px; width: 320px; height: 320px;
                  border-radius: 50%; pointer-events: none;
                  background: radial-gradient(circle, rgba(31,138,67,.10), transparent 65%); }
.sp-hero-ic { flex: none; width: 3.4rem; height: 3.4rem; border-radius: 16px; display: grid; place-items: center;
              background: var(--mint); color: var(--forest); border: 1px solid rgba(31,138,67,.18);
              position: relative; z-index: 1; }
.sp-hero-ic .mi { font-size: 1.7rem; }
.sp-hero-txt { flex: 1 1 340px; min-width: 0; position: relative; z-index: 1; }
.sp-eyebrow { display: inline-flex; align-items: center; gap: .45rem; font-size: .7rem; font-weight: 750;
              letter-spacing: .14em; text-transform: uppercase; color: var(--gold-ink); }
.sp-eyebrow::before { content: ""; width: .45rem; height: .45rem; border-radius: 50%; background: var(--gold); }
.sp-hero h1 { color: var(--forest); font-size: 1.75rem; font-weight: 800; margin: .3rem 0 .15rem; padding: 0;
              line-height: 1.15; letter-spacing: -.025em; }
.sp-hero p { color: var(--muted); font-size: .98rem; margin: 0; line-height: 1.5; }
.sp-hero p strong { color: var(--ink); }
.sp-hero-meta { display: flex; flex-wrap: wrap; gap: .45rem; position: relative; z-index: 1; }
.sp-meta { display: inline-flex; align-items: center; gap: .4rem; font-size: .8rem; font-weight: 600;
           color: var(--ink); background: #F6F8F5; border: 1px solid var(--line); padding: .4rem .75rem;
           border-radius: 999px; white-space: nowrap; }
.sp-meta .mi { color: var(--leaf); font-size: 1rem; }

/* ---------- feature banner (Overview) ---------- */
.sp-hero.feature { /* unused: kept so hero(feature=True) still renders like the light header */ }
                               background: rgba(245,183,0,.12); border-color: rgba(245,183,0,.35); }

/* ---------- section headings ---------- */
.sp-section { display: flex; flex-wrap: wrap; align-items: baseline; gap: .1rem .6rem; margin: 1.6rem 0 .6rem; }
.sp-section .sp-h { font-size: 1.3rem; font-weight: 750; letter-spacing: -0.02em; line-height: 1.3; color: var(--forest); }
.sp-section span { font-size: .85rem; opacity: .6; }

/* ---------- metrics as cards ---------- */
[data-testid="stMetric"] { background: var(--surface); border: 1px solid rgba(128,128,128,0.18);
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
/* Imboni logo, white-lettering variant on the dark sidebar (no background) */
[data-testid="stSidebarLogo"] { height: 3.2rem !important; max-width: 100% !important; width: auto !important;
                                margin-top: 1.3rem; }
[data-testid="stSidebarHeader"] { padding-bottom: .9rem; height: auto !important; }
[data-testid="stHeaderLogo"] { height: 2.2rem !important; }
.sp-side-note { font-size: .78rem; line-height: 1.55; color: rgba(220,239,228,.88);
                border-top: 1px solid rgba(255,255,255,.08); padding-top: .9rem; margin-top: .5rem; }
.sp-side-note b { color: #dcefe4; }

/* ---------- toolbar (filters) ---------- */
.st-key-toolbar { background: var(--surface); border: 1px solid rgba(128,128,128,0.18) !important;
                  border-radius: 16px !important; padding: .9rem 1.1rem .4rem !important; margin-bottom: .4rem; }
[data-testid="stButtonGroup"] button { font-weight: 600; }

/* ---------- ranked district list ---------- */
.sp-rank { display: grid; grid-template-columns: 1.4rem 1fr auto; align-items: center; gap: .15rem .6rem;
           padding: .5rem 0; border-bottom: 1px solid rgba(128,128,128,.12); }
.sp-rank:last-child { border-bottom: none; }
.sp-rank .n { font-size: .75rem; font-weight: 700; opacity: .45; }
.sp-rank .d { font-weight: 650; font-size: .93rem; line-height: 1.2; }
.sp-rank .d small { display: block; font-weight: 500; font-size: .74rem; opacity: .55; }
.sp-rank .v { font-weight: 800; font-size: .95rem; font-variant-numeric: tabular-nums; color: var(--c); }
.sp-rank .bar { grid-column: 2 / 4; height: 6px; border-radius: 99px; background: rgba(128,128,128,.13);
                overflow: hidden; }
.sp-rank .bar i { display: block; height: 100%; border-radius: 99px; background: var(--c); }
.sp-panel-h { font-size: .74rem; font-weight: 750; letter-spacing: .09em; text-transform: uppercase; opacity: .6;
              margin: .2rem 0 .2rem; }

/* ---------- tabs ---------- */
[data-baseweb="tab-list"] { gap: .3rem; border-bottom: 1px solid rgba(128,128,128,.18); }
[data-baseweb="tab"] { font-weight: 600; padding: .55rem .9rem !important; border-radius: 10px 10px 0 0; }
[data-baseweb="tab"][aria-selected="true"] { background: rgba(22,163,74,.08); }

/* ---------- filters (pro) ---------- */
:is(.st-key-toolbar, .st-key-atool, .st-key-toolbar2) { padding: .85rem 1.2rem .55rem !important;
    border-color: var(--line) !important; box-shadow: 0 1px 2px rgba(14,59,34,.04); }
.sp-fhead { display: flex; align-items: center; gap: .55rem; font-size: .95rem; color: var(--forest); }
.sp-fhead b { font-weight: 750; }
.sp-fhead .mi { font-size: 1.05rem; color: var(--leaf); }
.sp-fcount { font-size: .72rem; font-weight: 700; color: var(--forest); background: var(--mint);
             border: 1px solid rgba(31,138,67,.22); border-radius: 999px; padding: .12rem .55rem; }
.sp-fhint { font-size: .85rem; color: var(--muted); font-weight: 500; }
.st-key-toolbar .sp-fhead { padding-bottom: .55rem; margin-bottom: .15rem;
                                                border-bottom: 1px solid var(--line); }
/* small uppercase labels */
:is(.st-key-toolbar, .st-key-atool, .st-key-toolbar2) [data-testid="stWidgetLabel"] p {
    font-size: .68rem !important; font-weight: 750 !important; letter-spacing: .09em; text-transform: uppercase;
    color: var(--muted) !important; }
/* segmented control: grey track, the active option is a raised white tab */
[data-baseweb="button-group"]:has(> button[kind^="segmented_control"]) {
    background: #EDF1EE; padding: 3px; border-radius: 12px; gap: 2px !important; width: fit-content; max-width: 100%;
    flex-wrap: wrap; }
button[kind="segmented_control"], button[kind="segmented_controlActive"] {
    border: none !important; border-radius: 9px !important; min-height: 2.15rem; padding: 0 .95rem !important;
    box-shadow: none !important; font-weight: 600; }
button[kind="segmented_control"] { background: transparent !important; color: var(--muted) !important; }
button[kind="segmented_control"]:hover { color: var(--forest) !important; background: rgba(255,255,255,.55) !important; }
button[kind="segmented_controlActive"] { background: #ffffff !important; color: var(--forest) !important;
    box-shadow: 0 1px 3px rgba(14,59,34,.16), 0 0 0 1px rgba(14,59,34,.06) !important; }
button[kind^="segmented_control"] * { color: inherit !important; font-weight: 650; }
/* pills: soft grey off, solid forest on */
button[kind="pills"], button[kind="pillsActive"] { border-radius: 999px !important; min-height: 2.1rem;
    padding: 0 .9rem !important; font-weight: 600; transition: background .15s, border-color .15s, color .15s; }
button[kind="pills"] { background: #F2F5F2 !important; border: 1px solid transparent !important; color: var(--ink) !important; }
button[kind="pills"]:hover { background: #EAF4ED !important; border-color: rgba(31,138,67,.35) !important; }
button[kind="pillsActive"] { background: var(--forest) !important; border: 1px solid var(--forest) !important;
    color: #ffffff !important; box-shadow: 0 1px 2px rgba(14,59,34,.25); }
button[kind^="pills"] * { color: inherit !important; }
/* dropdowns */
.block-container [data-baseweb="select"] > div { background: #F6F8F5 !important; border-radius: 12px !important;
    border-color: var(--line) !important; min-height: 2.5rem; }
.block-container [data-baseweb="select"] > div:hover { border-color: rgba(31,138,67,.45) !important; }
.block-container [data-baseweb="tag"] { background: var(--forest) !important; border-radius: 999px !important;
    margin-top: 2px !important; margin-bottom: 2px !important; height: 1.6rem !important; font-size: .82rem !important; }
.block-container [data-baseweb="tag"] * { color: #fff !important; }
/* reset + popover buttons in the filter bar */
:is(.st-key-atool, .st-key-toolbar) button[kind="tertiary"] { color: var(--leaf) !important; font-weight: 650; }
:is(.st-key-atool, .st-key-toolbar) button[kind="tertiary"]:disabled { color: var(--muted) !important; opacity: .5; }
[data-testid="stPopoverButton"] { border-radius: 12px !important; border-color: var(--line) !important;
    background: #F6F8F5 !important; color: var(--forest) !important; font-weight: 650; }

/* ---------- "How to read" guide (Alerts popover) ---------- */
[data-testid="stPopoverBody"] { width: 640px !important; max-width: 94vw; padding: .9rem 1.1rem .7rem !important;
                                max-height: none !important; overflow: visible !important; }
.sp-guide { display: flex; flex-direction: column; gap: .2rem; }
.sp-g-title { font-size: 1.05rem; font-weight: 800; color: var(--forest); letter-spacing: -.01em; margin-bottom: .35rem; }
.sp-g-block { display: grid; grid-template-columns: 2.2rem 1fr; gap: .75rem; padding: .55rem 0;
              border-top: 1px solid var(--line); }
.sp-g-ic { width: 2.2rem; height: 2.2rem; border-radius: 10px; display: grid; place-items: center;
           background: var(--mint); color: var(--forest); }
.sp-g-ic .mi { font-size: 1.1rem; }
.sp-g-block b { display: block; font-size: .92rem; color: var(--ink); margin-bottom: .2rem; }
.sp-g-block p { font-size: .84rem; line-height: 1.45; color: var(--muted); margin: 0 0 .35rem; }
.sp-g-block p strong { color: var(--ink); }
.sp-g-scale { display: flex; justify-content: space-between; font-size: .68rem; color: var(--muted);
              padding-top: .55rem; position: relative; }
.sp-g-scale::before { content: ""; position: absolute; top: 0; left: 0; right: 0; height: 6px; border-radius: 99px;
                      background: linear-gradient(90deg, #dc2626, #f59e0b 30%, #e5e7eb 50%, #60a5fa 75%, #2563eb); }
.sp-g-levels { display: grid; grid-template-columns: repeat(3, auto); gap: .35rem .9rem; margin-top: .15rem;
               justify-content: start; }
.sp-g-level { display: flex; flex-direction: column; align-items: flex-start; gap: .3rem; font-size: .78rem;
              color: var(--muted); }
.sp-g-level .sp-badge { justify-content: center; }
.sp-g-formula { display: inline-block; font-weight: 700; font-size: .86rem; color: var(--forest);
                background: var(--mint); border: 1px solid rgba(31,138,67,.22); border-radius: 8px; padding: .3rem .6rem;
                margin-bottom: .35rem; }
.sp-g-formula i { font-style: normal; color: var(--leaf); padding: 0 .2rem; }
.sp-g-note { font-size: .76rem !important; }
.sp-g-acts { display: grid; grid-template-columns: 1fr 1fr; gap: .5rem .9rem; margin-top: .25rem; }
.sp-g-act { display: grid; grid-template-columns: 1.8rem 1fr; gap: .55rem; align-items: start; }
.sp-g-act-ic { width: 1.8rem; height: 1.8rem; border-radius: 8px; display: grid; place-items: center; color: var(--c);
               background: color-mix(in srgb, var(--c) 12%, transparent); }
.sp-g-act-ic .mi { font-size: .95rem; }
.sp-g-act b { font-size: .84rem !important; color: var(--c) !important; margin: 0 !important; }
.sp-g-act small { display: block; font-size: .76rem; color: var(--muted); line-height: 1.35; }
.sp-g-foot { font-size: .72rem; color: var(--muted); border-top: 1px solid var(--line); padding: .55rem 0 .1rem; }
@media (max-width: 640px) { .sp-g-acts { grid-template-columns: 1fr; } .sp-g-levels { grid-template-columns: 1fr; } }

/* ---------- production at stake (alert detail) ---------- */
.sp-stake { display: grid; grid-template-columns: repeat(3, 1fr); gap: .5rem; margin-top: .85rem; }
.sp-stake div { background: #F6F8F5; border: 1px solid var(--line); border-radius: 10px; padding: .5rem .6rem; }
.sp-stake b { display: block; font-size: .95rem; color: var(--ink); }
.sp-stake span { display: block; font-size: .7rem; color: var(--muted); line-height: 1.3; }
.sp-stake div:first-child b { color: var(--c); }

/* ---------- surfaces ---------- */
.sp-rows, .sp-tile, .sp-alert, .sp-stepcard, .sp-sum, .sp-plan, .sp-crop { background-color: var(--surface); }
.st-key-rep_card { background: var(--surface); }
[data-testid="stExpander"] details { background: var(--surface); }
[class*="st-key-card_"] { background: var(--surface); border-color: var(--line) !important; border-radius: 18px !important;
                         box-shadow: 0 1px 2px rgba(14,59,34,.04); }

/* ---------- footer ---------- */
.sp-footer { margin-top: 3.5rem; padding: 1.1rem 0 .4rem; border-top: 1px solid rgba(128,128,128,.18);
             display: flex; flex-wrap: wrap; gap: .4rem 1.4rem; justify-content: space-between;
             font-size: .78rem; opacity: .6; }
.sp-footer b { font-weight: 700; }

/* ---------- alerts page: status note ---------- */
.sp-note { border-radius: 12px; padding: .6rem .9rem; font-size: .9rem; margin: .4rem 0 1rem;
           border: 1px solid var(--b); background: var(--bg); display: flex; align-items: center; gap: .55rem; }
.sp-note .mi { color: var(--ic); font-size: 1.25rem; }
.sp-note-warn { --b: rgba(234,138,12,.35); --bg: rgba(234,138,12,.08); --ic: #d97706; }
.sp-note-info { --b: rgba(2,132,199,.3); --bg: rgba(2,132,199,.06); --ic: #0284c7; }

/* ---------- material icons ---------- */
svg.mi { font-size: 1.15em; width: 1em; height: 1em; display: inline-block; vertical-align: -0.18em; flex: none;
         stroke-width: 2; }

/* ---------- report page ---------- */
.st-key-rep_card { border: 1px solid rgba(128,128,128,.18) !important; border-radius: 18px !important;
                   padding: 1.2rem 1.3rem 1.3rem !important; }
.st-key-rep_card [data-testid="stButtonGroup"] button { min-height: 2.7rem; padding: 0 1rem; font-size: .98rem; }
.st-key-rep_card [data-baseweb="select"] > div { min-height: 2.9rem; font-size: 1rem; }
.st-key-rep_card [data-testid="stWidgetLabel"] p { font-weight: 600; font-size: .95rem; }
.sp-step { display: flex; align-items: center; gap: .6rem; margin: 1.1rem 0 .3rem; }
.sp-step:first-child { margin-top: 0; }
.sp-step b { width: 1.75rem; height: 1.75rem; border-radius: 50%; display: grid; place-items: center; flex: none;
             background: #16a34a; color: #fff; font-size: .85rem; }
.sp-step span { font-weight: 750; font-size: 1.05rem; letter-spacing: -.01em; }
.sp-sum { border: 1px solid rgba(128,128,128,.18); border-radius: 18px; padding: 1.1rem 1.2rem;
          background: linear-gradient(170deg, rgba(22,163,74,.07), transparent 55%); }
.sp-sum-h { display: flex; justify-content: space-between; align-items: baseline; font-weight: 750; }
.sp-sum-h small { font-weight: 600; opacity: .6; }
.sp-sum-bar { height: 7px; border-radius: 99px; background: rgba(128,128,128,.15); margin: .6rem 0 .8rem;
              overflow: hidden; }
.sp-sum-bar i { display: block; height: 100%; background: #16a34a; border-radius: 99px; transition: width .3s; }
.sp-sum-row { display: grid; grid-template-columns: 1.6rem 1fr auto; align-items: center; gap: .5rem;
              padding: .5rem 0; border-top: 1px solid rgba(128,128,128,.12); font-size: .9rem; }
.sp-sum-row .mi { font-size: 1.2rem; opacity: .7; }
.sp-sum-row span:nth-child(2) { opacity: .65; }
.sp-sum-row b { text-align: right; }
.sp-sum-row.todo b { opacity: .35; font-weight: 500; }
.sp-ctx { margin-top: .9rem; border-radius: 14px; padding: .8rem .95rem; display: flex; gap: .7rem;
          align-items: center; background: color-mix(in srgb, var(--c) 9%, transparent);
          border: 1px solid color-mix(in srgb, var(--c) 28%, transparent); }
.sp-ctx .mi { color: var(--c); font-size: 1.6rem; }
.sp-ctx b { font-size: 1.15rem; color: var(--c); }
.sp-ctx div { font-size: .82rem; line-height: 1.35; }

/* ---------- alerts page: level tiles ---------- */
.sp-tiles { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: .9rem; margin-bottom: .6rem; }
.sp-tile { border: 1px solid rgba(128,128,128,.18); border-radius: 16px; padding: .9rem 1.05rem .95rem;
           background: linear-gradient(160deg, color-mix(in srgb, var(--c) 7%, transparent), transparent 60%);
           position: relative; overflow: hidden; }
.sp-tile::before { content: ""; position: absolute; inset: 0 auto 0 0; width: 4px; background: var(--c); }
.sp-tile-h { display: flex; flex-direction: column; gap: .3rem; align-items: flex-start; }
.sp-tile-h > span:last-child { font-size: .74rem; opacity: .6; }
.sp-tile-n { font-size: 2.1rem; font-weight: 800; letter-spacing: -.03em; margin: .35rem 0 .45rem; line-height: 1; }
.sp-tile-n small { font-size: .78rem; font-weight: 500; opacity: .55; letter-spacing: 0; }
.sp-tile-bar { height: 6px; border-radius: 99px; background: rgba(128,128,128,.14); overflow: hidden; }
.sp-tile-bar i { display: block; height: 100%; background: var(--c); border-radius: 99px; }

/* ---------- alerts page: action plan ---------- */
.sp-plans { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: .8rem; }
.sp-plan { border: 1px solid rgba(128,128,128,.18); border-radius: 16px; padding: .95rem 1rem 1rem;
           display: grid; grid-template-columns: auto 1fr; grid-template-rows: auto auto auto 1fr; gap: .15rem .7rem;
           border-top: 3px solid var(--c); }
.sp-plan-ic { grid-row: 1; width: 2.3rem; height: 2.3rem; border-radius: 10px; display: grid; place-items: center;
              font-size: 1.15rem; background: color-mix(in srgb, var(--c) 13%, transparent); }
.sp-plan-n { grid-row: 1; align-self: center; justify-self: end; font-size: 1.75rem; font-weight: 800;
             color: var(--c); letter-spacing: -.03em; }
.sp-plan-t { grid-column: 1 / 3; font-weight: 700; font-size: .95rem; margin-top: .45rem; line-height: 1.25; }
.sp-plan-w { grid-column: 1 / 3; font-size: .76rem; opacity: .6; line-height: 1.35; }
.sp-plan-top { grid-column: 1 / 3; font-size: .78rem; line-height: 1.4; margin-top: .55rem; padding-top: .55rem;
               border-top: 1px dashed rgba(128,128,128,.25); }
.sp-plan-top i { opacity: .6; font-style: normal; }

/* ---------- alerts page: priority cards ---------- */
.sp-alerts { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 1rem; }
.sp-alert { border: 1px solid rgba(128,128,128,.18); border-radius: 18px; padding: 1.05rem 1.15rem 0;
            display: flex; flex-direction: column; position: relative; overflow: hidden;
            background: linear-gradient(180deg, color-mix(in srgb, var(--c) 6%, transparent), transparent 140px);
            transition: transform .15s ease, box-shadow .15s ease; }
.sp-alert::before { content: ""; position: absolute; inset: 0 0 auto 0; height: 4px; background: var(--c); }
.sp-alert:hover { transform: translateY(-3px); box-shadow: 0 14px 30px -18px rgba(0,0,0,.45); }
.sp-alert-top { display: flex; justify-content: space-between; align-items: center; }
.sp-rank-no { font-size: .8rem; font-weight: 800; opacity: .35; }
.sp-alert-t { font-size: 1.12rem; font-weight: 750; margin-top: .55rem; letter-spacing: -.01em; }
.sp-alert-p { font-size: .8rem; opacity: .55; }
.sp-alert-v { font-size: 2.15rem; font-weight: 800; letter-spacing: -.03em; color: var(--c); margin-top: .5rem;
              line-height: 1.05; }
.sp-alert-v small { display: block; font-size: .74rem; font-weight: 500; color: inherit; opacity: .7;
                    letter-spacing: 0; margin-top: .2rem; filter: grayscale(1); }
.sp-meter { position: relative; height: 8px; border-radius: 99px; margin-top: .75rem;
            background: linear-gradient(90deg, #dc2626 0%, #f59e0b 30%, #e5e7eb 50%, #60a5fa 75%, #2563eb 100%); }
.sp-meter-0 { position: absolute; left: 50%; top: -3px; bottom: -3px; width: 2px; background: rgba(0,0,0,.35); }
.sp-meter i { position: absolute; top: 50%; width: 16px; height: 16px; border-radius: 50%; background: #fff;
              border: 3px solid var(--c); transform: translate(-50%, -50%); box-shadow: 0 2px 6px rgba(0,0,0,.25); }
.sp-meter-l { display: flex; justify-content: space-between; font-size: .66rem; opacity: .5; margin-top: .3rem; }
.sp-alert-h { font-size: .68rem; font-weight: 750; letter-spacing: .1em; text-transform: uppercase; opacity: .5;
              margin: .9rem 0 .35rem; }
.sp-why { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: .35rem; }
.sp-why { margin: .85rem 0 .8rem !important; }
.sp-why li { display: grid; grid-template-columns: 1.3rem 1fr; gap: .45rem; font-size: .84rem; line-height: 1.4;
             margin: 0; padding: 0; align-items: center; }
.sp-why li .mi { font-size: 1.1rem; opacity: .55; }
.sp-tag .mi { font-size: 1rem; margin-top: -2px; }
.sp-alert-f .mi { display: block; margin: 0 auto .1rem; font-size: 1.05rem; opacity: .45; }
.sp-plan-top div { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.sp-plan-ic .mi { font-size: 1.35rem; }
.sp-why li::marker { content: none; }
.sp-tags { display: flex; flex-wrap: wrap; gap: .35rem; }
.sp-tag { font-size: .78rem; font-weight: 650; padding: .3rem .6rem; border-radius: 8px; color: var(--c);
          background: color-mix(in srgb, var(--c) 11%, transparent);
          border: 1px solid color-mix(in srgb, var(--c) 28%, transparent); }
.sp-alert-f { display: grid; grid-template-columns: repeat(4, 1fr); margin: 1rem -1.15rem 0; margin-top: auto;
              border-top: 1px solid rgba(128,128,128,.15); background: rgba(128,128,128,.04); }
.sp-alert-f div { padding: .65rem .2rem .7rem; text-align: center; border-right: 1px solid rgba(128,128,128,.12);
                  min-width: 0; }
.sp-alert-f div:last-child { border-right: none; }
.sp-alert-f b { display: block; font-size: .98rem; font-weight: 750; }
.sp-alert-f span { display: block; font-size: .7rem; opacity: .55; white-space: nowrap; }
.sp-alert .sp-tags { margin-bottom: 1rem; }

/* ---------- alerts page: list + detail ---------- */
.st-key-toolbar2 { background: var(--surface); border: 1px solid rgba(128,128,128,0.18) !important;
                   border-radius: 16px !important; padding: .8rem 1.1rem .5rem !important; margin-bottom: .2rem; }
.st-key-atool { background: var(--surface); border: 1px solid rgba(128,128,128,0.18) !important;
                border-radius: 16px !important; padding: .9rem 1.1rem .4rem !important; margin-bottom: .8rem; }
.st-key-toolbar2 { border-top: none !important; border-top-left-radius: 0 !important; border-top-right-radius: 0 !important; margin-top: -1rem; margin-bottom: .8rem; }
.sp-list-h { font-size: 1rem; margin: .2rem 0 .5rem; }
.sp-list-h b { font-size: 1.15rem; }
.sp-list-h span { opacity: .55; font-size: .85rem; }
.sp-detail { padding-bottom: 0; }
.sp-detail .sp-why { margin: 0 !important; gap: .5rem; }
.sp-detail .sp-why li { align-items: start; }
.sp-acts { display: flex; flex-direction: column; gap: .5rem; }
.sp-act { display: grid; grid-template-columns: 2.2rem 1fr; gap: .7rem; align-items: start; padding: .65rem .75rem;
          border-radius: 12px; background: color-mix(in srgb, var(--c) 7%, transparent);
          border: 1px solid color-mix(in srgb, var(--c) 22%, transparent); }
.sp-act-ic { width: 2.2rem; height: 2.2rem; border-radius: 9px; display: grid; place-items: center; color: var(--c);
             background: color-mix(in srgb, var(--c) 14%, transparent); }
.sp-act b { display: block; color: var(--c); font-size: .95rem; }
.sp-act span { display: block; font-size: .84rem; line-height: 1.35; }
.sp-act small { display: block; font-size: .74rem; opacity: .6; margin-top: .2rem; line-height: 1.35; }
.sp-partners { grid-template-columns: repeat(3, 1fr) !important; margin-top: .2rem !important; }

/* ---------- overview + district profile ---------- */
/* ---------- stat strip (overview + district) ---------- */
.sp-kpis { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 0; margin-bottom: 1.1rem;
           border: 1px solid rgba(128,128,128,.18); border-radius: 16px; overflow: hidden; background: var(--surface); }
.sp-kpi { display: flex; gap: .85rem; align-items: center; padding: 1rem 1.2rem;
          border-right: 1px solid rgba(128,128,128,.14); }
.sp-kpi:last-child { border-right: none; }
.sp-kpi-ic { flex: none; width: 2.5rem; height: 2.5rem; border-radius: 10px; display: grid; place-items: center;
             color: var(--c); background: rgba(128,128,128,.08); }
.sp-kpi-ic .mi { font-size: 1.25rem; }
.sp-kpi b { display: block; font-size: 1.6rem; font-weight: 800; letter-spacing: -.03em; line-height: 1.1; }
.sp-kpi span { display: block; font-size: .84rem; font-weight: 650; }
.sp-kpi small { display: block; font-size: .74rem; opacity: .55; white-space: nowrap; overflow: hidden;
                text-overflow: ellipsis; }

/* ---------- crop scorecard ---------- */
.sp-rows { border: 1px solid rgba(128,128,128,.18); border-radius: 16px; overflow: hidden; margin-bottom: .5rem; }
.sp-row { display: grid; grid-template-columns: 1.5fr .75fr 2fr .6fr 1.7fr; gap: 1rem; align-items: center;
          padding: .8rem 1.2rem; border-top: 1px solid rgba(128,128,128,.12); transition: background .15s; }
.sp-row:hover { background: rgba(22,163,74,.035); }
.sp-row-h { border-top: none; background: rgba(128,128,128,.05); padding: .55rem 1.2rem; font-size: .72rem;
            font-weight: 700; letter-spacing: .06em; text-transform: uppercase; opacity: .7; }
.sp-row-h:hover { background: rgba(128,128,128,.05); }
.sp-row-h small { text-transform: none; letter-spacing: 0; font-weight: 500; opacity: .75; }
.sp-row-crop { display: flex; align-items: center; gap: .7rem; min-width: 0; }
.sp-row-crop > div { min-width: 0; }
.sp-row > * { min-width: 0; }
.sp-row-ic { flex: none; width: 2.3rem; height: 2.3rem; border-radius: 10px; display: grid; place-items: center;
             background: rgba(22,163,74,.09); color: #15803d; }
.sp-row-ic .mi { font-size: 1.15rem; }
.sp-row-crop b { display: block; font-size: .98rem; }
.sp-row-crop small { display: block; font-size: .74rem; opacity: .55; white-space: nowrap; overflow: hidden;
                     text-overflow: ellipsis; }
.sp-scale { position: relative; height: 8px; border-radius: 99px; background: rgba(128,128,128,.13); }
.sp-scale-0 { position: absolute; left: 50%; top: -4px; bottom: -4px; width: 1.5px; background: rgba(0,0,0,.35); }
.sp-scale i { position: absolute; top: 0; bottom: 0; border-radius: 99px; background: var(--t); opacity: .85; }
.sp-scale em { position: absolute; top: -5px; bottom: -5px; width: 2.5px; border-radius: 2px; background: #334155;
               transform: translateX(-50%); }
.sp-row-v { font-size: 1.15rem; font-weight: 800; color: var(--t); letter-spacing: -.02em; text-align: right;
            font-variant-numeric: tabular-nums; }
.sp-row .sp-tags { gap: .3rem; }
.sp-row .sp-tag { font-size: .76rem; padding: .22rem .5rem; white-space: nowrap; }

.sp-steps { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: .9rem; }
.sp-stepcard { border: 1px solid rgba(128,128,128,.18); border-radius: 16px; padding: 1rem 1.05rem; position: relative; }
.sp-stepcard-ic { width: 2.5rem; height: 2.5rem; border-radius: 50%; display: grid; place-items: center; color: #fff;
                  background: linear-gradient(135deg, #22c55e, #15803d); margin-bottom: .6rem; }
.sp-stepcard b { display: block; font-size: .98rem; margin-bottom: .25rem; }
.sp-stepcard span { font-size: .84rem; opacity: .75; line-height: 1.45; }
.sp-finds { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: .9rem; }
.sp-find { border-radius: 16px; padding: 1rem 1.1rem; border: 1px solid color-mix(in srgb, var(--c) 25%, transparent);
           background: color-mix(in srgb, var(--c) 6%, transparent); }
.sp-find-ic { color: var(--c); margin-bottom: .4rem; }
.sp-find-ic .mi { font-size: 1.6rem; }
.sp-find b { display: block; font-size: 1rem; margin-bottom: .3rem; }
.sp-find span { font-size: .85rem; opacity: .78; line-height: 1.45; }
.sp-dhead { display: flex; align-items: baseline; gap: .7rem; margin: .3rem 0 .8rem; }
.sp-dhead b { font-size: 1.6rem; font-weight: 800; letter-spacing: -.02em; }
.sp-dhead span { opacity: .6; }
.sp-crops { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: .8rem; margin-bottom: .4rem; }
.sp-crop { border: 1px solid rgba(128,128,128,.18); border-radius: 16px; padding: .9rem 1rem; border-top: 4px solid var(--c); }
.sp-crop-top { display: flex; justify-content: space-between; align-items: center; }
.sp-crop-top small { font-size: .72rem; opacity: .55; }
.sp-crop > b { display: block; font-size: 1.02rem; margin-top: .55rem; }
.sp-crop-v { font-size: 1.6rem; font-weight: 800; color: var(--c); letter-spacing: -.03em; }
.sp-crop-v small { font-size: .74rem; font-weight: 500; color: inherit; opacity: .7; letter-spacing: 0; }
.sp-crop-s { font-size: .76rem; opacity: .6; }
.sp-crop-a { display: flex; gap: .35rem; align-items: start; font-size: .8rem; margin-top: .6rem; padding-top: .55rem;
             border-top: 1px dashed rgba(128,128,128,.25); }
.sp-crop-a .mi { font-size: 1rem; color: var(--c); }

@media (max-width: 1100px) {
  .sp-kpis, .sp-steps, .sp-crops { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .sp-kpi:nth-child(2) { border-right: none; }
  .sp-kpi:nth-child(-n+2) { border-bottom: 1px solid rgba(128,128,128,.14); }
  .sp-row { grid-template-columns: 1.4fr .8fr 1.6fr .6fr; }
  .sp-row > .sp-tags { grid-column: 1 / -1; }
  .sp-row-h > span:last-child { display: none; }
  .sp-finds { grid-template-columns: 1fr; }
  .sp-plans { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .sp-alerts { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .sp-tiles { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}

@media (max-width: 640px) {
  .sp-plans, .sp-alerts { grid-template-columns: 1fr; }
  .sp-steps, .sp-crops { grid-template-columns: 1fr 1fr; }
  .sp-row { grid-template-columns: 1fr auto; gap: .5rem .8rem; }
  .sp-row-v { text-align: left; }
  .sp-kpis { grid-template-columns: 1fr !important; }
  .sp-kpi { border-right: none !important; border-bottom: 1px solid rgba(128,128,128,.14); }
  .sp-kpi:last-child { border-bottom: none; }
  .sp-row > .sp-scale { grid-column: 1 / -1; }
  .sp-row-h { display: none; }
  .sp-kpi b { font-size: 1.4rem; }
  .block-container { padding: 0 1rem 3rem !important; }
  /* KPI rows: two cards per line instead of one tall stack */
  [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] [data-testid="stMetric"]) {
      flex-wrap: wrap !important; flex-direction: row !important; gap: .6rem !important; }
  [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] [data-testid="stMetric"]) > [data-testid="stColumn"] {
      width: calc(50% - .3rem) !important; flex: 1 1 calc(50% - .3rem) !important; min-width: calc(50% - .3rem) !important; }
  [data-testid="stMetricValue"] { font-size: 1.5rem; }
  .sp-hero { margin: 0 -1rem 1rem; padding: .9rem 1rem .9rem 1rem; }
  body:has([data-testid="stSidebar"][aria-expanded="false"]) .sp-hero { padding-left: 6.6rem; }
  .sp-hero-meta { display: none; }
  /* slim sticky bar on phones: label + title only */
  .sp-hero p, .sp-hero-ic { display: none; }
  .sp-hero h1 { font-size: 1.2rem !important; margin: .15rem 0 0; }
  .sp-hero h1 { font-size: 1.45rem; }

  .sp-hero.feature h1 { font-size: 1.75rem; }
  .sp-hero-ic { width: 2.9rem; height: 2.9rem; }
}
</style>
"""


def apply_theme() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
    # Every Plotly chart inherits the app font
    if "imboni" not in pio.templates:
        pio.templates["imboni"] = go.layout.Template(layout=dict(
            font=dict(family="Inter, Segoe UI, sans-serif"), hoverlabel=dict(font_family="Inter, Segoe UI, sans-serif")))
    pio.templates.default = "plotly+imboni"


# Lucide icons (lucide-static 0.460.0, ISC licence), vendored as SVG files in assets/lucide/.
# Pages ask for an icon by a descriptive name; this maps it to the Lucide file.
LUCIDE = {
    "visibility": "eye", "notifications_active": "bell-ring", "map": "map", "location_city": "building-2",
    "insights": "chart-line", "edit_note": "notebook-pen", "dialpad": "grid-3x3", "eco": "sprout",
    "water_drop": "droplet", "task_alt": "circle-check-big", "science": "flask-conical", "history": "history",
    "assignment": "clipboard-list", "verified": "badge-check", "crisis_alert": "siren", "warning": "triangle-alert",
    "trending_down": "trending-down", "restaurant": "utensils", "rainy": "cloud-rain", "location_on": "map-pin",
    "info": "info", "groups": "users", "check_circle": "circle-check", "factory": "factory", "public": "globe",
    "warehouse": "warehouse", "monitor_heart": "activity", "bug_report": "bug", "grain": "bean",
    "nutrition": "carrot", "egg": "egg", "grass": "wheat", "local_florist": "cherry",
    "calendar": "calendar-days", "database": "database", "clock": "clock", "languages": "languages",
    "offline": "wifi-off", "layers": "layers", "filters": "sliders-horizontal", "dashboard": "layout-dashboard", "target": "target", "scale": "scale",
}


@functools.cache
def _svg(name: str) -> str:
    raw = (ASSETS / "lucide" / f"{LUCIDE.get(name, name)}.svg").read_text(encoding="utf8")
    body = raw[raw.index("<svg"):]
    # one line (a blank line would end the HTML block in Markdown); size with the surrounding font
    return " ".join(body.split()).replace('width="24" height="24"', 'width="1em" height="1em"')


def icon(name: str, color: str = "", size: str = "") -> str:
    """Lucide icon as inline SVG, e.g. icon("water_drop"). Inherits the text colour unless `color` is given."""
    style = (f"color:{color};" if color else "") + (f"font-size:{size};" if size else "")
    return _svg(name).replace('class="lucide', f'style="{style}" class="mi lucide', 1)


def hero(title: str, subtitle: str, eyebrow: str = "Imboni", ic: str = "eco",
         meta: list[tuple[str, str]] | None = None, feature: bool = False) -> None:
    """Page header. `meta` = (icon, text) chips; `feature=True` = the dark forest banner used on the Overview.
    `subtitle` may contain **bold** (converted) but no other markup."""
    sub = html.escape(subtitle)
    while "**" in sub:
        sub = sub.replace("**", "<strong>", 1).replace("**", "</strong>", 1)
    chips = "".join(f'<span class="sp-meta">{icon(i)}{html.escape(t)}</span>' for i, t in meta or [])
    st.markdown(f'<div class="sp-hero{" feature" if feature else ""}"><div class="sp-hero-ic">{icon(ic)}</div>'
                f'<div class="sp-hero-txt"><span class="sp-eyebrow">{html.escape(eyebrow)}</span>'
                f'<h1>{html.escape(title)}</h1><p>{sub}</p></div>'
                + (f'<div class="sp-hero-meta">{chips}</div>' if chips else "") + "</div>", unsafe_allow_html=True)


def section(title: str, note: str = "") -> None:
    st.markdown(f'<div class="sp-section"><div class="sp-h">{html.escape(title)}</div>'
                f'<span>{html.escape(note)}</span></div>', unsafe_allow_html=True)


def nz(n, empty: str = "None"):
    """A count for display: never show a bare 0 in the design, use a word instead."""
    return empty if not n else n


def filter_head(n_active: int = 0, hint: str = "") -> str:
    """Header row for a filter panel: icon, optional hint, active-filter badge."""
    badge_html = f'<span class="sp-fcount">{n_active} active</span>' if n_active else ""
    hint_html = f'<span class="sp-fhint">{html.escape(hint)}</span>' if hint else ""
    return f'<div class="sp-fhead">{icon("filters")}{hint_html}{badge_html}</div>'


def badge(level: str) -> str:
    return f'<span class="sp-badge" style="--c:{LEVEL_STYLE[level]}">{level}</span>'


def sidebar_brand() -> None:
    # Sidebar is dark green, so it uses the white-lettering variant; README keeps the original dark logo
    st.logo(str(ASSETS / "imboni_logo_light.png"), size="large", icon_image=str(ASSETS / "imboni_icon.png"))


def sidebar_note() -> None:
    st.sidebar.markdown(
        '<div class="sp-side-note">Yields in <b>% vs typical district</b>.<br>'
        'Data: NISR SAS 2020–2026, EICV, Census, CHIRPS.<br><br><b>NISR Hackathon 2026</b></div>',
        unsafe_allow_html=True)


def rank_list(rows, title: str) -> None:
    """Ranked districts with a bar each. rows: iterable of (district, province, pct) with pct = % vs typical."""
    items = list(rows)
    top = max([abs(p) for _, _, p in items] + [1])
    html_rows = "".join(
        f'<div class="sp-rank" style="--c:{"#dc2626" if p < 0 else "#2563eb"}">'
        f'<span class="n">{i}</span><span class="d">{html.escape(d)}<small>{html.escape(prov)}</small></span>'
        f'<span class="v">{f"{p:+.0f}%" if round(p) else "typical"}</span><span class="bar"><i style="width:{max(abs(p) / top * 100, 3):.0f}%">'
        f'</i></span></div>'
        for i, (d, prov, p) in enumerate(items, 1))
    st.markdown(f'<div class="sp-panel-h">{html.escape(title)}</div>{html_rows}', unsafe_allow_html=True)


def footer() -> None:
    st.markdown('<div class="sp-footer"><span><b>Imboni</b> · in-season crop early warning for Rwanda</span>'
                '<span>NISR Big Data Hackathon 2026 · Track 1: Agricultural Productivity</span>'
                '<span>Data: NISR SAS, EICV, Establishment Census · CHIRPS · geoBoundaries</span></div>',
                unsafe_allow_html=True)
