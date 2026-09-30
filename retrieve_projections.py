from concurrent.futures import (
    ThreadPoolExecutor,
    as_completed,
)
import json
import os
import time
from pathlib import Path

import requests

from normalize_names import (
    normalize_name,
    normalize_team,
)


CURRENT_SEASON = 2026


POSITIONS = [
    "QB",
    "RB",
    "WR",
    "TE",
]


BASE_URL = (
    "https://api.fantasypros.com/"
    "public/v2/json/nfl/"
    "{season}/projections"
)


PROJECTION_CACHE_FILE = Path(
    "fantasypros_api_projection_cache.json"
)


PROJECTION_CACHE_MAX_AGE_SECONDS = (
    6 * 60 * 60
)


MIN_EXPECTED_COUNTS = {
    "QB": 20,
    "RB": 40,
    "WR": 50,
    "TE": 20,
}


def get_api_key():
    api_key = os.getenv(
        "FANTASYPROS_API_KEY"
    )

    if not api_key:
        raise ValueError(
            "FANTASYPROS_API_KEY "
            "environment variable "
            "is not set."
        )

    return api_key


def projection_cache_is_fresh():
    if not PROJECTION_CACHE_FILE.exists():
        return False

    cache_age = (
        time.time()
        - PROJECTION_CACHE_FILE.stat().st_mtime
    )

    return (
        cache_age
        < PROJECTION_CACHE_MAX_AGE_SECONDS
    )


def load_projection_cache():
    with PROJECTION_CACHE_FILE.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(
            file
        )


def save_projection_cache(
    projection_lookup,
):
    with PROJECTION_CACHE_FILE.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            projection_lookup,
            file,
            indent=2,
        )


def convert_to_float(
    value,
):
    if value is None:
        return None

    try:
        return float(
            value
        )

    except (
        TypeError,
        ValueError,
    ):
        return None


def get_points_from_stats(
    stats,
):
    if not stats:
        return None

    if isinstance(
        stats,
        dict,
    ):
        stats = [
            stats
        ]

    if not isinstance(
        stats,
        list,
    ):
        return None

    for stat_line in stats:
        if not isinstance(
            stat_line,
            dict,
        ):
            continue

        points_ppr = (
            convert_to_float(
                stat_line.get(
                    "points_ppr"
                )
            )
        )

        if points_ppr is not None:
            return points_ppr

    for stat_line in stats:
        if not isinstance(
            stat_line,
            dict,
        ):
            continue

        points = (
            convert_to_float(
                stat_line.get(
                    "points"
                )
            )
        )

        if points is not None:
            return points

    return None


def get_projected_games(
    stats,
):
    if not stats:
        return None

    if isinstance(
        stats,
        dict,
    ):
        stats = [
            stats
        ]

    if not isinstance(
        stats,
        list,
    ):
        return None

    possible_game_fields = [
        "games",
        "g",
        "gp",
        "games_played",
    ]

    for stat_line in stats:
        if not isinstance(
            stat_line,
            dict,
        ):
            continue

        for field in (
            possible_game_fields
        ):
            games = (
                convert_to_float(
                    stat_line.get(
                        field
                    )
                )
            )

            if (
                games is not None
                and games > 0
            ):
                return games

    return None


def fetch_position_projections(
    position,
    season=CURRENT_SEASON,
):
    api_key = get_api_key()

    url = BASE_URL.format(
        season=season
    )

    response = requests.get(
        url,
        params={
            "position": position,
            "week": 0,
        },
        headers={
            "x-api-key": (
                api_key
            ),
            "Accept": (
                "application/json"
            ),
        },
        timeout=30,
    )

    response.raise_for_status()

    data = response.json()

    players = data.get(
        "players",
        []
    )

    projections = []

    for player in players:
        if not isinstance(
            player,
            dict,
        ):
            continue

        name = (
            player.get(
                "name"
            )
        )

        if not name:
            continue

        player_position = (
            player.get(
                "position_id"
            )
            or player.get(
                "position"
            )
            or position
        )

        if (
            str(
                player_position
            ).upper()
            != position
        ):
            continue

        normalized_name = (
            normalize_name(
                name
            )
        )

        if not normalized_name:
            continue

        stats = player.get(
            "stats",
            []
        )

        projected_points = (
            get_points_from_stats(
                stats
            )
        )

        if (
            projected_points
            is None
        ):
            continue

        projected_games = (
            get_projected_games(
                stats
            )
        )

        projected_ppg = None

        if (
            projected_games
            is not None
            and projected_games > 0
        ):
            projected_ppg = (
                projected_points
                / projected_games
            )

        projections.append({
            "fantasypros_id": (
                player.get(
                    "fpid"
                )
            ),
            "name": name,
            "normalized_name": (
                normalized_name
            ),
            "position": position,
            "team": (
                normalize_team(
                    player.get(
                        "team_id"
                    )
                )
            ),
            "projected_points": (
                projected_points
            ),
            "projected_ppg": (
                projected_ppg
            ),
            "projected_games": (
                projected_games
            ),
        })

    projections.sort(
        key=lambda player: (
            player[
                "projected_points"
            ]
        ),
        reverse=True,
    )

    for (
        index,
        player,
    ) in enumerate(
        projections,
        start=1,
    ):
        player[
            "projected_position_rank"
        ] = index

    return projections


