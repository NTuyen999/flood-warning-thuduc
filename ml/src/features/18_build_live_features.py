"""Step 18: Build live weather features for XGBoost models.

Run:
    python -m ml.src.features.18_build_live_features --verify-local "2026-09-01 12:00:00"

    python -m ml.src.features.18_build_live_features --live

Live mode does not require historical CSV files.
"""

import argparse
import json

from datetime import datetime, timedelta, timezone
from pathlib import Path

from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import numpy as np
import pandas as pd


# ============================================================
# PATHS
# ============================================================

ROOT = Path(__file__).resolve().parents[3]

LABELED_FILE = (
    ROOT / "data/processed/weather_labeled.csv"
)

TRAIN_FEATURE_FILE = (
    ROOT / "data/processed/ml_dataset.csv"
)

FEATURE_LIST_FILE = (
    ROOT / "ml/saved_models/final/feature_list.json"
)

OUTPUT_DIR = (
    ROOT / "ml/outputs/live"
)

OUTPUT_FILE = (
    OUTPUT_DIR / "live_features.json"
)


# ============================================================
# OPEN-METEO CONFIG
# ============================================================

API_URL = "https://api.open-meteo.com/v1/forecast"

LATITUDE = 10.85
LONGITUDE = 106.77

TIMEZONE_NAME = "Asia/Ho_Chi_Minh"
VIETNAM_TZ = timezone(timedelta(hours=7))


# ============================================================
# RAW WEATHER FIELDS
# ============================================================

RAW_FIELDS = [
    "temperature_2m",
    "relative_humidity_2m",
    "pressure_msl",
    "surface_pressure",
    "cloud_cover",
    "wind_speed_10m",
    "wind_gusts_10m",
    "wind_direction_10m",
    "precipitation",
]


# ============================================================
# EXACT 30 MODEL FEATURES
# ============================================================

FEATURES = [
    "temperature_2m",
    "relative_humidity_2m",
    "pressure_msl",
    "surface_pressure",
    "cloud_cover",
    "wind_speed_10m",
    "wind_gusts_10m",

    "rain_last_1h",
    "rain_last_3h",
    "rain_last_6h",
    "rain_last_12h",
    "rain_last_24h",

    "rain_lag_1h",
    "rain_lag_2h",
    "rain_lag_3h",

    "humidity_lag_1h",
    "humidity_change_1h",
    "humidity_mean_3h",

    "pressure_lag_1h",
    "pressure_change_1h",
    "pressure_mean_3h",

    "wind_speed_lag_1h",
    "wind_speed_change_1h",

    "wind_direction_sin",
    "wind_direction_cos",

    "hour_sin",
    "hour_cos",
    "month_sin",
    "month_cos",

    "rainy_season",
]


# ============================================================
# RAINY SEASON
#
# Quy tắc đã xác minh từ dữ liệu train:
#
# Tháng 5–11: rainy_season = 1
# Tháng 12–4: rainy_season = 0
#
# Đưa trực tiếp vào cấu hình để không cần
# weather_labeled.csv khi chạy API.
# ============================================================

RAINY_MONTHS = frozenset(
    range(5, 12)
)


# ============================================================
# 1. FEATURE CONTRACT
# ============================================================

def check_feature_contract():

    with FEATURE_LIST_FILE.open(
        "r",
        encoding="utf-8"
    ) as handle:

        saved_features = json.load(
            handle
        )

    if saved_features != FEATURES:

        raise RuntimeError(
            "Feature names/order differ "
            "from final model feature_list.json"
        )

    print(
        "Feature contract: 30/30 OK"
    )


# ============================================================
# 2. SEASON MAPPING
#
# Giữ nguyên tên hàm để Bước 19 không cần sửa.
#
# KHÔNG còn đọc CSV lịch sử.
# ============================================================

def season_mapping_from_training():

    mapping = {
        month: float(
            month in RAINY_MONTHS
        )
        for month in range(1, 13)
    }

    print(
        "Rainy season mapping (source config):",
        mapping
    )

    return mapping


# ============================================================
# 3. LOCAL TIME
# ============================================================

def parse_local_time(value):

    timestamp = pd.Timestamp(
        value
    )

    if (
        pd.isna(timestamp)
        or timestamp.tzinfo is not None
    ):

        raise ValueError(
            "Use local time "
            "YYYY-MM-DD HH:00:00"
        )

    if (
        timestamp.minute
        or timestamp.second
        or timestamp.microsecond
        or timestamp.nanosecond
    ):

        raise ValueError(
            "Timestamp must align "
            "with a full hour"
        )

    return timestamp


