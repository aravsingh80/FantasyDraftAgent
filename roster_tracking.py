from normalize_names import (
    normalize_name,
    normalize_position,
    normalize_team,
)


ROSTER_POSITIONS = {
    "QB",
    "RB",
    "WR",
    "TE",
    "K",
    "DST",
}


DEFENSE_NAME_TO_TEAM = {
    "arizona cardinals": "ARI",
    "atlanta falcons": "ATL",
    "baltimore ravens": "BAL",
    "buffalo bills": "BUF",
    "carolina panthers": "CAR",
    "chicago bears": "CHI",
    "cincinnati bengals": "CIN",
    "cleveland browns": "CLE",
    "dallas cowboys": "DAL",
    "denver broncos": "DEN",
    "detroit lions": "DET",
    "green bay packers": "GB",
    "houston texans": "HOU",
    "indianapolis colts": "IND",
    "jacksonville jaguars": "JAC",
    "kansas city chiefs": "KC",
    "las vegas raiders": "LV",
    "los angeles chargers": "LAC",
    "los angeles rams": "LAR",
    "miami dolphins": "MIA",
    "minnesota vikings": "MIN",
    "new england patriots": "NE",
    "new orleans saints": "NO",
    "new york giants": "NYG",
    "new york jets": "NYJ",
    "philadelphia eagles": "PHI",
    "pittsburgh steelers": "PIT",
    "san francisco 49ers": "SF",
    "seattle seahawks": "SEA",
    "tampa bay buccaneers": "TB",
    "tennessee titans": "TEN",
    "washington commanders": "WAS",
}


def build_empty_roster():
    return {
        "QB": [],
        "RB": [],
        "WR": [],
        "TE": [],
        "K": [],
        "DST": [],
    }


def build_empty_draft_history():
    return []


def get_pick_player_name(
    pick,
):
    metadata = pick.get(
        "metadata",
        {},
    )

    first_name = str(
        metadata.get(
            "first_name",
            "",
        )
        or ""
    ).strip()

    last_name = str(
        metadata.get(
            "last_name",
            "",
        )
        or ""
    ).strip()

    full_name = (
        f"{first_name} "
        f"{last_name}"
    ).strip()

    if full_name:
        return full_name

    return (
        metadata.get(
            "player_name"
        )
        or metadata.get(
            "name"
        )
        or ""
    )


def get_defense_team(
    player_name,
):
    return (
        DEFENSE_NAME_TO_TEAM.get(
            normalize_name(
                player_name
            )
        )
    )


def find_defense_data(
    team,
    adp_rank_lookup,
):
    team = normalize_team(
        team
    )

    for player_data in (
        adp_rank_lookup.values()
    ):
        if (
            player_data.get(
                "position"
            )
            == "DST"
            and normalize_team(
                player_data.get(
                    "team"
                )
            )
            == team
        ):
            return player_data

    return None


def get_pick_position(
    pick,
    adp_rank_lookup,
):
    player_name = (
        get_pick_player_name(
            pick
        )
    )

    normalized_name = (
        normalize_name(
            player_name
        )
    )

    player_data = (
        adp_rank_lookup.get(
            normalized_name
        )
    )

    if player_data is not None:
        return normalize_position(
            player_data.get(
                "position"
            )
        )

    defense_team = (
        get_defense_team(
            player_name
        )
    )

    if defense_team:
        defense_data = (
            find_defense_data(
                defense_team,
                adp_rank_lookup,
            )
        )

        if defense_data:
            return "DST"

    metadata = pick.get(
        "metadata",
        {},
    )

    position = (
        metadata.get(
            "position"
        )
        or metadata.get(
            "player_position"
        )
    )

    return normalize_position(
        position
    )


def is_my_pick(
    pick,
    my_draft_slot,
):
    draft_slot = pick.get(
        "draft_slot"
    )

    if draft_slot is None:
        return False

    try:
        return (
            int(draft_slot)
            == int(
                my_draft_slot
            )
        )

    except (
        TypeError,
        ValueError,
    ):
        return False


def player_already_rostered(
    my_roster,
    player_name,
):
    target_name = (
        normalize_name(
            player_name
        )
    )

    for players in (
        my_roster.values()
    ):
        for existing_player in players:
            if (
                normalize_name(
                    existing_player
                )
                == target_name
            ):
                return True

    return False


def update_my_roster(
    my_roster,
    draft_history,
    pick,
    my_draft_slot,
    adp_rank_lookup,
):
    if not is_my_pick(
        pick,
        my_draft_slot,
    ):
        return (
            my_roster,
            draft_history,
        )

    player_name = (
        get_pick_player_name(
            pick
        )
    )

    if not player_name:
        return (
            my_roster,
            draft_history,
        )

    if player_already_rostered(
        my_roster,
        player_name,
    ):
        return (
            my_roster,
            draft_history,
        )

    position = (
        get_pick_position(
            pick,
            adp_rank_lookup,
        )
    )

    if (
        position
        not in ROSTER_POSITIONS
    ):
        return (
            my_roster,
            draft_history,
        )

    my_roster[
        position
    ].append(
        player_name
    )

    draft_history.append({
        "name": player_name,
        "position": position,
        "pick_no": pick.get(
            "pick_no"
        ),
    })

    return (
        my_roster,
        draft_history,
    )