"""Step 16: Explain final XGBoost models using native TreeSHAP.

Run:
    python -m ml.src.evaluation.16_explain_model

Explanations are retrospective and descriptive.
They must not be used to tune models on the 2026 test period.
"""

import json
from pathlib import Path

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xgboost as xgb

from scipy.special import expit


# ============================================================
# CONFIGURATION
# ============================================================

DATA_FILE = Path("data/processed/ml_dataset.csv")
MODEL_DIR = Path("ml/saved_models/final")
FEATURE_FILE = MODEL_DIR / "feature_list.json"
OUTPUT_DIR = Path("ml/outputs/explainability")

TEST_START = pd.Timestamp("2026-01-01")
TEST_END = pd.Timestamp("2026-10-01")

MAX_GLOBAL_SAMPLES = 1200
TOP_GLOBAL_FEATURES = 15
TOP_LOCAL_FEATURES = 5
TOP_SCORE_ROWS = 10

RANDOM_STATE = 42


# ============================================================
# LOAD DATA AND FEATURES
# ============================================================

def load_data():

    with FEATURE_FILE.open(
        "r",
        encoding="utf-8"
    ) as file:
        features = json.load(file)

    if (
        not isinstance(features, list)
        or len(features) != 30
        or len(features) != len(set(features))
    ):
        raise ValueError(
            "Expected 30 unique model features."
        )

    if any(
        name.startswith(("target_", "observed_"))
        for name in features
    ):
        raise ValueError(
            "Target leakage in feature list."
        )

    df = pd.read_csv(
        DATA_FILE,
        parse_dates=["time"]
    )

    df = df.sort_values(
        "time"
    ).reset_index(drop=True)

    if df["time"].duplicated().any():
        raise ValueError(
            "Duplicate timestamps in dataset."
        )

    missing = set(features) - set(df.columns)

    if missing:
        raise ValueError(
            f"Missing features: {sorted(missing)}"
        )

    return df, features


# ============================================================
# SELECT VALID 2026 TEST ROWS
# ============================================================

def prepare_test(df, features, horizon):

    target = f"target_h{horizon}"

    if target not in df.columns:
        raise ValueError(
            f"Missing target: {target}"
        )

    observed_end = min(
        TEST_END,
        df["time"].max() + pd.Timedelta(hours=1)
    )

    # The target needs rain until t+h+2.
    cutoff = observed_end - pd.Timedelta(
        hours=horizon + 2
    )

    test = df.loc[
        (df["time"] >= TEST_START)
        & (df["time"] < cutoff),
        ["time", *features, target],
    ].dropna().copy()

    test = test.reset_index(drop=True)

    if test.empty:
        raise ValueError(
            f"No valid test rows for h{horizon}"
        )

    X = test[features].copy()

    return test, X


# ============================================================
# NATIVE TREE SHAP
#
# pred_contribs=True returns:
#
# n_features SHAP contributions + 1 bias term
#
# For XGBoost binary logistic classification,
# contributions are additive in raw log-odds.
# ============================================================

def calculate_shap(model, X, features):

    booster = model.get_booster()

    model_features = booster.feature_names

    if (
        model_features is not None
        and model_features != features
    ):
        raise ValueError(
            "Feature order differs from model training."
        )

    matrix = xgb.DMatrix(
        X,
        feature_names=features
    )

    contributions = booster.predict(
        matrix,
        pred_contribs=True
    )

    expected_shape = (
        len(X),
        len(features) + 1
    )

    if contributions.shape != expected_shape:
        raise ValueError(
            "Unexpected SHAP shape: "
            f"{contributions.shape}"
        )

    shap_values = contributions[:, :-1]
    base_values = contributions[:, -1]

    raw_probabilities = model.predict_proba(
        X
    )[:, 1]

    reconstructed = expit(
        contributions.sum(axis=1)
    )

    max_error = float(
        np.max(
            np.abs(
                reconstructed - raw_probabilities
            )
        )
    )

    if max_error > 1e-3:
        raise RuntimeError(
            f"SHAP reconstruction error: {max_error}"
        )

    return (
        shap_values,
        base_values,
        raw_probabilities
    )


# ============================================================
# GLOBAL IMPORTANCE
# ============================================================

def save_global_importance(
    shap_values,
    features,
    horizon
):

    importance = pd.DataFrame({
        "feature": features,
        "mean_abs_shap_log_odds": (
            np.abs(shap_values).mean(axis=0)
        ),
        "mean_signed_shap_log_odds": (
            shap_values.mean(axis=0)
        ),
    })

    importance = importance.sort_values(
        "mean_abs_shap_log_odds",
        ascending=False
    ).reset_index(drop=True)

    output = (
        OUTPUT_DIR
        / f"shap_importance_h{horizon}.csv"
    )

    importance.to_csv(
        output,
        index=False,
        encoding="utf-8-sig"
    )

    return importance


