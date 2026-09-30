import re
import unicodedata


def normalize_name(name):
    if name is None:
        return ""

    name = str(name)

    name = unicodedata.normalize(
        "NFKD",
        name,
    )

    name = (
        name
        .encode("ascii", "ignore")
        .decode("ascii")
        .lower()
    )

    name = re.sub(
        r"\b(jr|sr|ii|iii|iv|v)\b\.?",
        "",
        name,
    )

    name = re.sub(
        r"[^a-z0-9 ]",
        "",
        name,
    )

    return " ".join(
        name.split()
    )


def normalize_team(team):
    if team is None:
        return None

    team = str(team).strip().upper()

    team_aliases = {
        "JAX": "JAC",
        "WSH": "WAS",
    }

    return team_aliases.get(
        team,
        team,
    )


def normalize_position(position):
    if position is None:
        return None

    position = (
        str(position)
        .strip()
        .upper()
    )

    position_aliases = {
        "HB": "RB",
        "FB": "RB",
        "PK": "K",
        "DEF": "DST",
        "D/ST": "DST",
    }

    return position_aliases.get(
        position,
        position,
    )