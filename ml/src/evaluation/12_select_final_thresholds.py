from pathlib import Path

import numpy as np
import pandas as pd


# ============================================================
# PATHS
# ============================================================

INPUT_FILE = Path(
    "ml/outputs/metrics/temporal_cv_predictions.csv"
)

OUTPUT_DIR = Path(
    "ml/outputs/metrics"
)


# ============================================================
# FINAL MODEL SELECTION
# ============================================================

SELECTED_MODELS = {
    1: "XGBoost",
    2: "XGBoost",
    3: "XGBoost",
    4: "XGBoost",
    5: "XGBoost",
    6: "XGBoost",
}


# ============================================================
# COST SENSITIVITY
#
# Không tự chọn một tỷ lệ tùy ý.
# Ta khảo sát nhiều tỷ lệ để thấy trade-off.
# ============================================================

FN_COSTS = [
    5,
    50,
    100,
    500,
    1000,
    5000,
]

FP_COST = 1


# ============================================================
# EVALUATE THRESHOLD
# ============================================================

def evaluate_threshold(
    y_true,
    probability,
    threshold,
    fn_cost,
):

    prediction = (
        probability >= threshold
    ).astype(int)

    tp = int(
        (
            (prediction == 1)
            &
            (y_true == 1)
        ).sum()
    )

    fp = int(
        (
            (prediction == 1)
            &
            (y_true == 0)
        ).sum()
    )

    tn = int(
        (
            (prediction == 0)
            &
            (y_true == 0)
        ).sum()
    )

    fn = int(
        (
            (prediction == 0)
            &
            (y_true == 1)
        ).sum()
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

    fnr = (
        fn / (fn + tp)
        if fn + tp > 0
        else 0.0
    )

    alert_rate = float(
        prediction.mean()
    )

    # ========================================================
    # STANDARD MISCLASSIFICATION COST
    #
    # Một FN có cost = fn_cost
    # Một FP có cost = 1
    # ========================================================

    total_cost = (
        fn_cost * fn
        +
        FP_COST * fp
    )

    cost_per_sample = (
        total_cost
        / len(y_true)
    )

    return {
        "threshold":
            float(threshold),

        "tp":
            tp,

        "fp":
            fp,

        "tn":
            tn,

        "fn":
            fn,

        "precision":
            precision,

        "recall":
            recall,

        "f1":
            f1,

        "fpr":
            fpr,

        "fnr":
            fnr,

        "alert_rate":
            alert_rate,

        "total_cost":
            float(total_cost),

        "cost_per_sample":
            float(cost_per_sample),
    }


# ============================================================
# THRESHOLD CANDIDATES
# ============================================================

def create_thresholds(
    probability
):

    probability = np.asarray(
        probability,
        dtype=float
    )

    # Probability của rare-event rất nhỏ.
    # Dùng distribution thực tế thay vì step 0.01.
    quantiles = np.linspace(
        0,
        1,
        5001
    )

    thresholds = np.quantile(
        probability,
        quantiles
    )

    thresholds = np.concatenate(
        [
            thresholds,

            np.array(
                [
                    0.0,
                    0.5,
                    1.0,
                ]
            ),
        ]
    )

    return np.unique(
        thresholds
    )


# ============================================================
# OPTIMIZE ONE HORIZON / COST
# ============================================================

def optimize(
    data,
    horizon,
    model_name,
    fn_cost,
):

    y_true = (
        data["y_true"]
        .astype(int)
        .to_numpy()
    )

    probability = (
        data["probability"]
        .astype(float)
        .to_numpy()
    )

    thresholds = (
        create_thresholds(
            probability
        )
    )

    rows = []

    for threshold in thresholds:

        metrics = evaluate_threshold(
            y_true,
            probability,
            threshold,
            fn_cost,
        )

        metrics[
            "model"
        ] = model_name

        metrics[
            "horizon"
        ] = horizon

        metrics[
            "fn_cost"
        ] = fn_cost

        metrics[
            "fp_cost"
        ] = FP_COST

        rows.append(
            metrics
        )

    search_df = pd.DataFrame(
        rows
    )

    # ========================================================
    # Selection rule
    #
    # 1. Minimum actual total cost
    # 2. Nếu bằng nhau: recall cao hơn
    # 3. Nếu vẫn bằng: FP thấp hơn
    # 4. Threshold cao hơn
    # ========================================================

    ranked = (
        search_df
        .sort_values(
            by=[
                "total_cost",
                "recall",
                "fp",
                "threshold",
            ],
            ascending=[
                True,
                False,
                True,
                False,
            ],
        )
        .reset_index(
            drop=True
        )
    )

    best = (
        ranked.iloc[0]
        .to_dict()
    )

    best[
        "samples"
    ] = len(
        y_true
    )

    best[
        "positives"
    ] = int(
        y_true.sum()
    )

    best[
        "negatives"
    ] = int(
        (
            y_true == 0
        ).sum()
    )

    return (
        best,
        search_df
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)

    print(
        "STANDARD COST-BASED "
        "THRESHOLD ANALYSIS"
    )

    print("=" * 70)

    predictions = pd.read_csv(
        INPUT_FILE,
        parse_dates=["time"]
    )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    all_best = []

    all_search = []

    # ========================================================
    # COST SENSITIVITY
    # ========================================================

    for fn_cost in FN_COSTS:

        print("\n")
        print("=" * 70)

        print(
            f"FN:FP COST = "
            f"{fn_cost}:1"
        )

        print("=" * 70)

        for horizon in range(
            1,
            7
        ):

            model_name = (
                SELECTED_MODELS[
                    horizon
                ]
            )

            data = predictions[
                (
                    predictions[
                        "horizon"
                    ]
                    == horizon
                )
                &
                (
                    predictions[
                        "model"
                    ]
                    == model_name
                )
            ].copy()

            if data.empty:

                raise RuntimeError(
                    f"No predictions "
                    f"for h{horizon}"
                )

            best, search_df = (
                optimize(
                    data,
                    horizon,
                    model_name,
                    fn_cost,
                )
            )

            all_best.append(
                best
            )

            all_search.append(
                search_df
            )

            print(
                f"\nH{horizon}"
            )

            print(
                "Threshold:",
                round(
                    best[
                        "threshold"
                    ],
                    8
                )
            )

            print(
                "TP:",
                int(
                    best["tp"]
                )
            )

            print(
                "FP:",
                int(
                    best["fp"]
                )
            )

            print(
                "FN:",
                int(
                    best["fn"]
                )
            )

            print(
                "Recall:",
                round(
                    best[
                        "recall"
                    ],
                    6
                )
            )

            print(
                "Precision:",
                round(
                    best[
                        "precision"
                    ],
                    6
                )
            )

            print(
                "Alert rate:",
                round(
                    best[
                        "alert_rate"
                    ]
                    * 100,
                    4
                ),
                "%"
            )

            print(
                "Total cost:",
                round(
                    best[
                        "total_cost"
                    ],
                    2
                )
            )

    # ========================================================
    # SAVE SENSITIVITY
    # ========================================================

    sensitivity_df = pd.DataFrame(
        all_best
    )

    sensitivity_file = (
        OUTPUT_DIR
        /
        "threshold_cost_sensitivity.csv"
    )

    sensitivity_df.to_csv(
        sensitivity_file,
        index=False,
        encoding="utf-8-sig"
    )

    search_df = pd.concat(
        all_search,
        ignore_index=True
    )

    search_file = (
        OUTPUT_DIR
        /
        "threshold_cost_search.csv"
    )

    search_df.to_csv(
        search_file,
        index=False,
        encoding="utf-8-sig"
    )

    # ========================================================
    # DISPLAY SUMMARY
    # ========================================================

    print("\n")
    print("=" * 70)
    print("COST SENSITIVITY SUMMARY")
    print("=" * 70)

    columns = [
        "fn_cost",
        "horizon",
        "model",
        "threshold",

        "tp",
        "fp",
        "fn",

        "precision",
        "recall",

        "alert_rate",

        "total_cost",
    ]

    print(
        sensitivity_df[
            columns
        ]
        .sort_values(
            [
                "fn_cost",
                "horizon",
            ]
        )
        .to_string(
            index=False
        )
    )

    print(
        "\nSensitivity:",
        sensitivity_file
    )

    print(
        "Full search:",
        search_file
    )

    print("\nIMPORTANT:")

    print(
        "This step is sensitivity analysis."
    )

    print(
        "No deployment threshold "
        "is automatically selected here."
    )


if __name__ == "__main__":
    main()