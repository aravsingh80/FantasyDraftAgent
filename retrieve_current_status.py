import nflreadpy as nfl
import polars as pl

from normalize_names import normalize_name


def get_current_status(season):
    output = {}

    try:
        injuries = nfl.load_injuries([season])

        injuries = injuries.with_columns(
            pl.col("full_name")
            .map_elements(
                normalize_name,
                return_dtype=pl.String,
            )
            .alias("normalized_name")
        )

        latest_week = injuries.select(
            pl.col("week").max()
        ).item()

        latest_injuries = injuries.filter(
            pl.col("week") == latest_week
        )

        for row in latest_injuries.to_dicts():
            normalized_name = row[
                "normalized_name"
            ]

            output.setdefault(
                normalized_name,
                {},
            )

            output[normalized_name].update({
                "current_injury_status": (
                    row.get("report_status")
                ),
                "current_injury": (
                    row.get(
                        "report_primary_injury"
                    )
                ),
                "practice_status": (
                    row.get("practice_status")
                ),
                "status_week": row.get("week"),
            })

    except Exception:
        pass

    try:
        rosters = nfl.load_rosters_weekly(
            [season]
        )

        status_column = next(
            (
                column
                for column in [
                    "status",
                    "roster_status",
                ]
                if column in rosters.columns
            ),
            None,
        )

        name_column = next(
            (
                column
                for column in [
                    "full_name",
                    "player_name",
                ]
                if column in rosters.columns
            ),
            None,
        )

        if status_column and name_column:
            latest_week = rosters.select(
                pl.col("week").max()
            ).item()

            latest_rosters = rosters.filter(
                pl.col("week") == latest_week
            )

            latest_rosters = (
                latest_rosters.with_columns(
                    pl.col(name_column)
                    .map_elements(
                        normalize_name,
                        return_dtype=pl.String,
                    )
                    .alias("normalized_name")
                )
            )

            for row in latest_rosters.to_dicts():
                normalized_name = row[
                    "normalized_name"
                ]

                output.setdefault(
                    normalized_name,
                    {},
                )

                status = row.get(status_column)

                output[normalized_name][
                    "current_roster_status"
                ] = status

                output[normalized_name][
                    "current_suspension_status"
                ] = (
                    "SUS"
                    if status == "SUS"
                    else None
                )

    except Exception:
        pass

    return output