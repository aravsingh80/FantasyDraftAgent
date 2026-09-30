import nflreadpy as nfl
import polars as pl

from normalize_names import (
    normalize_name,
    normalize_team,
)


OFFENSIVE_POSITIONS = {
    "QB",
    "RB",
    "WR",
    "TE",
}


def load_redraft_ecr():
    rankings = nfl.load_ff_rankings(
        "draft"
    )

    rankings = rankings.filter(
        (pl.col("ecr_type") == "rp")
        & (
            (
                (pl.col("pos") == "QB")
                & pl.col("page_type")
                .str.to_lowercase()
                .str.ends_with("qb")
            )
            |
            (
                (pl.col("pos") == "RB")
                & pl.col("page_type")
                .str.to_lowercase()
                .str.ends_with("rb")
            )
            |
            (
                (pl.col("pos") == "WR")
                & pl.col("page_type")
                .str.to_lowercase()
                .str.ends_with("wr")
            )
            |
            (
                (pl.col("pos") == "TE")
                & pl.col("page_type")
                .str.to_lowercase()
                .str.ends_with("te")
            )
        )
    )

    rankings = rankings.filter(
        pl.col("pos").is_in(
            list(
                OFFENSIVE_POSITIONS
            )
        )
    )

    return rankings


def get_ecr_lookup():
    rankings = load_redraft_ecr()

    lookup = {}

    for row in rankings.to_dicts():
        name = row.get(
            "player"
        )

        if not name:
            continue

        normalized_name = (
            normalize_name(
                name
            )
        )

        if not normalized_name:
            continue

        ecr = row.get(
            "ecr"
        )

        if ecr is None:
            continue

        lookup[
            normalized_name
        ] = {
            "name": name,
            "position": row.get(
                "pos"
            ),
            "team": (
                normalize_team(
                    row.get("tm")
                    or row.get("team")
                )
            ),
            "ecr": float(
                ecr
            ),
            "ecr_sd": (
                float(row["sd"])
                if row.get("sd")
                is not None
                else None
            ),
            "ecr_best": (
                float(
                    row["best"]
                )
                if row.get("best")
                is not None
                else None
            ),
            "ecr_worst": (
                float(
                    row["worst"]
                )
                if row.get("worst")
                is not None
                else None
            ),
            "ecr_rank_delta": (
                float(
                    row["rank_delta"]
                )
                if row.get(
                    "rank_delta"
                )
                is not None
                else None
            ),
            "ecr_scrape_date": (
                str(
                    row.get(
                        "scrape_date"
                    )
                )
            ),
        }

    print(
        "\nECR coverage:"
    )

    for position in [
        "QB",
        "RB",
        "WR",
        "TE",
    ]:
        count = sum(
            1
            for player
            in lookup.values()
            if player.get(
                "position"
            )
            == position
        )

        print(
            f"{position}: "
            f"{count} players"
        )

    print(
        f"Total ECR players: "
        f"{len(lookup)}"
    )

    return lookup