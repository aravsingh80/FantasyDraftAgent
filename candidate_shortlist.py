MARKET_TIER_WIDTH = 6.0
CROSS_TIER_MAX_ADP_GAP = 12.0
CROSS_TIER_ECR_ADVANTAGE = 5.0
CROSS_TIER_PROJECTION_ADVANTAGE = 0.05
BENCH_BALANCE_OVERRIDE_ADP_GAP = 20.0

QB_TE_HARD_ROUND = 7

BALANCED_QB_TE_SOFT_ROUND = 5
HEAVY_QB_TE_SOFT_ROUND = 6

DST_K_MIN_ROUND = 13

PROJECTION_SIMILAR_PERCENT = 0.03

ECR_SIMILAR_DIFFERENCE = 2.0

BACKUP_QB_MIN_ROUND = 11

#
# Global ranking adjustments.
#
# ADP remains the market baseline, but these signals
# can move a player earlier/later in "pick-equivalent"
# terms. This removes hard ADP tier boundaries without
# making ADP irrelevant.
#
ECR_ADVANTAGE_ADJUSTMENT = -10.0
ECR_DISADVANTAGE_ADJUSTMENT = 10.0

ECR_HIGH_CONFIDENCE_ADJUSTMENT = -2.0
ECR_LOW_CONFIDENCE_ADJUSTMENT = 2.0

STARTER_ROLE_ADJUSTMENT = -6.0
BACKUP_ROLE_ADJUSTMENT = 5.0
DEPTH_ROLE_ADJUSTMENT = 8.0

IMPROVING_TREND_ADJUSTMENT = -4.0
UNKNOWN_TREND_ADJUSTMENT = 1.0
DECLINING_TREND_ADJUSTMENT = 5.0

HIGH_AVAILABILITY_ADJUSTMENT = -2.0
UNKNOWN_AVAILABILITY_ADJUSTMENT = 1.0
LOW_AVAILABILITY_ADJUSTMENT = 4.0

BENCH_NEED_ADJUSTMENT = -5.0
BENCH_EXCESS_ADJUSTMENT = 2.0

BALANCED_MATCH_ADJUSTMENT = -3.0

HEAVY_PRIMARY_ADJUSTMENT = -5.0
HEAVY_EXCESS_ADJUSTMENT = 2.0

#
# Projection is intentionally the weakest ranking
# input because coverage is incomplete.
#
PROJECTION_ADVANTAGE_ADJUSTMENT = -1.0
PROJECTION_DISADVANTAGE_ADJUSTMENT = 1.0

#
# Major injury/status protection.
#
MAJOR_CONCERN_HEALTHY_OVERRIDE_GAP = 25.0

#
# Expert-consensus confidence.
#
ECR_LOW_SD = 4.0
ECR_HIGH_SD = 10.0

ECR_NARROW_RANGE = 10.0
ECR_WIDE_RANGE = 25.0

ECR_MOVEMENT_THRESHOLD = 3.0


STATUS_PRIORITY = {
    "clear": 0,
    "unknown": 1,
    "minor_concern": 2,
    "concern": 3,
    "major_concern": 4,
    "suspended": 5,
}


ROSTER_ROLE_PRIORITY = {
    "core_starter": 0,
    "superflex_starter": 1,
    "flex_starter": 2,
    "bench_depth": 3,
    "special_starter": 4,
}


ROLE_PRIORITY = {
    "starter": 0,
    "unknown": 1,
    "backup": 2,
    "depth": 3,
}


TREND_PRIORITY = {
    "improving": 0,
    "mixed_or_stable": 1,
    "unknown": 2,
    "declining": 3,
}


AVAILABILITY_PRIORITY = {
    "high": 0,
    "moderate": 1,
    "unknown": 2,
    "low": 3,
}


PROJECTION_PRIORITY = {
    "advantage": 0,
    "similar": 1,
    "unknown": 1,
    "disadvantage": 2,
}


ECR_PRIORITY = {
    "advantage": 0,
    "similar": 1,
    "unknown": 1,
    "disadvantage": 2,
}


ECR_CONFIDENCE_PRIORITY = {
    "high": 0,
    "normal": 1,
    "unknown": 1,
    "low": 2,
}


VALID_STRATEGIES = {
    "balanced",
    "rb-heavy",
    "wr-heavy",
}


def get_adp(
    candidate,
):
    adp = candidate.get(
        "adp"
    )

    if adp is None:
        return float("inf")

    return float(adp)


def get_rostered_count(
    candidate_context,
    position,
):
    return (
        candidate_context
        .get(
            "starter_context",
            {},
        )
        .get(
            position,
            {},
        )
        .get(
            "rostered",
            0,
        )
    )


def get_starter_requirement(
    candidate_context,
    position,
):
    return (
        candidate_context
        .get(
            "starter_context",
            {},
        )
        .get(
            position,
            {},
        )
        .get(
            "starter_requirement",
            0,
        )
    )


def get_starter_slots_remaining(
    candidate_context,
    position,
):
    return (
        candidate_context
        .get(
            "starter_context",
            {},
        )
        .get(
            position,
            {},
        )
        .get(
            "starter_slots_remaining",
            0,
        )
    )


def get_bench_count(
    candidate_context,
    position,
):
    return (
        candidate_context
        .get(
            "bench_context",
            {},
        )
        .get(
            "bench_counts",
            {},
        )
        .get(
            position,
            0,
        )
    )


