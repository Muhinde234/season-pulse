import html

import pandas as pd
import streamlit as st

from core.data import CROPS, PROVINCES, SEASONS, current_season, fmt_pct, pct_vs_typical
from core.db import get_reports
from core.risk import DRY_PCT, HIGH, LEVELS, SURPLUS, TRADITIONAL_PCT, WATCH, adjusted_table
from core.ui import LEVEL_STYLE, badge, hero, icon, nz

# Recommended actions, keyed by the labels core.risk.recommended_actions produces:
# (material icon, colour, short name, what it means, when the rule fires)
ACTIONS = {
    "💧 Small-scale irrigation": (
        "water_drop", "#0284c7", "Irrigation", "Support small-scale irrigation: pumps, water harvesting, drip kits.",
        f"Below typical, with rain problems, rainfall ≥{-DRY_PCT}% below average, or ≥{TRADITIONAL_PCT}% "
        "traditional irrigation."),
    "🌱 Soil testing & fertility support": (
        "science", "#16a34a", "Soil fertility", "Soil testing, lime and fertiliser support.",
        "Below typical in 3+ years of data, with no rainfall problem."),
    "🏚️ Post-harvest collection & storage": (
        "warehouse", "#b45309", "Post-harvest storage", "Plan collection, drying and storage before harvest.",
        "Expected above the typical district."),
    "🏭 Value addition / processing": (
        "factory", "#7c3aed", "Value addition", "Link the surplus to cooperatives and food processors.",
        f"≥{round((SURPLUS - 1) * 100)}% above typical, with co-ops or processors at or above the median district."),
    "🚢 Export opportunity": (
        "public", "#0f766e", "Export", "Connect the surplus with goods exporters.",
        f"≥{round((SURPLUS - 1) * 100)}% above typical, with exporters at or above the median district."),
}
SHORT = {v[2]: k for k, v in ACTIONS.items()}  # short name -> label
TINY = {"Irrigation": "Irrigation", "Soil fertility": "Soil", "Post-harvest storage": "Storage",
        "Value addition": "Processing", "Export": "Export"}  # fits the list column
METER = 60  # risk meter spans -60% ... +60% vs typical

hero("Alerts & Recommended Actions", "Where yields are at risk this season, and what to do.",
     eyebrow="Monitor · Alerts", ic="notifications_active")

# ---------- filters ----------
seasons = list(SEASONS)
with st.container(key="atool"):
    c1, c2, c3 = st.columns([1.15, 1, 1], vertical_alignment="bottom")
    season = c1.segmented_control("Season", seasons, default=current_season(), key="al_season",
                                  format_func=lambda s: SEASONS[s].split(" (")[0]) or current_season()
    levels = c2.pills("Risk level", list(LEVELS), default=["High", "Watch"], selection_mode="multi",
                      key="al_levels") or list(LEVELS)
    provinces = c3.multiselect("Province", list(PROVINCES), placeholder="All provinces", key="al_prov",
                               format_func=lambda p: p.replace(" Province", ""))
    c4, c6 = st.columns([3, 1], vertical_alignment="bottom")
    crops = c4.pills("Crop", CROPS, default=CROPS, selection_mode="multi", key="al_crops") or CROPS

reports = get_reports(season, include_simulated=st.session_state.get("al_sim", True))
t = adjusted_table(season, reports)
t = t[t.CropName.isin(crops) & (t.Province.isin(provinces) if provinces else True)]
n_sim = int(reports.is_simulated.sum())
has = {name: t.action.str.contains(label, regex=False) for name, label in SHORT.items()}

with st.container(key="toolbar2"):
    acts = st.pills("Recommended action", list(SHORT), selection_mode="multi", key="al_acts",
                    format_func=lambda a: f":material/{ACTIONS[SHORT[a]][0]}: {a}"
                                          + (f" · {int(has[a].sum())}" if has[a].sum() else ""))
with c6:
    with st.popover("How to read", icon=":material/help:", width="stretch"):
        st.markdown(f"""
**Expected yield** is shown as % vs the *typical district* (the median district for that crop and season).
It starts from the 2020–2024 history and moves with this season's field reports.

**Risk level**
- **High**: expected ≥{round((1 - HIGH) * 100)}% below typical
- **Watch**: ≥{round((1 - WATCH) * 100)}% below
- **Normal**: anything else

**Priority** ranks alerts at the same level: shortfall × how much households in the district eat the crop
(EICV 2020). The bigger the shortfall and the food dependence, the higher it ranks.

**Actions** are simple, transparent rules (hover an action in the detail panel to see its rule).
Local partner counts come from the NISR Establishment Census.
""")
        st.toggle("Include simulated reports", value=True, key="al_sim")

