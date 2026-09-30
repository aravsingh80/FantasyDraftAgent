import time

import requests

from build_candidate_context import (
    build_candidate_context,
)
from candidate_shortlist import (
    get_draft_recommendation,
)
from determine_roster_format import (
    determine_draft_slot,
    get_roster_format_from_draft,
)
from knowledge_base import (
    get_candidate_data,
    load_knowledge_base,
)
from normalize_names import (
    normalize_name,
    normalize_team,
)
from retrieve_current_rankings import (
    return_current_rankings,
)
from retrieve_ecr import (
    get_ecr_lookup,
)
from retrieve_initial_rankings import (
    get_adp_rankings,
)
from retrieve_live_player_data import (
    load_live_datasets,
    retrieve_live_player_data,
)
from retrieve_projections import (
    get_projection_lookup,
)
from roster_tracking import (
    build_empty_draft_history,
    build_empty_roster,
    update_my_roster,
)
from generate_reasoning import (
    add_reasoning_to_recommendation,
)
from extension_backend.recommendation_server import (
    publish_recommendation,
    start_recommendation_server,
    update_session_metadata,
    wait_for_session,
    wait_for_strategy,
)


OVERALL_LIMIT = 10

QB_LIMIT = 3
RB_LIMIT = 5
WR_LIMIT = 5
TE_LIMIT = 3

K_LIMIT = 3
DST_LIMIT = 3

SHORTLIST_LIMIT = 5

POLL_SECONDS = 0.5

CURRENT_SEASON = 2026


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


def determine_draft_id():
    while True:
        draft_id = input(
            "Enter Sleeper draft ID: "
        ).strip()

        if draft_id:
            return draft_id

        print(
            "Please enter a valid draft ID.\n"
        )


def get_draft_info(
    draft_id,
):
    url = (
        f"https://api.sleeper.app/"
        f"v1/draft/{draft_id}"
    )

    response = requests.get(
        url,
        timeout=10,
    )

    if response.status_code == 404:
        raise ValueError(
            f"Sleeper draft ID {draft_id} "
            f"was detected from the page, "
            f"but Sleeper's public API does "
            f"not recognize that draft yet."
        )

    response.raise_for_status()

    return response.json()


def get_draft_picks(
    draft_id,
):
    url = (
        f"https://api.sleeper.app/v1/"
        f"draft/{draft_id}/picks"
        f"?t={int(time.time() * 1000)}"
    )

    response = requests.get(
        url,
        headers={
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        },
        timeout=10,
    )

    response.raise_for_status()

    return response.json()


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
    return DEFENSE_NAME_TO_TEAM.get(
        normalize_name(
            player_name
        )
    )


def find_defense_lookup_entry(
    team,
    adp_rank_lookup,
):
    team = normalize_team(
        team
    )

    for (
        normalized_name,
        player_data,
    ) in adp_rank_lookup.items():

        if (
            player_data.get(
                "position"
            )
            != "DST"
        ):
            continue

        if (
            normalize_team(
                player_data.get(
                    "team"
                )
            )
            == team
        ):
            return (
                normalized_name,
                player_data,
            )

    return (
        None,
        None,
    )


def remove_player_from_rankings(
    player_name,
    overall_rankings,
    qb_rankings,
    rb_rankings,
    wr_rankings,
    te_rankings,
    k_rankings,
    dst_rankings,
    adp_rank_lookup,
):
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

    if player_data is None:
        defense_team = (
            get_defense_team(
                player_name
            )
        )

        if defense_team:
            (
                normalized_name,
                player_data,
            ) = (
                find_defense_lookup_entry(
                    defense_team,
                    adp_rank_lookup,
                )
            )

    if player_data is None:
        return False

    overall_ranking = (
        player_data.get(
            "overall_ranking"
        )
    )

    position_ranking = (
        player_data.get(
            "position_ranking"
        )
    )

    position = (
        player_data.get(
            "position"
        )
    )

    if (
        overall_ranking
        is not None
    ):
        overall_index = (
            overall_ranking - 1
        )

        if (
            0
            <= overall_index
            < len(
                overall_rankings
            )
        ):
            overall_rankings[
                overall_index
            ] = None

    position_rankings = {
        "QB": qb_rankings,
        "RB": rb_rankings,
        "WR": wr_rankings,
        "TE": te_rankings,
        "K": k_rankings,
        "DST": dst_rankings,
    }

    rankings = (
        position_rankings.get(
            position
        )
    )

    if (
        rankings is not None
        and position_ranking
        is not None
    ):
        position_index = (
            position_ranking - 1
        )

        if (
            0
            <= position_index
            < len(rankings)
        ):
            rankings[
                position_index
            ] = None

    return True