def is_superflex(
    candidate_context,
):
    return (
        candidate_context
        .get(
            "starter_context",
            {},
        )
        .get(
            "SUPER_FLEX",
            {},
        )
        .get(
            "starter_requirement",
            0,
        )
        > 0
    )


def get_missing_core_positions(
    candidate_context,
):
    missing = set()

    for position in [
        "QB",
        "RB",
        "WR",
        "TE",
    ]:
        if (
            get_starter_slots_remaining(
                candidate_context,
                position,
            )
            > 0
        ):
            missing.add(
                position
            )

    return missing


def get_missing_qb_te(
    candidate_context,
):
    missing = set()

    for position in [
        "QB",
        "TE",
    ]:
        if (
            get_starter_slots_remaining(
                candidate_context,
                position,
            )
            > 0
        ):
            missing.add(
                position
            )

    return missing


def get_missing_special_positions(
    candidate_context,
):
    missing = set()

    for position in [
        "DST",
        "K",
    ]:
        requirement = (
            get_starter_requirement(
                candidate_context,
                position,
            )
        )

        rostered = (
            get_rostered_count(
                candidate_context,
                position,
            )
        )

        if (
            requirement > 0
            and rostered < requirement
        ):
            missing.add(
                position
            )

    return missing


#
# --------------------------------------------------
# BENCH BALANCE
# --------------------------------------------------
#


def get_desired_bench_position(
    candidate_context,
    strategy,
):
    """
    Returns the RB/WR position that should receive
    reserve-depth preference right now.

    This only uses TRUE bench counts generated after
    core + FLEX/SUPERFLEX assignments.
    """

    rb_bench = get_bench_count(
        candidate_context,
        "RB",
    )

    wr_bench = get_bench_count(
        candidate_context,
        "WR",
    )

    if strategy == "balanced":

        #
        # At least one true RB reserve before
        # accumulating WR reserves.
        #
        if (
            rb_bench == 0
            and wr_bench >= 1
        ):
            return "RB"

        if (
            wr_bench == 0
            and rb_bench >= 2
        ):
            return "WR"

        #
        # Never let Balanced drift more than
        # one true reserve in either direction.
        #
        if (
            wr_bench
            - rb_bench
            >= 1
        ):
            return "RB"

        if (
            rb_bench
            - wr_bench
            >= 1
        ):
            return "WR"

        return None

    if strategy == "rb-heavy":

        #
        # RB-heavy may carry roughly two more
        # RB reserves than WR reserves.
        #
        if wr_bench == 0:
            return "WR"

        if (
            rb_bench
            < wr_bench + 2
        ):
            return "RB"

        return None

    if strategy == "wr-heavy":

        #
        # WR-heavy mirrors RB-heavy, but still
        # requires at least one RB reserve.
        #
        if rb_bench == 0:
            return "RB"

        if (
            wr_bench
            < rb_bench + 2
        ):
            return "WR"

        return None

    return None


def get_bench_balance_priority(
    candidate,
    candidate_context,
    strategy,
):
    if (
        candidate.get(
            "roster_role"
        )
        != "bench_depth"
    ):
        return 1

    position = candidate.get(
        "position"
    )

    if position not in {
        "RB",
        "WR",
    }:
        return 1

    desired_position = (
        get_desired_bench_position(
            candidate_context,
            strategy,
        )
    )

    if desired_position is None:
        return 1

    if position == desired_position:
        return 0

    return 2


def apply_bench_balance_override(
    ordered,
    candidate_context,
    strategy,
):
    """
    This is the important new piece.

    The old bench rule only worked WITHIN an ADP tier.
    Now a needed RB/WR reserve can move across nearby
    tiers when the roster is becoming unbalanced.
    """

    if not ordered:
        return ordered

    desired_position = (
        get_desired_bench_position(
            candidate_context,
            strategy,
        )
    )

    if desired_position is None:
        return ordered

    top_candidate = ordered[0]

    #
    # Do not override unfinished starters.
    #
    if (
        top_candidate.get(
            "roster_role"
        )
        != "bench_depth"
    ):
        return ordered

    if (
        top_candidate.get(
            "position"
        )
        == desired_position
    ):
        return ordered

    top_adp = get_adp(
        top_candidate
    )

    for index in range(
        1,
        len(ordered),
    ):
        candidate = ordered[
            index
        ]

        if (
            candidate.get(
                "roster_role"
            )
            != "bench_depth"
        ):
            continue

        if (
            candidate.get(
                "position"
            )
            != desired_position
        ):
            continue

        #
        # Do not force an injured/PUP option
        # merely for roster balance.
        #
        status = candidate.get(
            "current_status_category",
            "unknown",
        )

        if status in {
            "major_concern",
            "suspended",
        }:
            continue

        candidate_adp = get_adp(
            candidate
        )

        if (
            top_adp == float("inf")
            or candidate_adp
            == float("inf")
        ):
            continue

        adp_gap = (
            candidate_adp
            - top_adp
        )

        #
        # Example:
        # WR ADP 86 vs RB ADP 90
        # → take the needed RB reserve.
        #
        # WR ADP 86 vs RB ADP 135
        # → do not blindly force the RB.
        #
        if (
            adp_gap
            <= BENCH_BALANCE_OVERRIDE_ADP_GAP
        ):
            ordered.insert(
                0,
                ordered.pop(
                    index
                ),
            )

            return ordered

    return ordered


#
# --------------------------------------------------
# ELIGIBILITY / HARD ROSTER RULES
# --------------------------------------------------
#


