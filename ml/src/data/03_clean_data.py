from pathlib import Path

import pandas as pd


INPUT_FILE = (
    "data/raw/historical_weather.csv"
)

OUTPUT_FILE = (
    "data/processed/weather_clean.csv"
)


def main():

    print("=" * 60)
    print("CLEANING WEATHER DATA")
    print("=" * 60)

    df = pd.read_csv(
        INPUT_FILE,
        parse_dates=["time"]
    )

    print(
        "\nOriginal shape:",
        df.shape
    )

    # ==========================================
    # 1. Sort
    # ==========================================

    df = (
        df.sort_values("time")
        .reset_index(drop=True)
    )

    # ==========================================
    # 2. Remove duplicated timestamps
    # ==========================================

    before = len(df)

    df = df.drop_duplicates(
        subset=["time"],
        keep="first"
    )

    after = len(df)

    print(
        "Removed duplicate timestamps:",
        before - after
    )

    # ==========================================
    # 3. Check missing timestamps
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

    print(
        "Missing timestamps:",
        len(missing_time)
    )

    if len(missing_time) > 0:

        print(
            "WARNING: Time series is not continuous."
        )

        print(
            missing_time[:20]
        )

    # ==========================================
    # 4. Invalid values
    # ==========================================

    negative_rain = (
        df["rain"] < 0
    ).sum()

    negative_precipitation = (
        df["precipitation"] < 0
    ).sum()

    invalid_humidity = (
        (
            df["relative_humidity_2m"]
            < 0
        )
        |
        (
            df["relative_humidity_2m"]
            > 100
        )
    ).sum()

    negative_wind = (
        df["wind_speed_10m"]
        < 0
    ).sum()

    print(
        "\nNegative rain:",
        negative_rain
    )

    print(
        "Negative precipitation:",
        negative_precipitation
    )

    print(
        "Invalid humidity:",
        invalid_humidity
    )

    print(
        "Negative wind speed:",
        negative_wind
    )

    # ==========================================
    # 5. Time features
    # ==========================================

    df["year"] = (
        df["time"].dt.year
    )

    df["month"] = (
        df["time"].dt.month
    )

    df["hour"] = (
        df["time"].dt.hour
    )

    df["day_of_year"] = (
        df["time"].dt.dayofyear
    )

    # Quy ước mùa mưa ban đầu
    # Chỉ là feature hỗ trợ,
    # không phải ground truth.
    df["rainy_season"] = (
        df["month"]
        .between(
            5,
            11
        )
        .astype(int)
    )

    # ==========================================
    # 6. Missing values
    # ==========================================

    print(
        "\nMissing values:"
    )

    print(
        df.isna()
        .sum()
        .sort_values(
            ascending=False
        )
    )

    # Không tự động fill NaN bằng 0.

    # ==========================================
    # 7. Save
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
    print("CLEAN DATA COMPLETED")
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