# ============================================================
# 4. BUILD FEATURES
#
# Sử dụng đúng 24 giờ từ t-23 đến t.
# Không sử dụng dữ liệu tương lai.
# ============================================================

def build_features(
    hourly_df,
    at_time,
    season_by_month
):

    at_time = parse_local_time(
        at_time
    )

    required = {
        "time",
        *RAW_FIELDS
    }

    missing = (
        required
        - set(hourly_df.columns)
    )

    if missing:

        raise ValueError(
            f"Missing weather fields: "
            f"{sorted(missing)}"
        )

    data = hourly_df[
        [
            "time",
            *RAW_FIELDS
        ]
    ].copy()

    data["time"] = pd.to_datetime(
        data["time"],
        errors="raise"
    )

    if data["time"].dt.tz is not None:

        raise ValueError(
            "Hourly timestamps must use "
            "naive local time"
        )

    # --------------------------------------------------------
    # Exactly 24 consecutive hours
    # --------------------------------------------------------

    data = data.loc[
        (
            data["time"]
            >= at_time - pd.Timedelta(hours=23)
        )
        &
        (
            data["time"]
            <= at_time
        )
    ]

    data = (
        data.sort_values("time")
        .reset_index(drop=True)
    )

    expected_times = pd.Series(
        pd.date_range(
            end=at_time,
            periods=24,
            freq="h"
        )
    )

    if (
        len(data) != 24
        or not data["time"].equals(
            expected_times
        )
    ):

        raise RuntimeError(
            "Need 24 consecutive hourly rows "
            f"ending at {at_time}"
        )

    # --------------------------------------------------------
    # Validate raw values
    # --------------------------------------------------------

    for field in RAW_FIELDS:

        data[field] = pd.to_numeric(
            data[field],
            errors="raise"
        )

    if not np.isfinite(
        data[RAW_FIELDS].to_numpy(
            dtype=float
        )
    ).all():

        raise RuntimeError(
            "Weather data contains "
            "NaN or Infinity"
        )

    if (
        data["precipitation"] < 0
    ).any():

        raise RuntimeError(
            "Negative precipitation"
        )

    # ========================================================
    # RAIN
    # ========================================================

    rain = data["precipitation"]

    data["rain_last_1h"] = rain

    for hours in (
        3,
        6,
        12,
        24
    ):

        data[
            f"rain_last_{hours}h"
        ] = rain.rolling(
            window=hours,
            min_periods=hours
        ).sum()

    # ========================================================
    # RAIN LAGS
    # ========================================================

    for lag in (
        1,
        2,
        3
    ):

        data[
            f"rain_lag_{lag}h"
        ] = rain.shift(lag)

    # ========================================================
    # HUMIDITY
    # ========================================================

    humidity = data[
        "relative_humidity_2m"
    ]

    data["humidity_lag_1h"] = (
        humidity.shift(1)
    )

    data["humidity_change_1h"] = (
        humidity
        - data["humidity_lag_1h"]
    )

    data["humidity_mean_3h"] = (
        humidity.rolling(
            window=3,
            min_periods=3
        ).mean()
    )

    # ========================================================
    # PRESSURE
    # ========================================================

    pressure = data[
        "pressure_msl"
    ]

    data["pressure_lag_1h"] = (
        pressure.shift(1)
    )

    data["pressure_change_1h"] = (
        pressure
        - data["pressure_lag_1h"]
    )

    data["pressure_mean_3h"] = (
        pressure.rolling(
            window=3,
            min_periods=3
        ).mean()
    )

    # ========================================================
    # WIND SPEED
    # ========================================================

    wind = data[
        "wind_speed_10m"
    ]

    data["wind_speed_lag_1h"] = (
        wind.shift(1)
    )

    data["wind_speed_change_1h"] = (
        wind
        - data["wind_speed_lag_1h"]
    )

    # ========================================================
    # WIND DIRECTION
    # ========================================================

    radians = np.deg2rad(
        data["wind_direction_10m"]
    )

    data["wind_direction_sin"] = (
        np.sin(radians)
    )

    data["wind_direction_cos"] = (
        np.cos(radians)
    )

    # ========================================================
    # TIME CYCLICAL FEATURES
    # ========================================================

    hour = data["time"].dt.hour
    month = data["time"].dt.month

    data["hour_sin"] = np.sin(
        2 * np.pi * hour / 24
    )

    data["hour_cos"] = np.cos(
        2 * np.pi * hour / 24
    )

    data["month_sin"] = np.sin(
        2 * np.pi * month / 12
    )

    data["month_cos"] = np.cos(
        2 * np.pi * month / 12
    )

    # ========================================================
    # RAINY SEASON
    # ========================================================

    data["rainy_season"] = (
        month.map(
            season_by_month
        )
    )

    # ========================================================
    # FINAL 30 FEATURES
    # ========================================================

    last = data.iloc[-1]

    features = {
        feature: float(
            last[feature]
        )
        for feature in FEATURES
    }

    if not all(
        np.isfinite(value)
        for value in features.values()
    ):

        raise RuntimeError(
            "Calculated features contain "
            "NaN or Infinity"
        )

    return features


