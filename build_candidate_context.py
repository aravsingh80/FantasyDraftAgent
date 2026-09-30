from normalize_names import (
    normalize_name,
)


FLEX_POSITIONS = {
    "RB",
    "WR",
    "TE",
}


SUPERFLEX_POSITIONS = {
    "QB",
    "RB",
    "WR",
    "TE",
}


CORE_POSITIONS = {
    "QB",
    "RB",
    "WR",
    "TE",
}


def get_recent_ppg(
    season_history,
):
    if not season_history:
        return []

    seasons = sorted(
        season_history.keys(),
        key=int,
    )

    recent_seasons = seasons[-3:]

    return [
        season_history[season]["ppg"]
        for season in recent_seasons
        if season_history[
            season
        ].get("ppg") is not None
    ]


def get_performance_trend(
    recent_ppg,
):
    if len(recent_ppg) < 2:
        return "unknown"

    increases = 0
    decreases = 0

    for index in range(
        1,
        len(recent_ppg),
    ):
        difference = (
            recent_ppg[index]
            - recent_ppg[
                index - 1
            ]
        )

        if difference > 0.5:
            increases += 1

        elif difference < -0.5:
            decreases += 1

    if (
        increases > 0
        and decreases == 0
    ):
        return "improving"

    if (
        decreases > 0
        and increases == 0
    ):
        return "declining"

    return "mixed_or_stable"


def get_availability_level(
    games_played_percentage,
):
    if games_played_percentage is None:
        return "unknown"

    if games_played_percentage >= 0.9:
        return "high"

    if games_played_percentage >= 0.75:
        return "moderate"

    return "low"


def get_current_status_category(
    injury_status,
    suspension_status,
    roster_status,
):
    if suspension_status:
        return "suspended"

    normalized_roster_status = (
        str(roster_status)
        .strip()
        .upper()
        if roster_status
        else None
    )

    major_roster_statuses = {
        "PUP",
        "IR",
        "NFI",
        "RES",
        "OUT",
    }

    concern_roster_statuses = {
        "DNR",
    }

    if (
        normalized_roster_status
        in major_roster_statuses
    ):
        return "major_concern"

    if (
        normalized_roster_status
        in concern_roster_statuses
    ):
        return "concern"

    if injury_status is None:
        return "clear"

    status = str(
        injury_status
    ).lower()

    if (
        "out" in status
        or "injured reserve" in status
        or "pup" in status
        or "physically unable" in status
        or "non-football injury" in status
    ):
        return "major_concern"

    if "doubtful" in status:
        return "concern"

    if "questionable" in status:
        return "minor_concern"

    return "unknown"


def get_role_quality(
    position,
    depth_chart_role,
):
    if depth_chart_role is None:
        return "unknown"

    role = str(
        depth_chart_role
    ).upper()

    position = str(
        position
    ).upper()

    if role == f"{position}1":
        return "starter"

    if role == f"{position}2":
        return "backup"

    if (
        role.startswith(
            position
        )
        and role[-1:].isdigit()
    ):
        depth_number = int(
            role[-1]
        )

        if depth_number >= 3:
            return "depth"

    return "unknown"


def get_roster_counts(
    my_roster,
):
    return {
        position: len(players)
        for position, players
        in my_roster.items()
    }


def get_last_skill_position_pick(
    draft_history,
):
    if not draft_history:
        return None

    for pick in reversed(
        draft_history
    ):
        position = pick.get(
            "position"
        )

        if position in {
            "RB",
            "WR",
        }:
            return position

    return None


def get_balanced_preferred_position(
    draft_history,
):
    last_position = (
        get_last_skill_position_pick(
            draft_history
        )
    )

    if last_position == "RB":
        return "WR"

    if last_position == "WR":
        return "RB"

    return None


