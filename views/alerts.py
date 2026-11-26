import html

import pandas as pd
import streamlit as st

from core.data import CROPS, SEASONS, fmt_pct, pct_vs_typical, season_year
from core.db import get_reports
from core.official import attach_official, seasons_for, year_label, year_options
from core.risk import DRY_PCT, HIGH, LEVELS, SURPLUS, TRADITIONAL_PCT, WATCH, adjusted_table
from core.ui import LEVEL_STYLE, badge, filter_head, hero, icon, nz

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

hero("Alerts & Recommended Actions", "Where yields are at risk, and what to do.",
     eyebrow="Monitor · Alerts", ic="notifications_active")

# ---------- filters (dropdowns; an empty dropdown means "all") ----------
NOW_YEAR = season_year()
FILTER_DEFAULTS = {"af_year": NOW_YEAR, "af_levels": ["High", "Watch"], "af_crops": [], "af_acts": [], "al_sim": True}


def is_default(key: str, value) -> bool:
    d = FILTER_DEFAULTS[key]
    return sorted(value or []) == sorted(d) if isinstance(d, list) else value == d


def reset_filters() -> None:
    for k in list(st.session_state):  # dropping the stored value lets every widget start from its default again
        if k in FILTER_DEFAULTS or k.startswith("af_season_"):
            st.session_state.pop(k, None)


n_active = sum(not is_default(k, st.session_state[k]) for k in FILTER_DEFAULTS if k in st.session_state)
with st.container(key="atool"):
    h1, h2, h3 = st.columns([4.2, 1.1, .8], vertical_alignment="center")
    h1.markdown(filter_head(n_active, "Showing High and Watch alerts" if not n_active else ""),
                unsafe_allow_html=True)
    h3.button("Reset", icon=":material/restart_alt:", type="tertiary", on_click=reset_filters,
              disabled=not n_active, width="stretch", key="al_reset")
    c1, c2, c3, c4, c5 = st.columns([1.25, .8, 1.3, 1.1, 1.3], vertical_alignment="bottom")
    year = c1.selectbox("Year", year_options(), format_func=year_label, key="af_year")
    season = c2.selectbox("Season", seasons_for(year), key=f"af_season_{year}",
                          format_func=lambda s: SEASONS[s].split(" (")[0])
    levels = c3.multiselect("Risk level", list(LEVELS), default=["High", "Watch"], key="af_levels",
                            placeholder="All levels") or list(LEVELS)
    crops = c4.multiselect("Crop", CROPS, key="af_crops", placeholder="All crops") or CROPS

    current = year == NOW_YEAR
    reports = get_reports(season, include_simulated=st.session_state.get("al_sim", True))
    if not current:  # a past season: NISR's official results, no field reports
        reports = reports.iloc[0:0]
    t = adjusted_table(season, reports, None if current else year)
    t = t[t.CropName.isin(crops)]
    t = attach_official(t, season, None if current else year)  # official yield, area, tonnes below typical
    n_sim = int(reports.is_simulated.sum())
    has = {name: t.action.str.contains(label, regex=False) for name, label in SHORT.items()}
    acts = c5.multiselect("Recommended action", list(SHORT), key="af_acts", placeholder="All actions",
                          format_func=lambda a: f"{a} ({int(has[a].sum())})" if has[a].sum() else a)
def guide_html() -> str:
    """The "How to read" guide: four short sections built from the same thresholds and rules the page uses."""
    def block(ic: str, title: str, body: str) -> str:
        return (f'<div class="sp-g-block"><div class="sp-g-ic">{icon(ic)}</div><div><b>{title}</b>{body}</div></div>')

    levels = "".join(
        f'<div class="sp-g-level">{badge(lvl)}<span>{rule}</span></div>'
        for lvl, rule in [("High", f"expected ≥{round((1 - HIGH) * 100)}% below typical"),
                          ("Watch", f"≥{round((1 - WATCH) * 100)}% below typical"),
                          ("Normal", "near or above typical")])
    actions = "".join(
        f'<div class="sp-g-act" style="--c:{c}"><span class="sp-g-act-ic">{icon(ic)}</span>'
        f'<div><b>{html.escape(name)}</b><small>{html.escape(rule)}</small></div></div>'
        for ic, c, name, _, rule in ACTIONS.values())
    return (
        '<div class="sp-guide"><div class="sp-g-title">How to read this page</div>'
        + block("insights", "Expected yield",
                '<p>Shown as <strong>% vs the typical district</strong>: the median district for the same crop '
                'and season. It starts from the district\'s latest official NISR result for the same season '
                '(tomatoes: 2020–2024 cleaned files) and moves with this season\'s field reports.</p>'
                '<div class="sp-g-scale"><span>below typical</span><span>typical</span><span>above</span></div>')
        + block("crisis_alert", "Risk level", f'<div class="sp-g-levels">{levels}</div>')
        + block("trending_down", "Priority",
                '<p>Ranks alerts within the same level.</p><div class="sp-g-formula">shortfall '
                '<i>×</i> food dependence</div><p class="sp-g-note">Food dependence = the crop\'s share of household '
                'food spending in the district, compared with other districts (EICV 2020).</p>')
        + block("task_alt", "Recommended actions", f'<div class="sp-g-acts">{actions}</div>')
        + '<div class="sp-g-foot">Local partner counts: NISR Establishment Census · Rainfall: CHIRPS · '
          'Irrigation: SAS 2026 Season A</div></div>')


