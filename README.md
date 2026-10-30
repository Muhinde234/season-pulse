# Season Pulse 🌱
**In-season crop early warning for Rwanda's 30 districts**
NISR Big Data Hackathon 2026 · Track 1: Agricultural Productivity

🔗 **Live app:** [ADD STREAMLIT LINK]  
👥 **Team:** [NAMES, UNIVERSITY]

---

## 1. The problem
NISR's Seasonal Agricultural Survey (SAS) gives high-quality production estimates, but the results arrive **after the season ends**, when it's too late to act. Meanwhile:
- Some districts are below typical yields **year after year** (e.g. beans in Eastern Province during Season B), but this isn't turned into targeted action.
- History alone can't warn in time: our backtest shows past years catch only **about a third** of the districts that end up with a bad season.
- Farmers and agronomists see problems (dry fields, pests, poor growth) weeks earlier, but nobody collects those observations for planners.

## 2. Our solution
Season Pulse combines **NISR historical data** with **field reports during the season** to tell planners where productivity is at risk now, and what to do about it.

| User | What they get |
|---|---|
| **NISR / planners** | Early signal per district and crop before the survey results |
| **Agronomists** | Districts ranked by risk, with a recommended action for each |
| **Farmers** | A simple report form (Kinyarwanda / English) and how their district compares |

### App pages
1. **District Risk Map**: districts coloured by yield vs the typical district (crop + season filter), including official 2026 Season A yields.
2. **Submit Field Report**: mobile-friendly form: crop, condition (1–5), pests, rainfall problem.
3. **Alerts & Recommended Actions**: baseline adjusted by field reports, ranked by risk and food dependence.
4. **Model & Data Quality**: backtest, validation against official 2026 Season A yields, rainfall check and data limitations.
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
| **SAS 2026 Season A official tables** (Tables 13, 32) | NISR | Validation on a new season, official yields, irrigation |
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

**What this means:** history shows *where* risk tends to be, but it misses many bad seasons. That's why Season Pulse adds **field reports during the season**.

## 6. Limitations
- Absolute yields in the cleaned 2020–2024 files can't be trusted. Only relative comparisons are used.
- Maize and tomatoes only have 2022–2024 data. Season C is missing for 2022–2023.
- EICV 2017 values appear mis-scaled, so only EICV 2020 is used.
- Field reports in the demo are **simulated** unless marked otherwise. The system needs real reporters to reach its full value.

## 7. How it would scale
Rwanda has a Farmer Promoter in every village (14,000+). They can submit reports through the app, or through SMS/USSD for farmers without smartphones. NISR could use the reports as an early indicator alongside each season's survey.

## 8. Run locally
```bash
git clone https://github.com/Muhinde234/season-pulse.git
cd season-pulse
pip install -r requirements.txt
streamlit run app.py
```

The processed files in `app_data/` are committed, so the app runs straight away. To rebuild them from the raw data in `data/raw/`:

```bash
python build_baseline.py   # RYI baseline + 2024 backtest  -> app_data/out_district_baseline.csv, out_backtest.json
python prep_data.py        # census, EICV, SAS 2026 tables -> app_data/ (incl. out_validation_2026A.csv)
# optional, ~250 MB download: pip install -r requirements-data.txt && python fetch_rainfall.py
```

The 37 MB Establishment Census (`data/raw/establishment_census.csv`) is not committed; without it `prep_data.py` keeps the existing cooperative counts.

## 9. Project structure
```
app.py               Streamlit app: navigation, theme
views/               the five pages: map · alerts · report · ussd · model
core/                data loaders, risk + recommended actions, SQLite reports, Kinyarwanda/English labels, styling
build_baseline.py    RYI baseline + 2024 backtest
prep_data.py         Aggregates census + EICV, extracts SAS 2026 Season A Tables 13 and 32, builds the 2026 validation
fetch_rainfall.py    CHIRPS rainfall per district and season (optional)
app_data/            Small processed files used by the app (the only folder the app reads)
data/raw/            Source datasets: SAS 2020–2024, EICV, Tables_2026_Season_A.xlsx (census not committed)
assets/              Logo
.streamlit/          Theme
```