def get_starter_context(
    my_roster,
    starter_requirements,
):
    roster_counts = (
        get_roster_counts(
            my_roster
        )
    )

    starter_context = {}

    for position in [
        "QB",
        "RB",
        "WR",
        "TE",
        "DST",
        "K",
    ]:
        required = (
            starter_requirements.get(
                position,
                0,
            )
        )

        rostered = (
            roster_counts.get(
                position,
                0,
            )
        )

        filled = min(
            rostered,
            required,
        )

        starter_context[
            position
        ] = {
            "rostered": rostered,
            "starter_requirement": required,
            "starters_filled": filled,
            "starter_slots_remaining": max(
                required - filled,
                0,
            ),
        }

    flex_surplus = {
        position: max(
            roster_counts.get(
                position,
                0,
            )
            - starter_requirements.get(
                position,
                0,
            ),
            0,
        )
        for position in FLEX_POSITIONS
    }

    flex_eligible_count = sum(
        flex_surplus.values()
    )

    flex_required = (
        starter_requirements.get(
            "FLEX",
            0,
        )
    )

    flex_filled = min(
        flex_eligible_count,
        flex_required,
    )

    starter_context[
        "FLEX"
    ] = {
        "eligible_rostered": (
            flex_eligible_count
        ),
        "starter_requirement": (
            flex_required
        ),
        "starters_filled": (
            flex_filled
        ),
        "starter_slots_remaining": max(
            flex_required
            - flex_filled,
            0,
        ),
    }

    qb_excess = max(
        roster_counts.get(
            "QB",
            0,
        )
        - starter_requirements.get(
            "QB",
            0,
        ),
        0,
    )

    remaining_flex_eligible = max(
        flex_eligible_count
        - flex_filled,
        0,
    )

    superflex_eligible_count = (
        qb_excess
        + remaining_flex_eligible
    )

    superflex_required = (
        starter_requirements.get(
            "SUPER_FLEX",
            0,
        )
    )

    superflex_filled = min(
        superflex_eligible_count,
        superflex_required,
    )

    starter_context[
        "SUPER_FLEX"
    ] = {
        "eligible_rostered": (
            superflex_eligible_count
        ),
        "starter_requirement": (
            superflex_required
        ),
        "starters_filled": (
            superflex_filled
        ),
        "starter_slots_remaining": max(
            superflex_required
            - superflex_filled,
            0,
        ),
    }

    return starter_context


def build_bench_context(
    my_roster,
    starter_requirements,
    draft_history,
):
    """
    Assign actual extra RB/WR/TE picks into FLEX slots
    in draft order, then count what remains as bench.

    This prevents RB3/WR3 from automatically being
    treated as bench when FLEX slots are still open.
    """

    core_remaining = {
        position: (
            starter_requirements.get(
                position,
                0,
            )
        )
        for position in [
            "QB",
            "RB",
            "WR",
            "TE",
        ]
    }

    flex_slots_remaining = (
        starter_requirements.get(
            "FLEX",
            0,
        )
    )

    superflex_slots_remaining = (
        starter_requirements.get(
            "SUPER_FLEX",
            0,
        )
    )

    bench_counts = {
        "QB": 0,
        "RB": 0,
        "WR": 0,
        "TE": 0,
    }

    flex_assignments = []
    superflex_assignments = []
    bench_players = []

    for pick in draft_history:
        position = pick.get(
            "position"
        )

        name = pick.get(
            "name"
        )

        if position not in {
            "QB",
            "RB",
            "WR",
            "TE",
        }:
            continue

        if (
            core_remaining.get(
                position,
                0,
            )
            > 0
        ):
            core_remaining[
                position
            ] -= 1

            continue

        if (
            position
            in FLEX_POSITIONS
            and flex_slots_remaining
            > 0
        ):
            flex_slots_remaining -= 1

            flex_assignments.append({
                "name": name,
                "position": position,
            })

            continue

        if (
            position
            in SUPERFLEX_POSITIONS
            and superflex_slots_remaining
            > 0
        ):
            superflex_slots_remaining -= 1

            superflex_assignments.append({
                "name": name,
                "position": position,
            })

            continue

        bench_counts[
            position
        ] += 1

        bench_players.append({
            "name": name,
            "position": position,
        })

    return {
        "bench_counts": bench_counts,
        "bench_players": bench_players,
        "flex_assignments": (
            flex_assignments
        ),
        "superflex_assignments": (
            superflex_assignments
        ),
        "flex_slots_remaining": (
            flex_slots_remaining
        ),
        "superflex_slots_remaining": (
            superflex_slots_remaining
        ),
    }


