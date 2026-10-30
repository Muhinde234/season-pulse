"""Season Pulse - CHIRPS seasonal rainfall per district, and its link with relative yields.

Run after build_baseline.py (needs data/out_sas_clean_ryi.csv):
    pip install -r requirements-data.txt
    python fetch_rainfall.py

Downloads CHIRPS v2.0 Africa monthly GeoTIFFs (0.05°, mm/month) into data/raw/chirps/ (cached, not committed)
and averages each month over the geoBoundaries RWA ADM2 districts. Seasons, for SAS year Y:
    Season A = Sep-Dec of Y-1 · Season B = Mar-May of Y · Season C = Jun-Aug of Y
History is 2020-2024 (months from 2019 on). The latest season of each type is also fetched, even if only
some of its months are published yet (marked partial; compared with the same months on average).

Outputs (small, committed):
    app_data/district_rainfall.csv   district x season x year: rain_mm, avg_mm, rain_anom_pct, partial
    app_data/out_rain_vs_ryi.csv     SAS district x crop x season x year logRYI joined with that season's rainfall
"""
import re
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from rasterstats import zonal_stats

BASE = "https://data.chc.ucsb.edu/products/CHIRPS-2.0/africa_monthly/tifs/"
CACHE = Path("data/raw/chirps")
GEOJSON = "app_data/rwa_adm2.geojson"
HISTORY = range(2020, 2025)
SEASON_MONTHS = {"SeasonA": [(-1, 9), (-1, 10), (-1, 11), (-1, 12)],  # (year offset, month)
                 "SeasonB": [(0, 3), (0, 4), (0, 5)],
                 "SeasonC": [(0, 6), (0, 7), (0, 8)]}
MONTH = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def available_months() -> set[tuple[int, int]]:
    html = requests.get(BASE, timeout=60).text
    return {(int(y), int(m)) for y, m in re.findall(r"chirps-v2\.0\.(\d{4})\.(\d{2})\.tif\.gz", html)}


def tif_path(year: int, month: int) -> Path:
    return CACHE / f"chirps-v2.0.{year}.{month:02d}.tif.gz"


def download(ym: tuple[int, int]) -> None:
    path = tif_path(*ym)
    if path.exists():
        return
    for attempt in range(1, 6):  # the CHC server resets connections under load: retry with backoff
        try:
            r = requests.get(BASE + path.name, timeout=900)
            r.raise_for_status()
            break
        except requests.RequestException as e:
            if attempt == 5:
                raise
            print(f"  retry {attempt} for {path.name}: {type(e).__name__}")
            time.sleep(10 * attempt)
    tmp = path.with_suffix(".part")  # rename at the end so an interrupted download never looks cached
    tmp.write_bytes(r.content)
    tmp.replace(path)
    print(f"  downloaded {path.name}")


def district_means(year: int, month: int) -> dict[str, float]:
    """Mean monthly rainfall (mm) per district; all_touched so small districts (Nyarugenge) get pixels."""
    path = tif_path(year, month)
    stats = zonal_stats(GEOJSON, f"/vsigzip/{path.resolve().as_posix()}", stats="mean", all_touched=True, nodata=-9999,
                        geojson_out=True)
    return {f["properties"]["shapeName"]: f["properties"]["mean"] for f in stats}


CACHE.mkdir(parents=True, exist_ok=True)
avail = available_months()

# Seasons to compute: full history plus the latest season of each type with at least one month published
jobs = [(s, y) for y in HISTORY for s in SEASON_MONTHS]
for season, months in SEASON_MONTHS.items():
    latest = max(y for y in range(2025, date.today().year + 2)
                 if (y + months[0][0], months[0][1]) in avail)
    jobs.append((season, latest))

# The CHC server is slow per connection (~1-2 min per 4.5 MB file), so fetch the ~57 files in parallel
needed = sorted({(y + dy, m) for season, y in jobs for dy, m in SEASON_MONTHS[season]} & avail)
print(f"{len(needed)} monthly rasters needed, {sum(not tif_path(*ym).exists() for ym in needed)} to download")
with ThreadPoolExecutor(max_workers=4) as pool:
    list(pool.map(download, needed))

monthly, rows = {}, []
for season, year in jobs:
    months = [(year + dy, m) for dy, m in SEASON_MONTHS[season] if (year + dy, m) in avail]
    print(f"{season} {year}: {', '.join(f'{MONTH[m]} {y}' for y, m in months)}")
    for ym in months:
        if ym not in monthly:
            monthly[ym] = district_means(*ym)
    for district in monthly[months[0]]:
        rows.append(dict(DistrictName=district, Season=season, Year=year,
                         months="-".join(dict.fromkeys(MONTH[m] for _, m in months)),
                         n_months=len(months), partial=len(months) < len(SEASON_MONTHS[season]),
                         rain_mm=sum(monthly[ym][district] for ym in months)))

rain = pd.DataFrame(rows)

# District average for the same months over the history years (so a partial season compares like with like)
def same_months_avg(r) -> float:
    n = r.n_months
    vals = [sum(monthly[(y + dy, m)][r.DistrictName] for dy, m in SEASON_MONTHS[r.Season][:n]) for y in HISTORY]
    return float(np.mean(vals))

rain["avg_mm"] = rain.apply(same_months_avg, axis=1)
rain["rain_anom_pct"] = 100 * (rain.rain_mm / rain.avg_mm - 1)
rain[["rain_mm", "avg_mm", "rain_anom_pct"]] = rain[["rain_mm", "avg_mm", "rain_anom_pct"]].round(1)
rain.sort_values(["Season", "Year", "DistrictName"]).to_csv("app_data/district_rainfall.csv", index=False)

# ---------- Join with SAS relative yields (history only, reliable cells only) ----------
# RYI is relative to the median district that year, so a countrywide drought cancels out of it. Rainfall is
# made relative the same way: log(rain / district avg) minus the median of that across districts that season.
hist = rain[rain.Year.isin(HISTORY)].copy()
hist["log_rain_anom"] = np.log(hist.rain_mm / hist.avg_mm)
hist["rain_rel"] = hist.log_rain_anom - hist.groupby(["Season", "Year"]).log_rain_anom.transform("median")

sas = pd.read_csv("data/out_sas_clean_ryi.csv")
sas = sas[~sas.LowConfidence & sas.Year.isin(HISTORY)]
j = sas.merge(hist, on=["DistrictName", "Season", "Year"], how="inner")
# Deviation from the cell's own mean: "was this a bad year for this district, crop and season?"
j["ryi_dev"] = j.logRYI - j.groupby(["DistrictName", "CropName", "Season"]).logRYI.transform("mean")
j = j[j.groupby(["DistrictName", "CropName", "Season"]).Year.transform("nunique") >= 3]
out = j[["DistrictName", "CropName", "Season", "Year", "logRYI", "ryi_dev", "rain_mm", "avg_mm", "rain_anom_pct",
         "rain_rel"]].round(4)
out.to_csv("app_data/out_rain_vs_ryi.csv", index=False)

print(f"\nRainfall: {len(rain)} district-season rows -> app_data/district_rainfall.csv")
print(f"Rain vs RYI: {len(out)} rows, corr(ryi_dev, rain_rel) = {out.ryi_dev.corr(out.rain_rel):.3f}")
