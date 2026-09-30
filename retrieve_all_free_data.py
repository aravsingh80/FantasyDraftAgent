from retrieve_availability import get_availability_data
from retrieve_career_info import get_career_info
from retrieve_fantasy_stats import get_fantasy_stats
from retrieve_team_tendencies import get_team_tendencies


def retrieve_all_free_data(
    historical_seasons,
    current_season,
    knowledge_base,
):
    return {
        "fantasy_stats": get_fantasy_stats(
            historical_seasons
        ),
        "availability": get_availability_data(
            historical_seasons
        ),
        "career_info": get_career_info(
            current_season,
            knowledge_base,
        ),
        "team_tendencies": get_team_tendencies(
            historical_seasons,
            knowledge_base,
        ),
    }