<img src="assets/imboni_logo.png" alt="Imboni" width="280">

**In-season crop early warning for Rwanda's 30 districts**  
*Imboni* (Kinyarwanda): the one who watches over.
NISR Big Data Hackathon 2026 · Track 1: Agricultural Productivity

🔗 **Live app:** [imboni.streamlit.app](https://imboni.streamlit.app/)  
👥 **Team Tech Innovators:** IGIRIMPUHWE Dositha, IRADUKUNDA HIRWA Nadia · AIMS Rwanda  
🎬 **Demo videos** (in the [`demo`](demo/) folder):
- [`demo/live_demo_Part2.mp4`](demo/live_demo_Part2.mp4): our live demo of the app (Part 2)
- [`demo/demo.mp4`](demo/demo.mp4): our first demo video

GitHub may not play videos in the browser: open the file and click **Download** (⬇) to watch it.

---

## 1. The problem
NISR's Seasonal Agricultural Survey (SAS) gives high-quality production estimates, but the results arrive **after the season ends**, when it's too late to act. Meanwhile:
- Some districts are below typical yields **year after year** (e.g. beans in Eastern Province during Season B), but this isn't turned into targeted action.
- Last season's official results are a strong guide to where trouble will be, but they can't show a district that suddenly breaks its usual pattern.
- Farmers see problems (dry fields, pests, poor growth) during the season, but we found no national record of in-season crop problems. In 2024, 67.1% of farming households received some extension advice, only 13.8% on pest management, and 0.24% of advice came by phone message (NISR AHS 2024). Advice mostly flows *to* farmers; little flows back.
- **Our hypothesis (not yet tested):** crops whose problems are reported and acted on in time end the season in better condition. The Research questions page sets out what data would test it.

## 2. Our solution
Imboni combines **NISR's latest official survey results** with **field reports during the season** to tell planners where productivity is at risk now, and what to do about it.

| User | What they get |
|---|---|
| **NISR / planners** | Early signal per district and crop before the survey results |
| **Agronomists** | Districts ranked by risk, with a recommended action for each |
| **Farmers** | A simple report form (Kinyarwanda / English) and how their district compares |

### App pages
The Map, Alerts and District Profile pages share a **Year** filter, chosen before the Season: the current year shows this season's expected values (last official result plus field reports); 2022–2026 show NISR's official results, so you can look back at what actually happened.

**Monitor**
- **Overview**: national snapshot for the current season: alerts per district, the crops furthest below typical, how Imboni works and key findings.
- **District Risk Map**: districts coloured by yield vs the typical district, or by yield in kg/ha, for any crop, year and season; table view downloadable as CSV.
- **Alerts & Recommended Actions**: every district and crop with a risk level (High, Watch, Normal), why, the production at stake in tonnes, a recommended action and local partners. The tiles follow every filter; the full ranking downloads as CSV.
- **District Profile**: one district at a glance: risk per crop, both seasons, official yields and their 2022–2026 trend, farming practices vs the national average, rainfall, irrigation, local partners and field reports.

**Plan**
- **Trends 2022–2026**: how production, harvested area and yield changed per crop (did more food come from more land or better yields?), and which provinces and districts gained or fell back, with plain-language explanations of each calculation.
- **Road to +50%**: priority crop yields against PSTA 5's yearly target for each crop, a scenario calculator for two data-backed levers, and the districts where the most tonnes can be gained.
- **Farming Practices**: small- vs large-scale farmers (yields and use of improved seeds, fertilizer, pesticides, irrigation), district adoption maps, and priority districts for input programmes.

**Report**
- **Submit Field Report**: mobile-friendly form (Kinyarwanda / English): crop, condition (1–5), pests, rainfall problem. Organisers can load or remove simulated reports and download all reports as CSV.
- **USSD prototype**: simulates the `*XXX#` menu (Kinyarwanda by default) for farmers without a smartphone. No phone network is involved; reports are saved with source "USSD (simulated)".

**About**
- **Research questions**: the three pillars as questions, each statement labelled fact, hypothesis, assumption, recommendation or gap; the seven steps from a farmer spotting a problem to the outcome, with the data that exists for each; who does what (NISR, MINAGRI, RAB, NAEB, local government, farmer promoters).
- **Model & Data Quality**: backtest on every season 2023–2026, rainfall check, how the cleaned files compare with the official tables, and data limitations.

### Recommended actions (linked to the track's focus areas)
| Signal | Action |
|---|---|
| Below typical + rainfall problems / mostly traditional irrigation | Small-scale irrigation |
| At least 20% below typical in each of the last 3 official years, no rainfall problem | Soil testing and fertility support |
| Above typical (surplus expected) | Plan post-harvest collection and storage |
| Surplus + cooperatives / food processors nearby | Value addition / processing |
| Surplus + exporting firms nearby | Export opportunity |

## 3. Data
| Dataset | Source | Use |
|---|---|---|
| **SAS official tables, Seasons A and B 2022–2026** ([NISR SAS releases](https://statistics.gov.rw/data-sources/surveys/Seasonal-Agricultural-Survey)): annual tables for 2022 and 2023, per-season tables for 2024A–2026B | NISR | **The alert baseline** and its backtest; official yields, production and area by district and crop; yields of small- and large-scale farmers; use of seeds, fertilizer, pesticides, irrigation (2024–2026) |
| Seasonal Agricultural Survey 2020–2024 (cleaned, aggregated) | NISR | Tomato baseline only (NISR publishes tomatoes inside "vegetables"); compared with the official tables |
| [PSTA 5](https://www.minagri.gov.rw/fileadmin/user_upload/Minagri/Publications/Policies_and_strategies/PSTA_5_Abridged_version_Final.pdf) (2024/25–2028/29) | MINAGRI | The NST2 goal of "a 50% increase in productivity" (p. 14) and the yearly yield target per priority food crop from a 2023 baseline (results framework, p. 21); indicators on pest surveillance, extension and data collection |
| [Agricultural Household Survey 2024](https://statistics.gov.rw/data-sources/surveys/Agricultural-Household-Survey) (Jan–Dec 2024), Tables 27 and 29 | NISR | Who receives extension services, what kind, and from whom (Pillar 1 evidence) |
| EICV household consumption (2020) | NISR | Food dependence: each crop's share of household food spending per district |
| Establishment Census | NISR | Cooperatives, food processors, exporters per district |
| Field reports | Collected through the app | In-season adjustment (**simulated reports are clearly labelled**) |
| [CHIRPS v2.0](https://www.chc.ucsb.edu/data/chirps) monthly rainfall | UCSB Climate Hazards Center | Seasonal rainfall per district vs its 2020–2024 average (irrigation trigger, rain vs yield check) |
| [geoBoundaries](https://www.geoboundaries.org) RWA ADM2 | geoBoundaries (CC BY 4.0) | District map polygons |

## 4. Method
We compare districts with a **Relative Yield Index (RYI)**:

> RYI = district yield ÷ median district yield for the same crop, season and year

RYI 0.7 = "30% below the typical district". Comparing within a season also cancels anything that affects the whole country that season.

- **Baseline = the last official result.** For the seven priority crops (banana, beans, cassava, Irish potato, maize, paddy rice, sweet potato), the baseline is the district's RYI in NISR's latest official tables for the same season (Season A from Season A, B from B). It beat every alternative we tested (see Results).
- **Tomatoes** keep a baseline from the cleaned 2020–2024 files (average log-RYI, shrunk toward typical), because NISR publishes them only inside "vegetables". It is labelled "not validated" in the app.
- **In-season update:** the baseline is adjusted by field reports (crop condition, pests, rainfall problems). The weight given to reports grows with the number of reports. The size of each effect (±10% per condition step, −10% for pests, −10% for a rain problem) is an **assumption**: there are no past field reports to fit it on. It should be re-fitted once real reports can be compared with the next official results.
- **How NISR's district figures are made** (SAS 2026 B report, chapter 2): an area frame of 9 ha segments stratified by district and land cover, 1,200 segments a season (25–68 per district) plus a list of large-scale farmers; plot areas measured by GPS; yields from the production farmers report. District figures are direct survey estimates.

**Why not the cleaned 2020–2024 files?** Their yield units change between years (e.g. Irish potato ≈ 13 t/ha in 2020–21 vs ≈ 0.8 t/ha from 2022), and on the years both cover (2022–2024) they rank districts differently from the official tables: rank correlation 0.45–0.61 for Irish potatoes, 0.25–0.45 for beans, 0.29–0.42 for maize, and **≈ 0 for cassava**. The official district tables add up exactly to NISR's national totals.

## 5. Results
**Backtest on NISR's official tables (predict every Season A and B from 2023 to 2026 from the year before; 7 priority crops; 1,586 district-crop-seasons)**

| Predictor | Average error | Bad cells caught (≥20% below typical) | Precision of flags |
|---|---|---|---|
| Every district typical | 17.2% | 0 of 219 | – |
| Average of the last two seasons | 8.0% | 185 of 219 | 52% |
| **Last season (used by Imboni)** | **7.7%** | **189 of 219 (86%)** | **54%** |

- The error fell every year, from 12.0% (2023A) and 9.1% (2023B) to 3.8% (2026A) and 5.9% (2026B), because district positions became steadier: the cells that moved more than 10% from the year before dropped from 69 to 9 in Season A.
- So most of this accuracy reflects how stable the survey results are, not forecasting skill. It tells planners *where* trouble usually is; it cannot see a district that breaks its pattern.
- **Rainfall doesn't fill that gap:** CHIRPS rainfall relative to other districts has no link (r ≈ 0) with which cells moved away from the year before (seasons with rainfall data: 2023A/B, 2024A/B, 2026B). That is the gap field reports are for.

**The earlier baseline from the cleaned 2020–2024 files**, checked against official 2026 results, caught 10 of 21 bad cells in Season A and 4 of 13 in Season B, with a larger error than assuming every district is typical. The alerts no longer use it except for tomatoes.

**Trends 2022–2026 (official tables, Seasons A + B)**
- Most crops grew production mainly by **planting more land**, not by higher yields: cooking banana +19% (area +17%, yield +1%), paddy rice +12% (area +8%, yield +4%), beans +6% (area +5%, yield +1%). **Maize** is the exception: production +33%, mostly from yield (+18%).
- Sweet potato, wheat and soybean produced slightly less; cassava yields fell 5% while its area grew 9%.

**Road to +50% (PSTA 5 yearly targets vs NISR Season A national yields)**
- **The target is not a flat +50%.** PSTA 5 sets a yield target per crop and year from a 2023 baseline, from +12% (wheat) to +200% (soybean) by 2028/29. Its 2023 baselines equal NISR's 2023 Season A national yields for all eight crops, so we compare Season A yields (reading 2025/26 as Season A 2026).
- In 2025/26, **only wheat met its target** (1.40 vs 1.30 t/ha; already above its 2028/29 target of 1.35). Maize was close (1.99 vs 2.06, −3%). Furthest behind: soybean (−41%), beans (−22%), cooking banana (−14%), cassava (−13%), Irish potato (−12%).
- Large-scale farmers harvest **2.7×** more maize, 1.8× more paddy rice and 1.5× more Irish potato per hectare, and use improved seeds (69% vs 26%), irrigation (50% vs 12%) and pesticides (90% vs 42%) far more than small-scale farmers.
- If districts below the top quarter caught up and small-scale farmers closed half their gap to large-scale yields, maize production would rise about **+75%** and beans about **+32%** on the same land.

**What this means:** last season's official results show *where* risk tends to be, and they are a much better guide than the cleaned files. They can't show a new shock, which is why Imboni adds **field reports during the season**, and why the official tables guide where long-term investment (seeds, fertilizer, irrigation) pays off most.

## 6. Limitations
- Official district figures are survey estimates from 25–68 sampled segments per district, with farmer-reported production. Small districts and minor crops are the least precise.
- The baseline assumes a district repeats its last official position. Only field reports can show a season breaking that pattern.
- **Field-report weights are assumptions**, not estimates. They need re-fitting once real reports exist.
- Seasons A and B only. Season C (Jul–Aug, swamps and volcanic highlands) is published only in NISR's annual tables, for a few crops, and is left out.
- Tomatoes rely on the cleaned 2020–2024 files, which don't match the official tables for the crops we could check. Tomato alerts are indicative only.
- EICV 2020 covers only beans, cassava, Irish potatoes, maize and tomatoes; food dependence for the other crops is unknown and set to neutral. EICV 2017 values appear mis-scaled, so only EICV 2020 is used.
- NISR publishes farming practices per district for all crops together, so links between practices and a crop's yield are associations, not proof of cause.
- **Reports are stored in SQLite.** On Streamlit Community Cloud the file is wiped whenever the app restarts, so real reports must be downloaded (Submit Field Report → Organisers) until the app uses a hosted database.
- Field reports in the demo are **simulated** unless marked otherwise. The system needs real reporters to reach its full value.

## 7. How it would scale
Farmer promoters and Farmer Field School facilitators already reach farmers: in 2024 they were the source of 11.1% and 7.2% of the extension advice farming households received (NISR AHS 2024, Table 29). They could submit reports through the app, or through SMS/USSD for farmers without smartphones. NISR and MINAGRI could use the reports as an early indicator alongside each season's survey.

## 8. Future work
- **Role-based views.** Separate screens for farmers, extension officers and planners, each showing what that role needs.
- **A full Kinyarwanda version of the app.** Today only the report form and the USSD prototype are in Kinyarwanda; every page should be.
- **A plain-language farmer view** (web and USSD). It would cover how the farmer's district and crop did last season, what this season's reports say, and what to watch for. Official data is per district and crop, never per farm, so the view would say "your district" and not "your farm".
- **The report-to-response loop (Pillar 1).** For each report, record who received it, when it was assessed, what advice was given and when, and how the crop ended. That would make the timely-action hypothesis testable. It also needs contact data for farmer promoters and sector agronomists.
- **Re-fit the field-report weights** once real reports can be compared with the next official NISR results.
- **Find MINAGRI's published figures** for the PSTA 5 indicators on pest surveillance, extension reach and data collection.
- **Fill the rainfall gap** (Seasons 2025A, 2025B and 2026A) by re-running `fetch_rainfall.py` over more years.
- **Store reports in a hosted database**, so they survive app restarts.

## 9. AI use
We used ChatGPT and Claude for coding support, debugging, research clarification and drafting. Our team chose the problem and the questions, made the project decisions and reviewed the results. We checked important figures and claims against the official NISR and MINAGRI sources linked above, and removed an AI-suggested claim about NISR's method that the source did not support.

## 10. Run locally
```bash
git clone https://github.com/Muhinde234/season-pulse.git
cd season-pulse
pip install -r requirements.txt
streamlit run streamlit_app.py
```

The processed files in `app_data/` are committed, so the app runs straight away. To rebuild them from the raw data in `data/raw/`:

```bash
python build_baseline.py   # cleaned-data baseline (tomatoes) + 2024 backtest -> app_data/out_district_baseline.csv, out_backtest.json
python prep_data.py        # census, EICV, SAS 2026 A irrigation table, AHS 2024 extension tables -> app_data/
python prep_official.py    # NISR official SAS tables 2022-2026 -> app_data/ (alert baseline, backtest, yields, practices, rainfall check)
# optional, ~250 MB download, then re-run prep_official.py: pip install -r requirements-data.txt && python fetch_rainfall.py
```

The 37 MB Establishment Census (`data/raw/establishment_census.csv`) is not committed; without it `prep_data.py` keeps the existing cooperative counts.

## 11. Project structure
```
streamlit_app.py     Streamlit app: navigation, theme, reloads cached data when app_data/ changes
views/               the pages: home · map · alerts · district · trends · target · practices · report · ussd ·
                     questions · model
core/                data loaders, risk + recommended actions, official-table analysis (official.py), SQLite reports,
                     Kinyarwanda/English labels, styling
prep_official.py     Reads NISR's official SAS tables (2022A-2026B): alert baseline, backtest, yields, practices, checks
build_baseline.py    Cleaned-data RYI baseline (used for tomatoes) + 2024 backtest
prep_data.py         Aggregates census + EICV, extracts SAS 2026 Season A Table 32 (irrigation) and AHS 2024 Tables 27, 29
fetch_rainfall.py    CHIRPS rainfall per district and season (optional)
app_data/            Small processed files used by the app (the only folder the app reads)
data/raw/            Source datasets: SAS 2020–2024 (cleaned), EICV, sas_tables/ (official SAS tables 2022–2026), ahs/ (AHS 2024 tables), census not committed
assets/              Imboni logo and icon
demo/                Demo videos (live_demo_Part2.mp4, demo.mp4): download to watch
.streamlit/          Theme
```