def get_current_round(
    pick_number,
    number_of_teams,
):
    if pick_number <= 0:
        return 1

    return (
        (pick_number - 1)
        // number_of_teams
    ) + 1


def get_draft_slot_for_pick(
    pick_number,
    number_of_teams,
):
    round_number = (
        (pick_number - 1)
        // number_of_teams
    ) + 1

    position_in_round = (
        (pick_number - 1)
        % number_of_teams
    ) + 1

    if (
        round_number % 2
        == 1
    ):
        return position_in_round

    return (
        number_of_teams
        - position_in_round
        + 1
    )


def get_picks_until_my_turn(
    last_seen_pick,
    my_draft_slot,
    number_of_teams,
    total_rounds,
):
    max_pick = (
        total_rounds
        * number_of_teams
    )

    for upcoming_pick in range(
        last_seen_pick + 1,
        max_pick + 1,
    ):
        draft_slot = (
            get_draft_slot_for_pick(
                upcoming_pick,
                number_of_teams,
            )
        )

        if (
            draft_slot
            == my_draft_slot
        ):
            return (
                upcoming_pick
                - last_seen_pick
                - 1
            )

    return None


def is_my_turn(
    last_seen_pick,
    my_draft_slot,
    number_of_teams,
    total_rounds,
):
    return (
        get_picks_until_my_turn(
            last_seen_pick,
            my_draft_slot,
            number_of_teams,
            total_rounds,
        )
        == 0
    )


def ranking_item_name(
    item,
):
    if isinstance(
        item,
        dict,
    ):
        return item.get(
            "name"
        )

    return item


def get_candidates(
    knowledge_base,
    overall_rankings,
    qb_rankings,
    rb_rankings,
    wr_rankings,
    te_rankings,
    k_rankings,
    dst_rankings,
    adp_rank_lookup,
    projection_lookup,
    ecr_lookup,
):
    ranking_groups = [
        return_current_rankings(
            overall_rankings,
            OVERALL_LIMIT,
        ),
        return_current_rankings(
            qb_rankings,
            QB_LIMIT,
        ),
        return_current_rankings(
            rb_rankings,
            RB_LIMIT,
        ),
        return_current_rankings(
            wr_rankings,
            WR_LIMIT,
        ),
        return_current_rankings(
            te_rankings,
            TE_LIMIT,
        ),
        return_current_rankings(
            k_rankings,
            K_LIMIT,
        ),
        return_current_rankings(
            dst_rankings,
            DST_LIMIT,
        ),
    ]

    candidate_names = []
    seen = set()

    for group in ranking_groups:
        for item in group:
            player_name = (
                ranking_item_name(
                    item
                )
            )

            if not player_name:
                continue

            normalized_name = (
                normalize_name(
                    player_name
                )
            )

            if (
                normalized_name
                in seen
            ):
                continue

            seen.add(
                normalized_name
            )

            candidate_names.append(
                player_name
            )

    return get_candidate_data(
        knowledge_base,
        candidate_names,
        adp_rank_lookup,
        projection_lookup,
        ecr_lookup,
        normalize_name,
    )


def print_roster(
    my_roster,
):
    print(
        "\n=============================="
    )
    print(
        "MY ROSTER"
    )
    print(
        "=============================="
    )

    for (
        position,
        players,
    ) in my_roster.items():

        names = (
            ", ".join(
                players
            )
            if players
            else "-"
        )

        print(
            f"{position:<3}: "
            f"{names}"
        )


def print_recommendation(
    recommendation,
):
    print(
        "\n=============================="
    )
    print(
        "DRAFT RECOMMENDATION"
    )
    print(
        "=============================="
    )

    recommended = recommendation.get(
        "recommended_player"
    )

    if recommended is None:
        print(
            "No recommendation available."
        )
        return

    print(
        f"\nRecommended: "
        f"{recommended['name']} "
        f"({recommended['position']})"
    )

    reasoning = recommendation.get(
        "recommendation_reasoning"
    )

    if reasoning:
        print(
            f"\nWhy: {reasoning}"
        )

    print(
        "\nRankings:"
    )

    for player in recommendation.get(
        "rankings",
        [],
    ):
        projection = (
            player.get(
                "projected_points"
            )
        )

        projection_text = (
            f"{projection:.1f}"
            if projection is not None
            else "-"
        )

        ecr = player.get(
            "ecr"
        )

        ecr_text = (
            f"{ecr:.1f}"
            if ecr is not None
            else "-"
        )

        print(
            f"\n"
            f"{player['deterministic_rank']}. "
            f"{player['name']} "
            f"({player['position']})"
        )

        print(
            f"   ADP: "
            f"{player.get('adp')} "
            f"| ECR: {ecr_text} "
            f"| Proj: "
            f"{projection_text}"
        )

        print(
            f"   {player.get('reasoning')}"
        )



