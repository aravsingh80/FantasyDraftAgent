import nflreadpy as nfl
import polars as pl

from normalize_names import normalize_name


def get_depth_chart_data(season):
    depth_charts = nfl.load_depth_charts(
        [season]
    )

    name_column = next(
        (
            column
            for column in [
                "full_name",
                "player_name",
                "name",
            ]
            if column in depth_charts.columns
        ),
        None,
    )

    position_column = next(
        (
            column
            for column in [
                "pos_abb",
                "position",
                "position_name",
            ]
            if column in depth_charts.columns
        ),
        None,
    )

    rank_column = next(
        (
            column
            for column in [
                "pos_rank",
                "depth_position",
                "depth_chart_order",
                "rank",
            ]
            if column in depth_charts.columns
        ),
        None,
    )

    team_column = next(
        (
            column
            for column in [
                "depth_team",
                "team",
                "club_code",
            ]
            if column in depth_charts.columns
        ),
        None,
    )

    if name_column is None:
        return {}

    sort_columns = []

    for column in [
        "dt",
        "date",
        "week",
    ]:
        if column in depth_charts.columns:
            sort_columns.append(column)

    if sort_columns:
        depth_charts = depth_charts.sort(
            sort_columns,
            descending=True,
        )

    depth_charts = depth_charts.with_columns(
        pl.col(name_column)
        .map_elements(normalize_name, return_dtype=pl.String)
        .alias("normalized_name")
    )

    latest = depth_charts.unique(
        subset=["normalized_name"],
        keep="first",
    )

    output = {}

    for row in latest.to_dicts():
        normalized_name = row["normalized_name"]
        position = (
            row.get(position_column)
            if position_column
            else None
        )
        rank = (
            row.get(rank_column)
            if rank_column
            else None
        )

        output[normalized_name] = {
            "depth_chart_position": rank,
            "depth_chart_role": (
                f"{position}{rank}"
                if position is not None
                and rank is not None
                else position
            ),
            "depth_chart_team": (
                row.get(team_column)
                if team_column
                else None
            ),
        }

    return output