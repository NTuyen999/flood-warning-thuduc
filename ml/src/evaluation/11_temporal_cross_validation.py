"""Temporal cross-validation with purged label windows for h1..h6.

Run from the project root:
    python -m ml.src.evaluation.11_temporal_cross_validation

This writes out-of-fold predictions and fold/aggregate metrics. 2026 is held out.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from lightgbm import LGBMClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    roc_auc_score,
)
from xgboost import XGBClassifier


# ============================================================
# PATHS
# ============================================================

DATA_FILE = Path(
    "data/processed/ml_dataset.csv"
)

FEATURE_FILE = Path(
    "ml/saved_models/final/feature_list.json"
)

OUTPUT_DIR = Path(
    "ml/outputs/metrics"
)

TEST_START = pd.Timestamp(
    "2026-01-01 00:00:00"
)


# ============================================================
# TEMPORAL FOLDS
#
# (name, train_start, validation_start, validation_end)
#
# validation_end is exclusive.
# ============================================================

FOLDS = [
    (
        "fold1",
        "2010-01-01",
        "2019-01-01",
        "2022-01-01",
    ),
    (
        "fold2",
        "2010-01-01",
        "2022-01-01",
        "2024-01-01",
    ),
    (
        "fold3",
        "2010-01-01",
        "2024-01-01",
        "2026-01-01",
    ),
]


# ============================================================
# BUILD MODELS
#
# Giữ nguyên cấu hình model đã dùng.
# Không tuning lại theo kết quả TEST 2026.
# ============================================================

def build_models(pos_weight):

    return {
        "RandomForest": RandomForestClassifier(
            n_estimators=300,
            max_depth=10,
            min_samples_leaf=2,
            class_weight="balanced_subsample",
            random_state=42,
            n_jobs=-1,
        ),

        "XGBoost": XGBClassifier(
            objective="binary:logistic",
            n_estimators=300,
            max_depth=3,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            scale_pos_weight=pos_weight,
            eval_metric="logloss",
            tree_method="hist",
            random_state=42,
            n_jobs=-1,
        ),

        "LightGBM": LGBMClassifier(
            objective="binary",
            n_estimators=300,
            learning_rate=0.05,
            num_leaves=15,
            max_depth=5,
            min_child_samples=5,
            subsample=0.8,
            colsample_bytree=0.8,
            scale_pos_weight=pos_weight,
            random_state=42,
            n_jobs=-1,
            verbose=-1,
        ),
    }


# ============================================================
# PREPARE DATA
# ============================================================

def prepare(df, features, target):

    cols = [
        "time",
        *features,
        target,
    ]

    missing = (
        set(cols) - set(df.columns)
    )

    if missing:
        raise ValueError(
            f"Missing columns: {sorted(missing)}"
        )

    clean = (
        df.loc[:, cols]
        .dropna()
        .copy()
    )

    X = clean[features]

    y = (
        clean[target]
        .astype(int)
    )

    return clean, X, y


# ============================================================
# PURGED TEMPORAL FOLD
#
# Nhãn target_h sử dụng lượng mưa tương lai:
#
# h1: t+1, t+2, t+3
# h2: t+2, t+3, t+4
# ...
# h6: t+6, t+7, t+8
#
# Vì vậy:
#
# last label timestamp = t + horizon + 2 hours
#
# Nếu timestamp cuối của nhãn chạm vào
# giai đoạn validation thì không được đưa
# mẫu đó vào training.
#
# Tương tự, validation không được có nhãn
# vượt qua validation_end.
# ============================================================

def purged_fold(df, fold, horizon, features):

    (
        name,
        train_start,
        val_start,
        val_end,
    ) = fold

    train_start = pd.Timestamp(
        train_start
    )

    val_start = pd.Timestamp(
        val_start
    )

    val_end = pd.Timestamp(
        val_end
    )

    label_ahead = pd.Timedelta(
        hours=horizon + 2
    )

    # --------------------------------------------------------
    # Training cutoff
    #
    # Nhãn phải kết thúc trước val_start.
    # --------------------------------------------------------

    train_cutoff = (
        val_start - label_ahead
    )

    # --------------------------------------------------------
    # Validation cutoff
    #
    # Nhãn phải kết thúc trước val_end.
    # --------------------------------------------------------

    val_cutoff = (
        val_end - label_ahead
    )

    # --------------------------------------------------------
    # Training period
    # --------------------------------------------------------

    train = df.loc[
        (
            df["time"] >= train_start
        )
        &
        (
            df["time"] < train_cutoff
        )
    ]

    # --------------------------------------------------------
    # Validation period
    # --------------------------------------------------------

    validation = df.loc[
        (
            df["time"] >= val_start
        )
        &
        (
            df["time"] < val_cutoff
        )
    ]

    target = (
        f"target_h{horizon}"
    )

    tr, x_tr, y_tr = prepare(
        train,
        features,
        target,
    )

    va, x_va, y_va = prepare(
        validation,
        features,
        target,
    )

    # --------------------------------------------------------
    # Safety checks
    # --------------------------------------------------------

    if tr.empty or va.empty:
        raise RuntimeError(
            f"{name}/h{horizon}: "
            "empty train or validation"
        )

    if (
        tr["time"].max() + label_ahead
        >= val_start
    ):
        raise AssertionError(
            f"{name}/h{horizon}: "
            "train target crosses into validation"
        )

    if (
        va["time"].max() + label_ahead
        >= val_end
    ):
        raise AssertionError(
            f"{name}/h{horizon}: "
            "validation target crosses period end"
        )

    if val_end > TEST_START:
        raise AssertionError(
            "2026 must not be in "
            "any temporal-CV fold"
        )

    return (
        tr,
        x_tr,
        y_tr,
        va,
        x_va,
        y_va,
    )


# ============================================================
# RANKING METRICS
# ============================================================

def ranking_metrics(y, probabilities):

    y = np.asarray(
        y,
        dtype=int
    )

    p = np.asarray(
        probabilities,
        dtype=float
    )

    pr_auc = (
        float(
            average_precision_score(
                y,
                p
            )
        )
        if y.sum() > 0
        else np.nan
    )

    roc_auc = (
        float(
            roc_auc_score(
                y,
                p
            )
        )
        if len(np.unique(y)) == 2
        else np.nan
    )

    brier = float(
        brier_score_loss(
            y,
            p
        )
    )

    return {
        "pr_auc": pr_auc,
        "roc_auc": roc_auc,
        "brier": brier,
    }


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print(
        "TEMPORAL CROSS-VALIDATION "
        "- PURGED LABEL BOUNDARIES"
    )
    print("=" * 70)

    # ========================================================
    # LOAD FEATURES
    # ========================================================

    with FEATURE_FILE.open(
        "r",
        encoding="utf-8"
    ) as file:
        features = json.load(file)

    if (
        not isinstance(features, list)
        or not features
        or len(features) != len(set(features))
    ):
        raise ValueError(
            "Invalid feature_list.json"
        )

    if any(
        str(column).startswith(
            ("target_", "observed_")
        )
        for column in features
    ):
        raise ValueError(
            "Ground-truth column present "
            "in feature list"
        )

    print(
        "\nNumber of features:",
        len(features)
    )

    # ========================================================
    # LOAD DATA
    # ========================================================

    df = pd.read_csv(
        DATA_FILE,
        parse_dates=["time"]
    )

    df = (
        df.sort_values("time")
        .reset_index(drop=True)
    )

    # --------------------------------------------------------
    # Không đưa năm 2026 vào temporal CV.
    # --------------------------------------------------------

    df = df.loc[
        df["time"] < TEST_START
    ].copy()

    if df["time"].duplicated().any():
        raise ValueError(
            "Duplicate time values"
        )

    print(
        "Dataset:",
        DATA_FILE
    )

    print(
        "Samples before 2026:",
        len(df)
    )

    print(
        "Time range:",
        df["time"].min(),
        "->",
        df["time"].max()
    )

    prediction_frames = []
    fold_rows = []

    # ========================================================
    # TEMPORAL CROSS-VALIDATION
    # ========================================================

    for fold in FOLDS:

        print("\n")
        print("=" * 70)
        print(
            fold[0].upper()
        )
        print("=" * 70)

        # ----------------------------------------------------
        # HORIZON 1 -> 6
        # ----------------------------------------------------

        for horizon in range(1, 7):

            (
                tr,
                x_tr,
                y_tr,
                va,
                x_va,
                y_va,
            ) = purged_fold(
                df,
                fold,
                horizon,
                features,
            )

            # ------------------------------------------------
            # Class statistics
            # ------------------------------------------------

            pos = int(
                y_tr.sum()
            )

            neg = int(
                (y_tr == 0).sum()
            )

            if pos == 0 or neg == 0:
                raise RuntimeError(
                    f"{fold[0]} h{horizon}: "
                    "training needs two classes"
                )

            weight = neg / pos

            print(
                f"\nh{horizon}: "
                f"train={len(tr)} "
                f"(positive={pos}), "
                f"validation={len(va)} "
                f"(positive={int(y_va.sum())})"
            )

            print(
                "Last training timestamp:",
                tr["time"].max()
            )

            print(
                "Last validation timestamp:",
                va["time"].max()
            )

            print(
                "Scale pos weight:",
                round(weight, 2)
            )

            # ================================================
            # TRAIN AND EVALUATE EACH MODEL
            # ================================================

            models = build_models(
                weight
            )

            for model_name, model in models.items():

                print(
                    f"  Training {model_name}..."
                )

                model.fit(
                    x_tr,
                    y_tr
                )

                probability = (
                    model.predict_proba(
                        x_va
                    )[:, 1]
                )

                metrics = ranking_metrics(
                    y_va,
                    probability
                )

                # --------------------------------------------
                # Save fold metrics
                # --------------------------------------------

                fold_rows.append({
                    "fold": fold[0],
                    "model": model_name,
                    "horizon": horizon,
                    "train_samples": len(tr),
                    "train_positive": pos,
                    "validation_samples": len(va),
                    "validation_positive": int(
                        y_va.sum()
                    ),
                    "last_train_time": tr["time"].max(),
                    "last_validation_time": va["time"].max(),
                    **metrics,
                })

                # --------------------------------------------
                # Save OOF predictions
                # --------------------------------------------

                prediction_frames.append(
                    pd.DataFrame({
                        "time": va[
                            "time"
                        ].to_numpy(),

                        "fold": fold[0],

                        "model": model_name,

                        "horizon": horizon,

                        "y_true": y_va.to_numpy(
                            dtype=int
                        ),

                        "probability": (
                            probability.astype(float)
                        ),
                    })
                )

                print(
                    f"  {model_name}: "
                    f"PR-AUC={metrics['pr_auc']:.6f}, "
                    f"ROC-AUC={metrics['roc_auc']:.6f}, "
                    f"Brier={metrics['brier']:.8f}"
                )

    # ========================================================
    # COMBINE OOF PREDICTIONS
    # ========================================================

    predictions = pd.concat(
        prediction_frames,
        ignore_index=True
    )

    if predictions.duplicated(
        [
            "time",
            "model",
            "horizon",
        ]
    ).any():
        raise AssertionError(
            "Duplicate OOF timestamps"
        )

    # ========================================================
    # AGGREGATED METRICS
    # ========================================================

    aggregate_rows = []

    for (
        model_name,
        horizon
    ), group in predictions.groupby(
        [
            "model",
            "horizon",
        ]
    ):

        y = group[
            "y_true"
        ].to_numpy(dtype=int)

        p = group[
            "probability"
        ].to_numpy(dtype=float)

        aggregate_rows.append({
            "model": model_name,
            "horizon": int(horizon),
            "samples": len(y),
            "positive_samples": int(
                y.sum()
            ),
            **ranking_metrics(y, p),
        })

    # ========================================================
    # SAVE OUTPUTS
    # ========================================================

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    pred_path = (
        OUTPUT_DIR
        /
        "temporal_cv_predictions.csv"
    )

    fold_path = (
        OUTPUT_DIR
        /
        "temporal_cv_fold_metrics.csv"
    )

    agg_path = (
        OUTPUT_DIR
        /
        "temporal_cv_aggregated_metrics.csv"
    )

    predictions.to_csv(
        pred_path,
        index=False,
        encoding="utf-8-sig"
    )

    pd.DataFrame(
        fold_rows
    ).to_csv(
        fold_path,
        index=False,
        encoding="utf-8-sig"
    )

    aggregated = pd.DataFrame(
        aggregate_rows
    )

    aggregated.to_csv(
        agg_path,
        index=False,
        encoding="utf-8-sig"
    )

    # ========================================================
    # FINAL DISPLAY
    # ========================================================

    print("\n")
    print("=" * 70)
    print(
        "TEMPORAL CV AGGREGATED RESULTS"
    )
    print("=" * 70)

    print(
        aggregated.sort_values(
            [
                "horizon",
                "pr_auc",
            ],
            ascending=[
                True,
                False,
            ]
        ).to_string(
            index=False
        )
    )

    print(
        "\nPredictions:",
        pred_path
    )

    print(
        "Fold metrics:",
        fold_path
    )

    print(
        "Aggregate:",
        agg_path
    )

    print(
        "\nValidation labels are purged "
        "at period boundaries."
    )

    print(
        "2026 labels are not used."
    )


if __name__ == "__main__":
    main()