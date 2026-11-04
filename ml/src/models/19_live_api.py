"""Research API for live heavy-rain proxy predictions.

Run from the project root:

    python -m uvicorn ml.src.models.19_live_api:app --host 127.0.0.1 --port 8000

Endpoint:
    GET /api/v1/rain-proxy/latest

This API is a research prototype, not a public flood-warning service.
"""

import importlib
import logging

from datetime import datetime, timedelta, timezone
from functools import lru_cache

import pandas as pd

from fastapi import FastAPI, HTTPException
from starlette.concurrency import run_in_threadpool


# ============================================================
# IMPORT EXISTING STEPS
#
# Numeric file names require importlib.
# Reuse existing code; do not duplicate feature engineering.
# ============================================================

weather_module = importlib.import_module(
    "ml.src.features.18_build_live_features"
)

predict_module = importlib.import_module(
    "ml.src.models.17_predict"
)


# ============================================================
# CONFIG
# ============================================================

LOCAL_TZ = timezone(
    timedelta(hours=7)
)

LATITUDE = 10.85
LONGITUDE = 106.77

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Thu Duc Rainfall Research API",
    version="1.0.0",
    description=(
        "Experimental heavy-rain prediction prototype. "
        "Not validated for public flood warnings."
    ),
)


# ============================================================
# LOAD FIXED FEATURE CONFIGURATION ONCE
# ============================================================

@lru_cache(maxsize=1)
def get_season_mapping():

    weather_module.check_feature_contract()

    return (
        weather_module.season_mapping_from_training()
    )


# ============================================================
# MOST RECENT COMPLETED CLOCK HOUR
#
# Note: Open-Meteo past hourly values are model-derived.
# They must not be described as verified observations.
# ============================================================

def get_reference_time():

    now = datetime.now(
        LOCAL_TZ
    )

    previous_hour = (
        now.replace(
            minute=0,
            second=0,
            microsecond=0,
        )
        - timedelta(hours=1)
    )

    return pd.Timestamp(
        previous_hour.replace(
            tzinfo=None
        )
    )


# ============================================================
# COMPLETE LIVE INFERENCE
#
# 1. Load Open-Meteo weather
# 2. Generate the exact 30 training features
# 3. Call six saved XGBoost models
# 4. Return calibration + SHAP + source metadata
#
# No deployment threshold.
# No public warning decision.
# ============================================================

def run_live_inference():

    reference_time = get_reference_time()

    season_mapping = (
        get_season_mapping()
    )

    # --------------------------------------------------------
    # Retrieve model-based hourly weather
    # Uses existing Step 18 cache.
    # --------------------------------------------------------

    payload, cache_used = (
        weather_module.fetch_api_response(
            reference_time
        )
    )

    hourly_data = (
        weather_module.parse_api_hourly(
            payload
        )
    )

    # --------------------------------------------------------
    # Generate 30 features
    # --------------------------------------------------------

    feature_values = (
        weather_module.build_features(
            hourly_data,
            reference_time,
            season_mapping,
        )
    )

    observed_at = (
        reference_time.strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    )

    # --------------------------------------------------------
    # Six-horizon model prediction
    # --------------------------------------------------------

    predictions = (
        predict_module.predict_features(
            feature_values,
            observed_at=observed_at,
            top_n=5,
        )
    )

    # --------------------------------------------------------
    # API response
    # --------------------------------------------------------

    return {
        "api_version": "1.0.0",

        "location": {
            "name": "Thu Duc, Ho Chi Minh City",
            "latitude": LATITUDE,
            "longitude": LONGITUDE,
        },

        "weather_data": {
            "reference_time": observed_at,
            "timezone": "Asia/Ho_Chi_Minh",

            "source": "Open-Meteo Forecast API",

            "source_is_verified_observation": False,

            "description": (
                "Model-derived hourly weather "
                "for the reference time "
                "and previous hours."
            ),

            "cached": bool(
                cache_used
            ),

            "feature_count": len(
                feature_values
            ),
        },

        "research_status": {
            "ready_for_public_warning": False,

            "deployment_threshold_validated": False,

            "actual_flood_labels_available": False,

            "warning": (
                "Results represent an experimental "
                "heavy-rain proxy, not validated "
                "street-flooding risk."
            ),
        },

        "prediction": predictions,
    }


# ============================================================
# HEALTH ENDPOINT
#
# Checks that the API process is running.
# It does not validate model quality or API availability.
# ============================================================

@app.get("/health")
def health():

    return {
        "status": "running",
        "service": "rainfall_research_api",
        "mode": "research_only",
    }


# ============================================================
# PREDICTION ENDPOINT
# ============================================================

@app.get(
    "/api/v1/rain-proxy/latest",
    summary="Latest experimental six-horizon rainfall prediction",
)
async def latest_prediction():

    try:

        return await run_in_threadpool(
            run_live_inference
        )

    except (
        RuntimeError,
        ValueError,
        FileNotFoundError,
        OSError,
        KeyError,
    ):

        logger.exception(
            "Live rainfall inference failed"
        )

        raise HTTPException(
            status_code=503,
            detail=(
                "Live inference unavailable. "
                "Check server logs, weather source "
                "and saved model artifacts."
            ),
        )


# ============================================================
# LOCAL DIRECT EXECUTION
# ============================================================

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
    )