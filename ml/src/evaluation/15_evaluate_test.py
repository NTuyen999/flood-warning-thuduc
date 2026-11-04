"""Buoc 15: so sanh xac suat tren test 2026, KHONG chon threshold.

Chay tai thu muc goc du an:
    python -m ml.src.evaluation.15_evaluate_test
"""

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    log_loss,
    roc_auc_score,
)

DATA_FILE = Path("data/processed/ml_dataset.csv")
MODEL_DIR = Path("ml/saved_models/final")
CALIBRATOR_DIR = Path("ml/saved_models/calibrators")
FEATURE_FILE = MODEL_DIR / "feature_list.json"
OUTPUT_DIR = Path("ml/outputs/metrics")

TEST_START = pd.Timestamp("2026-01-01 00:00:00")
TEST_END_EXCLUSIVE = pd.Timestamp("2026-10-01 00:00:00")


def to_logit(probabilities):
    p = np.asarray(probabilities, dtype=float)
    p = np.clip(p, 1e-8, 1.0 - 1e-8)
    return np.log(p / (1.0 - p)).reshape(-1, 1)


def validate_probabilities(probabilities, label):
    p = np.asarray(probabilities, dtype=float)
    if not np.isfinite(p).all() or np.any((p < 0) | (p > 1)):
        raise ValueError(f"Invalid probabilities: {label}")
    return p


def probability_metrics(y_true, probabilities):
    p = validate_probabilities(probabilities, "metrics")
    p_safe = np.clip(p, 1e-8, 1.0 - 1e-8)

    metrics = {
        "brier": float(brier_score_loss(y_true, p)),
        "log_loss": float(
            log_loss(y_true, p_safe, labels=[0, 1])
        ),
        "average_precision": float(
            average_precision_score(y_true, p)
        ) if np.any(y_true == 1) else float("nan"),
        "roc_auc": float(
            roc_auc_score(y_true, p)
        ) if len(np.unique(y_true)) == 2 else float("nan"),
        "mean_probability": float(p.mean()),
    }

    return metrics


