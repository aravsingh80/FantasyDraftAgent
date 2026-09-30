def format_number(
    value,
    decimals=1,
):
    if value is None:
        return None

    try:
        return (
            f"{float(value):.{decimals}f}"
        )

    except (
        TypeError,
        ValueError,
    ):
        return None


def get_status_reason(
    candidate,
):
    status = candidate.get(
        "current_status_category"
    )

    injury_status = candidate.get(
        "current_injury_status"
    )

    body_part = candidate.get(
        "current_injury_body_part"
    )

    if status == "suspended":
        return (
            "is currently suspended"
        )

    if status == "major_concern":
        if injury_status:
            reason = (
                f"has a major current "
                f"availability concern "
                f"({injury_status})"
            )

            if body_part:
                reason += (
                    f" involving the "
                    f"{body_part}"
                )

            return reason

        return (
            "has a major current "
            "availability concern"
        )

    if status == "concern":
        if injury_status:
            return (
                f"has a current injury "
                f"concern "
                f"({injury_status})"
            )

        return (
            "has a current "
            "availability concern"
        )

    if status == "minor_concern":
        if injury_status:
            return (
                f"has a minor current "
                f"injury concern "
                f"({injury_status})"
            )

        return (
            "has a minor current "
            "availability concern"
        )

    return None


def get_roster_reason(
    candidate,
):
    roster_role = candidate.get(
        "roster_role"
    )

    position = candidate.get(
        "position"
    )

    if roster_role == "core_starter":
        return (
            f"fills an open "
            f"{position} starter slot"
        )

    if roster_role == "flex_starter":
        return (
            "fills an open FLEX slot"
        )

    if (
        roster_role
        == "superflex_starter"
    ):
        return (
            "fills an open SUPERFLEX slot"
        )

    if (
        roster_role
        == "special_starter"
    ):
        return (
            f"fills the remaining "
            f"{position} starter slot"
        )

    return None


def get_strategy_reason(
    candidate,
):
    flags = set(
        candidate.get(
            "decision_flags",
            [],
        )
    )

    if (
        "supports_bench_balance"
        in flags
    ):
        return (
            "adds needed depth at a "
            "position that is currently "
            "underrepresented on the bench"
        )

    if (
        "matches_balanced_alternation"
        in flags
    ):
        return (
            "fits the current balanced "
            "RB/WR roster construction"
        )

    if (
        "matches_rb_heavy_strategy"
        in flags
    ):
        return (
            "fits the selected RB-heavy "
            "draft strategy"
        )

    if (
        "matches_wr_heavy_strategy"
        in flags
    ):
        return (
            "fits the selected WR-heavy "
            "draft strategy"
        )

    return None


def get_value_reasons(
    candidate,
):
    reasons = []

    flags = set(
        candidate.get(
            "decision_flags",
            [],
        )
    )

    ecr = format_number(
        candidate.get(
            "ecr"
        ),
        1,
    )

    if (
        "ecr_advantage"
        in flags
    ):
        if ecr:
            reasons.append(
                f"has a strong expert "
                f"consensus rank of "
                f"{ecr} at the position"
            )

        else:
            reasons.append(
                "has an expert consensus "
                "advantage over other "
                "same-position options"
            )

    elif (
        "strong_expert_consensus"
        in flags
        and ecr
    ):
        reasons.append(
            f"has strong expert agreement "
            f"around an ECR of {ecr}"
        )

    if (
        "projection_advantage"
        in flags
    ):
        projection = format_number(
            candidate.get(
                "projected_points"
            ),
            1,
        )

        if projection:
            reasons.append(
                f"has a projection "
                f"advantage at "
                f"{projection} PPR points"
            )

        else:
            reasons.append(
                "has a projection advantage "
                "over other same-position "
                "options"
            )

    return reasons


def get_secondary_reasons(
    candidate,
):
    reasons = []

    flags = set(
        candidate.get(
            "decision_flags",
            [],
        )
    )

    if (
        "improving_recent_trend"
        in flags
    ):
        reasons.append(
            "recent fantasy production "
            "has been improving"
        )

    if (
        "high_historical_availability"
        in flags
    ):
        reasons.append(
            "has strong historical "
            "availability"
        )

    if (
        "low_historical_availability"
        in flags
    ):
        reasons.append(
            "has weaker historical "
            "availability"
        )

    if (
        "high_expert_disagreement"
        in flags
    ):
        reasons.append(
            "experts have relatively high "
            "disagreement on the ranking"
        )

    if (
        "recent_ecr_movement"
        in flags
    ):
        reasons.append(
            "the expert consensus ranking "
            "has moved recently"
        )

    return reasons