def candidate_is_eligible(
    candidate,
    candidate_context,
    current_round,
    total_rounds,
):
    position = candidate.get(
        "position"
    )

    missing_core = (
        get_missing_core_positions(
            candidate_context
        )
    )

    missing_qb_te = (
        get_missing_qb_te(
            candidate_context
        )
    )

    superflex = (
        is_superflex(
            candidate_context
        )
    )

    qb_rostered = (
        get_rostered_count(
            candidate_context,
            "QB",
        )
    )

    dst_rostered = (
        get_rostered_count(
            candidate_context,
            "DST",
        )
    )

    dst_required = (
        get_starter_requirement(
            candidate_context,
            "DST",
        )
    )

    k_rostered = (
        get_rostered_count(
            candidate_context,
            "K",
        )
    )

    k_required = (
        get_starter_requirement(
            candidate_context,
            "K",
        )
    )

    special_start_round = max(
        DST_K_MIN_ROUND,
        total_rounds - 2,
    )

    if position == "DST":

        if (
            dst_required <= 0
            or dst_rostered
            >= dst_required
        ):
            return False

        if (
            current_round
            < special_start_round
        ):
            return False

        if missing_qb_te:
            return False

    if position == "K":

        if (
            k_required <= 0
            or k_rostered
            >= k_required
        ):
            return False

        if (
            current_round
            < special_start_round
        ):
            return False

        if missing_qb_te:
            return False

    if (
        position == "QB"
        and not superflex
    ):

        #
        # No QB3 in a normal 1-QB league.
        #
        if qb_rostered >= 2:
            return False

        #
        # QB2 waits until late.
        #
        if (
            qb_rostered >= 1
            and current_round
            < BACKUP_QB_MIN_ROUND
        ):
            return False

        if (
            qb_rostered >= 1
            and missing_core
        ):
            return False

    return True


def apply_hard_qb_te_guardrail(
    candidates,
    candidate_context,
    current_round,
):
    if (
        current_round
        < QB_TE_HARD_ROUND
    ):
        return candidates

    missing_qb_te = (
        get_missing_qb_te(
            candidate_context
        )
    )

    if not missing_qb_te:
        return candidates

    urgent_candidates = [
        candidate
        for candidate in candidates
        if (
            candidate.get(
                "position"
            )
            in missing_qb_te
            and candidate.get(
                "roster_role"
            )
            == "core_starter"
        )
    ]

    if urgent_candidates:
        return urgent_candidates

    return candidates


def apply_endgame_special_guardrail(
    candidates,
    candidate_context,
    current_round,
    total_rounds,
):
    missing_special = (
        get_missing_special_positions(
            candidate_context
        )
    )

    if not missing_special:
        return candidates

    hard_special_round = max(
        total_rounds - 1,
        1,
    )

    if (
        current_round
        < hard_special_round
    ):
        return candidates

    special_candidates = [
        candidate
        for candidate in candidates
        if candidate.get(
            "position"
        )
        in missing_special
    ]

    if special_candidates:
        return special_candidates

    return candidates


def filter_candidates(
    candidate_context,
    current_round,
    total_rounds,
):
    candidates = [
        candidate
        for candidate
        in candidate_context[
            "candidates"
        ]
        if candidate_is_eligible(
            candidate,
            candidate_context,
            current_round,
            total_rounds,
        )
    ]

    candidates = (
        apply_hard_qb_te_guardrail(
            candidates,
            candidate_context,
            current_round,
        )
    )

    candidates = (
        apply_endgame_special_guardrail(
            candidates,
            candidate_context,
            current_round,
            total_rounds,
        )
    )

    return candidates


#
# --------------------------------------------------
# MARKET TIERS
# --------------------------------------------------
#


def create_market_tiers(
    candidates,
    tier_width=MARKET_TIER_WIDTH,
):
    ordered = sorted(
        candidates,
        key=get_adp,
    )

    tiers = []
    current_tier = []
    tier_start_adp = None

    for candidate in ordered:

        adp = get_adp(
            candidate
        )

        if adp == float("inf"):

            if current_tier:
                tiers.append(
                    current_tier
                )

                current_tier = []

            tiers.append(
                [candidate]
            )

            tier_start_adp = None

            continue

        if tier_start_adp is None:

            tier_start_adp = adp

            current_tier.append(
                candidate
            )

            continue

        if (
            adp - tier_start_adp
            <= tier_width
        ):
            current_tier.append(
                candidate
            )

        else:

            tiers.append(
                current_tier
            )

            current_tier = [
                candidate
            ]

            tier_start_adp = adp

    if current_tier:
        tiers.append(
            current_tier
        )

    return tiers


#
# --------------------------------------------------
# PROJECTIONS
# --------------------------------------------------
#


def add_projection_context(
    tier,
):
    by_position = {}

    for candidate in tier:

        position = candidate.get(
            "position"
        )

        projected_points = (
            candidate.get(
                "projected_points"
            )
        )

        if (
            position is None
            or projected_points
            is None
        ):
            candidate[
                "projection_context"
            ] = "unknown"

            continue

        by_position.setdefault(
            position,
            [],
        ).append(
            candidate
        )

    for players in (
        by_position.values()
    ):

        if len(players) == 1:

            players[0][
                "projection_context"
            ] = "unknown"

            continue

        ranked = sorted(
            players,
            key=lambda player: (
                player[
                    "projected_points"
                ]
            ),
            reverse=True,
        )

        best_points = (
            ranked[0][
                "projected_points"
            ]
        )

        second_points = (
            ranked[1][
                "projected_points"
            ]
        )

        if best_points <= 0:

            for player in players:
                player[
                    "projection_context"
                ] = "unknown"

            continue

        best_gap = (
            best_points
            - second_points
        ) / best_points

        for index, player in enumerate(
            ranked
        ):

            gap_from_best = (
                best_points
                - player[
                    "projected_points"
                ]
            ) / best_points

            if index == 0:

                if (
                    best_gap
                    > PROJECTION_SIMILAR_PERCENT
                ):
                    context = "advantage"

                else:
                    context = "similar"

            elif (
                gap_from_best
                <= PROJECTION_SIMILAR_PERCENT
            ):
                context = "similar"

            else:
                context = "disadvantage"

            player[
                "projection_context"
            ] = context


