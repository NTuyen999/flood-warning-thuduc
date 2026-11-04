from pathlib import Path
import pandas as pd


INPUT_FILE = "data/processed/weather_labeled.csv"

OUTPUT_DIR = Path("ml/outputs/metrics")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def main():

    df = pd.read_csv(
        INPUT_FILE,
        parse_dates=["time"]
    )

    df = (
        df.sort_values("time")
        .reset_index(drop=True)
    )

    print("=" * 60)
    print("HEAVY RAIN EVENT ANALYSIS")
    print("=" * 60)

    # ==========================================
    # 1. Kiểm tra nhiều threshold
    # Chỉ để phân tích, CHƯA thay threshold chính
    # ==========================================

    thresholds = [
        10,
        15,
        20,
        25,
        30
    ]

    sensitivity_results = []

    print("\nTHRESHOLD SENSITIVITY")

    for threshold in thresholds:

        count = (
            df["rain_3h"] >= threshold
        ).sum()

        percentage = (
            count
            / len(df)
            * 100
        )

        sensitivity_results.append({
            "threshold_mm_3h": threshold,
            "positive_hours": count,
            "percentage": percentage,
        })

        print(
            f">= {threshold} mm/3h:"
            f" {count} hours"
            f" ({percentage:.4f}%)"
        )

    sensitivity_df = pd.DataFrame(
        sensitivity_results
    )

    sensitivity_df.to_csv(
        OUTPUT_DIR
        / "threshold_sensitivity.csv",
        index=False
    )

    # ==========================================
    # 2. Phân tích threshold chính 30 mm/3h
    # ==========================================

    positive = (
        df["heavy_rain_event"] == 1
    )

    # Một episode mới bắt đầu khi:
    # dòng hiện tại = positive
    # nhưng dòng trước = negative
    starts = (
        positive
        & ~positive.shift(
            fill_value=False
        )
    )

    episode_id = starts.cumsum()

    positive_df = (
        df.loc[positive]
        .copy()
    )

    positive_df["episode_id"] = (
        episode_id[positive]
        .values
    )

    if len(positive_df) == 0:

        print(
            "\nNo heavy rain events found."
        )

        return

    episodes = (
        positive_df
        .groupby("episode_id")
        .agg(
            start_time=(
                "time",
                "min"
            ),
            end_time=(
                "time",
                "max"
            ),
            positive_hours=(
                "time",
                "size"
            ),
            max_rain_3h=(
                "rain_3h",
                "max"
            ),
            max_hourly_rain=(
                "precipitation",
                "max"
            ),
        )
        .reset_index()
    )

    print("\n" + "=" * 60)
    print("INDEPENDENT EPISODES")
    print("=" * 60)

    print(
        "Positive hours:",
        len(positive_df)
    )

    print(
        "Number of episodes:",
        len(episodes)
    )

    print("\nEpisodes:")

    print(
        episodes.to_string(
            index=False
        )
    )

    episodes.to_csv(
        OUTPUT_DIR
        / "heavy_rain_episodes.csv",
        index=False,
        encoding="utf-8-sig"
    )

    # ==========================================
    # 3. Top rain_3h
    # ==========================================

    print("\n" + "=" * 60)
    print("TOP 20 RAIN_3H")
    print("=" * 60)

    top = (
        df[
            [
                "time",
                "precipitation",
                "rain_3h"
            ]
        ]
        .sort_values(
            "rain_3h",
            ascending=False
        )
        .head(20)
    )

    print(
        top.to_string(
            index=False
        )
    )

    top.to_csv(
        OUTPUT_DIR
        / "top_rain_3h.csv",
        index=False,
        encoding="utf-8-sig"
    )

    print("\nAnalysis completed.")


if __name__ == "__main__":
    main()