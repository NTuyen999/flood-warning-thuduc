from pathlib import Path
import json

import joblib
import pandas as pd

from xgboost import XGBClassifier


# ============================================================
# PATHS
# ============================================================

DATA_FILE = Path(
    "data/processed/ml_dataset.csv"
)

MODEL_DIR = Path(
    "ml/saved_models/final"
)

OUTPUT_DIR = Path(
    "ml/outputs/metrics"
)


# ============================================================
# TEST PERIOD
#
# 2026 được giữ nguyên hoàn toàn làm TEST.
# Không được dùng để train.
# ============================================================

TEST_START = pd.Timestamp(
    "2026-01-01 00:00:00"
)


# ============================================================
# FINAL FEATURES
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
# BUILD FINAL XGBOOST
#
# Giữ đúng cấu hình đã dùng trong Temporal CV.
# Không tuning lại.
# ============================================================

def build_model(
    scale_pos_weight
):

    model = XGBClassifier(
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
    )

    return model


# ============================================================
# PREPARE FINAL TRAINING DATA
# ============================================================

def prepare_training_data(
    df,
    horizon
):

    target_col = (
        f"target_h{horizon}"
    )

    # --------------------------------------------------------
    # TARGET WINDOW:
    #
    # h1 -> t+1, t+2, t+3
    # h2 -> t+2, t+3, t+4
    # ...
    # h6 -> t+6, t+7, t+8
    #
    # Do đó target_h dùng dữ liệu tối đa tới:
    #
    # t + horizon + 2 giờ
    #
    # Muốn tuyệt đối không chạm TEST 2026:
    #
    # t + horizon + 2 < 2026-01-01
    # --------------------------------------------------------

    future_hours_needed = (
        horizon + 2
    )

    training_cutoff = (
        TEST_START
        - pd.Timedelta(
            hours=future_hours_needed
        )
    )

    # Ví dụ h6:
    #
    # cutoff = 2025-12-31 16:00
    #
    # chỉ lấy t < 16:00
    # tức timestamp cuối là 15:00.
    training_df = df[
        df["time"]
        < training_cutoff
    ].copy()

    required_columns = (
        ["time"]
        + FEATURES
        + [target_col]
    )

    training_df = (
        training_df[
            required_columns
        ]
        .dropna()
        .copy()
    )

    X_train = (
        training_df[
            FEATURES
        ].copy()
    )

    y_train = (
        training_df[
            target_col
        ]
        .astype(int)
    )

    return (
        training_df,
        X_train,
        y_train,
        training_cutoff,
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("TRAIN FINAL XGBOOST MODELS")
    print("=" * 70)

    # --------------------------------------------------------
    # Load complete dataset
    # --------------------------------------------------------

    df = pd.read_csv(
        DATA_FILE,
        parse_dates=["time"]
    )

    df = (
        df.sort_values("time")
        .reset_index(drop=True)
    )

    print(
        "\nDataset:",
        DATA_FILE
    )

    print(
        "Shape:",
        df.shape
    )

    print(
        "Time range:",
        df["time"].min(),
        "->",
        df["time"].max()
    )

    # --------------------------------------------------------
    # Feature sanity check
    # --------------------------------------------------------

    missing_features = [
        feature
        for feature in FEATURES
        if feature not in df.columns
    ]

    if missing_features:

        raise RuntimeError(
            "Missing features: "
            + str(
                missing_features
            )
        )

    MODEL_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    summary_rows = []

    # ========================================================
    # TRAIN H1 -> H6
    # ========================================================

    for horizon in range(
        1,
        7
    ):

        print("\n")
        print("=" * 70)
        print(
            f"FINAL MODEL HORIZON +{horizon}H"
        )
        print("=" * 70)

        target_col = (
            f"target_h{horizon}"
        )

        (
            training_df,
            X_train,
            y_train,
            training_cutoff,
        ) = prepare_training_data(
            df,
            horizon
        )

        # ----------------------------------------------------
        # Counts
        # ----------------------------------------------------

        positive_count = int(
            (
                y_train == 1
            ).sum()
        )

        negative_count = int(
            (
                y_train == 0
            ).sum()
        )

        if positive_count == 0:

            raise RuntimeError(
                f"No positive samples "
                f"for horizon {horizon}."
            )

        scale_pos_weight = (
            negative_count
            / positive_count
        )

        print(
            "Training cutoff:",
            training_cutoff
        )

        print(
            "Last training timestamp:",
            training_df[
                "time"
            ].max()
        )

        print(
            "Training samples:",
            len(y_train)
        )

        print(
            "Negative:",
            negative_count
        )

        print(
            "Positive:",
            positive_count
        )

        print(
            "Scale pos weight:",
            round(
                scale_pos_weight,
                2
            )
        )

        # ----------------------------------------------------
        # Build
        # ----------------------------------------------------

        model = build_model(
            scale_pos_weight
        )

        # ----------------------------------------------------
        # Train
        # ----------------------------------------------------

        print(
            "\nTraining XGBoost..."
        )

        model.fit(
            X_train,
            y_train
        )

        # ----------------------------------------------------
        # Save
        # ----------------------------------------------------

        model_file = (
            MODEL_DIR
            /
            f"final_xgboost_h{horizon}.joblib"
        )

        joblib.dump(
            model,
            model_file
        )

        print(
            "Saved:",
            model_file
        )

        # ----------------------------------------------------
        # Summary
        # ----------------------------------------------------

        summary_rows.append(
            {
                "horizon":
                    horizon,

                "model":
                    "XGBoost",

                "training_start":
                    training_df[
                        "time"
                    ].min(),

                "training_end":
                    training_df[
                        "time"
                    ].max(),

                "training_cutoff":
                    training_cutoff,

                "samples":
                    len(y_train),

                "positive_samples":
                    positive_count,

                "negative_samples":
                    negative_count,

                "scale_pos_weight":
                    scale_pos_weight,

                "model_file":
                    str(
                        model_file
                    ),
            }
        )

    # ========================================================
    # SAVE TRAINING SUMMARY
    # ========================================================

    summary_df = pd.DataFrame(
        summary_rows
    )

    summary_file = (
        OUTPUT_DIR
        /
        "final_training_summary.csv"
    )

    summary_df.to_csv(
        summary_file,
        index=False,
        encoding="utf-8-sig"
    )

    # ========================================================
    # SAVE FEATURE LIST
    #
    # Bước predict.py sau này sẽ dùng đúng list này.
    # ========================================================

    feature_file = (
        MODEL_DIR
        /
        "feature_list.json"
    )

    with open(
        feature_file,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            FEATURES,
            f,
            ensure_ascii=False,
            indent=4,
        )

    # ========================================================
    # FINAL DISPLAY
    # ========================================================

    print("\n")
    print("=" * 70)
    print("FINAL TRAINING COMPLETED")
    print("=" * 70)

    print(
        summary_df[
            [
                "horizon",
                "model",
                "training_end",
                "samples",
                "positive_samples",
                "negative_samples",
                "scale_pos_weight",
            ]
        ].to_string(
            index=False
        )
    )

    print(
        "\nTraining summary:",
        summary_file
    )

    print(
        "Feature list:",
        feature_file
    )

    print(
        "Final models:",
        MODEL_DIR
    )

    print("\nIMPORTANT:")
    print(
        "2026 has NOT been used "
        "for model training."
    )


if __name__ == "__main__":
    main()