import nflreadpy as nfl
import polars as pl

from normalize_names import normalize_team


DEFENSE_SCORING = {
    "sack": 1,
    "interception": 2,
    "fumble_recovery": 2,
    "defensive_touchdown": 6,
    "safety": 2,
}


POINTS_ALLOWED_SCORING = [
    (0, 0, 10),
    (1, 6, 7),
    (7, 13, 4),
    (14, 20, 1),
    (21, 27, 0),
    (28, 34, -1),
    (35, float("inf"), -4),
]


def points_allowed_score(points_allowed):
    if points_allowed is None:
        return 0

    for minimum, maximum, score in (
        POINTS_ALLOWED_SCORING
    ):
        if minimum <= points_allowed <= maximum:
            return score

    return 0


def add_missing_columns(pbp):
    required_columns = [
        "defteam",
        "sack",
        "interception",
        "fumble_lost",
        "touchdown",
        "td_team",
        "safety",
    ]

    expressions = []

    for column in required_columns:
        if column in pbp.columns:
            continue

        if column in {
            "defteam",
            "td_team",
        }:
            expressions.append(
                pl.lit(None)
                .cast(pl.String)
                .alias(column)
            )
        else:
            expressions.append(
                pl.lit(0).alias(column)
            )

    if expressions:
        pbp = pbp.with_columns(
            expressions
        )

    return pbp


def get_schedule_team_games(seasons):
    schedules = nfl.load_schedules(
        seasons
    )

    schedules = schedules.filter(
        pl.col("game_type") == "REG"
    )

    completed = schedules.filter(
        pl.col("home_score").is_not_null()
        & pl.col("away_score").is_not_null()
    )

    home_rows = completed.select(
        pl.col("season"),
        pl.col("game_id"),
        pl.col("home_team")
        .map_elements(
            normalize_team,
            return_dtype=pl.String,
        )
        .alias("team"),
        pl.col("away_score")
        .cast(pl.Int64)
        .alias("points_allowed"),
    )

    away_rows = completed.select(
        pl.col("season"),
        pl.col("game_id"),
        pl.col("away_team")
        .map_elements(
            normalize_team,
            return_dtype=pl.String,
        )
        .alias("team"),
        pl.col("home_score")
        .cast(pl.Int64)
        .alias("points_allowed"),
    )

    team_games = pl.concat(
        [
            home_rows,
            away_rows,
        ]
    )

    return team_games.with_columns(
        pl.col("points_allowed")
        .map_elements(
            points_allowed_score,
            return_dtype=pl.Int64,
        )
        .alias("points_allowed_fantasy_points")
    )


def get_defense_stats(seasons):
    pbp = nfl.load_pbp(seasons)
    pbp = add_missing_columns(pbp)

    pbp = pbp.filter(
        pl.col("season_type") == "REG"
    )

    pbp = pbp.with_columns(
        pl.col("defteam")
        .map_elements(
            normalize_team,
            return_dtype=pl.String,
        )
        .alias("normalized_defteam"),

        pl.col("td_team")
        .map_elements(
            normalize_team,
            return_dtype=pl.String,
        )
        .alias("normalized_td_team"),
    )

    defensive_plays = (
        pbp.filter(
            pl.col(
                "normalized_defteam"
            ).is_not_null()
        )
        .group_by(
            [
                "season",
                "normalized_defteam",
            ]
        )
        .agg(
            pl.col("sack")
            .fill_null(0)
            .sum()
            .alias("sacks"),

            pl.col("interception")
            .fill_null(0)
            .sum()
            .alias("interceptions"),

            pl.col("fumble_lost")
            .fill_null(0)
            .sum()
            .alias("fumble_recoveries"),

            (
                (
                    pl.col("touchdown")
                    .fill_null(0)
                    == 1
                )
                & (
                    pl.col(
                        "normalized_td_team"
                    )
                    == pl.col(
                        "normalized_defteam"
                    )
                )
            )
            .sum()
            .alias("defensive_touchdowns"),

            pl.col("safety")
            .fill_null(0)
            .sum()
            .alias("safeties"),
        )
        .rename({
            "normalized_defteam": "team",
        })
    )

    schedule_games = get_schedule_team_games(
        seasons
    )

    schedule_summary = (
        schedule_games.group_by(
            [
                "season",
                "team",
            ]
        )
        .agg(
            pl.col("game_id")
            .n_unique()
            .alias("games_played"),

            pl.col("points_allowed")
            .sum()
            .alias("points_allowed"),

            pl.col(
                "points_allowed_fantasy_points"
            )
            .sum()
            .alias(
                "points_allowed_fantasy_points"
            ),
        )
    )

    seasonal = schedule_summary.join(
        defensive_plays,
        on=[
            "season",
            "team",
        ],
        how="left",
    )

    numeric_columns = [
        "sacks",
        "interceptions",
        "fumble_recoveries",
        "defensive_touchdowns",
        "safeties",
    ]

    seasonal = seasonal.with_columns(
        [
            pl.col(column).fill_null(0)
            for column in numeric_columns
        ]
    )

    seasonal = seasonal.with_columns(
        (
            pl.col("sacks")
            * DEFENSE_SCORING["sack"]

            + pl.col("interceptions")
            * DEFENSE_SCORING[
                "interception"
            ]

            + pl.col("fumble_recoveries")
            * DEFENSE_SCORING[
                "fumble_recovery"
            ]

            + pl.col(
                "defensive_touchdowns"
            )
            * DEFENSE_SCORING[
                "defensive_touchdown"
            ]

            + pl.col("safeties")
            * DEFENSE_SCORING["safety"]

            + pl.col(
                "points_allowed_fantasy_points"
            )
        ).alias("total_points")
    )

    seasonal = seasonal.with_columns(
        (
            pl.col("total_points")
            / pl.col("games_played")
        ).alias("ppg"),

        pl.col("total_points")
        .rank(
            method="ordinal",
            descending=True,
        )
        .over("season")
        .cast(pl.Int64)
        .alias("position_rank"),
    )

    output = {}

    for team_group in seasonal.partition_by(
        "team",
        as_dict=False,
    ):
        rows = (
            team_group.sort("season")
            .tail(5)
            .to_dicts()
        )

        if not rows:
            continue

        team = rows[0]["team"]
        season_history = {}

        total_points = 0.0
        total_games = 0

        for row in rows:
            season = str(row["season"])

            row_total_points = float(
                row["total_points"]
            )

            games_played = int(
                row["games_played"]
            )

            total_points += row_total_points
            total_games += games_played

            season_history[season] = {
                "team": team,
                "total_points": round(
                    row_total_points,
                    3,
                ),
                "position_rank": int(
                    row["position_rank"]
                ),
                "ppg": round(
                    float(row["ppg"]),
                    3,
                ),
                "games_played": games_played,
                "sacks": int(row["sacks"]),
                "interceptions": int(
                    row["interceptions"]
                ),
                "fumble_recoveries": int(
                    row["fumble_recoveries"]
                ),
                "defensive_touchdowns": int(
                    row["defensive_touchdowns"]
                ),
                "safeties": int(
                    row["safeties"]
                ),
                "points_allowed": int(
                    row["points_allowed"]
                ),
            }

        output[team] = {
            "season_history": season_history,
            "career_ppg": (
                round(
                    total_points / total_games,
                    3,
                )
                if total_games > 0
                else None
            ),
        }

    return output