#
# --------------------------------------------------
# ECR
# --------------------------------------------------
#


def add_ecr_context(
    tier,
):
    by_position = {}

    for candidate in tier:

        position = candidate.get(
            "position"
        )

        ecr = candidate.get(
            "ecr"
        )

        if (
            position is None
            or ecr is None
        ):
            candidate[
                "ecr_context"
            ] = "unknown"

            continue

        by_position.setdefault(
            position,
            [],
        ).append(
            candidate
        )

    for players in (
        by_position.values()
    ):

        if len(players) == 1:

            players[0][
                "ecr_context"
            ] = "unknown"

            continue

        ranked = sorted(
            players,
            key=lambda player: (
                player["ecr"]
            ),
        )

        best_ecr = (
            ranked[0]["ecr"]
        )

        second_ecr = (
            ranked[1]["ecr"]
        )

        for index, player in enumerate(
            ranked
        ):

            difference = (
                player["ecr"]
                - best_ecr
            )

            if index == 0:

                if (
                    second_ecr
                    - best_ecr
                    > ECR_SIMILAR_DIFFERENCE
                ):
                    context = "advantage"

                else:
                    context = "similar"

            elif (
                difference
                <= ECR_SIMILAR_DIFFERENCE
            ):
                context = "similar"

            else:
                context = "disadvantage"

            player[
                "ecr_context"
            ] = context


def add_ecr_quality_context(
    candidate,
):
    sd = candidate.get(
        "ecr_sd"
    )

    best = candidate.get(
        "ecr_best"
    )

    worst = candidate.get(
        "ecr_worst"
    )

    rank_delta = candidate.get(
        "ecr_rank_delta"
    )

    spread = None

    if (
        best is not None
        and worst is not None
    ):
        spread = abs(
            float(worst)
            - float(best)
        )

    if (
        sd is None
        and spread is None
    ):
        confidence = "unknown"

    elif (
        (
            sd is None
            or float(sd)
            <= ECR_LOW_SD
        )
        and (
            spread is None
            or spread
            <= ECR_NARROW_RANGE
        )
    ):
        confidence = "high"

    elif (
        (
            sd is not None
            and float(sd)
            >= ECR_HIGH_SD
        )
        or (
            spread is not None
            and spread
            >= ECR_WIDE_RANGE
        )
    ):
        confidence = "low"

    else:
        confidence = "normal"

    candidate[
        "ecr_confidence"
    ] = confidence

    candidate[
        "ecr_range"
    ] = spread

    if rank_delta is None:

        candidate[
            "ecr_movement"
        ] = "unknown"

    elif (
        abs(
            float(rank_delta)
        )
        >= ECR_MOVEMENT_THRESHOLD
    ):
        candidate[
            "ecr_movement"
        ] = "moving"

    else:
        candidate[
            "ecr_movement"
        ] = "stable"


#
# --------------------------------------------------
# SORTING PRIORITIES
# --------------------------------------------------
#


def get_status_priority(
    candidate,
):
    if (
        candidate.get(
            "record_type"
        )
        == "team_defense"
    ):
        return 0

    return STATUS_PRIORITY.get(
        candidate.get(
            "current_status_category",
            "unknown",
        ),
        STATUS_PRIORITY[
            "unknown"
        ],
    )


def get_qb_te_urgency(
    candidate,
    current_round,
    strategy,
):
    position = candidate.get(
        "position"
    )

    if position not in {
        "QB",
        "TE",
    }:
        return 2

    if (
        candidate.get(
            "roster_role"
        )
        != "core_starter"
    ):
        return 2

    if (
        current_round
        >= QB_TE_HARD_ROUND
    ):
        return 0

    soft_round = (
        BALANCED_QB_TE_SOFT_ROUND
        if strategy == "balanced"
        else HEAVY_QB_TE_SOFT_ROUND
    )

    if (
        current_round
        >= soft_round
    ):
        return 1

    return 2


def get_roster_role_priority(
    candidate,
):
    return ROSTER_ROLE_PRIORITY.get(
        candidate.get(
            "roster_role",
            "bench_depth",
        ),
        ROSTER_ROLE_PRIORITY[
            "bench_depth"
        ],
    )


def get_balanced_priority(
    candidate,
    strategy,
):
    if strategy != "balanced":
        return 0

    position = candidate.get(
        "position"
    )

    if (
        position in {
            "RB",
            "WR",
        }
        and candidate.get(
            "matches_balanced_alternation"
        )
    ):
        return 0

    if position in {
        "RB",
        "WR",
    }:
        return 1

    return 0


def get_heavy_strategy_priority(
    candidate,
    strategy,
):
    position = candidate.get(
        "position"
    )

    roster_status = candidate.get(
        "starter_position_status",
        {},
    )

    rostered = roster_status.get(
        "rostered",
        0,
    )

    if strategy == "rb-heavy":

        if (
            position == "RB"
            and rostered < 3
        ):
            return 0

        if position == "WR":
            return 1

        if position == "RB":
            return 2

        return 1

    if strategy == "wr-heavy":

        if (
            position == "WR"
            and rostered < 3
        ):
            return 0

        if position == "RB":
            return 1

        if position == "WR":
            return 2

        return 1

    return 0