with h2:
    with st.popover("How to read", icon=":material/help:", width="stretch"):
        st.markdown(guide_html(), unsafe_allow_html=True)
        st.toggle("Include simulated reports", value=True, key="al_sim")

# ---------- apply every filter: the tiles and the list both follow them ----------
view = t[t.level.isin(levels)]
if acts:
    view = view[pd.concat([has[a] for a in acts], axis=1).any(axis=1).reindex(view.index, fill_value=False)]
view = view.reset_index(drop=True)
crop_reports = reports[reports.crop.isin(crops)] if len(reports) else reports

# ---------- status + tiles ----------
season_name = f"{SEASONS[season].split(' (')[0]} {year}"
if not current:
    note = ("history", f"Looking back: NISR's official results for <b>{season_name}</b>. Levels show how each "
                       "district actually did; no field reports apply.", "info")
elif n_sim:
    note = ("science", f"<b>{n_sim} of {len(reports)}</b> reports are simulated demo data", "warn")
elif reports.empty:
    note = ("info", "No field reports yet this season: estimates are the baseline only", "info")
else:
    note = None  # the Reports tile already says it
if note:
    st.markdown(f'<div class="sp-note sp-note-{note[2]}">{icon(note[0])}<span>{note[1]}</span></div>',
                unsafe_allow_html=True)

total = max(len(view), 1)
level_help = {"High": f"≥{round((1 - HIGH) * 100)}% below typical", "Watch": f"≥{round((1 - WATCH) * 100)}% below",
              "Normal": "near or above typical"}
covered = int((view.n_reports > 0).sum())


def tonnes_note(lvl: str) -> str:
    tons = view.loc[view.level == lvl, "tonnes_below"].sum()
    return f" · ≈{tons:,.0f} t below typical" if lvl != "Normal" and tons >= 1 else ""


tiles = "".join(
    f'<div class="sp-tile" style="--c:{LEVEL_STYLE[lvl]}"><div class="sp-tile-h">{badge(lvl)}'
    f'<span>{level_help[lvl]}{tonnes_note(lvl)}</span></div><div class="sp-tile-n">{nz(int((view.level == lvl).sum()))}</div>'
    f'<div class="sp-tile-bar"><i style="width:{100 * (view.level == lvl).sum() / total:.0f}%"></i></div></div>'
    for lvl in LEVELS)
reports_sub = ("past season: no field reports" if not current else
               f"{covered} of {len(view)} district-crops covered" if covered else "no district-crop covered yet")
tiles += (f'<div class="sp-tile" style="--c:#475569"><div class="sp-tile-h"><span class="sp-badge" '
          f'style="--c:#475569">Reports</span><span>{reports_sub}</span></div>'
          f'<div class="sp-tile-n">{nz(len(crop_reports), "None" if not current else "None yet")}</div>'
          f'<div class="sp-tile-bar"><i style="width:{100 * covered / total:.0f}%"></i></div></div>')
st.markdown(f'<div class="sp-tiles">{tiles}</div>', unsafe_allow_html=True)


def short_actions(a: str) -> str:
    return ", ".join(ACTIONS[x][2] for x in a.split(" · ") if x in ACTIONS) or "Monitor"


def why(r) -> list[tuple[str, str]]:
    if pd.notna(r.source_season):
        prev = f" (a year earlier: {fmt_pct(r.prev_RYI)})" if pd.notna(r.prev_RYI) else ""
        out = [("history", f"<b>{fmt_pct(r.baseline_RYI)}</b> vs typical in {html.escape(r.baseline_source)}{prev}"
                           + (", <b>below 0.8 in each of the last 3 years</b>" if r.persistently_low else ""))]
    else:
        out = [("history", f"<b>{fmt_pct(r.baseline_RYI)}</b> vs typical over {int(r.n_years)} years of the "
                           "cleaned 2020–2024 files (NISR doesn't publish tomatoes separately, so this is not "
                           "validated)" + (", <b>persistently low</b>" if r.persistently_low else ""))]
    if r.n_reports:
        bits = [f"avg condition {r.mean_condition:.1f}/5"]
        if r.rain_share:
            bits.append(f"{r.rain_share:.0%} rain problems")
        if r.pest_share:
            bits.append(f"{r.pest_share:.0%} pests")
        sim = f" ({int(r.n_simulated)} simulated)" if r.n_simulated else ""
        out.append(("edit_note", f"<b>{int(r.n_reports)} field reports</b>{sim}: " + ", ".join(bits)))
    else:
        out.append(("edit_note", "No field reports yet: the estimate is the baseline" if current else "Past season: official result, no field reports"))
    if pd.notna(r.rain_anom_pct):
        out.append(("rainy", f"Rain <b>{r.rain_anom_pct:+.0f}%</b> vs the district average "
                             f"({html.escape(r.rain_period)}{', partial season' if r.rain_partial else ''})"))
    if pd.notna(r.traditional_pct):
        out.append(("water_drop", f"<b>{r.traditional_pct:.0f}%</b> of irrigated plots use traditional methods"))
    if r.food_level == "No data":
        out.append(("restaurant", f"Food dependence unknown: EICV 2020 doesn't cover {r.CropName.lower()}"))
    else:
        out.append(("restaurant", f"<b>{r.food_level}</b> food dependence: {r.CropName.lower()}'s share of household "
                                  "food spending, compared with other districts"))
    return out


