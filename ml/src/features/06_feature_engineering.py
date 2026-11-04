from pathlib import Path
import numpy as np
import pandas as pd


INPUT_FILE = "data/processed/weather_labeled.csv"
OUTPUT_FILE = "data/processed/ml_dataset.csv"


def main():

    print("Loading labeled dataset...")

    df = pd.read_csv(
        INPUT_FILE,
        parse_dates=["time"]
    )

    df = (
        df.sort_values("time")
        .reset_index(drop=True)
    )

    # ==========================================
    # 1. Rain historical features
    # Chỉ sử dụng hiện tại và quá khứ
    # ==========================================

    df["rain_last_1h"] = df["precipitation"]

    df["rain_last_3h"] = (
        df["precipitation"]
        .rolling(
            window=3,
            min_periods=3
        )
        .sum()
    )

    df["rain_last_6h"] = (
        df["precipitation"]
        .rolling(
            window=6,
            min_periods=6
        )
        .sum()
    )

    df["rain_last_12h"] = (
        df["precipitation"]
        .rolling(
            window=12,
            min_periods=12
        )
        .sum()
    )

    df["rain_last_24h"] = (
        df["precipitation"]
        .rolling(
            window=24,
            min_periods=24
        )
        .sum()
    )

    # ==========================================
    # 2. Rain lag features
    # ==========================================

    df["rain_lag_1h"] = (
        df["precipitation"]
        .shift(1)
    )

    df["rain_lag_2h"] = (
        df["precipitation"]
        .shift(2)
    )

    df["rain_lag_3h"] = (
        df["precipitation"]
        .shift(3)
    )

    # ==========================================
    # 3. Humidity features
    # ==========================================

    df["humidity_lag_1h"] = (
        df["relative_humidity_2m"]
        .shift(1)
    )

    df["humidity_change_1h"] = (
        df["relative_humidity_2m"]
        - df["humidity_lag_1h"]
    )

    df["humidity_mean_3h"] = (
        df["relative_humidity_2m"]
        .rolling(
            window=3,
            min_periods=3
        )
        .mean()
    )

    # ==========================================
    # 4. Pressure features
    # ==========================================

    df["pressure_lag_1h"] = (
        df["pressure_msl"]
        .shift(1)
    )

    df["pressure_change_1h"] = (
        df["pressure_msl"]
        - df["pressure_lag_1h"]
    )

    df["pressure_mean_3h"] = (
        df["pressure_msl"]
        .rolling(
            window=3,
            min_periods=3
        )
        .mean()
    )

    # ==========================================
    # 5. Wind features
    # ==========================================

    df["wind_speed_lag_1h"] = (
        df["wind_speed_10m"]
        .shift(1)
    )

    df["wind_speed_change_1h"] = (
        df["wind_speed_10m"]
        - df["wind_speed_lag_1h"]
    )

    # Wind direction là biến tuần hoàn:
    # 359° gần 0°, nên encode sin/cos
    radians = np.deg2rad(
        df["wind_direction_10m"]
    )

    df["wind_direction_sin"] = np.sin(
        radians
    )

    df["wind_direction_cos"] = np.cos(
        radians
    )

    # ==========================================
    # 6. Time cyclical features
    # ==========================================

    df["hour_sin"] = np.sin(
        2 * np.pi
        * df["hour"]
        / 24
    )

    df["hour_cos"] = np.cos(
        2 * np.pi
        * df["hour"]
        / 24
    )

    df["month_sin"] = np.sin(
        2 * np.pi
        * df["month"]
        / 12
    )

    df["month_cos"] = np.cos(
        2 * np.pi
        * df["month"]
        / 12
    )

    # ==========================================
    # 7. Kiểm tra
    # ==========================================

    feature_columns = [
        "temperature_2m",
        "relative_humidity_2m",
        "pressure_msl",
        "surface_pressure",
        "cloud_cover",
        "wind_speed_10m",
        "wind_gusts_10m",

        "rain_last_1h",
        "rain_last_3h",
        "rain_last_6h",
        "rain_last_12h",
        "rain_last_24h",

        "rain_lag_1h",
        "rain_lag_2h",
        "rain_lag_3h",

        "humidity_lag_1h",
        "humidity_change_1h",
        "humidity_mean_3h",

        "pressure_lag_1h",
        "pressure_change_1h",
        "pressure_mean_3h",

        "wind_speed_lag_1h",
        "wind_speed_change_1h",

        "wind_direction_sin",
        "wind_direction_cos",

        "hour_sin",
        "hour_cos",
        "month_sin",
        "month_cos",

        "rainy_season",
    ]

    print("\nNumber of features:")
    print(len(feature_columns))

    print("\nFeature list:")
    for feature in feature_columns:
        print("-", feature)

    print("\nMissing values in features:")
    print(
        df[feature_columns]
        .isnull()
        .sum()
        .sort_values(
            ascending=False
        )
        .head(15)
    )

    # ==========================================
    # 8. Save
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

    print("\n==============================")
    print("FEATURE ENGINEERING COMPLETED")
    print("==============================")

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