def get_projection_priority(
    candidate,
):
    return PROJECTION_PRIORITY.get(
        candidate.get(
            "projection_context",
            "unknown",
        ),
        PROJECTION_PRIORITY[
            "unknown"
        ],
    )


def get_ecr_priority(
    candidate,
):
    return ECR_PRIORITY.get(
        candidate.get(
            "ecr_context",
            "unknown",
        ),
        ECR_PRIORITY[
            "unknown"
        ],
    )


def get_ecr_confidence_priority(
    candidate,
):
    return ECR_CONFIDENCE_PRIORITY.get(
        candidate.get(
            "ecr_confidence",
            "unknown",
        ),
        ECR_CONFIDENCE_PRIORITY[
            "unknown"
        ],
    )


def get_ecr_movement_priority(
    candidate,
):
    movement = candidate.get(
        "ecr_movement"
    )

    if movement == "stable":
        return 0

    return 1


def get_backup_qb_priority(
    candidate,
):
    if (
        candidate.get(
            "position"
        )
        == "QB"
        and candidate.get(
            "roster_role"
        )
        == "bench_depth"
    ):
        return 2

    return 0


def get_role_priority(
    candidate,
):
    if (
        candidate.get(
            "record_type"
        )
        != "player"
    ):
        return 0

    return ROLE_PRIORITY.get(
        candidate.get(
            "role_quality",
            "unknown",
        ),
        ROLE_PRIORITY[
            "unknown"
        ],
    )


def is_rookie_without_nfl_history(
    candidate,
):
    """
    Identify rookies whose missing historical NFL data is expected.

    The live Sleeper years-exp field can represent a rookie as 0,
    while the cached career-info field represents a rookie as
    year 1. Requiring no recent NFL PPG and no career PPG prevents
    a second-year player with real NFL history from being treated
    as a rookie simply because years_exp may equal 1.
    """
    if (
        candidate.get(
            "record_type"
        )
        != "player"
    ):
        return False

    years_in_league = candidate.get(
        "years_in_league"
    )

    try:
        years_in_league = int(
            years_in_league
        )
    except (
        TypeError,
        ValueError,
    ):
        return False

    if years_in_league not in {
        0,
        1,
    }:
        return False

    recent_ppg = candidate.get(
        "recent_ppg"
    )

    career_ppg = candidate.get(
        "career_ppg"
    )

    return (
        not recent_ppg
        and career_ppg is None
    )


def get_trend_priority(
    candidate,
):
    if (
        candidate.get(
            "record_type"
        )
        != "player"
    ):
        return 0

    trend = candidate.get(
        "performance_trend",
        "unknown",
    )

    #
    # A rookie has no prior NFL performance trend by definition.
    # Treat that missing history as neutral instead of worse than
    # a veteran with stable history.
    #
    if (
        trend == "unknown"
        and is_rookie_without_nfl_history(
            candidate
        )
    ):
        return TREND_PRIORITY[
            "mixed_or_stable"
        ]

    return TREND_PRIORITY.get(
        trend,
        TREND_PRIORITY[
            "unknown"
        ],
    )


def get_availability_priority(
    candidate,
):
    if (
        candidate.get(
            "record_type"
        )
        != "player"
    ):
        return 0

    availability = candidate.get(
        "availability_level",
        "unknown",
    )

    #
    # A rookie has no prior NFL availability record by definition.
    # Missing games-played history is therefore neutral, not a
    # negative signal.
    #
    if (
        availability == "unknown"
        and is_rookie_without_nfl_history(
            candidate
        )
    ):
        return AVAILABILITY_PRIORITY[
            "moderate"
        ]

    return AVAILABILITY_PRIORITY.get(
        availability,
        AVAILABILITY_PRIORITY[
            "unknown"
        ],
    )


def get_special_position_priority(
    candidate,
    candidate_context,
    current_round,
    total_rounds,
):
    position = candidate.get(
        "position"
    )

    if position not in {
        "K",
        "DST",
    }:
        return 1

    missing_special = (
        get_missing_special_positions(
            candidate_context
        )
    )

    if (
        position
        not in missing_special
    ):
        return 2

    if (
        current_round
        >= total_rounds - 2
    ):
        return 0

    return 1


