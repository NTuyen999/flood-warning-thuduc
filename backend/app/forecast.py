"""Model serving: one inference per clock hour, stored for every road segment.

Reuses the ML team's live pipeline (Open-Meteo fetch -> 30 training features ->
6 XGBoost models + calibrators + SHAP) from ml/src/models/19_live_api.py, so serving
uses exactly the training preprocessing. The model has a single input point
(10.85, 106.77), so every segment of a run gets the same probabilities.
"""

import hashlib
import importlib
import json
import logging
import threading
from datetime import datetime, timedelta
from functools import lru_cache

from psycopg.types.json import Jsonb

from . import config

live = importlib.import_module("ml.src.models.19_live_api")
predict = live.predict_module
log = logging.getLogger(__name__)

WEATHER_FIELDS = [
    "temperature_2m", "relative_humidity_2m", "pressure_msl", "surface_pressure",
    "cloud_cover", "wind_speed_10m", "wind_gusts_10m", "wind_direction_10m", "precipitation",
]

_lock = threading.Lock()


class ForecastUnavailable(RuntimeError):
    pass


@lru_cache(maxsize=1)
def model_version():
    """Content hash of the deployed model files: changes whenever a model is retrained."""
    files = sorted(predict.MODEL_DIR.glob("*")) + sorted(predict.CALIBRATOR_DIR.glob("*"))
    digest = hashlib.sha256()
    for f in files:
        digest.update(f.name.encode() + f.read_bytes())
    return f"xgb-final-{digest.hexdigest()[:12]}"


def risk_level(probability):
    return next((lvl for limit, lvl in config.RISK_BANDS if probability < limit), "red")


def _infer(reference_time):
    """Run the ML pipeline for one reference hour. Returns (weather dict | None, results)."""
    weather = live.weather_module
    payload, _ = weather.fetch_api_response(reference_time)
    hourly = weather.parse_api_hourly(payload)
    features = weather.build_features(hourly, reference_time, live.get_season_mapping())
    result = predict.predict_features(
        features, observed_at=reference_time.strftime("%Y-%m-%d %H:%M:%S"), top_n=5
    )
    row = hourly.loc[hourly["time"] == reference_time]
    weather_row = None if row.empty else {k: float(row.iloc[0][k]) for k in WEATHER_FIELDS}
    return weather_row, result["results"]


def _run_exists(conn, issued_at, version):
    return conn.execute(
        "SELECT 1 FROM prediction_explanations WHERE issued_at = %s AND model_version = %s",
        (issued_at, version),
    ).fetchone() is not None


def _store(conn, issued_at, version, weather_row, results):
    with conn.transaction():
        if weather_row:
            cols = ", ".join(WEATHER_FIELDS)
            conn.execute(
                f"INSERT INTO weather_hourly (observed_at, {cols}) "
                f"VALUES (%s, {', '.join(['%s'] * len(WEATHER_FIELDS))}) "
                "ON CONFLICT (observed_at) DO NOTHING",
                (issued_at, *weather_row.values()),
            )
        for r in results:
            h, p = int(r["horizon"]), float(r["calibrated_event_probability"])
            conn.execute(
                "INSERT INTO prediction_explanations (issued_at, horizon, model_version, top_features) "
                "VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING",
                (issued_at, h, version,
                 Jsonb(r["top_shap_features"], dumps=lambda o: json.dumps(o, default=float))),
            )
            conn.execute(
                "INSERT INTO predictions (segment_id, issued_at, horizon, probability, risk_level, model_version) "
                "SELECT segment_id, %s, %s, %s, %s, %s FROM road_segments ON CONFLICT DO NOTHING",
                (issued_at, h, p, risk_level(p), version),
            )


def ensure_latest_run(conn):
    """Return (issued_at, stale). Runs + stores inference once per hour; history is never overwritten."""
    reference_time = live.get_reference_time()
    issued_at = reference_time.to_pydatetime().replace(tzinfo=live.LOCAL_TZ)
    version = model_version()
    if _run_exists(conn, issued_at, version):
        return issued_at, False
    with _lock:  # one inference at a time; concurrent callers reuse its result
        if _run_exists(conn, issued_at, version):
            return issued_at, False
        try:
            weather_row, results = _infer(reference_time)
        except Exception as exc:
            log.exception("Live inference failed")
            latest = conn.execute(
                "SELECT max(issued_at) AS t FROM prediction_explanations WHERE model_version = %s",
                (version,),
            ).fetchone()["t"]
            if latest and issued_at - latest <= timedelta(hours=config.STALE_FORECAST_HOURS):
                return latest, True
            raise ForecastUnavailable("Live inference unavailable and no recent stored run") from exc
        _store(conn, issued_at, version, weather_row, results)
        log.info("Stored run %s (%s)", issued_at.isoformat(), version)
    return issued_at, False


# ------------------------------------------------------------
# SHAP features in plain Vietnamese for the explanation screen
# ------------------------------------------------------------

FEATURE_LABELS = {
    "temperature_2m": ("Nhiệt độ", "°C"),
    "relative_humidity_2m": ("Độ ẩm tương đối", "%"),
    "pressure_msl": ("Áp suất mực nước biển", " hPa"),
    "surface_pressure": ("Áp suất bề mặt", " hPa"),
    "cloud_cover": ("Độ che phủ mây", "%"),
    "wind_speed_10m": ("Tốc độ gió", " km/h"),
    "wind_gusts_10m": ("Gió giật", " km/h"),
    **{f"rain_last_{n}h": (f"Tổng mưa {n} giờ qua", " mm") for n in (1, 3, 6, 12, 24)},
    **{f"rain_lag_{n}h": (f"Lượng mưa {n} giờ trước", " mm") for n in (1, 2, 3)},
    "humidity_lag_1h": ("Độ ẩm 1 giờ trước", "%"),
    "humidity_change_1h": ("Thay đổi độ ẩm trong 1 giờ", "%"),
    "humidity_mean_3h": ("Độ ẩm trung bình 3 giờ", "%"),
    "pressure_lag_1h": ("Áp suất 1 giờ trước", " hPa"),
    "pressure_change_1h": ("Thay đổi áp suất trong 1 giờ", " hPa"),
    "pressure_mean_3h": ("Áp suất trung bình 3 giờ", " hPa"),
    "wind_speed_lag_1h": ("Tốc độ gió 1 giờ trước", " km/h"),
    "wind_speed_change_1h": ("Thay đổi tốc độ gió trong 1 giờ", " km/h"),
    "wind_direction_sin": ("Hướng gió (sin)", ""),
    "wind_direction_cos": ("Hướng gió (cos)", ""),
    "hour_sin": ("Giờ trong ngày (sin)", ""),
    "hour_cos": ("Giờ trong ngày (cos)", ""),
    "month_sin": ("Tháng trong năm (sin)", ""),
    "month_cos": ("Tháng trong năm (cos)", ""),
    "rainy_season": ("Đang trong mùa mưa (1 = có)", ""),
}


def explain_feature(item):
    label, unit = FEATURE_LABELS.get(item["feature"], (item["feature"], ""))
    impact = float(item["shap_log_odds"])
    value = float(item["input_value"])
    direction = "increases" if impact > 0 else "decreases" if impact < 0 else "neutral"
    verb = {"increases": "làm tăng", "decreases": "làm giảm", "neutral": "không ảnh hưởng"}[direction]
    return {
        "feature": item["feature"],
        "label": label,
        "value": value,
        "impact": impact,
        "direction": direction,
        "text": f"{label} = {value:.4g}{unit} → {verb} nguy cơ",
    }


def now_local():
    return datetime.now(live.LOCAL_TZ)