# ---------- status + tiles (after crop/province filters, before level/action filters) ----------
if n_sim:
    note = ("science", f"<b>{n_sim} of {len(reports)}</b> reports are simulated demo data", "warn")
elif reports.empty:
    note = ("info", "No field reports yet this season: estimates use the historical baseline only", "info")
else:
    note = None  # the Reports tile already says it
if note:
    st.markdown(f'<div class="sp-note sp-note-{note[2]}">{icon(note[0])}<span>{note[1]}</span></div>',
                unsafe_allow_html=True)

total = max(len(t), 1)
level_help = {"High": f"≥{round((1 - HIGH) * 100)}% below typical", "Watch": f"≥{round((1 - WATCH) * 100)}% below",
              "Normal": "near or above typical"}
covered = int((t.n_reports > 0).sum())
tiles = "".join(
    f'<div class="sp-tile" style="--c:{LEVEL_STYLE[lvl]}"><div class="sp-tile-h">{badge(lvl)}'
    f'<span>{level_help[lvl]}</span></div><div class="sp-tile-n">{nz(int((t.level == lvl).sum()))}</div>'
    f'<div class="sp-tile-bar"><i style="width:{100 * (t.level == lvl).sum() / total:.0f}%"></i></div></div>'
    for lvl in LEVELS)
tiles += (f'<div class="sp-tile" style="--c:#475569"><div class="sp-tile-h"><span class="sp-badge" '
          f'style="--c:#475569">Reports</span><span>'
          f'{f"{covered} of {len(t)} district-crops covered" if covered else "no district-crop covered yet"}'
          f'</span></div><div class="sp-tile-n">{nz(len(reports), "None yet")}</div><div class="sp-tile-bar"><i style="width:'
          f'{100 * covered / total:.0f}%"></i></div></div>')
st.markdown(f'<div class="sp-tiles">{tiles}</div>', unsafe_allow_html=True)

# ---------- list ----------
view = t[t.level.isin(levels)]
if acts:
    view = view[pd.concat([has[a] for a in acts], axis=1).any(axis=1).reindex(view.index, fill_value=False)]
view = view.reset_index(drop=True)


def short_actions(a: str) -> str:
    return ", ".join(ACTIONS[x][2] for x in a.split(" · ") if x in ACTIONS) or "Monitor"


def why(r) -> list[tuple[str, str]]:
    out = [("history", f"Historically <b>{fmt_pct(r.baseline_RYI)}</b> vs typical over {int(r.n_years)} years"
                       + (", <b>persistently low</b>" if r.persistently_low else ""))]
    if r.n_reports:
        bits = [f"avg condition {r.mean_condition:.1f}/5"]
        if r.rain_share:
            bits.append(f"{r.rain_share:.0%} rain problems")
        if r.pest_share:
            bits.append(f"{r.pest_share:.0%} pests")
        sim = f" ({int(r.n_simulated)} simulated)" if r.n_simulated else ""
        out.append(("edit_note", f"<b>{int(r.n_reports)} field reports</b>{sim}: " + ", ".join(bits)))
    else:
        out.append(("edit_note", "No field reports yet: the estimate is the historical baseline"))
    if pd.notna(r.rain_anom_pct):
        out.append(("rainy", f"Rain <b>{r.rain_anom_pct:+.0f}%</b> vs the district average "
                             f"({html.escape(r.rain_period)}{', partial season' if r.rain_partial else ''})"))
    if pd.notna(r.traditional_pct):
        out.append(("water_drop", f"<b>{r.traditional_pct:.0f}%</b> of irrigated plots use traditional methods"))
    out.append(("restaurant", f"<b>{r.food_level}</b> food dependence: household consumption of {r.CropName.lower()} "
                              "compared with other districts"))
    return out


