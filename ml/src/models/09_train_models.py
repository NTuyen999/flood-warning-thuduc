from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    precision_score,
    recall_score,
    f1_score,
    average_precision_score,
    roc_auc_score,
    brier_score_loss,
)

from xgboost import XGBClassifier
from lightgbm import LGBMClassifier


# ============================================================
# PATHS
# ============================================================

SPLIT_DIR = Path("data/processed/splits")
MODEL_DIR = Path("ml/saved_models")
OUTPUT_DIR = Path("ml/outputs/metrics")


# ============================================================
# FEATURES
#
# Chỉ sử dụng thông tin hiện tại + quá khứ.
#
# KHÔNG đưa:
# - target_h1 ... target_h6
# - observed_rain_h1_3h ... observed_rain_h6_3h
#
# vào model.
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
# EVALUATION
# ============================================================

def evaluate(
    y_true,
    probability,
    threshold=0.5
):

    y_true = np.asarray(
        y_true,
        dtype=int
    )

    probability = np.asarray(
        probability,
        dtype=float
    )

    prediction = (
        probability >= threshold
    ).astype(int)

    result = {
        "precision": precision_score(
            y_true,
            prediction,
            zero_division=0,
        ),

        "recall": recall_score(
            y_true,
            prediction,
            zero_division=0,
        ),

        "f1": f1_score(
            y_true,
            prediction,
            zero_division=0,
        ),

        "pr_auc": average_precision_score(
            y_true,
            probability,
        ),

        "brier": brier_score_loss(
            y_true,
            probability,
        ),
    }

    if len(np.unique(y_true)) == 2:

        result["roc_auc"] = roc_auc_score(
            y_true,
            probability
        )

    else:

        result["roc_auc"] = np.nan

    return result


# ============================================================
# PREPARE DATA
#
# FIX:
# Giữ lại cột time để sau này lưu prediction theo timestamp.
# ============================================================

def prepare_data(
    df,
    target_col
):

    required_columns = (
        ["time"]
        + FEATURES
        + [target_col]
    )

    valid = (
        df[required_columns]
        .dropna()
        .copy()
    )

    X = valid[
        FEATURES
    ].copy()

    y = (
        valid[target_col]
        .astype(int)
    )

    return (
        valid,
        X,
        y
    )


# ============================================================
# BUILD MODELS
# ============================================================