def get_market_adjustment(
    candidate,
    candidate_context,
    strategy,
):
    """
    Convert supporting evidence into a modest ADP adjustment.

    ADP is still the market baseline. Other signals can move a
    player earlier or later, but there is no hard tier boundary
    preventing any eligible candidate from competing globally.

    ECR remains same-position context because raw positional ECR
    should not be compared directly across different positions.
    """
    adjustment = 0.0

    ecr_context = candidate.get(
        "ecr_context",
        "unknown",
    )

    if ecr_context == "advantage":
        adjustment += (
            ECR_ADVANTAGE_ADJUSTMENT
        )

    elif ecr_context == "disadvantage":
        adjustment += (
            ECR_DISADVANTAGE_ADJUSTMENT
        )

    ecr_confidence = candidate.get(
        "ecr_confidence",
        "unknown",
    )

    if ecr_confidence == "high":
        adjustment += (
            ECR_HIGH_CONFIDENCE_ADJUSTMENT
        )

    elif ecr_confidence == "low":
        adjustment += (
            ECR_LOW_CONFIDENCE_ADJUSTMENT
        )

    role_quality = candidate.get(
        "role_quality",
        "unknown",
    )

    if role_quality == "starter":
        adjustment += (
            STARTER_ROLE_ADJUSTMENT
        )

    elif role_quality == "backup":
        adjustment += (
            BACKUP_ROLE_ADJUSTMENT
        )

    elif role_quality == "depth":
        adjustment += (
            DEPTH_ROLE_ADJUSTMENT
        )

    trend_priority = get_trend_priority(
        candidate
    )

    if trend_priority == TREND_PRIORITY[
        "improving"
    ]:
        adjustment += (
            IMPROVING_TREND_ADJUSTMENT
        )

    elif trend_priority == TREND_PRIORITY[
        "unknown"
    ]:
        adjustment += (
            UNKNOWN_TREND_ADJUSTMENT
        )

    elif trend_priority == TREND_PRIORITY[
        "declining"
    ]:
        adjustment += (
            DECLINING_TREND_ADJUSTMENT
        )

    availability_priority = (
        get_availability_priority(
            candidate
        )
    )

    if (
        availability_priority
        == AVAILABILITY_PRIORITY[
            "high"
        ]
    ):
        adjustment += (
            HIGH_AVAILABILITY_ADJUSTMENT
        )

    elif (
        availability_priority
        == AVAILABILITY_PRIORITY[
            "unknown"
        ]
    ):
        adjustment += (
            UNKNOWN_AVAILABILITY_ADJUSTMENT
        )

    elif (
        availability_priority
        == AVAILABILITY_PRIORITY[
            "low"
        ]
    ):
        adjustment += (
            LOW_AVAILABILITY_ADJUSTMENT
        )

    bench_priority = (
        get_bench_balance_priority(
            candidate,
            candidate_context,
            strategy,
        )
    )

    if bench_priority == 0:
        adjustment += (
            BENCH_NEED_ADJUSTMENT
        )

    elif bench_priority == 2:
        adjustment += (
            BENCH_EXCESS_ADJUSTMENT
        )

    if (
        strategy == "balanced"
        and candidate.get(
            "position"
        )
        in {
            "RB",
            "WR",
        }
        and candidate.get(
            "matches_balanced_alternation"
        )
    ):
        adjustment += (
            BALANCED_MATCH_ADJUSTMENT
        )

    heavy_priority = (
        get_heavy_strategy_priority(
            candidate,
            strategy,
        )
    )

    if strategy in {
        "rb-heavy",
        "wr-heavy",
    }:
        if heavy_priority == 0:
            adjustment += (
                HEAVY_PRIMARY_ADJUSTMENT
            )

        elif heavy_priority == 2:
            adjustment += (
                HEAVY_EXCESS_ADJUSTMENT
            )

    projection_context = candidate.get(
        "projection_context",
        "unknown",
    )

    if projection_context == "advantage":
        adjustment += (
            PROJECTION_ADVANTAGE_ADJUSTMENT
        )

    elif (
        projection_context
        == "disadvantage"
    ):
        adjustment += (
            PROJECTION_DISADVANTAGE_ADJUSTMENT
        )

    return adjustment


def get_market_adjusted_adp(
    candidate,
    candidate_context,
    strategy,
):
    adp = get_adp(
        candidate
    )

    if adp == float("inf"):
        return adp

    return (
        adp
        + get_market_adjustment(
            candidate,
            candidate_context,
            strategy,
        )
    )


def rank_candidates_globally(
    candidates,
    candidate_context,
    current_round,
    total_rounds,
    strategy,
):
    """
    Rank every eligible candidate together.

    Hard roster/status rules still come first. After that, ADP is
    treated as the market baseline and is adjusted by ECR, role,
    roster balance, strategy, trend, availability, and finally
    projections. There are no hard ADP tiers or adjacent-tier-only
    promotions.
    """
    return sorted(
        candidates,
        key=lambda candidate: (
            get_status_priority(
                candidate
            ),

            get_qb_te_urgency(
                candidate,
                current_round,
                strategy,
            ),

            get_special_position_priority(
                candidate,
                candidate_context,
                current_round,
                total_rounds,
            ),

            get_roster_role_priority(
                candidate
            ),

            get_backup_qb_priority(
                candidate
            ),

            get_market_adjusted_adp(
                candidate,
                candidate_context,
                strategy,
            ),

            #
            # Deterministic tie-breakers.
            #
            get_ecr_priority(
                candidate
            ),

            get_role_priority(
                candidate
            ),

            get_trend_priority(
                candidate
            ),

            get_availability_priority(
                candidate
            ),

            get_adp(
                candidate
            ),

            #
            # Projection is deliberately last.
            #
            get_projection_priority(
                candidate
            ),
        ),
    )


def rank_within_tier(
    tier,
    candidate_context,
    current_round,
    total_rounds,
    strategy,
):
    return sorted(
        tier,
        key=lambda candidate: (
            get_status_priority(
                candidate
            ),

            get_qb_te_urgency(
                candidate,
                current_round,
                strategy,
            ),

            get_special_position_priority(
                candidate,
                candidate_context,
                current_round,
                total_rounds,
            ),

            get_roster_role_priority(
                candidate
            ),

            get_bench_balance_priority(
                candidate,
                candidate_context,
                strategy,
            ),

            get_balanced_priority(
                candidate,
                strategy,
            ),

            get_heavy_strategy_priority(
                candidate,
                strategy,
            ),

            get_backup_qb_priority(
                candidate
            ),

            get_projection_priority(
                candidate
            ),

            get_ecr_priority(
                candidate
            ),

            get_ecr_confidence_priority(
                candidate
            ),

            get_ecr_movement_priority(
                candidate
            ),

            get_role_priority(
                candidate
            ),

            get_trend_priority(
                candidate
            ),

            get_availability_priority(
                candidate
            ),

            get_adp(
                candidate
            ),
        ),
    )