def get_sleeper_user_id(
    sleeper_session,
):
    user_id = sleeper_session.get(
        "sleeper_user_id"
    )

    if user_id:
        return str(user_id)

    username = sleeper_session.get(
        "sleeper_username"
    )

    if not username:
        return None

    response = requests.get(
        f"https://api.sleeper.app/v1/user/{username}",
        timeout=10,
    )
    response.raise_for_status()

    user_data = response.json()
    user_id = user_data.get("user_id")

    return (
        str(user_id)
        if user_id
        else None
    )


def get_draft_slot_for_user(
    draft_data,
    sleeper_user_id,
    draft_id,
):
    if sleeper_user_id:
        draft_order = draft_data.get(
            "draft_order",
            {},
        ) or {}

        slot = draft_order.get(
            str(sleeper_user_id)
        )

        if slot is not None:
            return int(slot)

        # Useful fallback once the draft has at least one pick.
        try:
            picks = get_draft_picks(
                draft_id
            )

            for pick in picks:
                picked_by = pick.get(
                    "picked_by"
                )

                if (
                    picked_by is not None
                    and str(picked_by)
                    == str(sleeper_user_id)
                ):
                    draft_slot = pick.get(
                        "draft_slot"
                    )

                    if draft_slot is not None:
                        return int(
                            draft_slot
                        )
        except requests.RequestException:
            pass

    print(
        "\nCould not automatically determine "
        "your Sleeper draft slot."
    )

    return determine_draft_slot()