# ============================================================
# 5. OFFLINE VERIFICATION
#
# Chỉ chế độ --verify-local mới cần CSV lịch sử.
#
# Thành viên khác không cần chạy chế độ này.
# ============================================================

def verify_local(
    at_time,
    season_by_month
):

    at_time = parse_local_time(
        at_time
    )

    if (
        not LABELED_FILE.exists()
        or not TRAIN_FEATURE_FILE.exists()
    ):

        raise FileNotFoundError(
            "Offline verification requires "
            "historical CSV files. "
            "Live API does not."
        )

    hourly = pd.read_csv(
        LABELED_FILE,

        usecols=[
            "time",
            *RAW_FIELDS
        ],

        parse_dates=["time"]
    )

    generated = build_features(
        hourly,
        at_time,
        season_by_month
    )

    reference = pd.read_csv(
        TRAIN_FEATURE_FILE,

        usecols=[
            "time",
            *FEATURES
        ],

        parse_dates=["time"]
    )

    reference = reference.loc[
        reference["time"] == at_time
    ]

    if len(reference) != 1:

        raise RuntimeError(
            "Expected exactly one "
            "reference row"
        )

    mismatches = []

    for feature in FEATURES:

        expected = float(
            reference.iloc[0][feature]
        )

        actual = generated[
            feature
        ]

        if not np.isclose(
            actual,
            expected,
            rtol=1e-6,
            atol=1e-6
        ):

            mismatches.append(
                (
                    feature,
                    actual,
                    expected
                )
            )

    if mismatches:

        raise RuntimeError(
            f"Feature parity failed: "
            f"{mismatches}"
        )

    print()
    print(
        "FEATURE PARITY CHECK PASSED"
    )

    print(
        "Time:",
        at_time
    )

    print(
        "Matching features: 30/30"
    )

    print(
        "Rain last 24h:",
        generated["rain_last_24h"]
    )

    print(
        "Rainy season:",
        generated["rainy_season"]
    )


# ============================================================
# 6. FETCH OPEN-METEO
# ============================================================

def fetch_api_response(
    at_time
):

    at_time = parse_local_time(
        at_time
    )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    cache_file = (
        OUTPUT_DIR
        / f"openmeteo_{at_time:%Y%m%d_%H}.json"
    )

    if cache_file.exists():

        with cache_file.open(
            "r",
            encoding="utf-8"
        ) as handle:

            return (
                json.load(handle),
                True
            )

    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,

        "timezone": TIMEZONE_NAME,

        "hourly": ",".join(
            RAW_FIELDS
        ),

        "past_days": 2,
        "forecast_days": 1,

        "temperature_unit": "celsius",
        "wind_speed_unit": "kmh",
        "precipitation_unit": "mm",
    }

    request = Request(
        f"{API_URL}?{urlencode(params)}",

        headers={
            "User-Agent":
                "UIT-Rain-Research-Prototype/1.0"
        }
    )

    try:

        with urlopen(
            request,
            timeout=25
        ) as response:

            payload = json.load(
                response
            )

    except HTTPError as error:

        if error.code == 429:

            raise RuntimeError(
                "Open-Meteo rate limit HTTP 429. "
                "Do not retry repeatedly."
            ) from error

        raise RuntimeError(
            f"Open-Meteo HTTP {error.code}"
        ) from error

    except (
        URLError,
        TimeoutError
    ) as error:

        raise RuntimeError(
            f"Open-Meteo request failed: "
            f"{error}"
        ) from error

    if (
        not isinstance(payload, dict)
        or payload.get("error")
    ):

        raise RuntimeError(
            f"Open-Meteo error: "
            f"{payload}"
        )

    with cache_file.open(
        "w",
        encoding="utf-8"
    ) as handle:

        json.dump(
            payload,
            handle,
            ensure_ascii=False
        )

    return (
        payload,
        False
    )


