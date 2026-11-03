from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


INPUT_FILE = "data/processed/weather_clean.csv"
OUTPUT_DIR = Path("ml/outputs/figures")


def save_figure(filename):
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    output_path = OUTPUT_DIR / filename

    plt.tight_layout()
    plt.savefig(
        output_path,
        dpi=150,
        bbox_inches="tight"
    )
    plt.close()

    print("Saved:", output_path)


def main():

    df = pd.read_csv(
        INPUT_FILE,
        parse_dates=["time"]
    )

    print("Dataset shape:", df.shape)

    # ======================================
    # 1. Precipitation distribution
    # ======================================

    plt.figure(figsize=(10, 5))

    df["precipitation"].hist(
        bins=50
    )

    plt.title(
        "Hourly Precipitation Distribution"
    )

    plt.xlabel(
        "Precipitation (mm)"
    )

    plt.ylabel(
        "Number of hours"
    )

    save_figure(
        "01_precipitation_distribution.png"
    )

    # ======================================
    # 2. Monthly total rainfall
    # ======================================

    monthly_rain = (
        df.groupby("month")["precipitation"]
        .sum()
    )

    plt.figure(figsize=(10, 5))

    monthly_rain.plot(
        kind="bar"
    )

    plt.title(
        "Total Precipitation by Month"
    )

    plt.xlabel(
        "Month"
    )

    plt.ylabel(
        "Total precipitation (mm)"
    )

    save_figure(
        "02_monthly_rainfall.png"
    )

    # ======================================
    # 3. Average rainfall by hour
    # ======================================

    hourly_rain = (
        df.groupby("hour")["precipitation"]
        .mean()
    )

    plt.figure(figsize=(10, 5))

    hourly_rain.plot(
        kind="bar"
    )

    plt.title(
        "Average Precipitation by Hour"
    )

    plt.xlabel(
        "Hour"
    )

    plt.ylabel(
        "Average precipitation (mm)"
    )

    save_figure(
        "03_hourly_rainfall.png"
    )

    # ======================================
    # 4. Humidity vs precipitation
    # ======================================

    plt.figure(figsize=(10, 5))

    plt.scatter(
        df["relative_humidity_2m"],
        df["precipitation"],
        alpha=0.25,
        s=10
    )

    plt.title(
        "Humidity vs Precipitation"
    )

    plt.xlabel(
        "Relative humidity (%)"
    )

    plt.ylabel(
        "Precipitation (mm)"
    )

    save_figure(
        "04_humidity_vs_precipitation.png"
    )

    # ======================================
    # 5. Pressure vs precipitation
    # ======================================

    plt.figure(figsize=(10, 5))

    plt.scatter(
        df["pressure_msl"],
        df["precipitation"],
        alpha=0.25,
        s=10
    )

    plt.title(
        "Pressure vs Precipitation"
    )

    plt.xlabel(
        "Mean sea level pressure"
    )

    plt.ylabel(
        "Precipitation (mm)"
    )

    save_figure(
        "05_pressure_vs_precipitation.png"
    )

    # ======================================
    # 6. Monthly average humidity
    # ======================================

    monthly_humidity = (
        df.groupby("month")[
            "relative_humidity_2m"
        ]
        .mean()
    )

    plt.figure(figsize=(10, 5))

    monthly_humidity.plot(
        kind="bar"
    )

    plt.title(
        "Average Humidity by Month"
    )

    plt.xlabel(
        "Month"
    )

    plt.ylabel(
        "Average humidity (%)"
    )

    save_figure(
        "06_monthly_humidity.png"
    )

    # ======================================
    # Console statistics
    # ======================================

    print("\n======================")
    print("PRECIPITATION STATS")
    print("======================")

    print(
        df["precipitation"]
        .describe()
    )

    rain_hours = (
        df["precipitation"] > 0
    ).sum()

    dry_hours = (
        df["precipitation"] == 0
    ).sum()

    print("\nRain hours:", rain_hours)
    print("Dry hours:", dry_hours)

    print(
        "Rain hour percentage:",
        round(
            rain_hours
            / len(df)
            * 100,
            2
        ),
        "%"
    )

    print("\nEDA completed.")


if __name__ == "__main__":
    main()
    