#
# --------------------------------------------------
# CROSS-TIER VALUE OVERRIDES
# --------------------------------------------------
#


def should_cross_tier_promote(
    challenger,
    current_top,
):
    challenger_adp = get_adp(
        challenger
    )

    top_adp = get_adp(
        current_top
    )

    if (
        challenger_adp
        == float("inf")
        or top_adp
        == float("inf")
    ):
        return False

    adp_gap = (
        challenger_adp
        - top_adp
    )

    if (
        adp_gap < 0
        or adp_gap
        > CROSS_TIER_MAX_ADP_GAP
    ):
        return False

    challenger_role = (
        challenger.get(
            "roster_role"
        )
    )

    top_role = (
        current_top.get(
            "roster_role"
        )
    )

    if (
        challenger_role
        == "core_starter"
        and top_role in {
            "flex_starter",
            "bench_depth",
        }
    ):
        return True

    #
    # ECR/projection comparisons remain
    # same-position only.
    #
    if (
        challenger.get(
            "position"
        )
        == current_top.get(
            "position"
        )
    ):

        challenger_ecr = (
            challenger.get(
                "ecr"
            )
        )

        top_ecr = (
            current_top.get(
                "ecr"
            )
        )

        if (
            challenger_ecr is not None
            and top_ecr is not None
            and (
                float(top_ecr)
                - float(
                    challenger_ecr
                )
            )
            >= CROSS_TIER_ECR_ADVANTAGE
        ):
            return True

        challenger_projection = (
            challenger.get(
                "projected_points"
            )
        )

        top_projection = (
            current_top.get(
                "projected_points"
            )
        )

        if (
            challenger_projection
            is not None
            and top_projection
            is not None
            and float(
                top_projection
            ) > 0
        ):

            projection_advantage = (
                float(
                    challenger_projection
                )
                - float(
                    top_projection
                )
            ) / float(
                top_projection
            )

            if (
                projection_advantage
                >= CROSS_TIER_PROJECTION_ADVANTAGE
            ):
                return True

    return False


def apply_cross_tier_overrides(
    ordered,
):
    if len(ordered) < 2:
        return ordered

    changed = True

    while changed:

        changed = False

        for index in range(
            1,
            len(ordered),
        ):

            challenger = ordered[
                index
            ]

            current_top = ordered[
                index - 1
            ]

            challenger_tier = (
                challenger.get(
                    "market_tier"
                )
            )

            top_tier = (
                current_top.get(
                    "market_tier"
                )
            )

            if (
                challenger_tier is None
                or top_tier is None
            ):
                continue

            if (
                challenger_tier
                - top_tier
                != 1
            ):
                continue

            if (
                should_cross_tier_promote(
                    challenger,
                    current_top,
                )
            ):
                ordered[
                    index - 1
                ], ordered[index] = (
                    challenger,
                    current_top,
                )

                changed = True

    return ordered


#
# --------------------------------------------------
# MAJOR STATUS GUARDRAIL
# --------------------------------------------------
#


def apply_major_concern_guardrail(
    ordered,
):
    """
    PUP / IR / suspended players can remain visible,
    but should not normally become recommendation #1
    when a reasonably close healthier alternative
    exists.

    Alec 59.4 vs Rico 75.3 is a 15.9 ADP gap,
    so Rico now correctly qualifies.
    """

    if not ordered:
        return ordered

    top_candidate = ordered[0]

    top_status = (
        top_candidate.get(
            "current_status_category"
        )
    )

    if top_status not in {
        "major_concern",
        "suspended",
    }:
        return ordered

    top_adp = get_adp(
        top_candidate
    )

    for index in range(
        1,
        len(ordered),
    ):

        candidate = ordered[
            index
        ]

        status = candidate.get(
            "current_status_category",
            "unknown",
        )

        if status in {
            "major_concern",
            "suspended",
        }:
            continue

        #
        # Do not replace a starter with a bench
        # player merely because the starter is hurt.
        #
        top_role = top_candidate.get(
            "roster_role"
        )

        candidate_role = candidate.get(
            "roster_role"
        )

        acceptable_roles = {
            "core_starter": 0,
            "superflex_starter": 1,
            "flex_starter": 2,
            "bench_depth": 3,
            "special_starter": 4,
        }

        if (
            acceptable_roles.get(
                candidate_role,
                99,
            )
            >
            acceptable_roles.get(
                top_role,
                99,
            )
        ):
            continue

        candidate_adp = get_adp(
            candidate
        )

        if (
            top_adp == float("inf")
            or candidate_adp
            == float("inf")
        ):
            continue

        if (
            candidate_adp
            - top_adp
            <= MAJOR_CONCERN_HEALTHY_OVERRIDE_GAP
        ):
            ordered.insert(
                0,
                ordered.pop(
                    index
                ),
            )

            return ordered

    return ordered


#
# --------------------------------------------------
# FLAGS
# --------------------------------------------------
#


