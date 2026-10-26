# 🌱 Season Pulse

**In-season crop early warning for Rwanda's 30 districts.** Built for the NISR Hackathon 2026.

Season Pulse combines five years of NISR Seasonal Agricultural Survey (SAS) results with field reports
collected during the season. It flags districts and crops likely to under-perform, and shows the local
cooperatives and food processors that could respond.

| Page | What it does |
|---|---|
| 🗺️ **District map** | Choropleth of the 30 districts coloured by yield vs the typical district, filtered by crop and season. Toggle between the historical baseline and the baseline adjusted by field reports. |
| 📝 **Field report** | Form for extension officers: crop, condition (1–5), pests, rain problem. Saved to SQLite. A button loads clearly labelled **simulated** reports for demos. |
| 🚨 **Alerts** | Baseline adjusted by reports and ranked by risk (🔴 High / 🟠 Watch / 🟢 Normal), with the reasons, district cooperative and food processor counts, and EICV 2020 household consumption. CSV download. |
| 📊 **Model & limitations** | How the index and adjustment work, backtest results (2020–23 → 2024), and data limitations. |

## Key idea: the Relative Yield Index (RYI)

SAS yield units are inconsistent across years in the cleaned files (e.g. Irish potato values drop ~20–30× from
2022). Absolute yields can't be compared over time, so Season Pulse **never shows kg/ha**. Instead:

```
RYI = district yield / median district yield   (same crop, season and year)
```

Any year-wide unit factor cancels out. The app shows RYI as **"% vs typical district"**:
RYI 0.73 → **−27%**.

- **Baseline:** mean log-RYI over 2020–2024 for each district × crop × season, shrunk toward typical by
  `n_years / (n_years + 1)`. Cells with fewer than 10 farm observations are excluded.
- **Field report adjustment** (log-RYI): condition `(c − 3) × 0.10`, pests `−0.10`, any rain problem `−0.10`.
  The average across reports is weighted by `n / (n + 2)`.
- **Alert levels:** High if expected RYI ≤ 0.75, Watch if ≤ 0.85 (the same thresholds the backtest uses).

## Backtest (train 2020–2023, test 2024)

| Metric | Result |
|---|---|
| Test cells (district × crop × season) | 303 |
| Error reduction vs "every district typical" | **13.3%** (MAE log-RYI 0.416 vs 0.480) |
| Precision / recall flagging cells that ended ≥25% below typical | 45% / 37% |

The baseline beats the naive benchmark for Beans, Irish potatoes, Maize and Tomatoes, but **not for Cassava**.
History tells you where to look, and field reports tell you what is happening now.

## Run locally

```bash
pip install -r requirements.txt
python build_baseline.py     # -> data/out_district_baseline.csv, data/out_backtest.json
python prepare_data.py       # -> data/district_cooperatives.csv, data/district_consumption_2020.csv
streamlit run app.py
```

The generated CSV/JSON files are committed, so `streamlit run app.py` works without rerunning the scripts.
To rebuild the cooperative counts, place the cleaned Establishment Census at
`data/raw/establishment_census.csv` (37 MB, not committed).

## Deploy on Streamlit Community Cloud

1. Push this folder to a public GitHub repository.
2. On [share.streamlit.io](https://share.streamlit.io), choose **Create app**, then pick the repo, branch `main`,
   and main file `app.py`.
3. In **Advanced settings**, choose Python 3.12, then deploy.

## Project structure

```
app.py                  navigation entry point
views/                  map.py · report.py · alerts.py · model.py
core/data.py            cached loaders, districts/provinces, season calendar, % formatting
core/db.py              SQLite field reports + simulated scenario
core/risk.py            baseline + report adjustment -> ranked alerts
build_baseline.py       RYI, baseline and backtest from SAS
prepare_data.py         census + EICV pre-aggregation
data/                   small committed inputs + rwa_adm2.geojson
data/raw/               SAS and EICV historical CSVs (census not committed)
```

## Data and processing rules

| Source | Use |
|---|---|
| NISR SAS 2020–2024 (cleaned, aggregated) | RYI baseline and backtest; `Annual` rows and unknown districts dropped |
| NISR EICV, **2020 round only** | Household consumption per district × crop; duplicate district rows are **summed** |
| NISR Establishment Census | Count of **cooperatives** (`Is_Cooperative = Yes`) and **food processors** (`Is_Food_Processing_Related = 1`) per district. Code 28, labelled "Unknown District", is mapped to Kamonyi |
| [geoBoundaries](https://www.geoboundaries.org) RWA ADM2 (simplified, CC BY 4.0) | District polygons, bundled locally |

## Limitations

- Only 3–5 years of history, and only 3 years for Maize and Tomatoes. Season C coverage is thin.
- Field report weights are expert judgement and haven't been calibrated, because no historical reports exist.
- Simulated reports are demo data (a dry spell in Eastern Province and fall armyworm on maize in the West). They
  are flagged `is_simulated = 1`, labelled in the UI, and can be removed with one click.
- The census gives only counts per district, not cooperative names or contacts.
- SQLite on Streamlit Cloud resets when the app restarts. Production use needs a hosted database
  (e.g. Postgres/Supabase).
