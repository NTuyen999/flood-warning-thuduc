"""Step 17: Research-only inference for six XGBoost rainfall-proxy models.

Run from project root:
    python -m ml.src.models.17_predict --time "2026-09-01 12:00:00"
    python -m ml.src.models.17_predict --input-json features.json

For a backend, use importlib.import_module("ml.src.models.17_predict")
and call predict_features(feature_dict, observed_at="...").
"""

import argparse
import json
import math
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import xgboost as xgb
from scipy.special import expit


# ============================================================
# PATHS
# ============================================================

ROOT = Path(__file__).resolve().parents[3]

MODEL_DIR = ROOT / "ml/saved_models/final"

CALIBRATOR_DIR = ROOT / "ml/saved_models/calibrators"

FEATURE_FILE = MODEL_DIR / "feature_list.json"

SUMMARY_FILE = (
    ROOT / "ml/outputs/metrics/final_training_summary.csv"
)

DATA_FILE = ROOT / "data/processed/ml_dataset.csv"


# ============================================================
# LOAD MODELS, CALIBRATORS AND FEATURES
#
# Cache artifacts to avoid loading all models on every
# backend request.
# ============================================================

@lru_cache(maxsize=1)
def load_artifacts():

    with FEATURE_FILE.open(
        "r",
        encoding="utf-8"
    ) as f:
        features = json.load(f)

    if (
        not isinstance(features, list)
        or len(features) != 30
    ):
        raise ValueError(
            "Expected 30 features in feature_list.json"
        )

    if len(set(features)) != len(features):
        raise ValueError(
            "Feature list contains duplicate names"
        )

    if any(
        not isinstance(k, str)
        or k.startswith(("target_", "observed_"))
        for k in features
    ):
        raise ValueError(
            "Invalid or ground-truth feature in feature list"
        )

    models = {}
    calibrators = {}

    for h in range(1, 7):

        model_path = (
            MODEL_DIR / f"final_xgboost_h{h}.joblib"
        )

        cal_path = (
            CALIBRATOR_DIR
            / f"xgboost_h{h}_calibrator.joblib"
        )

        models[h] = joblib.load(model_path)
        calibrators[h] = joblib.load(cal_path)

        booster_features = (
            models[h].get_booster().feature_names
        )

        if (
            booster_features is not None
            and booster_features != features
        ):
            raise ValueError(
                f"H{h}: model feature order "
                "does not match feature_list.json"
            )

    # Historical rate is only a comparison baseline.
    # It is NOT a warning threshold.

    historical_rates = {}

    if SUMMARY_FILE.exists():

        summary = pd.read_csv(SUMMARY_FILE)

        for _, row in summary.iterrows():

            h = int(row["horizon"])

            samples = int(row["samples"])

            positives = int(
                row["positive_samples"]
            )

            if 1 <= h <= 6 and samples > 0:

                historical_rates[h] = (
                    positives / samples
                )

    return (
        features,
        models,
        calibrators,
        historical_rates
    )


# ============================================================
# INPUT VALIDATION
#
# Backend must supply exactly the 30 features
# used during model training.
# ============================================================

def validate_feature_dict(values, names):

    if not isinstance(values, dict):

        raise ValueError(
            "features must be a dictionary"
        )

    missing = sorted(
        set(names) - set(values)
    )

    extra = sorted(
        set(values) - set(names)
    )

    if missing or extra:

        raise ValueError(
            f"Feature mismatch: "
            f"missing={missing}, "
            f"unexpected={extra}"
        )

    cleaned = {}

    for name in names:

        value = values[name]

        if (
            isinstance(value, (bool, str))
            or not isinstance(
                value,
                (int, float, np.number)
            )
        ):

            raise ValueError(
                f"{name}: expected a numeric value, "
                f"got {type(value).__name__}"
            )

        number = float(value)

        if not math.isfinite(number):

            raise ValueError(
                f"{name}: NaN/Infinity is not accepted"
            )

        cleaned[name] = number

    return cleaned


