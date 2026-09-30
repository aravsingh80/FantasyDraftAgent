from knowledge_base import (
    build_knowledge_base,
    save_knowledge_base,
)
from retrieve_all_free_data import (
    retrieve_all_free_data,
)
from retrieve_initial_rankings import (
    get_adp_rankings,
)


CURRENT_SEASON = 2026

HISTORICAL_SEASONS = [
    2021,
    2022,
    2023,
    2024,
    2025,
]


def merge_player_data(
    knowledge_base,
    retrieved_data,
):
    for (
        normalized_name,
        data,
    ) in retrieved_data.items():

        record = (
            knowledge_base.get(
                normalized_name
            )
        )

        if record is None:
            continue

        if (
            record.get(
                "record_type"
            )
            != "player"
        ):
            continue

        record.update(
            data
        )


def main():
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
        teams=12,
        position="all",
    )

    knowledge_base = (
        build_knowledge_base(
            adp_rank_lookup
        )
    )

    free_data = (
        retrieve_all_free_data(
            historical_seasons=(
                HISTORICAL_SEASONS
            ),
            current_season=(
                CURRENT_SEASON
            ),
            knowledge_base=(
                knowledge_base
            ),
        )
    )

    merge_player_data(
        knowledge_base,
        free_data[
            "fantasy_stats"
        ],
    )

    merge_player_data(
        knowledge_base,
        free_data[
            "availability"
        ],
    )

    merge_player_data(
        knowledge_base,
        free_data[
            "career_info"
        ],
    )

    merge_player_data(
        knowledge_base,
        free_data[
            "team_tendencies"
        ],
    )

    save_knowledge_base(
        knowledge_base
    )

    player_count = sum(
        1
        for record
        in knowledge_base.values()
        if (
            record.get(
                "record_type"
            )
            == "player"
        )
    )

    defense_count = sum(
        1
        for record
        in knowledge_base.values()
        if (
            record.get(
                "record_type"
            )
            == "team_defense"
        )
    )

    print(
        f"Saved {player_count} players "
        f"and {defense_count} defenses."
    )


if __name__ == "__main__":
    main()