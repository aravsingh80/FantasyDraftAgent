import json
import time
from pathlib import Path

import nflreadpy as nfl
import requests

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
    "K",
}


SLEEPER_PLAYERS_URL = (
    "https://api.sleeper.app/v1/players/nfl"
)

SLEEPER_CACHE_FILE = Path(
    "sleeper_players_cache.json"
)

SLEEPER_CACHE_MAX_AGE_SECONDS = (
    24 * 60 * 60
)


def get_first_existing_column(
    columns,
    possibilities,
):
    for column in possibilities:
        if column in columns:
            return column

    return None


def get_latest_sort_value(
    row,
    columns,
):
    for column in [
        "date",
        "dt",
        "gameday",
        "week",
    ]:
        if column in columns:
            value = row.get(column)

            if value is not None:
                return value

    return 0


def load_current_depth_charts(
    current_season,
):
    try:
        depth_charts = nfl.load_depth_charts(
            current_season
        )

        return depth_charts.to_dicts()

    except Exception:
        return []


def load_current_injuries(
    current_season,
):
    try:
        injuries = nfl.load_injuries(
            current_season
        )

        return injuries.to_dicts()

    except Exception:
        return []


def load_current_rosters(
    current_season,
):
    try:
        rosters = nfl.load_rosters_weekly(
            current_season
        )

        return rosters.to_dicts()

    except Exception:
        return []


def sleeper_cache_is_fresh():
    if not SLEEPER_CACHE_FILE.exists():
        return False

    cache_age = (
        time.time()
        - SLEEPER_CACHE_FILE.stat().st_mtime
    )

    return (
        cache_age
        < SLEEPER_CACHE_MAX_AGE_SECONDS
    )


def load_sleeper_players():
    if sleeper_cache_is_fresh():
        with SLEEPER_CACHE_FILE.open(
            "r",
            encoding="utf-8",
        ) as file:
            return json.load(file)

    response = requests.get(
        SLEEPER_PLAYERS_URL,
        timeout=30,
    )

    response.raise_for_status()

    players = response.json()

    with SLEEPER_CACHE_FILE.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            players,
            file,
        )

    return players


def build_sleeper_name_lookup(
    sleeper_players,
):
    lookup = {}

    for (
        player_id,
        player,
    ) in sleeper_players.items():

        position = normalize_position(
            player.get("position")
        )

        if (
            position
            not in OFFENSIVE_POSITIONS
        ):
            continue

        full_name = player.get(
            "full_name"
        )

        if not full_name:
            first_name = (
                player.get(
                    "first_name"
                )
                or ""
            )

            last_name = (
                player.get(
                    "last_name"
                )
                or ""
            )

            full_name = (
                f"{first_name} "
                f"{last_name}"
            ).strip()

        normalized_name = (
            normalize_name(
                full_name
            )
        )

        if not normalized_name:
            continue

        lookup.setdefault(
            normalized_name,
            [],
        ).append({
            **player,
            "player_id": (
                player.get(
                    "player_id"
                )
                or player_id
            ),
        })

    return lookup

def build_depth_chart_lookup(
    depth_rows,
):
    lookup = {}

    if not depth_rows:
        return lookup

    columns = set()

    for row in depth_rows[:10]:
        columns.update(
            row.keys()
        )

    name_column = (
        get_first_existing_column(
            columns,
            [
                "full_name",
                "player_name",
                "name",
                "player_display_name",
            ],
        )
    )

    if name_column is None:
        return lookup

    for row in depth_rows:
        normalized_name = (
            normalize_name(
                row.get(
                    name_column
                )
            )
        )

        if not normalized_name:
            continue

        lookup.setdefault(
            normalized_name,
            [],
        ).append(
            row
        )

    return lookup

def load_live_datasets(
    current_season=2026,
):
    depth_rows = (
        load_current_depth_charts(
            current_season
        )
    )

    injury_rows = (
        load_current_injuries(
            current_season
        )
    )

    roster_rows = (
        load_current_rosters(
            current_season
        )
    )

    sleeper_players = (
        load_sleeper_players()
    )

    return {
        "depth_rows": (
            depth_rows
        ),
        "depth_lookup": (
            build_depth_chart_lookup(
                depth_rows
            )
        ),
        "injury_rows": (
            injury_rows
        ),
        "roster_rows": (
            roster_rows
        ),
        "sleeper_players": (
            sleeper_players
        ),
        "sleeper_name_lookup": (
            build_sleeper_name_lookup(
                sleeper_players
            )
        ),
    }


