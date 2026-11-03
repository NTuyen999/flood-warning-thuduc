from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


INPUT_FILE = Path(
    "ml/outputs/metrics/temporal_cv_predictions.csv"
)

OUTPUT_DIR = Path(
    "ml/outputs/metrics"
)

CALIBRATOR_DIR = Path(
    "ml/saved_models/calibrators"
)

FOLDS = ("fold1", "fold2", "fold3")


def to_logit(probabilities):

    values = np.asarray(
        probabilities,
        dtype=float
    )

    if (
        not np.isfinite(values).all()
        or ((values < 0) | (values > 1)).any()
    ):
        raise ValueError(
            "Raw probabilities must be finite "
            "and within [0, 1]."
        )

    values = np.clip(
        values,
        1e-8,
        1 - 1e-8
    )

    return np.log(
        values / (1 - values)
    ).reshape(-1, 1)


def make_calibrator():

    return Pipeline([
        (
            "scaler",
            StandardScaler()
        ),
        (
            "logistic",
            LogisticRegression(
                max_iter=2000,
                random_state=42
            )
        ),
    ])


def score(y_true, probabilities):

    p = np.clip(
        np.asarray(
            probabilities,
            dtype=float
        ),
        1e-8,
        1 - 1e-8
    )

    return {
        "brier": float(
            brier_score_loss(
                y_true,
                p
            )
        ),
        "log_loss": float(
            log_loss(
                y_true,
                p,
                labels=[0, 1]
            )
        ),
        "mean_probability": float(
            p.mean()
        ),
    }