def build_models(
    scale_pos_weight
):

    models = {

        "RandomForest":
            RandomForestClassifier(
                n_estimators=300,
                max_depth=10,
                min_samples_leaf=2,

                class_weight=(
                    "balanced_subsample"
                ),

                random_state=42,
                n_jobs=-1,
            ),

        "XGBoost":
            XGBClassifier(
                objective="binary:logistic",

                n_estimators=300,
                max_depth=3,
                learning_rate=0.05,

                subsample=0.8,
                colsample_bytree=0.8,

                scale_pos_weight=(
                    scale_pos_weight
                ),

                eval_metric="logloss",

                tree_method="hist",

                random_state=42,
                n_jobs=-1,
            ),

        "LightGBM":
            LGBMClassifier(
                objective="binary",

                n_estimators=300,
                learning_rate=0.05,

                num_leaves=15,
                max_depth=5,

                min_child_samples=5,

                subsample=0.8,
                colsample_bytree=0.8,

                scale_pos_weight=(
                    scale_pos_weight
                ),

                random_state=42,
                n_jobs=-1,

                verbose=-1,
            ),
    }

    return models


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("TRAINING ML MODELS")
    print("=" * 70)

    # --------------------------------------------------------
    # Load Train / Validation
    # --------------------------------------------------------

    train_df = pd.read_csv(
        SPLIT_DIR / "train.csv",
        parse_dates=["time"]
    )

    validation_df = pd.read_csv(
        SPLIT_DIR / "validation.csv",
        parse_dates=["time"]
    )

    print(
        "\nTrain shape:",
        train_df.shape
    )

    print(
        "Validation shape:",
        validation_df.shape
    )

    # --------------------------------------------------------
    # Sanity check
    # --------------------------------------------------------

    missing_features = [
        feature
        for feature in FEATURES
        if feature not in train_df.columns
    ]

    if missing_features:

        raise ValueError(
            "Missing features: "
            + str(missing_features)
        )

    MODEL_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    results = []
    prediction_rows = []

    # ========================================================
    # 6 HORIZONS
    # ========================================================

    for h in range(1, 7):

        print("\n")
        print("=" * 70)
        print(f"HORIZON +{h}H")
        print("=" * 70)

        target_col = (
            f"target_h{h}"
        )

        # ----------------------------------------------------
        # Prepare Train
        # ----------------------------------------------------

        (
            train_valid,
            X_train,
            y_train,
        ) = prepare_data(
            train_df,
            target_col
        )

        # ----------------------------------------------------
        # Prepare Validation
        # ----------------------------------------------------

        (
            val_valid,
            X_val,
            y_val,
        ) = prepare_data(
            validation_df,
            target_col
        )

        negative_count = int(
            (y_train == 0).sum()
        )

        positive_count = int(
            (y_train == 1).sum()
        )

        validation_positive = int(
            (y_val == 1).sum()
        )

        print(
            "Train samples:",
            len(y_train)
        )

        print(
            "Train negative:",
            negative_count
        )

        print(
            "Train positive:",
            positive_count
        )

        print(
            "Validation samples:",
            len(y_val)
        )

        print(
            "Validation positive:",
            validation_positive
        )

        if positive_count == 0:

            print(
                "No positive samples "
                "in training set."
            )

            continue

        if validation_positive == 0:

            print(
                "WARNING: No positive "
                "samples in validation."
            )

        # ----------------------------------------------------
        # Class Imbalance Weight
        # ----------------------------------------------------

        scale_pos_weight = (
            negative_count
            / positive_count
        )

        print(
            "Scale pos weight:",
            round(
                scale_pos_weight,
                2
            )
        )

        # ----------------------------------------------------
        # Models
        # ----------------------------------------------------

        models = build_models(
            scale_pos_weight
        )

        # ====================================================
        # TRAIN MODELS
        # ====================================================

        for (
            model_name,
            model
        ) in models.items():

            print(
                f"\nTraining "
                f"{model_name}..."
            )

            # -----------------------------------------------
            # Train
            # -----------------------------------------------

            model.fit(
                X_train,
                y_train
            )

            # -----------------------------------------------
            # Probability on validation
            # -----------------------------------------------

            probability = (
                model.predict_proba(
                    X_val
                )[:, 1]
            )

            # -----------------------------------------------
            # Evaluate default threshold 0.5
            # -----------------------------------------------

            metrics = evaluate(
                y_val,
                probability,
                threshold=0.5
            )

            result = {
                "model":
                    model_name,

                "horizon":
                    h,

                "train_samples":
                    len(y_train),

                "train_positives":
                    positive_count,

                "validation_samples":
                    len(y_val),

                "validation_positives":
                    validation_positive,

                "scale_pos_weight":
                    scale_pos_weight,

                **metrics,
            }

            results.append(
                result
            )

            print(
                "Precision:",
                round(
                    metrics["precision"],
                    6
                )
            )

            print(
                "Recall:",
                round(
                    metrics["recall"],
                    6
                )
            )

            print(
                "F1:",
                round(
                    metrics["f1"],
                    6
                )
            )

            print(
                "PR-AUC:",
                round(
                    metrics["pr_auc"],
                    6
                )
            )

            print(
                "ROC-AUC:",
                round(
                    metrics["roc_auc"],
                    6
                )
            )

            print(
                "Brier:",
                round(
                    metrics["brier"],
                    6
                )
            )

            # -----------------------------------------------
            # Save Model
            # -----------------------------------------------

            model_filename = (
                f"{model_name.lower()}"
                f"_h{h}.joblib"
            )

            model_file = (
                MODEL_DIR
                / model_filename
            )

            joblib.dump(
                model,
                model_file
            )

            print(
                "Saved model:",
                model_file
            )

            # -----------------------------------------------
            # Save validation prediction
            # -----------------------------------------------

            for (
                timestamp,
                true_value,
                probability_value,
            ) in zip(
                val_valid["time"],
                y_val,
                probability,
            ):

                prediction_rows.append({
                    "time":
                        timestamp,

                    "model":
                        model_name,

                    "horizon":
                        h,

                    "y_true":
                        int(
                            true_value
                        ),

                    "probability":
                        float(
                            probability_value
                        ),
                })

    # ========================================================
    # SAVE RESULTS
    # ========================================================

    results_df = pd.DataFrame(
        results
    )

    predictions_df = pd.DataFrame(
        prediction_rows
    )

    results_file = (
        OUTPUT_DIR
        / "ml_validation_results.csv"
    )

    predictions_file = (
        OUTPUT_DIR
        / "validation_predictions.csv"
    )

    results_df.to_csv(
        results_file,
        index=False,
        encoding="utf-8-sig"
    )

    predictions_df.to_csv(
        predictions_file,
        index=False,
        encoding="utf-8-sig"
    )

    # ========================================================
    # FINAL TABLE
    # ========================================================

    print("\n")
    print("=" * 70)
    print("MODEL TRAINING COMPLETED")
    print("=" * 70)

    if not results_df.empty:

        display_columns = [
            "model",
            "horizon",
            "train_positives",
            "validation_positives",
            "precision",
            "recall",
            "f1",
            "pr_auc",
            "roc_auc",
            "brier",
        ]

        print(
            results_df[
                display_columns
            ].to_string(
                index=False
            )
        )

    print(
        "\nResults:",
        results_file
    )

    print(
        "Validation predictions:",
        predictions_file
    )


if __name__ == "__main__":
    main()