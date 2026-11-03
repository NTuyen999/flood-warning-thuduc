from pathlib import Path

import numpy as np
import pandas as pd

from sklearn.metrics import (
    precision_score,
    recall_score,
    f1_score,
    average_precision_score,
    roc_auc_score,
    brier_score_loss,
)


SPLIT_DIR = Path(
    "data/processed/splits"
)

OUTPUT_DIR = Path(
    "ml/outputs/metrics"
)

THRESHOLD = 0.5


def evaluate_model(
    y_true,
    probability,
    model_name,
    horizon,
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
        probability >= THRESHOLD
    ).astype(int)

    result = {
        "model": model_name,
        "horizon": horizon,

        "samples": len(y_true),

        "positives": int(
            y_true.sum()
        ),

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

    # ROC-AUC cần cả class 0 và 1
    if len(
        np.unique(y_true)
    ) == 2:

        result["roc_auc"] = (
            roc_auc_score(
                y_true,
                probability,
            )
        )

    else:

        result["roc_auc"] = np.nan

    return result


def create_persistence_probability(
    df
):
    """
    Persistence baseline:

    Nếu 3 giờ vừa qua đang đạt
    ngưỡng >= 30 mm / 3h

    thì dự báo trạng thái đó
    tiếp tục xảy ra.

    Output là xác suất binary:
    0 hoặc 1.
    """

    probability = (
        df["rain_last_3h"]
        >= 30.0
    ).astype(float)

    return probability


def build_climatology_table(
    train_df,
    target_col,
):
    """
    Climatology baseline:

    P(event | month)

    Chỉ được học probability
    từ TRAIN SET.

    Không dùng validation/test
    để tính climatology.
    """

    train_valid = (
        train_df[
            [
                "month",
                target_col,
            ]
        ]
        .dropna()
        .copy()
    )

    train_valid[
        target_col
    ] = (
        train_valid[
            target_col
        ].astype(int)
    )

    climatology = (
        train_valid
        .groupby("month")[
            target_col
        ]
        .mean()
    )

    global_rate = (
        train_valid[
            target_col
        ]
        .mean()
    )

    return (
        climatology,
        global_rate,
    )


def apply_climatology(
    df,
    climatology,
    global_rate,
):

    probability = (
        df["month"]
        .map(climatology)
        .fillna(global_rate)
        .astype(float)
    )

    return probability


def evaluate_split(
    train_df,
    eval_df,
    split_name,
):

    results = []

    print("\n")
    print("=" * 70)
    print(split_name)
    print("=" * 70)

    for h in range(1, 7):

        target_col = (
            f"target_h{h}"
        )

        # ======================================
        # Chỉ dùng dòng có target hợp lệ
        # ======================================

        valid_mask = (
            eval_df[target_col]
            .notna()
        )

        df_h = (
            eval_df.loc[
                valid_mask
            ]
            .copy()
        )

        y_true = (
            df_h[target_col]
            .astype(int)
        )

        print(
            f"\nHorizon +{h}h"
        )

        print(
            "Samples:",
            len(y_true)
        )

        print(
            "Positive:",
            y_true.sum()
        )

        # ======================================
        # 1. PERSISTENCE
        # ======================================

        persistence_probability = (
            create_persistence_probability(
                df_h
            )
        )

        persistence_result = (
            evaluate_model(
                y_true,
                persistence_probability,
                "Persistence",
                h,
            )
        )

        persistence_result[
            "split"
        ] = split_name

        results.append(
            persistence_result
        )

        print(
            "Persistence:"
        )

        print(
            "  Precision:",
            round(
                persistence_result[
                    "precision"
                ],
                4
            )
        )

        print(
            "  Recall:",
            round(
                persistence_result[
                    "recall"
                ],
                4
            )
        )

        print(
            "  F1:",
            round(
                persistence_result[
                    "f1"
                ],
                4
            )
        )

        print(
            "  PR-AUC:",
            round(
                persistence_result[
                    "pr_auc"
                ],
                6
            )
        )

        # ======================================
        # 2. CLIMATOLOGY
        # ======================================

        (
            climatology,
            global_rate,
        ) = build_climatology_table(
            train_df,
            target_col,
        )

        climatology_probability = (
            apply_climatology(
                df_h,
                climatology,
                global_rate,
            )
        )

        climatology_result = (
            evaluate_model(
                y_true,
                climatology_probability,
                "Climatology",
                h,
            )
        )

        climatology_result[
            "split"
        ] = split_name

        results.append(
            climatology_result
        )

        print(
            "Climatology:"
        )

        print(
            "  Precision:",
            round(
                climatology_result[
                    "precision"
                ],
                4
            )
        )

        print(
            "  Recall:",
            round(
                climatology_result[
                    "recall"
                ],
                4
            )
        )

        print(
            "  F1:",
            round(
                climatology_result[
                    "f1"
                ],
                4
            )
        )

        print(
            "  PR-AUC:",
            round(
                climatology_result[
                    "pr_auc"
                ],
                6
            )
        )

        print(
            "  Train global event rate:",
            round(
                global_rate,
                8
            )
        )

    return results


def main():

    print(
        "Loading time-series splits..."
    )

    train = pd.read_csv(
        SPLIT_DIR / "train.csv",
        parse_dates=["time"]
    )

    validation = pd.read_csv(
        SPLIT_DIR / "validation.csv",
        parse_dates=["time"]
    )

    test = pd.read_csv(
        SPLIT_DIR / "test.csv",
        parse_dates=["time"]
    )

    all_results = []

    # ==========================================
    # Baseline trên Validation
    # ==========================================

    validation_results = (
        evaluate_split(
            train,
            validation,
            "validation",
        )
    )

    all_results.extend(
        validation_results
    )

    # ==========================================
    # Baseline trên Test
    #
    # Chỉ report.
    # Không dùng test để chỉnh model.
    # ==========================================

    test_results = (
        evaluate_split(
            train,
            test,
            "test",
        )
    )

    all_results.extend(
        test_results
    )

    results_df = pd.DataFrame(
        all_results
    )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    output_file = (
        OUTPUT_DIR
        / "baseline_results.csv"
    )

    results_df.to_csv(
        output_file,
        index=False,
        encoding="utf-8-sig"
    )

    print("\n")
    print("=" * 70)
    print("BASELINE EVALUATION COMPLETED")
    print("=" * 70)

    print(
        results_df[
            [
                "split",
                "model",
                "horizon",
                "positives",
                "precision",
                "recall",
                "f1",
                "pr_auc",
                "brier",
                "roc_auc",
            ]
        ].to_string(
            index=False
        )
    )

    print(
        "\nOutput:",
        output_file
    )


if __name__ == "__main__":
    main()
    