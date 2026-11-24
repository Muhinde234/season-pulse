<img src="assets/imboni_logo.png" alt="Imboni" width="280">

**In-season crop early warning for Rwanda's 30 districts**  
*Imboni* (Kinyarwanda): the one who watches over.
NISR Big Data Hackathon 2026 · Track 1: Agricultural Productivity

🔗 **Live app:** [imboni.streamlit.app](https://imboni.streamlit.app/)  
👥 **Team:** IGIRIMPUHWE Dositha, IRADUKUNDA HIRWA Nadia · AIMS Rwanda  
🎬 **Demo video:** we uploaded our demo to the [`demo`](demo/) folder: [`demo/demo.mp4`](demo/demo.mp4). GitHub may not play it in the browser, so open the file and click **Download** (⬇) to watch it.

---

## 1. The problem
NISR's Seasonal Agricultural Survey (SAS) gives high-quality production estimates, but the results arrive **after the season ends**, when it's too late to act. Meanwhile:
- Some districts are below typical yields **year after year** (e.g. beans in Eastern Province during Season B), but this isn't turned into targeted action.
- History alone can't warn in time: our backtest shows past years catch only **about a third** of the districts that end up with a bad season.
- Farmers and agronomists see problems (dry fields, pests, poor growth) weeks earlier, but nobody collects those observations for planners.

## 2. Our solution
Imboni combines **NISR historical data** with **field reports during the season** to tell planners where productivity is at risk now, and what to do about it.

| User | What they get |
|---|---|
| **NISR / planners** | Early signal per district and crop before the survey results |
| **Agronomists** | Districts ranked by risk, with a recommended action for each |
| **Farmers** | A simple report form (Kinyarwanda / English) and how their district compares |

### App pages
- **Overview**: national snapshot for the current season: alerts per district, top priorities, how Imboni works and key findings.
- **District Profile**: one district at a glance: risk per crop, history by season, official yields and their 2024–2026 trend, farming practices vs the national average, rainfall, irrigation, local partners and field reports.
- **Road to +50%**: priority crop yields against Rwanda's PSTA 5 target (+50% productivity of priority food crops by 2029), a scenario calculator for two data-backed levers, and the districts where the most tonnes can be gained.
- **Farming Practices**: small- vs large-scale farmers (yields and use of improved seeds, fertilizer, pesticides, irrigation), district adoption maps, and priority districts for input programmes.

1. **District Risk Map**: districts coloured by yield vs the typical district (crop + season filter), including official 2026 Season A yields.
2. **Submit Field Report**: mobile-friendly form: crop, condition (1–5), pests, rainfall problem.
3. **Alerts & Recommended Actions**: baseline adjusted by field reports, ranked by risk and food dependence, with the production at stake in tonnes (official area × yield).
4. **Model & Data Quality**: backtest, validation against official 2026 Seasons A and B, a forecast from NISR's official tables, rainfall check and data limitations.
5. **USSD prototype**: simulates the `*XXX#` menu (Kinyarwanda by default) for farmers without a smartphone. No phone network is involved; reports are saved with source "USSD (simulated)".

### Recommended actions (linked to the track's focus areas)
| Signal | Action |
|---|---|
| Below typical + rainfall problems / mostly traditional irrigation | Small-scale irrigation |
| Below typical for 3+ years, no rainfall problem | Soil testing and fertility support |
| Above typical (surplus expected) | Plan post-harvest collection and storage |
| Surplus + cooperatives / food processors nearby | Value addition / processing |
| Surplus + exporting firms nearby | Export opportunity |

## 3. Data
| Dataset | Source | Use |
|---|---|---|
| Seasonal Agricultural Survey 2020–2024 (cleaned, aggregated) | NISR | District baseline and backtest |
| **SAS official tables, Seasons A and B 2024–2026** ([NISR SAS releases](https://statistics.gov.rw/data-sources/surveys/Seasonal-Agricultural-Survey)) | NISR | Official yields, production and area by district and crop; yields of small- and large-scale farmers; use of seeds, fertilizer, pesticides, irrigation; validation and forecast |
| [PSTA 5](https://www.minagri.gov.rw/fileadmin/user_upload/Minagri/Publications/Policies_and_strategies/PSTA_5_Abridged_version_Final.pdf) (2024–2029) | MINAGRI | The +50% productivity target for priority food crops |
| EICV household consumption (2020) | NISR | Food dependence per district |
| Establishment Census | NISR | Cooperatives, food processors, exporters per district |
| Field reports | Collected through the app | In-season adjustment (**simulated reports are clearly labelled**) |
| [CHIRPS v2.0](https://www.chc.ucsb.edu/data/chirps) monthly rainfall | UCSB Climate Hazards Center | Seasonal rainfall per district vs its 2020–2024 average (irrigation trigger, rain vs yield check) |
| [geoBoundaries](https://www.geoboundaries.org) RWA ADM2 | geoBoundaries (CC BY 4.0) | District map polygons |

## 4. Method
**Key finding while cleaning:** yield units in the aggregated SAS files are **not consistent across years** (e.g. Irish potato ≈ 13 t/ha in 2020–21 vs ≈ 0.8 t/ha from 2022). The official 2026 tables confirm this: real beans yield is ≈ 700 kg/ha, not the ≈ 6,000 kg/ha in the cleaned files.

So we never compare absolute yields across years. We use a **Relative Yield Index (RYI)**:

> RYI = district yield ÷ median district yield for the same crop, season and year

Any unit error that affects a whole year cancels out. RYI 0.7 = "30% below the typical district".

- Yield = total production ÷ total area (more reliable than averaging each farm's yield).
- Cells with fewer than 10 farms observed are marked low-confidence and not used for alerts.
- Baseline = average log-RYI per district × crop × season, shrunk toward "typical" when there are few years of data.
- In-season update: the baseline is adjusted by field reports (crop condition, pests, rainfall problems). The weight given to reports grows with the number of reports.

## 5. Results
**Backtest (trained on 2020–2023, predicted 2024; 303 district-crop-season cells)**
- History reduces prediction error by **13%** compared with assuming every district is typical.
- It catches **37%** of districts that end up at least 25% below typical (precision 45%).

**Validation against official NISR 2026 Season A yields (117 cells)**
- History correctly ranks which districts do worse for **Irish potatoes (r = 0.66), beans (0.53) and maize (0.44)**. It doesn't work for cassava (≈ 0).
- It caught **10 of 21** districts that came in at least 20% below typical.
- It overstates how far below typical a district will be, so we use it as a **risk ranking**, not an exact forecast.

**Validation against official NISR 2026 Season B yields (115 cells)**
- History ranks districts in the right order for beans (r = 0.53) and Irish potatoes (0.34), weakly for maize and cassava.
- It caught **4 of 13** cells that came in at least 20% below typical.

**Forecast from NISR's official tables alone (predict 2026 from 2025, same season, 7 major crops)**
- Season A: average error **3.7%** (vs 16.1% assuming every district is typical); caught **27 of 27** bad cells.
- Season B: average error **5.9%** (vs 15.8%); caught **20 of 20** bad cells.
- District positions in the official tables are very stable from year to year (rank correlation 0.92–0.94).

**Road to +50% (official national yields, Seasons A + B)**
- No priority crop is on the straight path to +50% by 2029 (+20% expected by 2026). Best: sweet potato +9.5% since 2024; maize, beans and cassava slightly down.
- Large-scale farmers harvest **2.7×** more maize, 1.8× more paddy rice and 1.5× more Irish potato per hectare, and use improved seeds (69% vs 26%), irrigation (50% vs 12%) and pesticides (90% vs 42%) far more than small-scale farmers.
- If districts below the top quarter caught up and small-scale farmers closed half their gap to large-scale yields, maize production would rise about **+75%** and beans about **+32%** on the same land.

**What this means:** history shows *where* risk tends to be, but it misses many bad seasons. That's why Imboni adds **field reports during the season**, and why the official tables guide where long-term investment (seeds, fertilizer, irrigation) pays off most.

## 6. Limitations
- Absolute yields in the cleaned 2020–2024 files can't be trusted. Only relative comparisons are used.
- Maize and tomatoes only have 2022–2024 data. Season C is missing for 2022–2023.
- EICV 2017 values appear mis-scaled, so only EICV 2020 is used.
- NISR publishes farming practices per district for all crops together, so links between practices and a crop's yield are associations, not proof of cause.
- The official district figures are survey estimates; part of their year-to-year stability may come from the estimation method.
- Field reports in the demo are **simulated** unless marked otherwise. The system needs real reporters to reach its full value.

## 7. How it would scale
Rwanda has a Farmer Promoter in every village (14,000+). They can submit reports through the app, or through SMS/USSD for farmers without smartphones. NISR could use the reports as an early indicator alongside each season's survey.

## 8. Run locally
```bash
git clone https://github.com/Muhinde234/season-pulse.git
cd season-pulse
pip install -r requirements.txt
streamlit run streamlit_app.py
```

The processed files in `app_data/` are committed, so the app runs straight away. To rebuild them from the raw data in `data/raw/`:

```bash
python build_baseline.py   # RYI baseline + 2024 backtest  -> app_data/out_district_baseline.csv, out_backtest.json
python prep_data.py        # census, EICV, SAS 2026 A irrigation table -> app_data/
python prep_official.py    # NISR official SAS tables 2024-2026 -> app_data/ (yields, practices, validation, forecast)
# optional, ~250 MB download: pip install -r requirements-data.txt && python fetch_rainfall.py
```

The 37 MB Establishment Census (`data/raw/establishment_census.csv`) is not committed; without it `prep_data.py` keeps the existing cooperative counts.

## 9. Project structure
```
streamlit_app.py     Streamlit app: navigation, theme
views/               the pages: home · map · alerts · district · target · practices · report · ussd · model
core/                data loaders, risk + recommended actions, official-table analysis (official.py), SQLite reports,
                     Kinyarwanda/English labels, styling
prep_official.py     Reads NISR's official SAS tables (6 seasons): yields, practices, validation, forecast
build_baseline.py    RYI baseline + 2024 backtest
prep_data.py         Aggregates census + EICV, extracts SAS 2026 Season A Tables 13 and 32
fetch_rainfall.py    CHIRPS rainfall per district and season (optional)
app_data/            Small processed files used by the app (the only folder the app reads)
data/raw/            Source datasets: SAS 2020–2024, EICV, sas_tables/ (official SAS tables 2024A–2026B), census not committed
assets/              Imboni logo and icon
demo/                Demo video (demo.mp4): download to watch
.streamlit/          Theme
```
