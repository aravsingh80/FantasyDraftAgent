import nflreadpy as nfl
import polars as pl

from normalize_names import normalize_team


def get_team_tendencies(
    seasons,
    knowledge_base,
):
    pbp = nfl.load_pbp(seasons)

    pbp = pbp.filter(
        pl.col("season_type") == "REG"
    )

    pbp = pbp.filter(
        (
            pl.col("pass_attempt")
            .fill_null(0)
            == 1
        )
        | (
            pl.col("rush_attempt")
            .fill_null(0)
            == 1
        )
    )

    pbp = pbp.with_columns(
        pl.col("posteam")
        .map_elements(
            normalize_team,
            return_dtype=pl.String,
        )
        .alias("normalized_team")
    )

    team_data = (
        pbp.group_by(
            [
                "season",
                "normalized_team",
            ]
        )
        .agg(
            pl.col("pass_attempt")
            .fill_null(0)
            .sum()
            .alias("pass_plays"),

            pl.col("rush_attempt")
            .fill_null(0)
            .sum()
            .alias("run_plays"),
        )
        .with_columns(
            (
                pl.col("pass_plays")
                + pl.col("run_plays")
            ).alias("total_plays")
        )
        .filter(
            pl.col("total_plays") > 0
        )
        .with_columns(
            (
                pl.col("pass_plays")
                / pl.col("total_plays")
            ).alias("team_pass_rate"),

            (
                pl.col("run_plays")
                / pl.col("total_plays")
            ).alias("team_run_rate"),
        )
    )

    tendencies_by_team = {}

    for row in team_data.to_dicts():
        team = row.get(
            "normalized_team"
        )

        season = row.get("season")

        if not team:
            continue

        tendencies_by_team.setdefault(
            team,
            {},
        )

        tendencies_by_team[team][
            str(season)
        ] = {
            "team_pass_rate": round(
                float(
                    row["team_pass_rate"]
                ),
                3,
            ),
            "team_run_rate": round(
                float(
                    row["team_run_rate"]
                ),
                3,
            ),
        }

    output = {}

    for (
        normalized_name,
        player,
    ) in knowledge_base.items():
        team = normalize_team(
            player.get("team")
        )

        team_history = (
            tendencies_by_team.get(
                team,
                {},
            )
        )

        if not team_history:
            continue

        available_seasons = [
            int(season)
            for season in team_history
            if str(season).isdigit()
        ]

        if not available_seasons:
            continue

        latest_season = max(
            available_seasons
        )

        latest_data = team_history[
            str(latest_season)
        ]

        output[normalized_name] = {
            "team_pass_rate": (
                latest_data[
                    "team_pass_rate"
                ]
            ),
            "team_run_rate": (
                latest_data[
                    "team_run_rate"
                ]
            ),
            "team_tendencies_by_season": (
                team_history
            ),
        }

    return output