from datetime import date, datetime

import nflreadpy as nfl
import polars as pl

from normalize_names import (
    normalize_name,
    normalize_position,
    normalize_team,
)


def calculate_age(birth_date):
    if birth_date is None:
        return None

    if isinstance(birth_date, datetime):
        birth_date = birth_date.date()

    if isinstance(birth_date, str):
        parsed_date = None

        for date_format in [
            "%Y-%m-%d",
            "%m/%d/%Y",
        ]:
            try:
                parsed_date = datetime.strptime(
                    birth_date,
                    date_format,
                ).date()
                break
            except ValueError:
                continue

        if parsed_date is None:
            return None

        birth_date = parsed_date

    today = date.today()

    return (
        today.year
        - birth_date.year
        - (
            (today.month, today.day)
            < (birth_date.month, birth_date.day)
        )
    )


def get_career_info(
    current_season,
    knowledge_base,
):
    players = nfl.load_players()

    name_column = next(
        (
            column
            for column in [
                "display_name",
                "full_name",
                "player_name",
            ]
            if column in players.columns
        ),
        None,
    )

    position_column = next(
        (
            column
            for column in [
                "position",
                "position_group",
            ]
            if column in players.columns
        ),
        None,
    )

    team_column = next(
        (
            column
            for column in [
                "latest_team",
                "team",
                "team_abbr",
            ]
            if column in players.columns
        ),
        None,
    )

    rookie_column = next(
        (
            column
            for column in [
                "rookie_season",
                "entry_year",
                "draft_year",
            ]
            if column in players.columns
        ),
        None,
    )

    birth_column = next(
        (
            column
            for column in [
                "birth_date",
                "birthdate",
            ]
            if column in players.columns
        ),
        None,
    )

    if name_column is None or position_column is None:
        return {}

    players = players.with_columns(
        pl.col(name_column)
        .map_elements(
            normalize_name,
            return_dtype=pl.String,
        )
        .alias("normalized_name")
    )

    output = {}

    for row in players.to_dicts():
        normalized_name = row.get("normalized_name")
        knowledge_player = knowledge_base.get(normalized_name)

        if knowledge_player is None:
            continue

        expected_position = normalize_position(
            knowledge_player.get("position")
        )

        actual_position = normalize_position(
            row.get(position_column)
        )

        if actual_position != expected_position:
            continue

        expected_team = normalize_team(
            knowledge_player.get("team")
        )

        actual_team = (
            normalize_team(row.get(team_column))
            if team_column
            else None
        )

        if (
            expected_team
            and actual_team
            and expected_team != actual_team
        ):
            continue

        rookie_season = (
            row.get(rookie_column)
            if rookie_column
            else None
        )

        try:
            rookie_season = int(rookie_season)
        except (TypeError, ValueError):
            rookie_season = None

        season_history = knowledge_player.get(
            "season_history",
            {},
        )

        historical_seasons = [
            int(season)
            for season in season_history
            if str(season).isdigit()
        ]

        if historical_seasons:
            earliest_history_season = min(
                historical_seasons
            )

            if (
                rookie_season is not None
                and rookie_season
                > earliest_history_season
            ):
                continue

        years_in_league = (
            current_season - rookie_season + 1
            if rookie_season is not None
            else None
        )

        output[normalized_name] = {
            "rookie_season": rookie_season,
            "years_in_league": years_in_league,
            "age": (
                calculate_age(
                    row.get(birth_column)
                )
                if birth_column
                else None
            ),
        }

    return output