def get_candidate_roster_role(
    position,
    starter_context,
):
    position_context = (
        starter_context.get(
            position,
            {},
        )
    )

    if (
        position in CORE_POSITIONS
        and position_context.get(
            "starter_slots_remaining",
            0,
        ) > 0
    ):
        return "core_starter"

    if (
        position in FLEX_POSITIONS
        and starter_context.get(
            "FLEX",
            {},
        ).get(
            "starter_slots_remaining",
            0,
        ) > 0
    ):
        return "flex_starter"

    if (
        position
        in SUPERFLEX_POSITIONS
        and starter_context.get(
            "SUPER_FLEX",
            {},
        ).get(
            "starter_slots_remaining",
            0,
        ) > 0
    ):
        return "superflex_starter"

    if (
        position in {
            "DST",
            "K",
        }
        and position_context.get(
            "starter_slots_remaining",
            0,
        ) > 0
    ):
        return "special_starter"

    return "bench_depth"


def get_candidate_starting_slots(
    position,
    starter_context,
):
    roster_role = (
        get_candidate_roster_role(
            position,
            starter_context,
        )
    )

    if roster_role == "core_starter":
        return [position]

    if roster_role == "flex_starter":
        return ["FLEX"]

    if (
        roster_role
        == "superflex_starter"
    ):
        return ["SUPER_FLEX"]

    if (
        roster_role
        == "special_starter"
    ):
        return [position]

    return []


def get_latest_season_data(
    season_history,
):
    if not season_history:
        return None

    latest_season = max(
        season_history.keys(),
        key=int,
    )

    return {
        "season": int(
            latest_season
        ),
        **season_history[
            latest_season
        ],
    }


def merge_live_data(
    candidate,
    live_data,
):
    merged = candidate.copy()

    if not live_data:
        return merged

    normalized_name = (
        normalize_name(
            candidate.get(
                "name",
                "",
            )
        )
    )

    merged.update(
        live_data.get(
            normalized_name,
            {},
        )
    )

    return merged


def build_player_context(
    candidate,
    starter_context,
    balanced_preferred_position,
):
    season_history = candidate.get(
        "season_history",
        {},
    )

    recent_ppg = get_recent_ppg(
        season_history
    )

    position = candidate.get(
        "position"
    )

    injury_status = candidate.get(
        "current_injury_status"
    )

    suspension_status = candidate.get(
        "current_suspension_status"
    )

    roster_status = candidate.get(
        "current_roster_status"
    )

    depth_chart_role = candidate.get(
        "current_depth_chart_role"
    )

    roster_role = (
        get_candidate_roster_role(
            position,
            starter_context,
        )
    )

    starting_slots = (
        get_candidate_starting_slots(
            position,
            starter_context,
        )
    )

    return {
        "record_type": "player",
        "name": candidate.get(
            "name"
        ),
        "position": position,
        "team": (
            candidate.get(
                "current_team"
            )
            or candidate.get(
                "team"
            )
        ),
        "adp": candidate.get(
            "adp"
        ),
        "overall_ranking": (
            candidate.get(
                "overall_ranking"
            )
        ),
        "position_ranking": (
            candidate.get(
                "position_ranking"
            )
        ),
        "projected_points": (
            candidate.get(
                "projected_points"
            )
        ),
        "projected_position_rank": (
            candidate.get(
                "projected_position_rank"
            )
        ),
        "ecr": candidate.get(
            "ecr"
        ),
        "ecr_sd": candidate.get(
            "ecr_sd"
        ),
        "ecr_best": candidate.get(
            "ecr_best"
        ),
        "ecr_worst": candidate.get(
            "ecr_worst"
        ),
        "ecr_rank_delta": (
            candidate.get(
                "ecr_rank_delta"
            )
        ),
        "career_ppg": candidate.get(
            "career_ppg"
        ),
        "latest_season": (
            get_latest_season_data(
                season_history
            )
        ),
        "recent_ppg": recent_ppg,
        "performance_trend": (
            get_performance_trend(
                recent_ppg
            )
        ),
        "games_played": candidate.get(
            "games_played"
        ),
        "possible_games": candidate.get(
            "possible_games"
        ),
        "games_played_percentage": (
            candidate.get(
                "games_played_percentage"
            )
        ),
        "availability_level": (
            get_availability_level(
                candidate.get(
                    "games_played_percentage"
                )
            )
        ),
        "injury_history": candidate.get(
            "injury_history",
            [],
        ),
        "suspension_history": candidate.get(
            "suspension_history",
            [],
        ),
        "age": (
            candidate.get(
                "current_age"
            )
            if candidate.get(
                "current_age"
            ) is not None
            else candidate.get(
                "age"
            )
        ),
        "years_in_league": (
            candidate.get(
                "current_years_exp"
            )
            if candidate.get(
                "current_years_exp"
            ) is not None
            else candidate.get(
                "years_in_league"
            )
        ),
        "sleeper_id": candidate.get(
            "sleeper_id"
        ),
        "team_pass_rate": candidate.get(
            "team_pass_rate"
        ),
        "team_run_rate": candidate.get(
            "team_run_rate"
        ),
        "current_depth_chart_role": (
            depth_chart_role
        ),
        "role_quality": (
            get_role_quality(
                position,
                depth_chart_role,
            )
        ),
        "current_injury_status": (
            injury_status
        ),
        "current_injury_body_part": (
            candidate.get(
                "current_injury_body_part"
            )
        ),
        "current_injury_notes": (
            candidate.get(
                "current_injury_notes"
            )
        ),
        "current_injury_start_date": (
            candidate.get(
                "current_injury_start_date"
            )
        ),
        "current_practice_participation": (
            candidate.get(
                "current_practice_participation"
            )
        ),
        "current_suspension_status": (
            suspension_status
        ),
        "current_roster_status": (
            roster_status
        ),
        "current_status_category": (
            get_current_status_category(
                injury_status,
                suspension_status,
                roster_status,
            )
        ),
        "news": candidate.get(
            "news",
            [],
        ),
        "roster_role": roster_role,
        "fills_unfilled_starter": bool(
            starting_slots
        ),
        "can_fill_starting_slots": (
            starting_slots
        ),
        "starter_position_status": (
            starter_context.get(
                position
            )
        ),
        "matches_balanced_alternation": (
            position
            == balanced_preferred_position
        ),
    }