def detail(r) -> str:
    p = float(pct_vs_typical(r.adjusted_RYI))
    pos = (max(min(p, METER), -METER) + METER) / (2 * METER) * 100
    shift = p - float(pct_vs_typical(r.baseline_RYI))
    sub = f"{shift:+.0f} pts from field reports" if r.n_reports else "historical baseline"
    reasons = "".join(f'<li>{icon(ic)}<span>{txt}</span></li>' for ic, txt in why(r))
    todo = [a for a in r.action.split(" · ") if a in ACTIONS]
    steps = "".join(
        f'<div class="sp-act" style="--c:{ACTIONS[a][1]}" title="Rule: {html.escape(ACTIONS[a][4])}">'
        f'<div class="sp-act-ic">{icon(ACTIONS[a][0])}</div><div><b>{ACTIONS[a][2]}</b>'
        f'<span>{html.escape(ACTIONS[a][3])}</span><small>Why: {html.escape(ACTIONS[a][4])}</small></div></div>'
        for a in todo) or ('<div class="sp-act" style="--c:#64748b"><div class="sp-act-ic">'
                           f'{icon("visibility")}</div><div><b>Monitor</b><span>No rule fires: keep collecting '
                           'field reports.</span></div></div>')
    partners = [("groups", int(r.cooperatives), "co-ops"), ("factory", int(r.food_processors), "processors"),
                ("public", int(r.exporters), "exporters")]
    foot = "".join(f'<div>{icon(ic)}<b>{nz(v, "–")}</b><span>{k}</span></div>' for ic, v, k in partners)
    return (f'<div class="sp-alert sp-detail" style="--c:{LEVEL_STYLE[r.level]}">'
            f'<div class="sp-alert-top">{badge(r.level)}<span class="sp-rank-no">'
            f'{f"priority {r.priority:.2f}" if r.priority else ""}</span></div>'
            f'<div class="sp-alert-t">{html.escape(r.DistrictName)} · {html.escape(r.CropName)}</div>'
            f'<div class="sp-alert-p">{html.escape(r.Province)} · {SEASONS[season].split(" (")[0]}</div>'
            f'<div class="sp-alert-v">{fmt_pct(r.adjusted_RYI)}<small>expected vs typical district · {sub}</small></div>'
            f'<div class="sp-meter"><span class="sp-meter-0"></span><i style="left:{pos:.1f}%"></i></div>'
            f'<div class="sp-meter-l"><span>−{METER}%</span><span>typical</span><span>+{METER}%</span></div>'
            f'<div class="sp-alert-h">Why this alert</div><ul class="sp-why">{reasons}</ul>'
            f'<div class="sp-alert-h">What to do</div><div class="sp-acts">{steps}</div>'
            f'<div class="sp-alert-h">Local partners in {html.escape(r.DistrictName)}</div>'
            f'<div class="sp-alert-f sp-partners">{foot}</div></div>')


left, right = st.columns([1.6, 1], gap="medium")
with left:
    if len(view):
        st.markdown(f'<div class="sp-list-h"><b>{len(view)}</b> alert{"s" if len(view) > 1 else ""} '
                    '<span>· select a row for details</span></div>', unsafe_allow_html=True)
    if view.empty:
        st.info("No alerts match these filters.", icon=":material/filter_alt_off:")
        sel = None
    else:
        table = view.assign(Expected=pct_vs_typical(view.adjusted_RYI),
                            Actions=view.action.map(lambda a: " · ".join(TINY[n] for n in short_actions(a).split(", ")
                                                                           if n in TINY) or "Monitor"))
        event = st.dataframe(
            table, hide_index=True, width="stretch", height=560, on_select="rerun", selection_mode="single-row",
            key=f"al_table_{season}",
            column_order=["level", "DistrictName", "CropName", "Expected", "priority", "Actions"],
            column_config={
                "level": st.column_config.TextColumn("Level", width=58),
                "DistrictName": st.column_config.TextColumn("District", width=100),
                "CropName": st.column_config.TextColumn("Crop", width=100),
                "Expected": st.column_config.NumberColumn("Exp.", format="%+d%%", width=58,
                                                          help="Expected % vs typical district this season"),
                "priority": st.column_config.ProgressColumn(
                    "Priority", format="%.2f", min_value=0, max_value=max(float(t.priority.max()), 0.01), width=95,
                    help="Shortfall × food dependence: orders alerts within a level"),
                "Actions": st.column_config.TextColumn("Actions", width="medium"),
            })
        rows = event.selection.rows
        sel = view.iloc[rows[0] if rows and rows[0] < len(view) else 0]
    export = t.assign(actions=t.action.map(short_actions)).drop(columns=["baseline_logRYI", "baseline_log", "action"])
    st.download_button("Download full ranking (CSV)", export.to_csv(index=False), icon=":material/download:",
                       file_name=f"imboni_alerts_{season}.csv", mime="text/csv")
with right:
    if sel is not None:
        st.markdown(detail(sel), unsafe_allow_html=True)
