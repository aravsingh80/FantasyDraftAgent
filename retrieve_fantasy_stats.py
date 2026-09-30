import nflreadpy as nfl
import polars as pl

from normalize_names import (
    normalize_name,
    normalize_position,
    normalize_team,
)


OFFENSIVE_POSITIONS = {
    "QB",
    "RB",
    "WR",
    "TE",
}


def add_missing_columns(stats):
    required_columns = [
        "passing_yards",
        "passing_tds",
        "passing_interceptions",
        "rushing_yards",
        "rushing_tds",
        "receiving_yards",
        "receiving_tds",
        "receptions",
        "rushing_fumbles_lost",
        "receiving_fumbles_lost",
        "sack_fumbles_lost",
    ]

    missing_columns = [
        pl.lit(0).alias(column)
        for column in required_columns
        if column not in stats.columns
    ]

    if missing_columns:
        stats = stats.with_columns(
            missing_columns
        )

    return stats


def calculate_ppr_points(stats):
    stats = add_missing_columns(stats)

    return stats.with_columns(
        (
            pl.col("passing_yards")
            .fill_null(0)
            * 0.04

            + pl.col("passing_tds")
            .fill_null(0)
            * 4

            - pl.col(
                "passing_interceptions"
            )
            .fill_null(0)
            * 2

            + pl.col("rushing_yards")
            .fill_null(0)
            * 0.1

            + pl.col("rushing_tds")
            .fill_null(0)
            * 6

            + pl.col("receiving_yards")
            .fill_null(0)
            * 0.1

            + pl.col("receiving_tds")
            .fill_null(0)
            * 6

            + pl.col("receptions")
            .fill_null(0)

            - pl.col(
                "rushing_fumbles_lost"
            )
            .fill_null(0)
            * 2

            - pl.col(
                "receiving_fumbles_lost"
            )
            .fill_null(0)
            * 2

            - pl.col(
                "sack_fumbles_lost"
            )
            .fill_null(0)
            * 2
        ).alias("fantasy_points")
    )


def get_fantasy_stats(seasons):
    stats = nfl.load_player_stats(
        seasons,
        summary_level="week",
    )

    stats = stats.with_columns(
        pl.col("position")
        .map_elements(
            normalize_position,
            return_dtype=pl.String,
        )
        .alias("normalized_position")
    )

    stats = stats.filter(
        (pl.col("season_type") == "REG")
        & pl.col(
            "normalized_position"
        ).is_in(
            list(OFFENSIVE_POSITIONS)
        )
    )

    stats = calculate_ppr_points(stats)

    stats = stats.with_columns(
        pl.col("player_display_name")
        .map_elements(
            normalize_name,
            return_dtype=pl.String,
        )
        .alias("normalized_name")
    )

    if "recent_team" in stats.columns:
        team_column = "recent_team"
    elif "team" in stats.columns:
        team_column = "team"
    else:
        raise KeyError(
            "Could not find a team column "
            "in player stats."
        )

    stats = stats.with_columns(
        pl.col(team_column)
        .map_elements(
            normalize_team,
            return_dtype=pl.String,
        )
        .alias("normalized_team")
    )

    seasonal = (
        stats.group_by(
            [
                "normalized_name",
                "player_display_name",
                "normalized_position",
                "season",
            ]
        )
        .agg(
            pl.col("fantasy_points")
            .sum()
            .alias("total_points"),

            pl.col("game_id")
            .n_unique()
            .alias("games_played"),

            pl.col("normalized_team")
            .drop_nulls()
            .last()
            .alias("team"),
        )
        .filter(
            pl.col("games_played") > 0
        )
        .with_columns(
            (
                pl.col("total_points")
                / pl.col("games_played")
            ).alias("ppg")
        )
    )

    seasonal = seasonal.with_columns(
        pl.col("total_points")
        .rank(
            method="ordinal",
            descending=True,
        )
        .over("season")
        .cast(pl.Int64)
        .alias("overall_rank"),

        pl.col("total_points")
        .rank(
            method="ordinal",
            descending=True,
        )
        .over(
            [
                "season",
                "normalized_position",
            ]
        )
        .cast(pl.Int64)
        .alias("position_rank"),
    )

    output = {}

    for group in seasonal.partition_by(
        "normalized_name",
        as_dict=False,
    ):
        rows = (
            group.sort("season")
            .tail(5)
            .to_dicts()
        )

        if not rows:
            continue

        normalized_name = rows[0][
            "normalized_name"
        ]

        season_history = {}

        total_points_across_seasons = 0.0
        total_games_across_seasons = 0

        for row in rows:
            season = str(row["season"])
            total_points = float(
                row["total_points"]
            )
            games_played = int(
                row["games_played"]
            )

            total_points_across_seasons += (
                total_points
            )

            total_games_across_seasons += (
                games_played
            )

            season_history[season] = {
                "team": normalize_team(
                    row.get("team")
                ),
                "total_points": round(
                    total_points,
                    3,
                ),
                "overall_rank": int(
                    row["overall_rank"]
                ),
                "position_rank": int(
                    row["position_rank"]
                ),
                "ppg": round(
                    float(row["ppg"]),
                    3,
                ),
                "games_played": (
                    games_played
                ),
            }

        career_ppg = (
            total_points_across_seasons
            / total_games_across_seasons
            if total_games_across_seasons > 0
            else None
        )

        output[normalized_name] = {
            "season_history": season_history,
            "career_ppg": (
                round(career_ppg, 3)
                if career_ppg is not None
                else None
            ),
        }

    return output