# ============================================================
# RAW PROBABILITY -> LOGIT
#
# Must match Step 13 calibration.
# ============================================================

def to_logit(probability):

    p = np.clip(
        np.array(
            [probability],
            dtype=float
        ),
        1e-8,
        1 - 1e-8
    )

    return np.log(
        p / (1 - p)
    ).reshape(-1, 1)


# ============================================================
# MAIN INFERENCE FUNCTION
#
# This is the function the backend should call.
#
# It requires already-engineered weather features
# matching Step 06.
#
# No future observed rainfall may enter the features.
# ============================================================

def predict_features(
    feature_values,
    observed_at=None,
    top_n=5
):

    (
        features,
        models,
        calibrators,
        historical_rates
    ) = load_artifacts()

    cleaned = validate_feature_dict(
        feature_values,
        features
    )

    X = pd.DataFrame(
        [
            [
                cleaned[name]
                for name in features
            ]
        ],
        columns=features
    )

    if (
        not isinstance(top_n, int)
        or not 1 <= top_n <= len(features)
    ):

        raise ValueError(
            "top_n must be an integer between 1 and 30"
        )

    outputs = []

    # ========================================================
    # PREDICT H1 -> H6
    # ========================================================

    for h in range(1, 7):

        model = models[h]

        # ----------------------------------------------------
        # RAW XGBOOST SCORE
        # ----------------------------------------------------

        raw = float(
            model.predict_proba(X)[0, 1]
        )

        if (
            not math.isfinite(raw)
            or not 0 <= raw <= 1
        ):

            raise ValueError(
                f"H{h}: model returned invalid probability"
            )

        # ----------------------------------------------------
        # CALIBRATED PROBABILITY
        # ----------------------------------------------------

        calibrated = float(
            calibrators[h]
            .predict_proba(
                to_logit(raw)
            )[0, 1]
        )

        if (
            not math.isfinite(calibrated)
            or not 0 <= calibrated <= 1
        ):

            raise ValueError(
                f"H{h}: calibrator returned "
                "invalid probability"
            )

        # ----------------------------------------------------
        # NATIVE TREE SHAP
        #
        # Feature contributions are in raw log-odds.
        # They do not directly explain calibrated probability.
        # ----------------------------------------------------

        matrix = xgb.DMatrix(
            X,
            feature_names=features
        )

        contributions = np.asarray(
            model.get_booster().predict(
                matrix,
                pred_contribs=True
            )
        )

        expected_shape = (
            1,
            len(features) + 1
        )

        if contributions.shape != expected_shape:

            raise RuntimeError(
                f"H{h}: unexpected SHAP shape "
                f"{contributions.shape}"
            )

        shap_values = contributions[
            0,
            :-1
        ]

        base = float(
            contributions[0, -1]
        )

        log_odds = float(
            np.sum(
                contributions[0]
            )
        )

        reconstructed_probability = float(
            expit(log_odds)
        )

        if abs(
            reconstructed_probability - raw
        ) > 1e-3:

            raise RuntimeError(
                f"H{h}: SHAP reconstruction "
                "does not match model prediction"
            )

        # ----------------------------------------------------
        # TOP SHAP CONTRIBUTIONS
        # ----------------------------------------------------

        order = np.argsort(
            np.abs(shap_values)
        )[::-1][:top_n]

        explanations = []

        for index in order:

            index = int(index)

            effect = float(
                shap_values[index]
            )

            if effect > 0:

                direction = "increases"

            elif effect < 0:

                direction = "decreases"

            else:

                direction = "neutral"

            explanations.append(
                {
                    "feature":
                        features[index],

                    "input_value":
                        cleaned[
                            features[index]
                        ],

                    "shap_log_odds":
                        effect,

                    "effect_on_raw_score":
                        direction,
                }
            )

        # ----------------------------------------------------
        # PREDICTION OUTPUT
        #
        # H1 target uses observed rainfall at:
        # t+1, t+2, t+3
        #
        # H6 target uses observed rainfall at:
        # t+6, t+7, t+8
        #
        # No validated operational warning threshold.
        # ----------------------------------------------------

        outputs.append(
            {
                "horizon": h,

                "target_window_hours_from_t": [
                    h,
                    h + 2
                ],

                "raw_xgboost_score":
                    raw,

                "calibrated_event_probability":
                    calibrated,

                "historical_event_rate":
                    historical_rates.get(h),

                "warning_decision":
                    None,

                "warning_reason":
                    "No validated deployment threshold",

                "shap_base_log_odds":
                    base,

                "shap_prediction_log_odds":
                    log_odds,

                "top_shap_features":
                    explanations,
            }
        )

    # ========================================================
    # FINAL RESPONSE
    # ========================================================

    return {
        "observed_at":
            observed_at,

        "task":
            "heavy_rain_proxy_not_observed_street_flooding",

        "event_definition":
            (
                "Observed rain >= 30 mm summed over "
                "t+h, t+h+1, t+h+2 "
                "(hourly values)"
            ),

        "status":
            "research_only_not_validated_for_public_warnings",

        "feature_count":
            len(features),

        "shap_unit":
            (
                "raw XGBoost log-odds, "
                "not calibrated probability or causality"
            ),

        "results":
            outputs,
    }