def get_depth_chart_data(
    candidate,
    depth_lookup,
):
    if not depth_lookup:
        return {}

    candidate_name = normalize_name(
        candidate.get(
            "name",
            "",
        )
    )

    matches = depth_lookup.get(
        candidate_name,
        [],
    )

    if not matches:
        return {}

    candidate_position = (
        normalize_position(
            candidate.get(
                "position"
            )
        )
    )

    candidate_team = normalize_team(
        candidate.get(
            "team"
        )
    )

    columns = set()

    for row in matches[:10]:
        columns.update(
            row.keys()
        )

    position_column = (
        get_first_existing_column(
            columns,
            [
                "pos_abb",
                "position",
                "pos",
                "position_group",
            ],
        )
    )

    rank_column = (
        get_first_existing_column(
            columns,
            [
                "pos_rank",
                "depth_position",
                "depth_chart_order",
                "rank",
            ],
        )
    )

    team_column = (
        get_first_existing_column(
            columns,
            [
                "team",
                "club_code",
                "depth_team",
                "team_abbr",
            ],
        )
    )

    filtered = []

    for row in matches:
        row_position = (
            normalize_position(
                row.get(
                    position_column
                )
            )
            if position_column
            else None
        )

        row_team = (
            normalize_team(
                row.get(
                    team_column
                )
            )
            if team_column
            else None
        )

        if (
            candidate_position
            and row_position
            and candidate_position
            != row_position
        ):
            continue

        if (
            candidate_team
            and row_team
            and candidate_team
            != row_team
        ):
            continue

        filtered.append(
            row
        )

    if not filtered:
        return {}

    filtered.sort(
        key=lambda row: (
            get_latest_sort_value(
                row,
                columns,
            )
        ),
        reverse=True,
    )

    latest = filtered[0]

    depth_rank = (
        latest.get(
            rank_column
        )
        if rank_column
        else None
    )

    role = candidate_position

    if depth_rank is not None:
        role = (
            f"{candidate_position}"
            f"{depth_rank}"
        )

    return {
        "current_depth_chart_position": (
            depth_rank
        ),
        "current_depth_chart_role": (
            role
        ),
    }


def get_injury_data(
    candidate,
    injury_rows,
):
    if not injury_rows:
        return {}

    candidate_name = normalize_name(
        candidate.get("name", "")
    )

    candidate_team = normalize_team(
        candidate.get("team")
    )

    columns = set()

    for row in injury_rows[:10]:
        columns.update(
            row.keys()
        )

    name_column = (
        get_first_existing_column(
            columns,
            [
                "full_name",
                "player_name",
                "name",
            ],
        )
    )

    team_column = (
        get_first_existing_column(
            columns,
            [
                "team",
                "team_abbr",
            ],
        )
    )

    if name_column is None:
        return {}

    matches = []

    for row in injury_rows:
        row_name = normalize_name(
            row.get(
                name_column
            )
        )

        row_team = (
            normalize_team(
                row.get(
                    team_column
                )
            )
            if team_column
            else None
        )

        if (
            row_name
            != candidate_name
        ):
            continue

        if (
            candidate_team
            and row_team
            and candidate_team
            != row_team
        ):
            continue

        matches.append(
            row
        )

    if not matches:
        return {}

    matches.sort(
        key=lambda row: (
            get_latest_sort_value(
                row,
                columns,
            )
        ),
        reverse=True,
    )

    latest = matches[0]

    injury = latest.get(
        "report_primary_injury"
    )

    status = latest.get(
        "report_status"
    )

    practice_status = latest.get(
        "practice_status"
    )

    if (
        injury is None
        and status is None
        and practice_status is None
    ):
        return {}

    parts = []

    if status:
        parts.append(
            str(status)
        )

    if injury:
        parts.append(
            str(injury)
        )

    if practice_status:
        parts.append(
            str(practice_status)
        )

    return {
        "nflverse_injury_status": (
            " | ".join(parts)
            if parts
            else None
        ),
    }