def main():
    start_recommendation_server()

    print(
        "\nWaiting for Sleeper draft page..."
    )

    sleeper_session = (
        wait_for_session()
    )

    draft_id = sleeper_session[
        "draft_id"
    ]

    print(
        f"Sleeper draft detected: "
        f"{draft_id}"
    )

    draft_data = (
        get_draft_info(
            draft_id
        )
    )

    settings = draft_data.get(
        "settings",
        {},
    )

    number_of_teams = int(
        settings.get(
            "teams",
            12,
        )
    )

    total_rounds = int(
        settings.get(
            "rounds",
            15,
        )
    )

    (
        roster_format,
        starter_requirements,
    ) = (
        get_roster_format_from_draft(
            draft_data
        )
    )

    print(
        "\nSelect draft strategy in the "
        "FantasyAgent Chrome extension..."
    )

    strategy = wait_for_strategy()

    print(
        f"Strategy selected: {strategy}"
    )

    sleeper_user_id = (
        get_sleeper_user_id(
            sleeper_session
        )
    )

    my_draft_slot = (
        get_draft_slot_for_user(
            draft_data,
            sleeper_user_id,
            draft_id,
        )
    )

    update_session_metadata(
        sleeper_user_id=(
            sleeper_user_id
        ),
        draft_slot=my_draft_slot,
        number_of_teams=(
            number_of_teams
        ),
        total_rounds=total_rounds,
        strategy=strategy,
        roster_format=roster_format,
        starter_requirements=(
            starter_requirements
        ),
    )

    print(
        f"\nTeams: "
        f"{number_of_teams}"
    )

    print(
        f"Rounds: "
        f"{total_rounds}"
    )

    print(
        f"Strategy: "
        f"{strategy}"
    )

    print(
        f"Roster format: "
        f"{roster_format}"
    )

    print(
        f"Starter requirements: "
        f"{starter_requirements}"
    )

    print(
        f"Draft slot: "
        f"{my_draft_slot}"
    )

    print(
        "\nLoading fresh ADP..."
    )

    (
        overall_rankings,
        qb_rankings,
        rb_rankings,
        wr_rankings,
        te_rankings,
        k_rankings,
        dst_rankings,
        adp_rank_lookup,
    ) = get_adp_rankings(
        year=CURRENT_SEASON,
        scoring="ppr",
        teams=number_of_teams,
        position="all",
    )

    print(
        "ADP loaded."
    )

    print(
        "\nLoading fresh projections..."
    )

    projection_lookup = (
        get_projection_lookup()
    )

    print(
        f"Loaded projections for "
        f"{len(projection_lookup)} "
        f"players."
    )

    print(
        "\nLoading fresh ECR..."
    )

    ecr_lookup = (
        get_ecr_lookup()
    )

    print(
        f"Loaded ECR for "
        f"{len(ecr_lookup)} "
        f"players."
    )

    print(
        "\nLoading NFL live data..."
    )

    live_datasets = (
        load_live_datasets(
            CURRENT_SEASON
        )
    )

    print(
        "NFL live data loaded."
    )

    print(
        "\nLoading knowledge base..."
    )

    knowledge_base = (
        load_knowledge_base()
    )

    print(
        "Knowledge base loaded."
    )

    my_roster = (
        build_empty_roster()
    )

    draft_history = (
        build_empty_draft_history()
    )

    last_seen_pick = 0

    recommendation_generated_for_pick = (
        None
    )

    print(
        "\n=============================="
    )
    print(
        "READY FOR DRAFT"
    )
    print(
        "=============================="
    )

    while True:
        try:
            picks = (
                get_draft_picks(
                    draft_id
                )
            )

            for pick in sorted(
                picks,
                key=lambda item: (
                    item["pick_no"]
                ),
            ):
                pick_number = (
                    pick[
                        "pick_no"
                    ]
                )

                if (
                    pick_number
                    <= last_seen_pick
                ):
                    continue

                player_name = (
                    get_pick_player_name(
                        pick
                    )
                )

                if not player_name:
                    last_seen_pick = (
                        pick_number
                    )

                    continue

                matched = (
                    remove_player_from_rankings(
                        player_name,
                        overall_rankings,
                        qb_rankings,
                        rb_rankings,
                        wr_rankings,
                        te_rankings,
                        k_rankings,
                        dst_rankings,
                        adp_rank_lookup,
                    )
                )

                if matched:
                    print(
                        f"\nNew pick "
                        f"{pick_number}: "
                        f"{player_name}"
                    )

                else:
                    print(
                        f"\nCould not match "
                        f"pick "
                        f"{pick_number}: "
                        f"{player_name}"
                    )

                previous_roster = {
                    position: (
                        players.copy()
                    )
                    for (
                        position,
                        players,
                    )
                    in my_roster.items()
                }

                (
                    my_roster,
                    draft_history,
                ) = update_my_roster(
                    my_roster=(
                        my_roster
                    ),
                    draft_history=(
                        draft_history
                    ),
                    pick=pick,
                    my_draft_slot=(
                        my_draft_slot
                    ),
                    adp_rank_lookup=(
                        adp_rank_lookup
                    ),
                )

                if (
                    my_roster
                    != previous_roster
                ):
                    print_roster(
                        my_roster
                    )

                last_seen_pick = (
                    pick_number
                )

                recommendation_generated_for_pick = (
                    None
                )

            if is_my_turn(
                last_seen_pick,
                my_draft_slot,
                number_of_teams,
                total_rounds,
            ):
                next_pick = (
                    last_seen_pick
                    + 1
                )

                if (
                    recommendation_generated_for_pick
                    != next_pick
                ):
                    candidates = (
                        get_candidates(
                            knowledge_base,
                            overall_rankings,
                            qb_rankings,
                            rb_rankings,
                            wr_rankings,
                            te_rankings,
                            k_rankings,
                            dst_rankings,
                            adp_rank_lookup,
                            projection_lookup,
                            ecr_lookup,
                        )
                    )

                    live_data = (
                        retrieve_live_player_data(
                            candidates,
                            live_datasets,
                        )
                    )

                    current_round = (
                        get_current_round(
                            next_pick,
                            number_of_teams,
                        )
                    )

                    candidate_context = (
                        build_candidate_context(
                            candidates=(
                                candidates
                            ),
                            my_roster=(
                                my_roster
                            ),
                            starter_requirements=(
                                starter_requirements
                            ),
                            live_data=(
                                live_data
                            ),
                            draft_history=(
                                draft_history
                            ),
                        )
                    )

                    recommendation = (
                        get_draft_recommendation(
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
                            limit=(
                                SHORTLIST_LIMIT
                            ),
                        )
                    )

                    recommendation = (
                        add_reasoning_to_recommendation(
                            recommendation
                        )
                    )

                    print_recommendation(
                        recommendation
                    )

                    publish_recommendation(
                        recommendation
                    )

                    recommendation_generated_for_pick = (
                        next_pick
                    )

            time.sleep(
                POLL_SECONDS
            )

        except requests.RequestException as error:
            print(
                f"\nSleeper request failed: "
                f"{error}"
            )

            time.sleep(5)

        except Exception as error:
            print(
                f"\nError: {error}"
            )

            time.sleep(5)

        except KeyboardInterrupt:
            print(
                "\nDraft monitor stopped."
            )

            break


if __name__ == "__main__":
    main()