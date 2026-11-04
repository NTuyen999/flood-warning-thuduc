from pathlib import Path

import numpy as np
import pandas as pd


INPUT_FILE = Path(
    "ml/outputs/metrics/validation_predictions.csv"
)

OUTPUT_DIR = Path(
    "ml/outputs/metrics"
)


# Giới hạn cảnh báo chính
MAX_ALERT_RATE = 0.02


def evaluate_threshold(
    y_true,
    probabilities,
    threshold,
):

    prediction = (
        probabilities >= threshold
    ).astype(int)

    tp = int(
        ((prediction == 1) & (y_true == 1)).sum()
    )

    fp = int(
        ((prediction == 1) & (y_true == 0)).sum()
    )

    tn = int(
        ((prediction == 0) & (y_true == 0)).sum()
    )

    fn = int(
        ((prediction == 0) & (y_true == 1)).sum()
    )

    precision = (
        tp / (tp + fp)
        if tp + fp > 0
        else 0.0
    )

    recall = (
        tp / (tp + fn)
        if tp + fn > 0
        else 0.0
    )

    f1 = (
        2 * precision * recall
        / (precision + recall)
        if precision + recall > 0
        else 0.0
    )

    fpr = (
        fp / (fp + tn)
        if fp + tn > 0
        else 0.0
    )

    alert_rate = (
        prediction.mean()
    )

    return {
        "threshold": float(threshold),

        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,

        "precision": precision,
        "recall": recall,
        "f1": f1,

        "fpr": fpr,
        "alert_rate": alert_rate,
    }


def create_thresholds(
    probabilities
):

    probabilities = np.asarray(
        probabilities,
        dtype=float
    )

    # Dùng chính các probability mà model tạo ra
    # để không bỏ lỡ threshold nhỏ.
    thresholds = np.unique(
        probabilities
    )

    thresholds = np.concatenate(
        [
            thresholds,
            np.array([
                0.0,
                0.5,
                1.0,
            ])
        ]
    )

    return np.unique(
        thresholds
    )


def optimize_group(
    df_group,
    model_name,
    horizon,
    max_alert_rate,
):

    y_true = (
        df_group["y_true"]
        .astype(int)
        .to_numpy()
    )

    probabilities = (
        df_group["probability"]
        .astype(float)
        .to_numpy()
    )

    thresholds = (
        create_thresholds(
            probabilities
        )
    )

    rows = []

    for threshold in thresholds:

        result = evaluate_threshold(
            y_true,
            probabilities,
            threshold,
        )

        result["model"] = model_name
        result["horizon"] = horizon

        rows.append(
            result
        )

    search_df = pd.DataFrame(
        rows
    )

    # Chỉ giữ threshold nằm trong
    # ngân sách cảnh báo.
    feasible = search_df[
        search_df["alert_rate"]
        <= max_alert_rate
    ].copy()

    if feasible.empty:

        # Trường hợp cực hiếm:
        # lấy threshold có alert rate thấp nhất.
        feasible = (
            search_df
            .sort_values(
                "alert_rate"
            )
            .head(1)
            .copy()
        )

    # Thứ tự ưu tiên:
    #
    # 1. Recall cao
    # 2. Precision cao
    # 3. F1 cao
    # 4. Ít alert hơn
    # 5. Threshold cao hơn
    ranked = (
        feasible
        .sort_values(
            by=[
                "recall",
                "precision",
                "f1",
                "alert_rate",
                "threshold",
            ],
            ascending=[
                False,
                False,
                False,
                True,
                False,
            ],
        )
        .reset_index(drop=True)
    )

    best = (
        ranked.iloc[0]
        .to_dict()
    )

    return (
        search_df,
        best
    )


def run_for_alert_budget(
    predictions,
    max_alert_rate,
):

    best_rows = []
    search_rows = []

    grouped = predictions.groupby(
        [
            "model",
            "horizon",
        ]
    )

    for (
        model_name,
        horizon,
    ), df_group in grouped:

        (
            search_df,
            best
        ) = optimize_group(
            df_group,
            model_name,
            horizon,
            max_alert_rate,
        )

        search_df[
            "max_alert_rate"
        ] = max_alert_rate

        best[
            "max_alert_rate"
        ] = max_alert_rate

        search_rows.append(
            search_df
        )

        best_rows.append(
            best
        )

    return (
        pd.concat(
            search_rows,
            ignore_index=True
        ),
        pd.DataFrame(
            best_rows
        ),
    )


def main():

    print("=" * 70)
    print("CONSTRAINED THRESHOLD OPTIMIZATION")
    print("=" * 70)

    predictions = pd.read_csv(
        INPUT_FILE,
        parse_dates=["time"]
    )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # ========================================================
    # Sensitivity analysis:
    # 0.5%, 1%, 2%, 5%
    # ========================================================

    alert_budgets = [
        0.005,
        0.01,
        0.02,
        0.05,
    ]

    all_best = []
    all_search = []

    for budget in alert_budgets:

        print("\n" + "=" * 70)

        print(
            "MAX ALERT RATE:",
            budget * 100,
            "%"
        )

        print("=" * 70)

        (
            search_df,
            best_df
        ) = run_for_alert_budget(
            predictions,
            budget,
        )

        all_search.append(
            search_df
        )

        all_best.append(
            best_df
        )

    # ========================================================
    # Save sensitivity analysis
    # ========================================================

    sensitivity_df = pd.concat(
        all_best,
        ignore_index=True
    )

    sensitivity_file = (
        OUTPUT_DIR
        /
        "threshold_alert_budget_sensitivity.csv"
    )

    sensitivity_df.to_csv(
        sensitivity_file,
        index=False,
        encoding="utf-8-sig"
    )

    # ========================================================
    # Chọn budget chính = 2%
    # ========================================================

    main_df = sensitivity_df[
        sensitivity_df[
            "max_alert_rate"
        ]
        == MAX_ALERT_RATE
    ].copy()

    # ========================================================
    # Best model per horizon
    # ========================================================

    selected_rows = []

    for horizon in range(1, 7):

        candidates = (
            main_df[
                main_df["horizon"]
                == horizon
            ]
            .copy()
        )

        candidates = (
            candidates
            .sort_values(
                by=[
                    "recall",
                    "precision",
                    "f1",
                    "alert_rate",
                ],
                ascending=[
                    False,
                    False,
                    False,
                    True,
                ],
            )
        )

        selected_rows.append(
            candidates.iloc[0]
        )

    selected_df = pd.DataFrame(
        selected_rows
    )

    selected_file = (
        OUTPUT_DIR
        /
        "selected_thresholds_2pct.csv"
    )

    selected_df.to_csv(
        selected_file,
        index=False,
        encoding="utf-8-sig"
    )

    # ========================================================
    # Print main result
    # ========================================================

    print("\n")
    print("=" * 70)
    print("SELECTED MODELS - MAX ALERT RATE 2%")
    print("=" * 70)

    columns = [
        "model",
        "horizon",
        "threshold",

        "tp",
        "fp",
        "fn",

        "precision",
        "recall",
        "f1",

        "fpr",
        "alert_rate",
    ]

    print(
        selected_df[
            columns
        ].to_string(
            index=False
        )
    )

    print(
        "\nSensitivity analysis:",
        sensitivity_file
    )

    print(
        "Selected thresholds:",
        selected_file
    )


if __name__ == "__main__":
    main()