"""Research questions: what Imboni set out to test, what the evidence says, and what is still missing.
Every number names its source, year and what it measures. Labels: FACT (published statistic), HYPOTHESIS (to be
tested), ASSUMPTION (used without evidence), RECOMMENDATION (our suggestion)."""
import html

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core.data import DATA, load_official_backtest
from core.official import PSTA5_URL, SOURCE_URL
from core.ui import hero, icon, section

AHS_URL = "https://statistics.gov.rw/data-sources/surveys/Agricultural-Household-Survey"
TAG = {"FACT": "#16a34a", "HYPOTHESIS": "#7c3aed", "ASSUMPTION": "#ea8a0c", "RECOMMENDATION": "#0284c7",
       "GAP": "#dc2626"}
LAYOUT = dict(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", hoverlabel=dict(bgcolor="white"))


def tag(kind: str) -> str:
    return f'<span class="sp-badge" style="--c:{TAG[kind]}">{kind.title()}</span>'


def claim(kind: str, text: str) -> None:
    st.markdown(f'<div class="sp-note" style="border-left:4px solid {TAG[kind]};padding:.6rem .9rem">'
                f'{tag(kind)}&nbsp; <span>{text}</span></div>', unsafe_allow_html=True)


types = pd.read_csv(DATA / "ahs2024_extension_types.csv").set_index("item")
sources = pd.read_csv(DATA / "ahs2024_extension_sources.csv").set_index("service")
any_ext = types.loc["Any extension service"]
ipm = types.loc["Integrated pest management"]
weather = types.loc["Weather and climate information products/services"]
overall = sources.loc["Overall"].drop("households_000")

hero("Research questions", "What we set out to test, what the evidence says, and what is still missing.",
     eyebrow="About · Evidence", ic="science", meta=[("database", "NISR SAS · AHS 2024 · PSTA 5")])
st.markdown(" ".join(tag(k) for k in TAG) + "&nbsp; Every statement below is labelled with one of these.",
            unsafe_allow_html=True)

# ---------- Pillar 1 ----------
section("Pillar 1 · Timely action: from reporting to intervention")
claim("HYPOTHESIS", "<b>Crops whose problems are reported and acted on while there is still time end the season in "
                    "better condition.</b> Not yet tested: no data set we found links when a problem was reported, "
                    "when help arrived, and how the crop ended.")

st.markdown("**The seven steps, and what data exists for each**")
steps = pd.DataFrame([
    ("1. Farmer spots a problem", "Report form and USSD prototype", "None found", "No national record of in-season "
     "crop problems"),
    ("2. Farmer reports it", "Saves district, crop, condition, pests, rain problem and the time",
     f"AHS 2024: telephone messages were the source of {overall['Telephone']:.2f}% of extension services received",
     "Nothing measures reports going from farmers to officers"),
    ("3. Report reaches an officer", "Not built", "None found", "Who receives reports, and how fast"),
    ("4. Problem is assessed", "Not built", "None found", "Assessment records"),
    ("5. Advice or help is given", "Rule-based recommended action per alert",
     f"AHS 2024: {any_ext['Rwanda']:.1f}% of farming households received some extension service; "
     f"{ipm['Rwanda']:.1f}% received pest-management advice", "Advice is counted, not its timing"),
    ("6. Help arrives in time", "Not measured", "None found", "Dates of problem, report and response"),
    ("7. Outcome is monitored", "Next official NISR result per district and crop",
     "NISR SAS: yield per district and crop each season", "Per district, not per farm; harvested area equals "
     "cultivated area in the median district, so crop failure isn't visible"),
], columns=["Step", "What Imboni does today", "Evidence available", "Gap"])
st.dataframe(steps, hide_index=True, width="stretch")

st.markdown(f"**What the evidence says** · [NISR Agricultural Household Survey 2024]({AHS_URL}), Jan–Dec 2024, "
            "Tables 27 and 29")
k = st.columns(4)
k[0].metric("Households receiving any extension service", f"{any_ext['Rwanda']:.1f}%",
            help="% of agricultural households with at least one member who received an extension service (AHS 2024, "
                 "Table 27). 2.16 million agricultural households.")
k[1].metric("Received pest-management (IPM) advice", f"{ipm['Rwanda']:.1f}%", help="AHS 2024, Table 27")
k[2].metric("Received weather and climate information", f"{weather['Rwanda']:.1f}%", help="AHS 2024, Table 27")
k[3].metric("Advice that came by telephone message", f"{overall['Telephone']:.2f}%",
            help="Share of all extension services received, by source (AHS 2024, Table 29, 'Overall')")
claim("FACT", f"Female-headed households were less likely to receive any extension service "
              f"({any_ext['Female-headed']:.1f}%) than male-headed ones ({any_ext['Male-headed']:.1f}%). By province, "
              f"from {any_ext[['Kigali', 'South', 'West', 'North', 'East']].min():.1f}% (Kigali) to "
              f"{any_ext[['Kigali', 'South', 'West', 'North', 'East']].max():.1f}% (East).")

o = overall.sort_values()
fig = go.Figure(go.Bar(x=o.values, y=o.index, orientation="h", marker=dict(color="#1F8A43", cornerradius=4),
                       text=[f"{v:.1f}%" for v in o.values], textposition="outside", cliponaxis=False,
                       hovertemplate="%{y}: %{x:.2f}% of extension services received<extra></extra>"))
fig.update_layout(**LAYOUT, height=420, margin=dict(l=0, r=40, t=10, b=0),
                  xaxis=dict(ticksuffix="%", gridcolor="rgba(14,59,34,.10)"), yaxis=dict(showgrid=False))
c1, c2 = st.columns([1.4, 1])
with c1:
    st.markdown("**Where extension advice comes from** (share of all services received, 2024)")
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
with c2:
    st.markdown(f"""
    **Reading it**

    - Most advice reaches farmers through **media** ({overall['Media communication with agriculture technical information']:.1f}%),
      **local government officials** ({overall['Government officials']:.1f}%) and **community meetings**
      ({overall['Meeting/Community work']:.1f}%).
    - **Farmer promoters** ({overall['Farmer /Livestock promoters']:.1f}%) and **Farmer Field School facilitators**
      ({overall['Farmer Field School facilitator']:.1f}%) come next. Government extension workers from MINAGRI,
      NAEB and RAB were the source of {overall['Government extension workers']:.1f}%.
    - **Telephone messages: {overall['Telephone']:.2f}%.** Advice mostly flows *to* farmers through broadcast and
      meetings. A channel for farmers to report a problem and get an answer back is almost unused.
    """)
    claim("FACT", "These numbers measure advice <i>received</i>. They say nothing about problems farmers "
                  "<i>reported</i>, or how quickly anyone responded.")

st.markdown(f"**What the government has committed to** · [PSTA 5]({PSTA5_URL}) results framework (MINAGRI), "
            "indicators whose source is MINAGRI reports")
st.dataframe(pd.DataFrame([
    ("Farmers using pest and disease surveillance tools", "10% → 50%", "2024/25 → 2028/29", "p. 22"),
    ("Pest/disease surveillance conducted", "2 a year", "each year", "p. 22"),
    ("Relevant data stored in the expanded and incentivized data collection network", "10% → 50%",
     "2024/25 → 2028/29", "p. 32"),
    ("Farmers accessing extension (including climate smart) services through the CAES", "from 1,300,000",
     "first value in the table", "p. 29"),
], columns=["PSTA 5 indicator", "Values", "Years", "Page"]), hide_index=True, width="stretch")
claim("GAP", "We haven't found published MINAGRI figures for these indicators yet. They are the closest official "
             "measures of Pillar 1 and the next thing to look for.")
claim("RECOMMENDATION", "To test the hypothesis, a pilot would need to record, for each report: the date the problem "
                        "was seen, the date it was reported, who received it, the date and type of response, and "
                        "the crop's state at harvest. Comparing reports answered within a set number of days with "
                        "those answered later, against the district's next official result (allowing for where it "
                        "stood last season), would give the first real evidence. Imboni's report form already "
                        "stores the report time; the response steps would need adding.")

# ---------- Institutions ----------
section("Who does what", "institutions named in the sources we used, and what each provides")
st.dataframe(pd.DataFrame([
    ("NISR", "Official statistics", "Seasonal Agricultural Survey (each season: area, yield, production, inputs, "
     "by district and farmer type); Agricultural Household Survey (2017, 2020, 2024: households, extension, inputs); "
     "EICV (household consumption)", "Imboni's baseline, backtest, extension and food-dependence figures"),
    ("MINAGRI", "Agriculture policy and planning", "PSTA 5 and its yield targets; reports named as the source for "
     "pest surveillance, extension and data-network indicators", "Road to +50% targets; Pillar 1 indicators "
     "(figures not yet found)"),
    ("RAB, NAEB", "Named by AHS 2024 as government extension providers, with MINAGRI",
     "Not yet checked", f"Source of {overall['Government extension workers']:.1f}% of extension services (AHS 2024)"),
    ("Local government (district, sector, cell, village)", "Largest single source of extension advice",
     "Not yet checked", f"{overall['Government officials']:.1f}% of extension services (AHS 2024)"),
    ("Farmer promoters, Farmer Field School facilitators", "Community-level extension",
     "Not yet checked", f"{overall['Farmer /Livestock promoters']:.1f}% and "
                        f"{overall['Farmer Field School facilitator']:.1f}% of extension services (AHS 2024)"),
    ("Climate Hazards Center, UC Santa Barbara", "CHIRPS satellite rainfall", "Monthly rainfall, ~5 km",
     "Rainfall check and irrigation trigger"),
], columns=["Institution", "Role", "Data it publishes or holds", "How Imboni uses it"]), hide_index=True,
    width="stretch")
claim("FACT", "NISR measures what happened (each season's results, household conditions). Monitoring farms during "
              "the season, receiving farmer reports and giving advice sit with MINAGRI, its agencies and local "
              "government, not with NISR.")

# ---------- Pillars 2 and 3 ----------
bt = load_official_backtest()
last, typ = bt[bt.method == "Last season"], bt[bt.method == "Every district typical"]
err = lambda m: (m.mae_pct * m.cells).sum() / m.cells.sum()
section("Pillar 2 · Historical knowledge and prediction")
claim("FACT", f"A district's last official result for the same season predicted the next one with "
              f"{err(last):.1f}% average error on every season {last.year.min()}–{last.year.max()}, vs {err(typ):.1f}% "
              f"for assuming every district is typical, and flagged {int(last.caught.sum())} of "
              f"{int(last.bad_cells.sum())} cells that ended ≥20% below typical "
              f"([NISR SAS tables]({SOURCE_URL}); details on the Model page).")
claim("FACT", "Rainfall relative to other districts did not explain which cells moved away from the year before "
              "(r ≈ 0). History shows where risk usually is; it cannot see a new shock.")
claim("ASSUMPTION", "Machine learning is not used: with about 200 district-crop cells a season, eight seasons and no "
                    "farm-level outcomes, a more complex model would not be testable. That can change once field "
                    "reports and outcomes are collected.")

section("Pillar 3 · Statistics people can use")
claim("FACT", "Planners get ranked alerts, tonnes at stake and progress against PSTA 5 targets. Extension officers "
              "get a district view with recommended actions.")
claim("GAP", "Farmers see one line after submitting a report. A plain-language farmer view (how my district and crop "
             "did last season, what to watch for, how this season compares) is still to be designed.")
