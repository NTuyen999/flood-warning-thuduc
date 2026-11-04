import pandas as pd


FILE_PATH = "data/raw/historical_weather.csv"


def main():
    df = pd.read_csv(
        FILE_PATH,
        parse_dates=["time"]
    )

    print("=" * 60)
    print("DATASET OVERVIEW")
    print("=" * 60)

    print("\nShape:")
    print(df.shape)

    print("\nColumns:")
    print(df.columns.tolist())

    print("\nData types:")
    print(df.dtypes)

    print("\nTime range:")
    print(df["time"].min())
    print("->")
    print(df["time"].max())

    print("\nMissing values:")
    print(
        df.isnull()
        .sum()
        .sort_values(ascending=False)
    )

    print("\nDuplicate rows:")
    print(df.duplicated().sum())

    print("\nDuplicate timestamps:")
    print(df["time"].duplicated().sum())

    print("\nNumeric statistics:")
    print(df.describe().T)

    # Check missing hourly timestamps
    expected_time = pd.date_range(
        start=df["time"].min(),
        end=df["time"].max(),
        freq="h"
    )

    missing_time = expected_time.difference(
        df["time"]
    )

    print("\nMissing timestamps:")
    print(len(missing_time))

    if len(missing_time) > 0:
        print("\nFirst missing timestamps:")
        print(missing_time[:20])


if __name__ == "__main__":
    main()