# ============================================================
# HISTORICAL SMOKE TEST
#
# Read one already-engineered feature row from
# ml_dataset.csv.
#
# This does NOT retrieve live weather.
# ============================================================

def features_at_historical_time(timestamp):

    (
        features,
        _,
        _,
        _
    ) = load_artifacts()

    df = pd.read_csv(
        DATA_FILE,
        parse_dates=["time"]
    )

    time = pd.Timestamp(
        timestamp
    )

    if time.tzinfo is not None:

        raise ValueError(
            "Use local naive time "
            "YYYY-MM-DD HH:MM:SS "
            "as stored in the dataset"
        )

    matches = df.loc[
        df["time"] == time
    ]

    if len(matches) != 1:

        raise ValueError(
            f"Expected exactly one historical row "
            f"for {timestamp}; "
            f"found {len(matches)}"
        )

    row = matches.iloc[0]

    return {
        name: row[name]
        for name in features
    }


# ============================================================
# COMMAND LINE INTERFACE
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "Research-only XGBoost inference; "
            "no warning threshold"
        )
    )

    input_group = (
        parser.add_mutually_exclusive_group(
            required=True
        )
    )

    input_group.add_argument(
        "--time",
        help=(
            "Historical timestamp for smoke test, "
            "e.g. 2026-09-01 12:00:00"
        )
    )

    input_group.add_argument(
        "--input-json",
        type=Path,
        help=(
            "JSON file containing "
            "30 engineered features"
        )
    )

    parser.add_argument(
        "--top-n",
        type=int,
        default=5
    )

    args = parser.parse_args()

    # --------------------------------------------------------
    # HISTORICAL ROW
    # --------------------------------------------------------

    if args.time:

        values = (
            features_at_historical_time(
                args.time
            )
        )

        observed_at = args.time

    # --------------------------------------------------------
    # EXTERNAL INPUT FROM JSON
    # --------------------------------------------------------

    else:

        with args.input_json.open(
            "r",
            encoding="utf-8"
        ) as f:

            payload = json.load(f)

        if not isinstance(payload, dict):

            raise ValueError(
                "Input JSON must be an object"
            )

        observed_at = payload.get(
            "time"
        )

        if "features" in payload:

            values = payload[
                "features"
            ]

        else:

            values = {
                key: value
                for key, value in payload.items()
                if key != "time"
            }

    # --------------------------------------------------------
    # PREDICT
    # --------------------------------------------------------

    result = predict_features(
        values,
        observed_at=observed_at,
        top_n=args.top_n
    )

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
            allow_nan=False
        )
    )


if __name__ == "__main__":
    main()