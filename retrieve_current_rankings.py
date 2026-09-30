def return_current_rankings(rankings, limit_value):
    current_rankings = []

    for player in rankings:
        if player is None:
            continue

        current_rankings.append(player)

        if len(current_rankings) == limit_value:
            break

    return current_rankings