def get_decision_flags(
    candidate,
    candidate_context,
    current_round,
    total_rounds,
    strategy,
):
    flags = []

    roster_role = candidate.get(
        "roster_role"
    )

    if roster_role:
        flags.append(
            f"roster_role_{roster_role}"
        )

    urgency = get_qb_te_urgency(
        candidate,
        current_round,
        strategy,
    )

    if urgency == 0:

        flags.append(
            "urgent_qb_te_starter_need"
        )

    elif urgency == 1:

        flags.append(
            "increasing_qb_te_starter_need"
        )

    if (
        candidate.get(
            "roster_role"
        )
        == "bench_depth"
        and candidate.get(
            "position"
        )
        in {
            "RB",
            "WR",
        }
        and get_bench_balance_priority(
            candidate,
            candidate_context,
            strategy,
        )
        == 0
    ):
        flags.append(
            "supports_bench_balance"
        )

    if (
        strategy == "balanced"
        and candidate.get(
            "matches_balanced_alternation"
        )
    ):
        flags.append(
            "matches_balanced_alternation"
        )

    if (
        strategy == "rb-heavy"
        and candidate.get(
            "position"
        )
        == "RB"
    ):
        flags.append(
            "matches_rb_heavy_strategy"
        )

    if (
        strategy == "wr-heavy"
        and candidate.get(
            "position"
        )
        == "WR"
    ):
        flags.append(
            "matches_wr_heavy_strategy"
        )

    if (
        candidate.get(
            "position"
        )
        in {
            "K",
            "DST",
        }
        and current_round
        >= total_rounds - 2
    ):
        flags.append(
            "late_round_starter_need"
        )

    projection_context = (
        candidate.get(
            "projection_context"
        )
    )

    if (
        projection_context
        == "advantage"
    ):
        flags.append(
            "projection_advantage"
        )

    if (
        projection_context
        == "disadvantage"
    ):
        flags.append(
            "projection_disadvantage"
        )

    ecr_context = candidate.get(
        "ecr_context"
    )

    if ecr_context == "advantage":
        flags.append(
            "ecr_advantage"
        )

    if ecr_context == "disadvantage":
        flags.append(
            "ecr_disadvantage"
        )

    ecr_confidence = candidate.get(
        "ecr_confidence"
    )

    if ecr_confidence == "high":
        flags.append(
            "strong_expert_consensus"
        )

    if ecr_confidence == "low":
        flags.append(
            "high_expert_disagreement"
        )

    if (
        candidate.get(
            "ecr_movement"
        )
        == "moving"
    ):
        flags.append(
            "recent_ecr_movement"
        )

    if (
        candidate.get(
            "performance_trend"
        )
        == "improving"
    ):
        flags.append(
            "improving_recent_trend"
        )

    if (
        candidate.get(
            "availability_level"
        )
        == "high"
    ):
        flags.append(
            "high_historical_availability"
        )

    if (
        candidate.get(
            "availability_level"
        )
        == "low"
    ):
        flags.append(
            "low_historical_availability"
        )

    status = candidate.get(
        "current_status_category"
    )

    if status in {
        "minor_concern",
        "concern",
        "major_concern",
        "suspended",
    }:
        flags.append(
            f"current_status_{status}"
        )

    return flags


#
# --------------------------------------------------
# FINAL SHORTLIST
# --------------------------------------------------
#


def create_shortlist(
    candidate_context,
    current_round,
    total_rounds,
    strategy="balanced",
    limit=5,
):
    if (
        strategy
        not in VALID_STRATEGIES
    ):
        raise ValueError(
            "Invalid strategy."
        )

    candidates = filter_candidates(
        candidate_context,
        current_round,
        total_rounds,
    )

    #
    # ECR and projections are still evaluated within
    # position, but they are now built across the entire
    # eligible candidate pool rather than an ADP tier.
    #
    add_projection_context(
        candidates
    )

    add_ecr_context(
        candidates
    )

    for candidate in candidates:
        add_ecr_quality_context(
            candidate
        )

    ordered = rank_candidates_globally(
        candidates,
        candidate_context,
        current_round,
        total_rounds,
        strategy,
    )

    #
    # Keep the major injury/suspension protection for
    # recommendation #1.
    #
    ordered = (
        apply_major_concern_guardrail(
            ordered
        )
    )

    for candidate in ordered:

        candidate[
            "decision_flags"
        ] = get_decision_flags(
            candidate,
            candidate_context,
            current_round,
            total_rounds,
            strategy,
        )

        candidate[
            "market_adjustment"
        ] = round(
            get_market_adjustment(
                candidate,
                candidate_context,
                strategy,
            ),
            2,
        )

        adjusted_adp = (
            get_market_adjusted_adp(
                candidate,
                candidate_context,
                strategy,
            )
        )

        candidate[
            "market_adjusted_adp"
        ] = (
            None
            if adjusted_adp
            == float("inf")
            else round(
                adjusted_adp,
                2,
            )
        )

    shortlist = ordered[
        :limit
    ]

    for (
        index,
        candidate,
    ) in enumerate(
        shortlist,
        start=1,
    ):

        candidate[
            "deterministic_rank"
        ] = index

    return shortlist

def get_draft_recommendation(
    candidate_context,
    current_round,
    total_rounds,
    strategy="balanced",
    limit=5,
):
    shortlist = create_shortlist(
        candidate_context=(
            candidate_context
        ),
        current_round=(
            current_round
        ),
        total_rounds=(
            total_rounds
        ),
        strategy=(
            strategy
        ),
        limit=limit,
    )

    return {
        "recommended_player": (
            shortlist[0]
            if shortlist
            else None
        ),
        "rankings": shortlist,
    }