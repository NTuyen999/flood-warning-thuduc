"""Settings from environment variables. Defaults are for local dev (docker compose db on 5433)."""

import os
from pathlib import Path

APP_ENV = os.getenv("APP_ENV", "dev")  # dev | prod
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://flood:flood_dev_pw@127.0.0.1:5433/flood"
)
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")  # empty = report moderation disabled
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",")]

BACKEND_DIR = Path(__file__).resolve().parents[1]
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", BACKEND_DIR / "uploads"))
MAX_UPLOAD_BYTES = 5 * 1024 * 1024

REPORT_TTL_HOURS = float(os.getenv("REPORT_TTL_HOURS", "6"))  # older reports -> expired
DUPLICATE_WINDOW_MIN = 30
DUPLICATE_RADIUS_M = 100
SEGMENT_SNAP_M = 150  # a report farther than this from every segment keeps segment_id = NULL
STALE_FORECAST_HOURS = 3  # serve the last stored run this long when Open-Meteo is down

# Reports must fall inside TP Thu Duc (lat_min, lon_min, lat_max, lon_max).
THU_DUC_BBOX = (10.70, 106.68, 10.93, 106.90)

# Calibrated probability -> risk level, upper bounds exclusive.
# shortcut: fixed bands, not validated against flood observations; replace with the
# thresholds from ml/src/evaluation/12_select_final_thresholds.py once ground truth exists.
RISK_BANDS = [(0.10, "green"), (0.30, "yellow"), (0.60, "orange")]

if APP_ENV == "prod" and (not ADMIN_TOKEN or "DATABASE_URL" not in os.environ):
    raise RuntimeError("APP_ENV=prod requires DATABASE_URL and ADMIN_TOKEN")
