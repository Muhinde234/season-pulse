"""What changed, 2022-2026: production, area and yield per crop from NISR's official tables, with plain-language
explanations of every calculation."""
import html

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core.data import DISTRICT_PROVINCE
from core.official import SOURCE_URL, load_district_crops
from core.ui import hero, icon, section

CROPS = ["Maize", "Beans", "Irish potato", "Cassava", "Sweet potato", "Paddy rice", "Cooking banana", "Wheat",
         "Soybean"]
LEAF, RED, GOLD, MUTED, GRID = "#1F8A43", "#dc2626", "#E0A100", "#5E6E65", "rgba(14,59,34,.10)"
LAYOUT = dict(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", hoverlabel=dict(bgcolor="white"))


def note(text: str, ic: str = "info") -> None:
    st.markdown(f'<div class="sp-note sp-note-info">{icon(ic)}<span>{text}</span></div>', unsafe_allow_html=True)


dc = load_district_crops()
dc = dc[dc.crop.isin(CROPS) & dc.season.str[-1].isin(["A", "B"])].assign(year=lambda d: d.season.str[:4].astype(int))
years = sorted(dc.year.unique())
first, last = years[0], years[-1]

# national = sum of districts (they add up exactly to NISR's national totals), Seasons A + B
nat = dc.groupby(["crop", "year"])[["production_mt", "harvested_ha"]].sum().reset_index()
nat["yield_t_ha"] = nat.production_mt / nat.harvested_ha
w = nat.pivot(index="crop", columns="year")
chg = pd.DataFrame({
    "production": w.production_mt[last] / w.production_mt[first] - 1,
    "area": w.harvested_ha[last] / w.harvested_ha[first] - 1,
    "yield": w.yield_t_ha[last] / w.yield_t_ha[first] - 1,
}).reindex(CROPS)
# the bigger of the two changes (in size) is the main driver
chg["driver"] = np.where(chg.area.abs() > chg["yield"].abs(), "land", "yield")

hero(f"Trends {first}–{last}", "How production, land and yields changed, crop by crop, and where.",
     eyebrow="Plan · What changed", ic="chart-line",
     meta=[("calendar", f"Seasons A + B, {first}–{last}"), ("database", "NISR SAS official tables")])

up = chg[chg.production > 0]
by_land = chg[chg.driver == "land"]
st.markdown('<div class="sp-kpis">' + "".join(
    f'<div class="sp-kpi" style="--c:{c}"><div class="sp-kpi-ic">{icon(ic)}</div><div><b>{html.escape(n)}</b>'
    f'<span>{html.escape(label)}</span><small>{html.escape(sub)}</small></div></div>' for ic, c, n, label, sub in [
        ("trending_down", LEAF, f"{len(up)} of {len(chg)}", "Crops producing more", f"{first} → {last}"),
        ("layers", GOLD, f"{len(by_land)} of {len(chg)}", "Changes driven mainly by land",
         "area changed more than yield"),
        ("verified", LEAF, chg["yield"].idxmax(), "Biggest yield gain", f"{chg['yield'].max():+.0%} per hectare"),
        ("crisis_alert", RED, chg["yield"].idxmin(), "Biggest yield fall", f"{chg['yield'].min():+.0%} per hectare"),
    ]) + "</div>", unsafe_allow_html=True)

# ---------- 1. production = land x yield ----------
section("1 · Did production grow because of more land or better yields?", f"change {first} → {last}, Seasons A + B")
c = chg.sort_values("production")
fig = go.Figure()
for col, name, color in [("area", "Harvested area", GOLD), ("yield", "Yield per hectare", LEAF),
                         ("production", "Production", "#0E3B22")]:
    fig.add_bar(y=c.index, x=100 * c[col], orientation="h", name=name, marker=dict(color=color, cornerradius=3),
                hovertemplate="<b>%{y}</b><br>" + name + ": %{x:+.1f}%<extra></extra>")
fig.add_vline(x=0, line=dict(color=MUTED, width=1))
fig.update_layout(**LAYOUT, barmode="group", height=470, margin=dict(l=0, r=10, t=10, b=0), bargap=.25,
                  legend=dict(orientation="h", y=-0.08, x=0), xaxis=dict(ticksuffix="%", gridcolor=GRID),
                  yaxis=dict(showgrid=False))
c1, c2 = st.columns([1.5, 1])
c1.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
with c2:
    def story(crop: str, r) -> str:
        land = f"{'more' if r.area > 0 else 'less'} land ({r.area:+.0%})"
        yld = f"{'higher' if r['yield'] > 0 else 'lower'} yields ({r['yield']:+.0%})"
        if r.area * r["yield"] >= 0:  # same direction: name the bigger one first
            big, small = (land, yld) if abs(r.area) > abs(r["yield"]) else (yld, land)
            how = f"mostly {big}, plus {small}"
        else:  # opposite directions: the one pointing the same way as production won (changes multiply)
            big, small = (land, yld) if r.area * r.production > 0 else (yld, land)
            how = f"{big} outweighed {small}"
        return f"<b>{crop}</b>: production {r.production:+.0%}: {how}"

    lines = [story(crop, r) for crop, r in chg.sort_values("production").iterrows()]
    st.markdown("**What it says**<br>" + "<br>".join(lines), unsafe_allow_html=True)
note("<b>How it's calculated.</b> Production = harvested area × yield. If a crop is planted on 10% more land and "
     "each hectare gives 5% more, production grows by about 10% + 5% = 15% (exactly 1.10 × 1.05 − 1 = 15.5%). So "
     "comparing the area and yield bars shows what drove the change. Yield is what PSTA 5 targets: more food from "
     "the same land.", "insights")

# ---------- 2. yield trend ----------
section("2 · Yield per hectare, year by year", f"index: {first} = 100, Seasons A + B")
pick = st.multiselect("Crops", CROPS, default=["Maize", "Beans", "Irish potato", "Cassava", "Paddy rice"],
                      key="tr_crops") or CROPS
fig2 = go.Figure()
for crop in pick:
    d = nat[nat.crop == crop].sort_values("year")
    base = float(d[d.year == first].yield_t_ha.iloc[0])
    fig2.add_scatter(x=d.year, y=100 * d.yield_t_ha / base, mode="lines+markers", name=crop,
                     customdata=d.yield_t_ha, hovertemplate=crop + " %{x}: %{customdata:.2f} t/ha (index %{y:.0f})"
                                                             "<extra></extra>")
fig2.add_hline(y=100, line=dict(color=MUTED, width=1, dash="dot"))
fig2.update_layout(**LAYOUT, height=380, margin=dict(l=0, r=0, t=10, b=0), legend=dict(orientation="h", y=-0.15),
                   xaxis=dict(tickvals=years, gridcolor=GRID), yaxis=dict(title="index", gridcolor=GRID))
st.plotly_chart(fig2, width="stretch", config={"displayModeBar": False})
note(f"<b>How to read an index.</b> Each crop's {first} yield is set to 100. A value of 110 means 10% more per hectare "
     f"than in {first}; 95 means 5% less. It lets crops with very different yields (cassava ≈ 14 t/ha, beans ≈ 0.7 "
     "t/ha) share one chart.", "insights")

# ---------- 3. where ----------
section("3 · Where: provinces and districts", "yield compared with the national figure")
crop = st.selectbox("Crop", CROPS, key="tr_where")
d = dc[dc.crop == crop].dropna(subset=["production_mt", "harvested_ha"]).assign(
    Province=lambda x: x.DistrictName.map(DISTRICT_PROVINCE))
prov = d[d.year == last].groupby("Province")[["production_mt", "harvested_ha"]].sum()
prov["yield"] = prov.production_mt / prov.harvested_ha
national = prov.production_mt.sum() / prov.harvested_ha.sum()
prov["vs"] = prov["yield"] / national - 1
prov = prov.sort_values("vs")
fig3 = go.Figure(go.Bar(y=prov.index.str.replace(" Province", ""), x=100 * prov.vs, orientation="h",
                        marker=dict(color=[LEAF if v >= 0 else RED for v in prov.vs], cornerradius=4),
                        text=[f"{v:+.0%}" for v in prov.vs], textposition="outside", cliponaxis=False,
                        customdata=prov[["yield", "harvested_ha"]],
                        hovertemplate="<b>%{y}</b><br>%{customdata[0]:.2f} t/ha (%{x:+.0f}% vs national)<br>"
                                      "%{customdata[1]:,.0f} ha harvested<extra></extra>"))
fig3.add_vline(x=0, line=dict(color=MUTED, width=1))
fig3.update_layout(**LAYOUT, height=280, margin=dict(l=0, r=40, t=10, b=0), xaxis=dict(ticksuffix="%", gridcolor=GRID),
                   yaxis=dict(showgrid=False))

# district movers: average position vs the median district, first two years vs last two years
d["ryi"] = d.yield_kgha / d.groupby("season").yield_kgha.transform("median")
early = d[d.year <= first + 1].groupby("DistrictName").ryi.apply(lambda s: np.exp(np.log(s).mean()))
late = d[d.year >= last - 1].groupby("DistrictName").ryi.apply(lambda s: np.exp(np.log(s).mean()))
mv = pd.DataFrame({"early": early, "late": late}).dropna()
mv["change"] = mv.late / mv.early - 1
mv = mv.sort_values("change")
c1, c2 = st.columns(2)
with c1:
    st.markdown(f"**Provinces, {last} (Seasons A + B)** · national {national:.2f} t/ha")
    st.plotly_chart(fig3, width="stretch", config={"displayModeBar": False})
with c2:
    st.markdown(f"**Districts that moved most** · position vs the median district, {first}–{first + 1} → "
                f"{last - 1}–{last}")
    show = pd.concat([mv.head(5), mv.tail(5)]).iloc[::-1]
    st.dataframe(show.assign(**{f"{first}–{first + 1}": (100 * (show.early - 1)).round(0),
                                f"{last - 1}–{last}": (100 * (show.late - 1)).round(0),
                                "Change": (100 * show.change).round(0)})
                 [[f"{first}–{first + 1}", f"{last - 1}–{last}", "Change"]].rename_axis("District"),
                 width="stretch", column_config={c: st.column_config.NumberColumn(format="%+d%%")
                                                 for c in [f"{first}–{first + 1}", f"{last - 1}–{last}", "Change"]})
note("<b>How it's calculated.</b> Province yield = the province's total production ÷ its total harvested area. For "
     "districts we compare each one with the median district of the same season (the one in the middle): +20% "
     "means 20% more per hectare than that district. Averaging two years at each end smooths out one-off seasons.",
     "insights")

st.caption(f"Source: NISR Seasonal Agricultural Survey, official tables 2022–2026 ([releases]({SOURCE_URL})): "
           "production (MT) and harvested area (ha) by district and crop, Seasons A and B. District figures add up "
           "exactly to NISR's national totals. Cooking banana is NISR's cooking-banana column.")
