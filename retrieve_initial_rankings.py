import requests

from normalize_names import (
    normalize_name,
    normalize_position,
    normalize_team,
)


def get_adp_rankings(
    year=2026,
    scoring="ppr",
    teams=12,
    position="all",
):
    url = (
        "https://fantasyfootballcalculator.com/api/v1/adp/"
        f"{scoring}?teams={teams}&year={year}&position={position}"
    )

    response = requests.get(url, timeout=15)
    response.raise_for_status()

    data = response.json()
    rankings = []

    for player in data.get("players", []):
        name = player.get("name")
        player_position = normalize_position(
            player.get("position")
        )
        adp = player.get("adp")

        if not name or not player_position or adp is None:
            continue

        rankings.append({
            "name": name,
            "position": player_position,
            "team": normalize_team(player.get("team")) or "FA",
            "adp": float(adp),
        })

    rankings.sort(key=lambda player: player["adp"])

    overall_rankings = [
        player["name"]
        for player in rankings
    ]

    qb_rankings = [
        player["name"]
        for player in rankings
        if player["position"] == "QB"
    ]

    rb_rankings = [
        player["name"]
        for player in rankings
        if player["position"] == "RB"
    ]

    wr_rankings = [
        player["name"]
        for player in rankings
        if player["position"] == "WR"
    ]

    te_rankings = [
        player["name"]
        for player in rankings
        if player["position"] == "TE"
    ]

    k_rankings = [
        player["name"]
        for player in rankings
        if player["position"] == "K"
    ]

    dst_rankings = [
        player["name"]
        for player in rankings
        if player["position"] == "DST"
    ]

    adp_rank_lookup = {}
    position_counts = {}

    for overall_index, player in enumerate(
        rankings,
        start=1,
    ):
        normalized_name = normalize_name(
            player["name"]
        )
        player_position = player["position"]

        position_counts[player_position] = (
            position_counts.get(player_position, 0)
            + 1
        )

        adp_rank_lookup[normalized_name] = {
            "name": player["name"],
            "team": player["team"],
            "adp": player["adp"],
            "position": player_position,
            "overall_ranking": overall_index,
            "position_ranking": position_counts[
                player_position
            ],
        }

    return (
        overall_rankings,
        qb_rankings,
        rb_rankings,
        wr_rankings,
        te_rankings,
        k_rankings,
        dst_rankings,
        adp_rank_lookup,
    )