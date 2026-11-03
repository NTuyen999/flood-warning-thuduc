from pathlib import Path

import pandas as pd
import requests

from ml.src.config import (
    LATITUDE,
    LONGITUDE,
    TIMEZONE,
    START_DATE,
    END_DATE,
)


URL = "https://archive-api.open-meteo.com/v1/archive"

HOURLY_VARIABLES = [
    "temperature_2m",
    "relative_humidity_2m",
    "precipitation",
    "rain",
    "pressure_msl",
    "surface_pressure",
    "cloud_cover",
    "wind_speed_10m",
    "wind_direction_10m",
    "wind_gusts_10m",
]


def main():

    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "start_date": START_DATE,
        "end_date": END_DATE,
        "hourly": ",".join(HOURLY_VARIABLES),
        "timezone": TIMEZONE,
    }

    print("=" * 60)
    print("DOWNLOADING HISTORICAL WEATHER")
    print("=" * 60)

    response = requests.get(
        URL,
        params=params,
        timeout=120,
    )

    response.raise_for_status()

    data = response.json()

    if "hourly" not in data:
        raise RuntimeError(
            "Open-Meteo response does not contain hourly data."
        )

    df = pd.DataFrame(
        data["hourly"]
    )

    df["time"] = pd.to_datetime(
        df["time"]
    )

    # Sort theo thời gian
    df = (
        df.sort_values("time")
        .reset_index(drop=True)
    )

    output_dir = Path(
        "data/raw"
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = (
        output_dir
        / "historical_weather.csv"
    )

    df.to_csv(
        output_path,
        index=False,
        encoding="utf-8-sig",
    )

    print("\nDOWNLOAD COMPLETED")

    print(
        "Rows:",
        len(df)
    )

    print(
        "Columns:",
        len(df.columns)
    )

    print("\nColumns:")

    for col in df.columns:
        print("-", col)

    print("\nTime range:")

    print(
        df["time"].min()
    )

    print("->")

    print(
        df["time"].max()
    )

    print("\nRain statistics:")

    print(
        df["rain"]
        .describe()
    )

    print(
        "\nMax hourly rain:",
        df["rain"].max(),
        "mm"
    )

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

    print(
        "\nOutput:",
        output_path
    )


if __name__ == "__main__":
    main()