from pathlib import Path

import pandas as pd


INPUT_FILE = "data/processed/ml_dataset.csv"

OUTPUT_DIR = Path(
    "data/processed/splits"
)

TRAIN_END = "2023-12-31 23:00:00"

VAL_START = "2024-01-01 00:00:00"
VAL_END = "2025-12-31 23:00:00"

TEST_START = "2026-01-01 00:00:00"


def report_split(name, df):

    print("\n" + "=" * 60)
    print(name)
    print("=" * 60)

    print(
        "Rows:",
        len(df)
    )

    print(
        "Time:",
        df["time"].min(),
        "->",
        df["time"].max()
    )

    for h in range(1, 7):

        target = f"target_h{h}"

        if target not in df.columns:
            continue

        y = (
            df[target]
            .dropna()
            .astype(int)
        )

        positive = (
            y == 1
        ).sum()

        negative = (
            y == 0
        ).sum()

        print(
            f"h{h}: "
            f"positive={positive}, "
            f"negative={negative}"
        )


def main():

    print("Loading ML dataset...")

    df = pd.read_csv(
        INPUT_FILE,
        parse_dates=["time"]
    )

    df = (
        df.sort_values("time")
        .reset_index(drop=True)
    )

    # ==========================================
    # TIME-BASED SPLIT
    # Không random shuffle.
    # ==========================================

    train = df[
        df["time"]
        <= TRAIN_END
    ].copy()

    validation = df[
        (
            df["time"]
            >= VAL_START
        )
        &
        (
            df["time"]
            <= VAL_END
        )
    ].copy()

    test = df[
        df["time"]
        >= TEST_START
    ].copy()

    # ==========================================
    # Kiểm tra overlap
    # ==========================================

    assert (
        train["time"].max()
        < validation["time"].min()
    )

    assert (
        validation["time"].max()
        < test["time"].min()
    )

    # ==========================================
    # Reports
    # ==========================================

    report_split(
        "TRAIN",
        train
    )

    report_split(
        "VALIDATION",
        validation
    )

    report_split(
        "TEST",
        test
    )

    # ==========================================
    # Save
    # ==========================================

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    train.to_csv(
        OUTPUT_DIR / "train.csv",
        index=False,
        encoding="utf-8-sig"
    )

    validation.to_csv(
        OUTPUT_DIR / "validation.csv",
        index=False,
        encoding="utf-8-sig"
    )

    test.to_csv(
        OUTPUT_DIR / "test.csv",
        index=False,
        encoding="utf-8-sig"
    )

    print("\n" + "=" * 60)
    print("TIME SPLIT COMPLETED")
    print("=" * 60)

    print(
        "Train:",
        OUTPUT_DIR / "train.csv"
    )

    print(
        "Validation:",
        OUTPUT_DIR / "validation.csv"
    )

    print(
        "Test:",
        OUTPUT_DIR / "test.csv"
    )


if __name__ == "__main__":
    main()