def retrieve_all_projections():
    projections_by_position = {}

    with ThreadPoolExecutor(
        max_workers=4
    ) as executor:

        futures = {
            executor.submit(
                fetch_position_projections,
                position,
            ): position
            for position in POSITIONS
        }

        for future in as_completed(
            futures
        ):
            position = (
                futures[
                    future
                ]
            )

            try:
                projections = (
                    future.result()
                )

            except Exception as error:
                print(
                    f"FantasyPros API "
                    f"projection retrieval "
                    f"failed for "
                    f"{position}: "
                    f"{error}"
                )

                projections = []

            projections_by_position[
                position
            ] = projections

    return projections_by_position


def validate_projection_counts(
    projections_by_position,
):
    valid = True

    print(
        "\nFantasyPros API "
        "projection coverage:"
    )

    for position in POSITIONS:
        projections = (
            projections_by_position.get(
                position,
                [],
            )
        )

        count = len(
            projections
        )

        minimum = (
            MIN_EXPECTED_COUNTS[
                position
            ]
        )

        status = (
            "OK"
            if count >= minimum
            else "WARNING"
        )

        print(
            f"{position}: "
            f"{count} players "
            f"[{status}]"
        )

        if count < minimum:
            valid = False

    return valid


def build_projection_lookup(
    projections_by_position,
):
    projection_lookup = {}

    for position in POSITIONS:
        projections = (
            projections_by_position.get(
                position,
                [],
            )
        )

        for player in projections:
            normalized_name = (
                player[
                    "normalized_name"
                ]
            )

            projection_lookup[
                normalized_name
            ] = player

    return projection_lookup


def print_projection_examples(
    projection_lookup,
):
    test_players = [
        "Jaxon Smith-Njigba",
        "Chase Brown",
        "Dak Prescott",
        "Dallas Goedert",
        "Alec Pierce",
    ]

    print(
        "\nProjection examples:"
    )

    for player_name in (
        test_players
    ):
        normalized_name = (
            normalize_name(
                player_name
            )
        )

        projection = (
            projection_lookup.get(
                normalized_name
            )
        )

        if projection is None:
            print(
                f"{player_name}: "
                f"NOT FOUND"
            )

            continue

        print(
            f"{player_name}: "
            f"{projection.get('projected_points')} "
            f"PPR points, "
            f"position rank "
            f"{projection.get('projected_position_rank')}"
        )


def get_projection_lookup(
    force_refresh=False,
):
    if (
        not force_refresh
        and projection_cache_is_fresh()
    ):
        projection_lookup = (
            load_projection_cache()
        )

        print(
            "Using cached "
            "FantasyPros API "
            "projections."
        )

        print(
            f"Projection cache contains "
            f"{len(projection_lookup)} "
            f"players."
        )

        return (
            projection_lookup
        )

    projections_by_position = (
        retrieve_all_projections()
    )

    valid = (
        validate_projection_counts(
            projections_by_position
        )
    )

    projection_lookup = (
        build_projection_lookup(
            projections_by_position
        )
    )

    if valid:
        save_projection_cache(
            projection_lookup
        )

    else:
        print(
            "\nWARNING: FantasyPros "
            "API projection coverage "
            "looks incomplete."
        )

        if (
            PROJECTION_CACHE_FILE.exists()
        ):
            print(
                "Using existing "
                "FantasyPros API "
                "projection cache."
            )

            return (
                load_projection_cache()
            )

    print(
        f"\nLoaded FantasyPros "
        f"projections for "
        f"{len(projection_lookup)} "
        f"players."
    )

    print_projection_examples(
        projection_lookup
    )

    return (
        projection_lookup
    )