def stake(r) -> str:
    """Production at stake, from NISR's latest official season (absent for tomatoes)."""
    if pd.isna(r.off_yield_kgha):
        return ""
    tons = f"≈{r.tonnes_below:,.0f} t" if r.tonnes_below >= 1 else "No shortfall"
    season_name = f"{r.off_season[:4]} Season {r.off_season[-1]}"
    return (f'<div class="sp-stake"><div><b>{tons}</b><span>below a typical district\'s harvest</span></div>'
            f'<div><b>{r.off_yield_kgha:,.0f} kg/ha</b><span>official {season_name} · median district '
            f'{r.off_median_kgha:,.0f}</span></div><div><b>{r.off_harvested_ha:,.0f} ha</b>'
            f'<span>harvested · NISR SAS</span></div></div>')


def detail(r) -> str:
    p = float(pct_vs_typical(r.adjusted_RYI))
    pos = (max(min(p, METER), -METER) + METER) / (2 * METER) * 100
    shift = p - float(pct_vs_typical(r.baseline_RYI))
    sub = (f"{shift:+.0f} pts from field reports" if r.n_reports else "baseline, no reports yet") if current else "official NISR result"
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
            f'<div class="sp-alert-p">{html.escape(r.Province)} · {season_name}</div>'
            f'<div class="sp-alert-v">{fmt_pct(r.adjusted_RYI)}<small>{"expected" if current else "actual"} vs typical district · {sub}</small></div>'
            f'<div class="sp-meter"><span class="sp-meter-0"></span><i style="left:{pos:.1f}%"></i></div>'
            f'<div class="sp-meter-l"><span>−{METER}%</span><span>typical</span><span>+{METER}%</span></div>'
            f'{stake(r)}'
            f'<div class="sp-alert-h">Why this alert</div><ul class="sp-why">{reasons}</ul>'
            f'<div class="sp-alert-h">What to do</div><div class="sp-acts">{steps}</div>'
            f'<div class="sp-alert-h">Local partners in {html.escape(r.DistrictName)}</div>'
            f'<div class="sp-alert-f sp-partners">{foot}</div></div>')


left, right = st.columns([1.6, 1], gap="medium")
with left:
    if len(view):
        st.markdown(f'<div class="sp-list-h"><b>{len(view)}</b> alert{"s" if len(view) > 1 else ""} '
                    '<span>· select a row for details</span></div>', unsafe_allow_html=True)
        st.caption(f"**{'Exp.' if current else 'Result'}** = yield vs the typical (median) district for the same crop "
                   "and season: −30% means 30% less per hectare. **High** = 25% or more below, **Watch** = 15% or "
                   "more below. **Priority** puts crops that households depend on more first. **At stake** = tonnes "
                   "below a typical district's harvest.")
    if view.empty:
        st.info("No alerts match these filters.", icon=":material/filter_alt_off:")
        sel = None
    else:
        table = view.assign(Expected=pct_vs_typical(view.adjusted_RYI),
                            tonnes_below=view.tonnes_below.map(lambda v: f"{v:,.0f} t" if v == v and v >= 1 else "–"),
                            Actions=view.action.map(lambda a: " · ".join(TINY[n] for n in short_actions(a).split(", ")
                                                                           if n in TINY) or "Monitor"))
        event = st.dataframe(
            table, hide_index=True, width="stretch", height=560, on_select="rerun", selection_mode="single-row",
            key=f"al_table_{year}{season}",
            column_order=["level", "DistrictName", "CropName", "Expected", "priority", "tonnes_below", "Actions"],
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
                "tonnes_below": st.column_config.TextColumn(
                    "At stake", width=80,
                    help="Tonnes below a typical district's harvest: official harvested area × median district yield × expected shortfall (NISR SAS, latest season)"),
            })
        rows = event.selection.rows
        sel = view.iloc[rows[0] if rows and rows[0] < len(view) else 0]
    export = t.assign(actions=t.action.map(short_actions)).drop(columns=["baseline_log", "action"])
    st.download_button("Download full ranking (CSV)", export.to_csv(index=False), icon=":material/download:",
                       file_name=f"imboni_alerts_{year}{season[-1]}.csv", mime="text/csv")
with right:
    if sel is not None:
        st.markdown(detail(sel), unsafe_allow_html=True)