def get_negative_reasons(
    candidate,
):
    reasons = []

    flags = set(
        candidate.get(
            "decision_flags",
            [],
        )
    )

    status_reason = (
        get_status_reason(
            candidate
        )
    )

    if status_reason:
        reasons.append(
            status_reason
        )

    if (
        "projection_disadvantage"
        in flags
    ):
        reasons.append(
            "projects below other "
            "same-position alternatives"
        )

    if (
        "ecr_disadvantage"
        in flags
    ):
        reasons.append(
            "has a weaker expert consensus "
            "ranking than other "
            "same-position alternatives"
        )

    return reasons


def find_same_position_comparison(
    candidate,
    rankings,
):
    position = candidate.get(
        "position"
    )

    candidate_rank = candidate.get(
        "deterministic_rank",
        999,
    )

    comparisons = [
        other
        for other in rankings
        if (
            other is not candidate
            and other.get(
                "position"
            )
            == position
            and other.get(
                "deterministic_rank",
                999,
            )
            > candidate_rank
        )
    ]

    if not comparisons:
        return None

    return comparisons[0]


def get_relative_reason(
    candidate,
    rankings,
):
    comparison = (
        find_same_position_comparison(
            candidate,
            rankings,
        )
    )

    if comparison is None:
        return None

    candidate_ecr = candidate.get(
        "ecr"
    )

    comparison_ecr = comparison.get(
        "ecr"
    )

    if (
        candidate_ecr is not None
        and comparison_ecr is not None
    ):
        difference = (
            float(comparison_ecr)
            - float(candidate_ecr)
        )

        if difference >= 3:
            return (
                f"is ranked notably higher "
                f"by experts than "
                f"{comparison['name']}"
            )

    candidate_projection = (
        candidate.get(
            "projected_points"
        )
    )

    comparison_projection = (
        comparison.get(
            "projected_points"
        )
    )

    if (
        candidate_projection is not None
        and comparison_projection
        is not None
    ):
        difference = (
            float(candidate_projection)
            - float(
                comparison_projection
            )
        )

        if difference >= 8:
            return (
                f"projects for more PPR "
                f"points than "
                f"{comparison['name']}"
            )

    return None


def join_reasons(
    reasons,
):
    reasons = [
        reason
        for reason in reasons
        if reason
    ]

    if not reasons:
        return (
            "Ranks highest under the "
            "current deterministic draft "
            "rules."
        )

    if len(reasons) == 1:
        return (
            reasons[0][0].upper()
            + reasons[0][1:]
            + "."
        )

    if len(reasons) == 2:
        sentence = (
            f"{reasons[0].capitalize()} "
            f"and {reasons[1]}."
        )

        return sentence

    sentence = (
        f"{reasons[0].capitalize()}, "
        f"{reasons[1]}, and "
        f"{reasons[2]}."
    )

    return sentence


def generate_candidate_reason(
    candidate,
    rankings,
):
    reasons = []

    roster_reason = (
        get_roster_reason(
            candidate
        )
    )

    strategy_reason = (
        get_strategy_reason(
            candidate
        )
    )

    value_reasons = (
        get_value_reasons(
            candidate
        )
    )

    relative_reason = (
        get_relative_reason(
            candidate,
            rankings,
        )
    )

    secondary_reasons = (
        get_secondary_reasons(
            candidate
        )
    )

    negative_reasons = (
        get_negative_reasons(
            candidate
        )
    )

    if roster_reason:
        reasons.append(
            roster_reason
        )

    if strategy_reason:
        reasons.append(
            strategy_reason
        )

    if value_reasons:
        reasons.extend(
            value_reasons
        )

    if relative_reason:
        reasons.append(
            relative_reason
        )

    if secondary_reasons:
        reasons.extend(
            secondary_reasons
        )

    #
    # Keep each explanation concise.
    #
    positive_reasons = reasons[:3]

    explanation = (
        join_reasons(
            positive_reasons
        )
    )

    #
    # Add one meaningful warning if needed.
    #
    if negative_reasons:
        warning = (
            negative_reasons[0]
        )

        explanation += (
            f" However, "
            f"{warning}."
        )

    return explanation


def generate_recommendation_reason(
    recommendation,
):
    rankings = recommendation.get(
        "rankings",
        [],
    )

    recommended = recommendation.get(
        "recommended_player"
    )

    if recommended is None:
        return (
            "No recommendation is "
            "currently available."
        )

    return generate_candidate_reason(
        recommended,
        rankings,
    )


def add_reasoning_to_recommendation(
    recommendation,
):
    rankings = recommendation.get(
        "rankings",
        [],
    )

    for candidate in rankings:
        candidate[
            "reasoning"
        ] = generate_candidate_reason(
            candidate,
            rankings,
        )

    recommendation[
        "recommendation_reasoning"
    ] = (
        generate_recommendation_reason(
            recommendation
        )
    )

    return recommendation