def main():
    print("=" * 72)
    print("2026 TEST: PROBABILITY COMPARISON (NO DEPLOYMENT THRESHOLD)")
    print("=" * 72)

    with FEATURE_FILE.open("r", encoding="utf-8") as f:
        features = json.load(f)

    if (
        not isinstance(features, list)
        or not features
        or len(features) != len(set(features))
    ):
        raise ValueError("feature_list.json is invalid")

    if any(
        str(name).startswith(("target_", "observed_"))
        for name in features
    ):
        raise ValueError(
            "Ground-truth data leaked into the feature list"
        )

    df = pd.read_csv(DATA_FILE, parse_dates=["time"])
    df = df.sort_values("time").reset_index(drop=True)

    if df.empty or df["time"].duplicated().any():
        raise ValueError(
            "Dataset is empty or contains duplicate timestamps"
        )

    missing = set(features) - set(df.columns)

    if missing:
        raise ValueError(
            f"Missing features: {sorted(missing)}"
        )

    # Chi danh gia cac nhan co day du
    # quan sat mua tuong lai trong dataset.
    observations_end_exclusive = min(
        TEST_END_EXCLUSIVE,
        df["time"].max() + pd.Timedelta(hours=1),
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    rows = []
    detailed_predictions = []
    table_rows = []

    for horizon in range(1, 7):
        target = f"target_h{horizon}"

        if target not in df.columns:
            raise ValueError(f"Missing target: {target}")

        # h1 dung mua tai t+1, t+2, t+3
        # h6 dung mua tai t+6, t+7, t+8
        lookahead = pd.Timedelta(hours=horizon + 2)

        # Train: nhan khong duoc cham nam 2026.
        train_cutoff = TEST_START - lookahead

        # Test: nhan khong vuot khoi du lieu quan sat.
        test_cutoff = observations_end_exclusive - lookahead

        columns = ["time", *features, target]

        train = df.loc[
            df["time"] < train_cutoff,
            columns,
        ].dropna().copy()

        test = df.loc[
            (df["time"] >= TEST_START)
            & (df["time"] < test_cutoff),
            columns,
        ].dropna().copy()

        if train.empty or test.empty:
            raise ValueError(
                f"Empty train/test for h{horizon}"
            )

        if train["time"].max() + lookahead >= TEST_START:
            raise AssertionError(
                f"h{horizon}: train target crosses into 2026"
            )

        if (
            test["time"].max() + lookahead
            >= observations_end_exclusive
        ):
            raise AssertionError(
                f"h{horizon}: test target exceeds observed period"
            )

        y_train = train[target].astype(int).to_numpy()
        y_test = test[target].astype(int).to_numpy()

        if (
            not set(np.unique(y_train)).issubset({0, 1})
            or not set(np.unique(y_test)).issubset({0, 1})
        ):
            raise ValueError(
                f"Non-binary target h{horizon}"
            )

        if len(np.unique(y_train)) != 2:
            raise ValueError(
                f"Training has only one class for h{horizon}"
            )

        X_test = test[features]

        # ====================================================
        # LOAD FINAL MODEL AND CALIBRATOR
        # ====================================================

        model_path = (
            MODEL_DIR / f"final_xgboost_h{horizon}.joblib"
        )

        calibrator_path = (
            CALIBRATOR_DIR
            / f"xgboost_h{horizon}_calibrator.joblib"
        )

        model = joblib.load(model_path)
        calibrator = joblib.load(calibrator_path)

        # ====================================================
        # THREE PROBABILITY METHODS
        #
        # 1. Historical event rate
        # 2. Raw XGBoost
        # 3. Calibrated XGBoost
        # ====================================================

        raw = validate_probabilities(
            model.predict_proba(X_test)[:, 1],
            "raw",
        )

        calibrated = validate_probabilities(
            calibrator.predict_proba(
                to_logit(raw)
            )[:, 1],
            "calibrated",
        )

        # Baseline chi dung train 2010-2025.
        # Tuyet doi khong dung nhan TEST de tinh baseline.
        historical_rate = float(y_train.mean())

        historical = np.full(
            len(test),
            historical_rate,
            dtype=float,
        )

        # ====================================================
        # METRICS
        # ====================================================

        scores = {
            "historical_rate": probability_metrics(
                y_test, historical
            ),
            "xgboost_raw": probability_metrics(
                y_test, raw
            ),
            "xgboost_calibrated": probability_metrics(
                y_test, calibrated
            ),
        }

        reference_brier = (
            scores["historical_rate"]["brier"]
        )

        print(
            f"\nH{horizon}: "
            f"test={len(test)}, "
            f"positives={int(y_test.sum())}, "
            f"train_positives={int(y_train.sum())}, "
            f"historical_rate={historical_rate:.8f}"
        )

        for name, values in scores.items():
            if reference_brier > 0:
                brier_skill = (
                    1.0
                    - values["brier"] / reference_brier
                )
            else:
                brier_skill = float("nan")

            print(
                f"  {name:20s} "
                f"Brier={values['brier']:.8f} "
                f"LogLoss={values['log_loss']:.8f} "
                f"AP={values['average_precision']:.6f} "
                f"BrierSkill={brier_skill:+.4f}"
            )

            rows.append({
                "horizon": horizon,
                "method": name,
                "test_samples": len(test),
                "test_positives": int(y_test.sum()),
                "train_samples": len(train),
                "train_positives": int(y_train.sum()),
                "train_historical_rate": historical_rate,
                **values,
                "brier_skill_vs_historical": brier_skill,
            })

        # ====================================================
        # SUMMARY PER HORIZON
        # ====================================================

        table_rows.append({
            "horizon": horizon,
            "positives": int(y_test.sum()),

            "baseline_brier":
                scores["historical_rate"]["brier"],

            "raw_brier":
                scores["xgboost_raw"]["brier"],

            "calibrated_brier":
                scores["xgboost_calibrated"]["brier"],

            "cal_brier_skill":
                1.0
                - scores["xgboost_calibrated"]["brier"]
                / reference_brier,

            "baseline_log_loss":
                scores["historical_rate"]["log_loss"],

            "raw_log_loss":
                scores["xgboost_raw"]["log_loss"],

            "calibrated_log_loss":
                scores["xgboost_calibrated"]["log_loss"],

            "raw_ap":
                scores["xgboost_raw"]["average_precision"],

            "raw_roc_auc":
                scores["xgboost_raw"]["roc_auc"],
        })

        # ====================================================
        # ROW-LEVEL PREDICTIONS
        # ====================================================

        detailed_predictions.append(
            pd.DataFrame({
                "time": test["time"].to_numpy(),
                "horizon": horizon,
                "y_true": y_test,
                "historical_rate_probability": historical,
                "raw_probability": raw,
                "calibrated_probability": calibrated,
            })
        )

    # ========================================================
    # SAVE RESULTS
    # ====================================================

    results_path = (
        OUTPUT_DIR
        / "final_test_probability_comparison.csv"
    )

    predictions_path = (
        OUTPUT_DIR
        / "final_test_probability_predictions.csv"
    )

    summary_path = (
        OUTPUT_DIR
        / "final_test_probability_summary.csv"
    )

    pd.DataFrame(rows).to_csv(
        results_path,
        index=False,
        encoding="utf-8-sig",
    )

    pd.concat(
        detailed_predictions,
        ignore_index=True,
    ).to_csv(
        predictions_path,
        index=False,
        encoding="utf-8-sig",
    )

    summary = pd.DataFrame(table_rows)

    summary.to_csv(
        summary_path,
        index=False,
        encoding="utf-8-sig",
    )

    # ========================================================
    # FINAL OUTPUT
    # ====================================================

    print("\n" + "=" * 72)
    print("2026 PROBABILITY COMPARISON SUMMARY")
    print("=" * 72)

    print(
        summary.to_string(
            index=False,
            float_format=lambda value: f"{value:.8f}",
        )
    )

    print(f"\nMetrics: {results_path}")
    print(f"Predictions: {predictions_path}")
    print(f"Summary: {summary_path}")

    print(
        "\nNo old thresholds used. "
        "No deployment warning decisions made."
    )

    print(
        "2026 was examined previously; "
        "these are retrospective test results."
    )

    print(
        "Only about one positive per horizon: "
        "conclusions are highly uncertain."
    )


if __name__ == "__main__":
    main()