def main():

    print("=" * 72)
    print(
        "FORWARD TEMPORAL CALIBRATION "
        "- XGBOOST H1 TO H6"
    )
    print("=" * 72)

    predictions = pd.read_csv(
        INPUT_FILE,
        parse_dates=["time"]
    )

    expected_columns = {
        "time",
        "fold",
        "model",
        "horizon",
        "y_true",
        "probability",
    }

    missing = (
        expected_columns
        - set(predictions.columns)
    )

    if missing:
        raise ValueError(
            f"Missing columns: {sorted(missing)}"
        )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    CALIBRATOR_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    summary_rows = []
    fold_rows = []
    forward_predictions = []

    for horizon in range(1, 7):

        data = predictions.loc[
            (
                predictions["model"]
                == "XGBoost"
            )
            &
            (
                predictions["horizon"]
                == horizon
            )
        ].copy().sort_values("time")

        if (
            data.empty
            or set(data["fold"].unique())
            != set(FOLDS)
        ):
            raise ValueError(
                f"h{horizon}: expected data "
                "for all three folds"
            )

        if data.duplicated(
            ["time", "fold"]
        ).any():
            raise ValueError(
                f"h{horizon}: duplicate "
                "time/fold rows"
            )

        if not data["y_true"].isin(
            [0, 1]
        ).all():
            raise ValueError(
                f"h{horizon}: invalid "
                "ground-truth labels"
            )

        print(
            f"\nHORIZON h{horizon}"
        )

        evaluated_parts = []

        # Forward calibration:
        #
        # fold1 -> evaluate fold2
        # fold1 + fold2 -> evaluate fold3
        #
        # Khong hoc tu fold tuong lai.

        for index, held_out_fold in enumerate(
            FOLDS[1:],
            start=1
        ):

            past_folds = FOLDS[:index]

            calibration_train = data.loc[
                data["fold"].isin(past_folds)
            ].copy()

            evaluation = data.loc[
                data["fold"] == held_out_fold
            ].copy()

            if (
                calibration_train["time"].max()
                >= evaluation["time"].min()
            ):
                raise ValueError(
                    f"h{horizon}: training must "
                    f"precede {held_out_fold}"
                )

            y_train = (
                calibration_train["y_true"]
                .astype(int)
                .to_numpy()
            )

            y_eval = (
                evaluation["y_true"]
                .astype(int)
                .to_numpy()
            )

            if len(np.unique(y_train)) != 2:
                raise ValueError(
                    f"h{horizon}: past calibration "
                    "data needs both classes"
                )

            calibrator = make_calibrator()

            calibrator.fit(
                to_logit(
                    calibration_train[
                        "probability"
                    ]
                ),
                y_train
            )

            raw_p = (
                evaluation["probability"]
                .to_numpy(dtype=float)
            )

            calibrated_p = (
                calibrator.predict_proba(
                    to_logit(raw_p)
                )[:, 1]
            )

            # Baseline xac suat theo ty le
            # su kien trong du lieu qua khu.
            base_rate = float(
                y_train.mean()
            )

            baseline_p = np.full(
                len(evaluation),
                base_rate,
                dtype=float
            )

            evaluated = evaluation[
                [
                    "time",
                    "fold",
                    "model",
                    "horizon",
                    "y_true",
                ]
            ].copy()

            evaluated[
                "raw_probability"
            ] = raw_p

            evaluated[
                "calibrated_probability"
            ] = calibrated_p

            evaluated[
                "past_event_rate_probability"
            ] = baseline_p

            evaluated_parts.append(
                evaluated
            )

            forward_predictions.append(
                evaluated
            )

            row = {
                "horizon": horizon,
                "evaluation_fold": held_out_fold,
                "training_folds": "+".join(
                    past_folds
                ),
                "samples": len(y_eval),
                "positives": int(
                    y_eval.sum()
                ),
                "raw_brier": score(
                    y_eval,
                    raw_p
                )["brier"],
                "calibrated_brier": score(
                    y_eval,
                    calibrated_p
                )["brier"],
                "past_rate_brier": score(
                    y_eval,
                    baseline_p
                )["brier"],
                "raw_log_loss": score(
                    y_eval,
                    raw_p
                )["log_loss"],
                "calibrated_log_loss": score(
                    y_eval,
                    calibrated_p
                )["log_loss"],
                "past_rate_log_loss": score(
                    y_eval,
                    baseline_p
                )["log_loss"],
            }

            fold_rows.append(row)

            print(
                f"  {past_folds} -> "
                f"{held_out_fold}: "
                f"{len(y_eval)} rows; "
                f"positives={int(y_eval.sum())}; "
                f"Brier raw/cal/past-rate="
                f"{row['raw_brier']:.8f}/"
                f"{row['calibrated_brier']:.8f}/"
                f"{row['past_rate_brier']:.8f}"
            )

        # Evaluate tren fold2 + fold3
        # (khong dung fold1 tu danh gia).

        combined = pd.concat(
            evaluated_parts,
            ignore_index=True
        )

        y = (
            combined["y_true"]
            .astype(int)
            .to_numpy()
        )

        raw = (
            combined["raw_probability"]
            .to_numpy()
        )

        calibrated = (
            combined["calibrated_probability"]
            .to_numpy()
        )

        baseline = (
            combined["past_event_rate_probability"]
            .to_numpy()
        )

        summary_rows.append({
            "horizon": horizon,
            "evaluation_folds": "fold2+fold3",
            "samples": len(y),
            "positives": int(y.sum()),

            "raw_brier": score(
                y, raw
            )["brier"],

            "calibrated_brier": score(
                y, calibrated
            )["brier"],

            "past_rate_brier": score(
                y, baseline
            )["brier"],

            "raw_log_loss": score(
                y, raw
            )["log_loss"],

            "calibrated_log_loss": score(
                y, calibrated
            )["log_loss"],

            "past_rate_log_loss": score(
                y, baseline
            )["log_loss"],
        })

        # Sau khi forward-evaluate:
        # Fit final calibrator tren tat ca
        # OOF predictions truoc 2026.

        y_all = (
            data["y_true"]
            .astype(int)
            .to_numpy()
        )

        final_calibrator = (
            make_calibrator()
        )

        final_calibrator.fit(
            to_logit(
                data["probability"]
            ),
            y_all
        )

        output_model = (
            CALIBRATOR_DIR
            /
            f"xgboost_h{horizon}_calibrator.joblib"
        )

        joblib.dump(
            final_calibrator,
            output_model
        )

        print(
            f"  Saved: {output_model}"
        )

    summary = pd.DataFrame(
        summary_rows
    )

    by_fold = pd.DataFrame(
        fold_rows
    )

    all_predictions = pd.concat(
        forward_predictions,
        ignore_index=True
    )

    summary_path = (
        OUTPUT_DIR
        /
        "calibration_forward_summary.csv"
    )

    folds_path = (
        OUTPUT_DIR
        /
        "calibration_forward_by_fold.csv"
    )

    predictions_path = (
        OUTPUT_DIR
        /
        "calibration_forward_predictions.csv"
    )

    summary.to_csv(
        summary_path,
        index=False,
        encoding="utf-8-sig"
    )

    by_fold.to_csv(
        folds_path,
        index=False,
        encoding="utf-8-sig"
    )

    all_predictions.to_csv(
        predictions_path,
        index=False,
        encoding="utf-8-sig"
    )

    print("\n" + "=" * 72)
    print(
        "FORWARD CALIBRATION SUMMARY"
    )
    print("=" * 72)

    print(
        summary.to_string(
            index=False
        )
    )

    print(
        f"\nSummary: {summary_path}"
    )

    print(
        f"By fold: {folds_path}"
    )

    print(
        f"Predictions: {predictions_path}"
    )

    print(
        f"Calibrators: {CALIBRATOR_DIR}"
    )

    print(
        "Note: only fold2 and fold3 "
        "are evaluated; just four "
        "positive labels per horizon."
    )


if __name__ == "__main__":
    main()