# ============================================================
# GLOBAL BAR PLOT
# ============================================================

def save_bar_plot(importance, horizon):

    top = importance.head(
        TOP_GLOBAL_FEATURES
    ).iloc[::-1]

    fig, ax = plt.subplots(
        figsize=(10, 7)
    )

    ax.barh(
        top["feature"],
        top["mean_abs_shap_log_odds"]
    )

    ax.set_xlabel(
        "Mean absolute SHAP contribution (log-odds)"
    )

    ax.set_title(
        f"XGBoost h{horizon} - Global SHAP Importance"
    )

    ax.grid(
        axis="x",
        alpha=0.25
    )

    fig.tight_layout()

    output = (
        OUTPUT_DIR
        / f"shap_bar_h{horizon}.png"
    )

    fig.savefig(
        output,
        dpi=180,
        bbox_inches="tight"
    )

    plt.close(fig)


# ============================================================
# SHAP DISTRIBUTION PLOT
#
# Color indicates relative feature value.
# Each feature is normalized independently.
# ============================================================

def save_distribution_plot(
    X_sample,
    shap_values,
    importance,
    features,
    horizon
):

    top_features = (
        importance["feature"]
        .head(TOP_GLOBAL_FEATURES)
        .tolist()
    )

    rng = np.random.default_rng(
        RANDOM_STATE
    )

    fig, ax = plt.subplots(
        figsize=(11, 8)
    )

    scatter_handle = None

    for row_index, feature in enumerate(
        top_features
    ):

        column_index = features.index(
            feature
        )

        values = X_sample[
            feature
        ].to_numpy(dtype=float)

        shap_column = shap_values[
            :, column_index
        ]

        min_value = float(
            values.min()
        )

        max_value = float(
            values.max()
        )

        if max_value > min_value:
            normalized = (
                (values - min_value)
                / (max_value - min_value)
            )
        else:
            normalized = np.full(
                len(values),
                0.5
            )

        jitter = rng.uniform(
            -0.25,
            0.25,
            size=len(values)
        )

        scatter_handle = ax.scatter(
            shap_column,
            row_index + jitter,
            c=normalized,
            cmap="coolwarm",
            vmin=0,
            vmax=1,
            s=10,
            alpha=0.55,
            linewidths=0
        )

    ax.axvline(
        0,
        linewidth=1
    )

    ax.set_yticks(
        range(len(top_features))
    )

    ax.set_yticklabels(
        top_features
    )

    ax.invert_yaxis()

    ax.set_xlabel(
        "SHAP contribution (log-odds)"
    )

    ax.set_title(
        f"XGBoost h{horizon} - SHAP Distribution"
    )

    if scatter_handle is not None:

        colorbar = fig.colorbar(
            scatter_handle,
            ax=ax,
            pad=0.02
        )

        colorbar.set_label(
            "Relative feature value"
        )

    fig.tight_layout()

    output = (
        OUTPUT_DIR
        / f"shap_distribution_h{horizon}.png"
    )

    fig.savefig(
        output,
        dpi=180,
        bbox_inches="tight"
    )

    plt.close(fig)


# ============================================================
# LOCAL EXPLANATIONS
#
# Positive SHAP -> increases raw model log-odds.
# Negative SHAP -> decreases raw model log-odds.
#
# SHAP is NOT a causal explanation.
# ============================================================

