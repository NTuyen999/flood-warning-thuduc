from pathlib import Path

import pandas as pd


INPUT_FILE = (
    "data/processed/weather_clean.csv"
)

OUTPUT_FILE = (
    "data/processed/weather_labeled.csv"
)

HEAVY_RAIN_THRESHOLD = 30.0


def main():

    print("=" * 60)
    print("CREATING SUPERVISED LEARNING TARGETS")
    print("=" * 60)

    df = pd.read_csv(
        INPUT_FILE,
        parse_dates=["time"]
    )

    df = (
        df.sort_values("time")
        .reset_index(drop=True)
    )

    print(
        "\nDataset shape:",
        df.shape
    )

    # ==========================================
    # IMPORTANT:
    #
    # Kiểm tra dữ liệu có liên tục từng giờ.
    #
    # Vì shift(1), shift(2)... chỉ đúng nghĩa
    # +1h, +2h khi không bị thiếu timestamp.
    # ==========================================

    expected_time = pd.date_range(
        start=df["time"].min(),
        end=df["time"].max(),
        freq="h"
    )

    missing_time = (
        expected_time
        .difference(
            df["time"]
        )
    )

    if len(missing_time) > 0:

        raise ValueError(
            f"Dataset has "
            f"{len(missing_time)} "
            f"missing hourly timestamps."
        )

    print(
        "Hourly time series continuity: OK"
    )

    # ==========================================
    # TARGET DEFINITION
    #
    # Đây là ground truth từ dữ liệu lịch sử.
    #
    # Ví dụ tại thời điểm t:
    #
    # target_h1:
    # lượng mưa đã quan sát thực tế
    # ở t+1, t+2, t+3
    #
    # target_h2:
    # t+2, t+3, t+4
    #
    # ...
    #
    # target_h6:
    # t+6, t+7, t+8
    #
    # Nếu tổng >= 30 mm / 3h:
    # target = 1
    #
    # Đây KHÔNG phải feature.
    # Đây chỉ là đáp án dùng để train/evaluate.
    # ==========================================

    for h in range(1, 7):

        observed_col = (
            f"observed_rain_h{h}_3h"
        )

        target_col = (
            f"target_h{h}"
        )

        # Dữ liệu mưa thực tế đã xảy ra
        # trong lịch sử sau thời điểm t.
        observed_future_rain = (
            df["rain"].shift(-h)
            + df["rain"].shift(-(h + 1))
            + df["rain"].shift(-(h + 2))
        )

        df[
            observed_col
        ] = observed_future_rain

        # Nullable integer:
        # 0 / 1 / NA
        df[target_col] = pd.Series(
            pd.NA,
            index=df.index,
            dtype="Int64"
        )

        valid_mask = (
            df[observed_col]
            .notna()
        )

        df.loc[
            valid_mask,
            target_col
        ] = (
            df.loc[
                valid_mask,
                observed_col
            ]
            >= HEAVY_RAIN_THRESHOLD
        ).astype(int)

    # ==========================================
    # TARGET REPORT
    # ==========================================

    print("\n" + "=" * 60)
    print("TARGET DISTRIBUTION")
    print("=" * 60)

    for h in range(1, 7):

        target_col = (
            f"target_h{h}"
        )

        observed_col = (
            f"observed_rain_h{h}_3h"
        )

        y = (
            df[target_col]
            .dropna()
            .astype(int)
        )

        negative_count = (
            y == 0
        ).sum()

        positive_count = (
            y == 1
        ).sum()

        positive_rate = (
            positive_count
            / len(y)
            * 100
        )

        print(
            f"\nHorizon +{h}h"
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
            "Positive rate:",
            round(
                positive_rate,
                4
            ),
            "%"
        )

        print(
            "Max observed rainfall:",
            round(
                df[
                    observed_col
                ].max(),
                2
            ),
            "mm/3h"
        )

    # ==========================================
    # SAMPLE
    # ==========================================

    sample_columns = [
        "time",
        "rain",

        "observed_rain_h1_3h",
        "target_h1",

        "observed_rain_h3_3h",
        "target_h3",

        "observed_rain_h6_3h",
        "target_h6",
    ]

    print("\n" + "=" * 60)
    print("SAMPLE")
    print("=" * 60)

    print(
        df[
            sample_columns
        ]
        .tail(15)
        .to_string(
            index=False
        )
    )

    # ==========================================
    # SAVE
    # ==========================================

    output_path = Path(
        OUTPUT_FILE
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    df.to_csv(
        output_path,
        index=False,
        encoding="utf-8-sig"
    )

    print("\n" + "=" * 60)
    print("LABEL CREATION COMPLETED")
    print("=" * 60)

    print(
        "Shape:",
        df.shape
    )

    print(
        "Output:",
        OUTPUT_FILE
    )


if __name__ == "__main__":
    main()