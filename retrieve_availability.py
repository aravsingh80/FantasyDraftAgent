import nflreadpy as nfl
import polars as pl

from normalize_names import (
    normalize_name,
    normalize_team,
)


def get_games_played_percentages(seasons):
    snaps = nfl.load_snap_counts(seasons)

    snaps = snaps.filter(
        pl.col("game_type") == "REG"
    )

    snaps = snaps.with_columns(
        pl.col("player")
        .map_elements(
            normalize_name,
            return_dtype=pl.String,
        )
        .alias("normalized_name"),

        pl.col("team")
        .map_elements(
            normalize_team,
            return_dtype=pl.String,
        )
        .alias("normalized_team"),
    )

    player_games = (
        snaps.group_by(
            [
                "normalized_name",
                "season",
            ]
        )
        .agg(
            pl.col("game_id")
            .n_unique()
            .alias("games_played")
        )
    )

    season_games = (
        snaps.group_by("season")
        .agg(
            pl.col("game_id")
            .n_unique()
            .alias("league_games")
        )
        .with_columns(
            (
                pl.col("league_games") / 16
            )
            .round(0)
            .cast(pl.Int64)
            .alias("possible_games")
        )
        .select(
            [
                "season",
                "possible_games",
            ]
        )
    )

    joined = player_games.join(
        season_games,
        on="season",
        how="left",
    )

    output = {}

    for group in joined.partition_by(
        "normalized_name",
        as_dict=False,
    ):
        rows = group.to_dicts()

        if not rows:
            continue

        total_played = sum(
            int(row["games_played"])
            for row in rows
        )

        total_possible = sum(
            int(row["possible_games"])
            for row in rows
            if row["possible_games"] is not None
        )

        percentage = (
            total_played / total_possible
            if total_possible > 0
            else None
        )

        normalized_name = rows[0][
            "normalized_name"
        ]

        output[normalized_name] = {
            "games_played": total_played,
            "possible_games": total_possible,
            "games_played_percentage": (
                round(percentage, 3)
                if percentage is not None
                else None
            ),
        }

    return output


def is_meaningful_injury_record(row):
    primary_injury = row.get(
        "report_primary_injury"
    )

    secondary_injury = row.get(
        "report_secondary_injury"
    )

    game_status = row.get(
        "report_status"
    )

    practice_status = row.get(
        "practice_status"
    )

    meaningful_game_statuses = {
        "Out",
        "Doubtful",
        "Questionable",
    }

    meaningful_practice_statuses = {
        "Did Not Participate In Practice",
        "Limited Participation in Practice",
    }

    return (
        primary_injury is not None
        or secondary_injury is not None
        or game_status in meaningful_game_statuses
        or practice_status
        in meaningful_practice_statuses
    )


def get_injury_history(seasons):
    injuries = nfl.load_injuries(seasons)

    if "season_type" in injuries.columns:
        injuries = injuries.filter(
            pl.col("season_type") == "REG"
        )

    injuries = injuries.with_columns(
        pl.col("full_name")
        .map_elements(
            normalize_name,
            return_dtype=pl.String,
        )
        .alias("normalized_name")
    )

    output = {}

    for row in injuries.to_dicts():
        if not is_meaningful_injury_record(row):
            continue

        normalized_name = row.get(
            "normalized_name"
        )

        if not normalized_name:
            continue

        record = {
            "season": row.get("season"),
            "week": row.get("week"),
            "team": normalize_team(
                row.get("team")
            ),
            "primary_injury": row.get(
                "report_primary_injury"
            ),
            "secondary_injury": row.get(
                "report_secondary_injury"
            ),
            "game_status": row.get(
                "report_status"
            ),
            "practice_status": row.get(
                "practice_status"
            ),
        }

        output.setdefault(
            normalized_name,
            {
                "injury_history": [],
            },
        )

        output[normalized_name][
            "injury_history"
        ].append(record)

    return output


def get_suspension_history(seasons):
    rosters = nfl.load_rosters_weekly(
        seasons
    )

    status_column = next(
        (
            column
            for column in [
                "status",
                "roster_status",
            ]
            if column in rosters.columns
        ),
        None,
    )

    name_column = next(
        (
            column
            for column in [
                "full_name",
                "player_name",
            ]
            if column in rosters.columns
        ),
        None,
    )

    team_column = next(
        (
            column
            for column in [
                "team",
                "team_abbr",
            ]
            if column in rosters.columns
        ),
        None,
    )

    if status_column is None or name_column is None:
        return {}

    suspended = rosters.filter(
        pl.col(status_column) == "SUS"
    )

    suspended = suspended.with_columns(
        pl.col(name_column)
        .map_elements(
            normalize_name,
            return_dtype=pl.String,
        )
        .alias("normalized_name")
    )

    output = {}

    seen_records = set()

    for row in suspended.to_dicts():
        normalized_name = row.get(
            "normalized_name"
        )

        season = row.get("season")
        week = row.get("week")

        record_key = (
            normalized_name,
            season,
            week,
        )

        if record_key in seen_records:
            continue

        seen_records.add(record_key)

        record = {
            "season": season,
            "week": week,
            "team": (
                normalize_team(
                    row.get(team_column)
                )
                if team_column
                else None
            ),
            "status": "SUS",
        }

        output.setdefault(
            normalized_name,
            {
                "suspension_history": [],
            },
        )

        output[normalized_name][
            "suspension_history"
        ].append(record)

    return output


def get_availability_data(seasons):
    percentages = (
        get_games_played_percentages(
            seasons
        )
    )

    injuries = get_injury_history(
        seasons
    )

    suspensions = get_suspension_history(
        seasons
    )

    names = (
        set(percentages)
        | set(injuries)
        | set(suspensions)
    )

    output = {}

    for normalized_name in names:
        percentage_data = percentages.get(
            normalized_name,
            {},
        )

        output[normalized_name] = {
            "games_played": (
                percentage_data.get(
                    "games_played"
                )
            ),
            "possible_games": (
                percentage_data.get(
                    "possible_games"
                )
            ),
            "games_played_percentage": (
                percentage_data.get(
                    "games_played_percentage"
                )
            ),
            "injury_history": (
                injuries
                .get(normalized_name, {})
                .get("injury_history", [])
            ),
            "suspension_history": (
                suspensions
                .get(normalized_name, {})
                .get(
                    "suspension_history",
                    [],
                )
            ),
        }

    return output