def get_sleeper_player_data(
    candidate,
    sleeper_name_lookup,
):
    normalized_name = (
        normalize_name(
            candidate.get(
                "name",
                "",
            )
        )
    )

    matches = (
        sleeper_name_lookup.get(
            normalized_name,
            [],
        )
    )

    if not matches:
        return {}

    candidate_team = normalize_team(
        candidate.get("team")
    )

    candidate_position = (
        normalize_position(
            candidate.get(
                "position"
            )
        )
    )

    filtered = []

    for player in matches:
        sleeper_team = normalize_team(
            player.get("team")
        )

        sleeper_position = (
            normalize_position(
                player.get(
                    "position"
                )
            )
        )

        if (
            candidate_position
            and sleeper_position
            and candidate_position
            != sleeper_position
        ):
            continue

        if (
            candidate_team
            and sleeper_team
            and candidate_team
            != sleeper_team
        ):
            continue

        filtered.append(
            player
        )

    if filtered:
        player = filtered[0]

    else:
        player = matches[0]

    injury_status = player.get(
        "injury_status"
    )

    roster_status = player.get(
        "status"
    )

    depth_order = player.get(
        "depth_chart_order"
    )

    return {
        "sleeper_id": (
            player.get(
                "player_id"
            )
        ),
        "current_team": (
            normalize_team(
                player.get(
                    "team"
                )
            )
            or candidate_team
        ),
        "current_roster_status": (
            roster_status
        ),
        "current_injury_status": (
            injury_status
        ),
        "current_injury_body_part": (
            player.get(
                "injury_body_part"
            )
        ),
        "current_injury_notes": (
            player.get(
                "injury_notes"
            )
        ),
        "current_injury_start_date": (
            player.get(
                "injury_start_date"
            )
        ),
        "current_practice_participation": (
            player.get(
                "practice_participation"
            )
        ),
        "current_age": (
            player.get(
                "age"
            )
        ),
        "current_years_exp": (
            player.get(
                "years_exp"
            )
        ),
        "sleeper_depth_chart_position": (
            player.get(
                "depth_chart_position"
            )
        ),
        "sleeper_depth_chart_order": (
            depth_order
        ),
        "current_suspension_status": (
            "Suspended"
            if (
                str(
                    injury_status
                    or ""
                ).upper()
                in {
                    "SUS",
                    "SUSPENDED",
                }
                or str(
                    roster_status
                    or ""
                ).upper()
                in {
                    "SUS",
                    "SUSPENDED",
                }
            )
            else None
        ),
    }


def retrieve_live_player_data(
    candidates,
    live_datasets,
):
    depth_lookup = (
        live_datasets.get(
            "depth_lookup",
            {},
        )
    )

    injury_rows = (
        live_datasets.get(
            "injury_rows",
            [],
        )
    )

    sleeper_name_lookup = (
        live_datasets.get(
            "sleeper_name_lookup",
            {},
        )
    )

    output = {}

    for candidate in candidates:
        if (
            candidate.get(
                "record_type"
            )
            == "team_defense"
        ):
            continue

        position = normalize_position(
            candidate.get(
                "position"
            )
        )

        if (
            position
            not in OFFENSIVE_POSITIONS
        ):
            continue

        normalized_name = (
            normalize_name(
                candidate.get(
                    "name",
                    "",
                )
            )
        )

        player_data = {
            "current_depth_chart_position": None,
            "current_depth_chart_role": None,
            "current_injury_status": None,
            "current_injury_body_part": None,
            "current_injury_notes": None,
            "current_injury_start_date": None,
            "current_practice_participation": None,
            "current_suspension_status": None,
            "current_roster_status": None,
            "current_team": normalize_team(
                candidate.get(
                    "team"
                )
            ),
            "current_age": None,
            "current_years_exp": None,
            "sleeper_id": None,
        }

        player_data.update(
            get_depth_chart_data(
                candidate,
                depth_lookup,
            )
        )

        player_data.update(
            get_injury_data(
                candidate,
                injury_rows,
            )
        )

        sleeper_data = (
            get_sleeper_player_data(
                candidate,
                sleeper_name_lookup,
            )
        )

        player_data.update(
            sleeper_data
        )

        if (
            player_data.get(
                "current_injury_status"
            )
            is None
        ):
            player_data[
                "current_injury_status"
            ] = player_data.get(
                "nflverse_injury_status"
            )

        sleeper_order = (
            player_data.get(
                "sleeper_depth_chart_order"
            )
        )

        if (
            player_data.get(
                "current_depth_chart_position"
            )
            is None
            and sleeper_order
            is not None
        ):
            player_data[
                "current_depth_chart_position"
            ] = sleeper_order

            player_data[
                "current_depth_chart_role"
            ] = (
                f"{position}"
                f"{sleeper_order}"
            )

        output[
            normalized_name
        ] = player_data

    return output