# ============================================================
# 7. PARSE API RESPONSE
# ============================================================

def parse_api_hourly(
    payload
):

    if payload.get(
        "timezone"
    ) != TIMEZONE_NAME:

        raise RuntimeError(
            "Unexpected API timezone"
        )

    hourly = payload.get(
        "hourly"
    )

    if not isinstance(
        hourly,
        dict
    ):

        raise RuntimeError(
            "Open-Meteo has no hourly data"
        )

    missing = (
        {"time", *RAW_FIELDS}
        - set(hourly)
    )

    if missing:

        raise RuntimeError(
            f"Missing hourly fields: "
            f"{sorted(missing)}"
        )

    units = payload.get(
        "hourly_units",
        {}
    )

    expected_units = {
        "temperature_2m": "°C",
        "precipitation": "mm",
        "wind_speed_10m": "km/h",
        "wind_gusts_10m": "km/h",
        "pressure_msl": "hPa",
        "surface_pressure": "hPa",
    }

    for (
        field,
        expected
    ) in expected_units.items():

        if (
            field in units
            and units[field] != expected
        ):

            raise RuntimeError(
                f"Unexpected unit "
                f"{field}: {units[field]}"
            )

    frame = pd.DataFrame(
        {
            field: hourly[field]
            for field in [
                "time",
                *RAW_FIELDS
            ]
        }
    )

    frame["time"] = pd.to_datetime(
        frame["time"],
        errors="raise"
    )

    if frame["time"].dt.tz is not None:

        raise RuntimeError(
            "Expected local naive "
            "API timestamps"
        )

    return frame


# ============================================================
# 8. LIVE INFERENCE FEATURES
# ============================================================

def run_live(
    season_by_month
):

    now = datetime.now(
        VIETNAM_TZ
    )

    reference = pd.Timestamp(
        now.replace(
            minute=0,
            second=0,
            microsecond=0,
            tzinfo=None
        )
        - timedelta(hours=1)
    )

    payload, cache_used = (
        fetch_api_response(
            reference
        )
    )

    hourly = parse_api_hourly(
        payload
    )

    features = build_features(
        hourly,
        reference,
        season_by_month
    )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    output = {
        "time": reference.strftime(
            "%Y-%m-%d %H:%M:%S"
        ),

        "features": features,

        "meta": {
            "location":
                "Thu Duc, Ho Chi Minh City",

            "latitude_requested":
                LATITUDE,

            "longitude_requested":
                LONGITUDE,

            "timezone":
                TIMEZONE_NAME,

            "source":
                "Open-Meteo Forecast API",

            "source_is_ground_observation":
                False,

            "cache_used":
                bool(cache_used),

            "fetched_at_local":
                now.isoformat(),

            "mode":
                "research_only",

            "note":
                (
                    "Model-derived weather is "
                    "not a verified ground observation."
                ),
        }
    }

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8"
    ) as handle:

        json.dump(
            output,
            handle,
            indent=2,
            ensure_ascii=False,
            allow_nan=False
        )

    print()
    print(
        "LIVE FEATURE ENGINEERING COMPLETED"
    )

    print(
        "Time:",
        output["time"]
    )

    print(
        "Feature count:",
        len(features)
    )

    print(
        "Cache used:",
        bool(cache_used)
    )

    print(
        "Output:",
        OUTPUT_FILE
    )

    print()
    print(
        "Next command:"
    )

    print(
        "python -m ml.src.models.17_predict "
        "--input-json "
        "ml/outputs/live/live_features.json"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "Build 30 model features"
        )
    )

    group = (
        parser.add_mutually_exclusive_group(
            required=True
        )
    )

    group.add_argument(
        "--verify-local",
        metavar="TIME"
    )

    group.add_argument(
        "--live",
        action="store_true"
    )

    args = parser.parse_args()

    check_feature_contract()

    season_by_month = (
        season_mapping_from_training()
    )

    if args.verify_local:

        verify_local(
            args.verify_local,
            season_by_month
        )

    else:

        run_live(
            season_by_month
        )


if __name__ == "__main__":
    main()