def save_local_explanations(
    model,
    test,
    X,
    features,
    positions,
    horizon,
    output_name
):

    output = OUTPUT_DIR / output_name

    if len(positions) == 0:

        pd.DataFrame().to_csv(
            output,
            index=False
        )

        return

    X_selected = X.iloc[
        positions
    ].copy()

    shap_values, base_values, probabilities = (
        calculate_shap(
            model,
            X_selected,
            features
        )
    )

    target = f"target_h{horizon}"

    rows = []

    for local_index, original_position in enumerate(
        positions
    ):

        shap_row = shap_values[
            local_index
        ]

        feature_order = np.argsort(
            np.abs(shap_row)
        )[::-1]

        row = {
            "time": test.iloc[
                original_position
            ]["time"],

            "horizon": horizon,

            "observed_label": int(
                test.iloc[
                    original_position
                ][target]
            ),

            "raw_model_probability": float(
                probabilities[
                    local_index
                ]
            ),

            "base_log_odds": float(
                base_values[
                    local_index
                ]
            ),

            "prediction_log_odds": float(
                base_values[local_index]
                + shap_row.sum()
            ),
        }

        for rank, feature_index in enumerate(
            feature_order[
                :TOP_LOCAL_FEATURES
            ],
            start=1
        ):

            feature = features[
                feature_index
            ]

            row[
                f"feature_{rank}"
            ] = feature

            row[
                f"value_{rank}"
            ] = float(
                X_selected.iloc[
                    local_index,
                    feature_index
                ]
            )

            row[
                f"shap_log_odds_{rank}"
            ] = float(
                shap_row[
                    feature_index
                ]
            )

        rows.append(row)

    pd.DataFrame(rows).to_csv(
        output,
        index=False,
        encoding="utf-8-sig"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 72)
    print(
        "STEP 16 - XGBOOST NATIVE TREE SHAP"
    )
    print("=" * 72)

    df, features = load_data()

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    summary_rows = []

    for horizon in range(1, 7):

        print("\n" + "=" * 72)
        print(f"HORIZON h{horizon}")
        print("=" * 72)

        test, X_test = prepare_test(
            df,
            features,
            horizon
        )

        model_file = (
            MODEL_DIR
            / f"final_xgboost_h{horizon}.joblib"
        )

        model = joblib.load(
            model_file
        )

        # -----------------------------------------------
        # Global SHAP sample:
        # random sample only, no class oversampling.
        # -----------------------------------------------

        X_sample = X_test.sample(
            n=min(
                MAX_GLOBAL_SAMPLES,
                len(X_test)
            ),
            random_state=RANDOM_STATE
        )

        shap_values, _, _ = (
            calculate_shap(
                model,
                X_sample,
                features
            )
        )

        importance = (
            save_global_importance(
                shap_values,
                features,
                horizon
            )
        )

        save_bar_plot(
            importance,
            horizon
        )

        save_distribution_plot(
            X_sample,
            shap_values,
            importance,
            features,
            horizon
        )

        # -----------------------------------------------
        # Full test scores, for retrospective diagnosis.
        # No threshold and no warning decisions.
        # -----------------------------------------------

        raw_scores = model.predict_proba(
            X_test
        )[:, 1]

        top_positions = (
            np.argsort(
                -raw_scores,
                kind="stable"
            )[:TOP_SCORE_ROWS]
            .tolist()
        )

        target = f"target_h{horizon}"

        positive_positions = (
            np.flatnonzero(
                test[target]
                .astype(int)
                .to_numpy() == 1
            )
            .tolist()
        )

        save_local_explanations(
            model,
            test,
            X_test,
            features,
            top_positions,
            horizon,
            f"shap_top_scores_h{horizon}.csv"
        )

        save_local_explanations(
            model,
            test,
            X_test,
            features,
            positive_positions,
            horizon,
            f"shap_observed_events_h{horizon}.csv"
        )

        # -----------------------------------------------
        # Rank of the actual observed positive sample
        # among all test predictions.
        # -----------------------------------------------

        observed_rank = np.nan

        if len(positive_positions) == 1:

            position = positive_positions[0]

            observed_rank = int(
                1 + np.sum(
                    raw_scores
                    > raw_scores[position]
                )
            )

        top_feature = str(
            importance.iloc[0]["feature"]
        )

        print(
            "Test samples:",
            len(test)
        )

        print(
            "Positive samples:",
            len(positive_positions)
        )

        print(
            "Global SHAP samples:",
            len(X_sample)
        )

        print(
            "Top feature:",
            top_feature
        )

        print(
            "Observed event score rank:",
            observed_rank
        )

        print("\nTop 5 global features:")

        print(
            importance.head(5)
            .to_string(index=False)
        )

        summary_rows.append({
            "horizon": horizon,
            "test_samples": len(test),
            "positive_samples": len(
                positive_positions
            ),
            "shap_samples": len(X_sample),
            "top_feature": top_feature,
            "observed_event_score_rank": (
                observed_rank
            ),
        })

    summary = pd.DataFrame(
        summary_rows
    )

    summary_file = (
        OUTPUT_DIR
        / "shap_summary.csv"
    )

    summary.to_csv(
        summary_file,
        index=False,
        encoding="utf-8-sig"
    )

    print("\n" + "=" * 72)
    print("SHAP EXPLAINABILITY COMPLETED")
    print("=" * 72)

    print(
        summary.to_string(
            index=False
        )
    )

    print(
        "\nOutput directory:",
        OUTPUT_DIR
    )

    print(
        "SHAP contributions explain raw "
        "XGBoost log-odds, not calibrated "
        "probability or causality."
    )

    print(
        "No threshold selection or "
        "model tuning performed."
    )


if __name__ == "__main__":
    main()