"""SQLite storage for field reports. Simulated reports are flagged with is_simulated = 1."""
import random
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

from core.data import CROPS, DISTRICT_PROVINCE, DISTRICTS

DB_PATH = Path(__file__).resolve().parent.parent / "app_data" / "reports.db"

SIM_COUNT = 150
RAIN_OPTIONS = ["None", "Too little rain / dry spell", "Too much rain / flooding", "Late onset of rains"]

SCHEMA = """
CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    district TEXT NOT NULL,
    crop TEXT NOT NULL,
    season TEXT NOT NULL,
    condition INTEGER NOT NULL CHECK (condition BETWEEN 1 AND 5),
    pests INTEGER NOT NULL,
    rain_problem TEXT NOT NULL,
    notes TEXT,
    reporter TEXT,
    is_simulated INTEGER NOT NULL DEFAULT 0,
    source TEXT NOT NULL DEFAULT 'Web form'
)
"""
SOURCES = ["Web form", "USSD (simulated)", "Simulator"]


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(SCHEMA)
    # Databases created before the source column existed: add it (existing rows count as web-form reports)
    if "source" not in {row[1] for row in conn.execute("PRAGMA table_info(reports)")}:
        conn.execute("ALTER TABLE reports ADD COLUMN source TEXT NOT NULL DEFAULT 'Web form'")
        conn.execute("UPDATE reports SET source = 'Simulator' WHERE is_simulated = 1")
    return conn


def add_report(district, crop, season, condition, pests, rain_problem, notes="", reporter="", simulated=False,
               created_at=None, source=None):
    source = source or ("Simulator" if simulated else "Web form")
    with _conn() as conn:
        conn.execute(
            "INSERT INTO reports (created_at, district, crop, season, condition, pests, rain_problem, notes, "
            "reporter, is_simulated, source) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            ((created_at or datetime.now()).isoformat(timespec="seconds"), district, crop, season, int(condition),
             int(pests), rain_problem, notes, reporter, int(simulated), source),
        )


def get_reports(season=None, include_simulated=True) -> pd.DataFrame:
    q, args = "SELECT * FROM reports WHERE 1=1", []
    if season:
        q += " AND season = ?"
        args.append(season)
    if not include_simulated:
        q += " AND is_simulated = 0"
    with _conn() as conn:
        return pd.read_sql_query(q + " ORDER BY created_at DESC", conn, params=args)


def delete_simulated() -> int:
    with _conn() as conn:
        return conn.execute("DELETE FROM reports WHERE is_simulated = 1").rowcount


def load_simulated(season: str, n: int = SIM_COUNT, seed: int = 42) -> int:
    """Scenario: a dry spell in Eastern Province plus a fall armyworm outbreak on maize in the West.
    All rows are stored with is_simulated = 1 and shown with a SIMULATED label in the app."""
    rng = random.Random(seed)
    now = datetime.now()
    for _ in range(n):
        district = rng.choice(DISTRICTS)
        crop = rng.choice(CROPS)
        province = DISTRICT_PROVINCE[district]
        condition, pests, rain = rng.choice([3, 4, 4, 5]), rng.random() < 0.1, "None"
        if province == "Eastern Province":
            rain = rng.choice(["Too little rain / dry spell"] * 3 + ["Late onset of rains"])
            condition = rng.choice([1, 2, 2, 3])
        if province == "Western Province" and crop == "Maize":
            pests, condition = True, rng.choice([1, 2, 3])
        add_report(district, crop, season, condition, pests, rain,
                   notes="SIMULATED report for demo purposes", reporter="Simulator", simulated=True,
                   created_at=now - timedelta(days=rng.randint(0, 20), hours=rng.randint(0, 23)))
    return n