def build_defense_context(
    candidate,
    starter_context,
):
    roster_role = (
        get_candidate_roster_role(
            "DST",
            starter_context,
        )
    )

    return {
        "record_type": "team_defense",
        "name": candidate.get(
            "name"
        ),
        "position": "DST",
        "team": candidate.get(
            "team"
        ),
        "adp": candidate.get(
            "adp"
        ),
        "overall_ranking": (
            candidate.get(
                "overall_ranking"
            )
        ),
        "position_ranking": (
            candidate.get(
                "position_ranking"
            )
        ),
        "news": candidate.get(
            "news",
            [],
        ),
        "roster_role": roster_role,
        "fills_unfilled_starter": (
            roster_role
            == "special_starter"
        ),
    }


def build_candidate_context(
    candidates,
    my_roster,
    starter_requirements=None,
    live_data=None,
    draft_history=None,
):
    if starter_requirements is None:
        starter_requirements = {
            "QB": 1,
            "RB": 2,
            "WR": 2,
            "TE": 1,
            "FLEX": 1,
            "SUPER_FLEX": 0,
            "DST": 1,
            "K": 1,
        }

    if draft_history is None:
        draft_history = []

    starter_context = (
        get_starter_context(
            my_roster,
            starter_requirements,
        )
    )

    bench_context = (
        build_bench_context(
            my_roster,
            starter_requirements,
            draft_history,
        )
    )

    balanced_preferred_position = (
        get_balanced_preferred_position(
            draft_history
        )
    )

    candidate_contexts = []

    for candidate in candidates:
        candidate = merge_live_data(
            candidate,
            live_data,
        )

        if (
            candidate.get(
                "record_type"
            )
            == "team_defense"
        ):
            context = (
                build_defense_context(
                    candidate,
                    starter_context,
                )
            )

        else:
            context = (
                build_player_context(
                    candidate,
                    starter_context,
                    balanced_preferred_position,
                )
            )

        candidate_contexts.append(
            context
        )

    return {
        "starter_context": (
            starter_context
        ),
        "bench_context": (
            bench_context
        ),
        "balanced_preferred_position": (
            balanced_preferred_position
        ),
        "candidates": (
            candidate_contexts
        ),
    }