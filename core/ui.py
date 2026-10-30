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
.block-container { padding-top: 2.2rem; padding-bottom: 4rem; max-width: 1280px; }
h1, h2, h3 { letter-spacing: -0.02em; }
[data-testid="stHeader"] { background: transparent; }

/* ---------- hero header ---------- */
.sp-hero { position: relative; overflow: hidden; border-radius: 18px; padding: 1.3rem 1.6rem;
           display: flex; align-items: center; gap: 1.1rem;
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
.sp-hero h1 { color: #ffffff; font-size: 1.85rem; font-weight: 800; margin: .35rem 0 .15rem; padding: 0;
              line-height: 1.15; }
.sp-hero-ic { flex: none; width: 3.6rem; height: 3.6rem; border-radius: 16px; display: grid; place-items: center;
              background: rgba(255,255,255,.1); border: 1px solid rgba(255,255,255,.16); color: #86efac; }
.sp-hero-ic .mi { font-size: 2rem; }
.sp-hero p { color: rgba(242,251,245,.82); font-size: 1rem; margin: 0; max-width: 820px; line-height: 1.5; }
.sp-hero p strong { color: #fff; }

/* ---------- section headings ---------- */
.sp-section { display: flex; flex-wrap: wrap; align-items: baseline; gap: .1rem .6rem; margin: 1.6rem 0 .6rem; }
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
/* Imboni logo, white-lettering variant on the dark sidebar (no background) */
[data-testid="stSidebarLogo"] { height: 3.2rem !important; max-width: 100% !important; width: auto !important;
                                margin-top: 1.3rem; }
[data-testid="stSidebarHeader"] { padding-bottom: .9rem; height: auto !important; }
[data-testid="stHeaderLogo"] { height: 2.2rem !important; }
.sp-side-note { font-size: .78rem; line-height: 1.55; color: rgba(220,239,228,.88);
                border-top: 1px solid rgba(255,255,255,.08); padding-top: .9rem; margin-top: .5rem; }
.sp-side-note b { color: #dcefe4; }

/* ---------- toolbar (filters) ---------- */
.st-key-toolbar { background: rgba(22,163,74,0.035); border: 1px solid rgba(128,128,128,0.18) !important;
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
.st-key-toolbar2 { background: rgba(22,163,74,0.035); border: 1px solid rgba(128,128,128,0.18) !important;
                   border-radius: 16px !important; padding: .8rem 1.1rem .5rem !important; margin-bottom: .2rem; }
.st-key-atool { background: rgba(22,163,74,0.035); border: 1px solid rgba(128,128,128,0.18) !important;
                border-radius: 16px 16px 0 0 !important; padding: .9rem 1.1rem .4rem !important; }
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
.sp-kpis { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: .9rem; margin-bottom: 1rem; }
.sp-kpi { display: flex; gap: .85rem; align-items: center; border: 1px solid rgba(128,128,128,.18);
          border-radius: 16px; padding: 1rem 1.05rem;
          background: linear-gradient(150deg, color-mix(in srgb, var(--c) 8%, transparent), transparent 65%); }
.sp-kpi-ic { flex: none; width: 2.8rem; height: 2.8rem; border-radius: 12px; display: grid; place-items: center;
             color: var(--c); background: color-mix(in srgb, var(--c) 14%, transparent); }
.sp-kpi-ic .mi { font-size: 1.5rem; }
.sp-kpi b { display: block; font-size: 1.75rem; font-weight: 800; letter-spacing: -.03em; line-height: 1.05; }
.sp-kpi span { display: block; font-size: .86rem; font-weight: 650; }
.sp-kpi small { display: block; font-size: .74rem; opacity: .58; }
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
  .sp-finds { grid-template-columns: 1fr; }
  .sp-plans { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .sp-alerts { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .sp-tiles { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}

@media (max-width: 640px) {
  .sp-plans, .sp-alerts { grid-template-columns: 1fr; }
  .sp-steps, .sp-crops { grid-template-columns: 1fr 1fr; }
  .sp-kpi b { font-size: 1.4rem; }
  .block-container { padding-top: 3.6rem; }
  /* KPI rows: two cards per line instead of one tall stack */
  [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] [data-testid="stMetric"]) {
      flex-wrap: wrap !important; flex-direction: row !important; gap: .6rem !important; }
  [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] [data-testid="stMetric"]) > [data-testid="stColumn"] {
      width: calc(50% - .3rem) !important; flex: 1 1 calc(50% - .3rem) !important; min-width: calc(50% - .3rem) !important; }
  [data-testid="stMetricValue"] { font-size: 1.5rem; }
  .sp-hero { padding: 1.2rem 1.1rem; border-radius: 14px; }
  .sp-hero h1 { font-size: 1.55rem; }
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


def hero(title: str, subtitle: str, eyebrow: str = "Imboni", ic: str = "eco") -> None:
    """Gradient page header with an icon tile. `subtitle` may contain **bold** (converted) but no other markup."""
    sub = html.escape(subtitle)
    while "**" in sub:
        sub = sub.replace("**", "<strong>", 1).replace("**", "</strong>", 1)
    st.markdown(f'<div class="sp-hero"><div class="sp-hero-ic">{icon(ic)}</div><div>'
                f'<span class="sp-eyebrow">{html.escape(eyebrow)}</span>'
                f'<h1>{html.escape(title)}</h1><p>{sub}</p></div></div>', unsafe_allow_html=True)


def section(title: str, note: str = "") -> None:
    st.markdown(f'<div class="sp-section"><div class="sp-h">{html.escape(title)}</div>'
                f'<span>{html.escape(note)}</span></div>', unsafe_allow_html=True)


def nz(n, empty: str = "None"):
    """A count for display: never show a bare 0 in the design, use a word instead."""
    return empty if not n else n


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
