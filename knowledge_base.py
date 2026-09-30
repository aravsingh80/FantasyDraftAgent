import json
from pathlib import Path

from normalize_names import (
    normalize_name,
)


KNOWLEDGE_BASE_FILE = Path(
    "player_knowledge_base.json"
)


NFL_DEFENSES = {
    "ARI": "Arizona Defense",
    "ATL": "Atlanta Defense",
    "BAL": "Baltimore Defense",
    "BUF": "Buffalo Defense",
    "CAR": "Carolina Defense",
    "CHI": "Chicago Defense",
    "CIN": "Cincinnati Defense",
    "CLE": "Cleveland Defense",
    "DAL": "Dallas Defense",
    "DEN": "Denver Defense",
    "DET": "Detroit Defense",
    "GB": "Green Bay Defense",
    "HOU": "Houston Defense",
    "IND": "Indianapolis Defense",
    "JAC": "Jacksonville Defense",
    "KC": "Kansas City Defense",
    "LV": "Las Vegas Defense",
    "LAC": "Los Angeles Chargers Defense",
    "LAR": "Los Angeles Rams Defense",
    "MIA": "Miami Defense",
    "MIN": "Minnesota Defense",
    "NE": "New England Defense",
    "NO": "New Orleans Defense",
    "NYG": "New York Giants Defense",
    "NYJ": "New York Jets Defense",
    "PHI": "Philadelphia Defense",
    "PIT": "Pittsburgh Defense",
    "SEA": "Seattle Defense",
    "SF": "San Francisco Defense",
    "TB": "Tampa Bay Defense",
    "TEN": "Tennessee Defense",
    "WAS": "Washington Defense",
}


def build_offensive_record(
    normalized_name,
    player,
):
    return {
        "record_type": "player",
        "name": player["name"],
        "normalized_name": (
            normalized_name
        ),
        "position": (
            player["position"]
        ),
        "team": player["team"],
        "season_history": {},
        "career_ppg": None,
        "games_played": None,
        "possible_games": None,
        "games_played_percentage": None,
        "injury_history": [],
        "suspension_history": [],
        "rookie_season": None,
        "years_in_league": None,
        "age": None,
        "team_pass_rate": None,
        "team_run_rate": None,
        "team_tendencies_by_season": {},
        "bye_week": None,
        "sleeper_id": None,
        "current_depth_chart_position": None,
        "current_depth_chart_role": None,
        "current_injury_status": None,
        "current_suspension_status": None,
        "news": [],
        "dynamic_status_last_updated": None,
    }


def build_defense_record(
    normalized_name,
    player,
):
    return {
        "record_type": (
            "team_defense"
        ),
        "name": player["name"],
        "normalized_name": (
            normalized_name
        ),
        "position": "DST",
        "team": player["team"],
        "news": [],
        "dynamic_status_last_updated": None,
    }


def add_missing_defenses(
    knowledge_base,
):
    existing_teams = {
        record["team"]
        for record in (
            knowledge_base.values()
        )
        if (
            record.get(
                "record_type"
            )
            == "team_defense"
        )
    }

    for team, name in (
        NFL_DEFENSES.items()
    ):
        if team in existing_teams:
            continue

        normalized_name = (
            normalize_name(
                name
            )
        )

        knowledge_base[
            normalized_name
        ] = build_defense_record(
            normalized_name,
            {
                "name": name,
                "team": team,
            },
        )


def build_knowledge_base(
    adp_rank_lookup,
):
    knowledge_base = {}

    for (
        normalized_name,
        player,
    ) in adp_rank_lookup.items():

        if (
            player["position"]
            == "DST"
        ):
            knowledge_base[
                normalized_name
            ] = build_defense_record(
                normalized_name,
                player,
            )

        else:
            knowledge_base[
                normalized_name
            ] = build_offensive_record(
                normalized_name,
                player,
            )

    add_missing_defenses(
        knowledge_base
    )

    return knowledge_base


def save_knowledge_base(
    knowledge_base,
    file_path=KNOWLEDGE_BASE_FILE,
):
    with file_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            knowledge_base,
            file,
            indent=2,
        )


def load_knowledge_base(
    file_path=KNOWLEDGE_BASE_FILE,
):
    with file_path.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(
            file
        )


def update_player_field(
    knowledge_base,
    normalized_name,
    field,
    value,
):
    record = (
        knowledge_base.get(
            normalized_name
        )
    )

    if record is None:
        return False

    record[field] = value

    return True


def get_player_data(
    knowledge_base,
    normalized_name,
):
    return knowledge_base.get(
        normalized_name
    )


def get_candidate_data(
    knowledge_base,
    player_names,
    adp_rank_lookup,
    projection_lookup,
    ecr_lookup,
    normalize_name,
):
    candidates = []

    for player_name in (
        player_names
    ):
        normalized_name = (
            normalize_name(
                player_name
            )
        )

        cached_player = (
            knowledge_base.get(
                normalized_name
            )
        )

        fresh_adp_data = (
            adp_rank_lookup.get(
                normalized_name
            )
        )

        if (
            cached_player is None
            or fresh_adp_data is None
        ):
            continue

        candidate = (
            cached_player.copy()
        )

        candidate["adp"] = (
            fresh_adp_data.get(
                "adp"
            )
        )

        candidate[
            "overall_ranking"
        ] = fresh_adp_data.get(
            "overall_ranking"
        )

        candidate[
            "position_ranking"
        ] = fresh_adp_data.get(
            "position_ranking"
        )

        candidate["team"] = (
            fresh_adp_data.get(
                "team"
            )
            or candidate.get(
                "team"
            )
        )

        candidate["position"] = (
            fresh_adp_data.get(
                "position"
            )
            or candidate.get(
                "position"
            )
        )

        projection = (
            projection_lookup.get(
                normalized_name,
                {},
            )
        )

        candidate[
            "projected_points"
        ] = projection.get(
            "projected_points"
        )

        candidate[
            "projected_position_rank"
        ] = projection.get(
            "projected_position_rank"
        )

        ecr_data = ecr_lookup.get(
            normalized_name,
            {},
        )

        candidate[
            "ecr"
        ] = ecr_data.get(
            "ecr"
        )

        candidate[
            "ecr_sd"
        ] = ecr_data.get(
            "ecr_sd"
        )

        candidate[
            "ecr_best"
        ] = ecr_data.get(
            "ecr_best"
        )

        candidate[
            "ecr_worst"
        ] = ecr_data.get(
            "ecr_worst"
        )

        candidate[
            "ecr_rank_delta"
        ] = ecr_data.get(
            "ecr_rank_delta"
        )

        candidates.append(
            candidate
        )

    return candidates