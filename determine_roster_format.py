STANDARD_FLEX = {
    "QB": 1,
    "RB": 2,
    "WR": 2,
    "TE": 1,
    "FLEX": 1,
    "SUPER_FLEX": 0,
    "DST": 1,
    "K": 1,
}


SUPERFLEX = {
    "QB": 1,
    "RB": 2,
    "WR": 2,
    "TE": 1,
    "FLEX": 1,
    "SUPER_FLEX": 1,
    "DST": 1,
    "K": 1,
}


def get_int_setting(
    settings,
    keys,
    default=0,
):
    for key in keys:
        value = settings.get(
            key
        )

        if value is None:
            continue

        try:
            return int(value)

        except (
            TypeError,
            ValueError,
        ):
            continue

    return default


def get_roster_format_from_draft(
    draft_data,
):
    settings = draft_data.get(
        "settings",
        {},
    )

    starter_requirements = {
        "QB": get_int_setting(
            settings,
            [
                "slots_qb",
            ],
            1,
        ),
        "RB": get_int_setting(
            settings,
            [
                "slots_rb",
            ],
            2,
        ),
        "WR": get_int_setting(
            settings,
            [
                "slots_wr",
            ],
            2,
        ),
        "TE": get_int_setting(
            settings,
            [
                "slots_te",
            ],
            1,
        ),
        "FLEX": get_int_setting(
            settings,
            [
                "slots_flex",
            ],
            1,
        ),
        "SUPER_FLEX": get_int_setting(
            settings,
            [
                "slots_super_flex",
                "slots_superflex",
            ],
            0,
        ),
        "DST": get_int_setting(
            settings,
            [
                "slots_def",
                "slots_dst",
            ],
            1,
        ),
        "K": get_int_setting(
            settings,
            [
                "slots_k",
            ],
            1,
        ),
    }

    if (
        starter_requirements[
            "SUPER_FLEX"
        ]
        > 0
    ):
        roster_format = (
            "superflex"
        )

    else:
        roster_format = (
            "standard-flex"
        )

    return (
        roster_format,
        starter_requirements,
    )


def determine_roster_format():
    while True:
        print(
            "\nSelect roster format:"
        )
        print(
            "1. Standard Flex"
        )
        print(
            "2. Superflex"
        )

        choice = input(
            "Choice: "
        ).strip()

        if choice == "1":
            return (
                "standard-flex",
                STANDARD_FLEX.copy(),
            )

        if choice == "2":
            return (
                "superflex",
                SUPERFLEX.copy(),
            )

        print(
            "Please enter 1 or 2.\n"
        )


def determine_draft_slot():
    while True:
        try:
            draft_slot = int(
                input(
                    "What is your "
                    "draft slot? "
                )
            )

            if draft_slot > 0:
                return draft_slot

            print(
                "Draft slot must be "
                "a positive integer.\n"
            )

        except ValueError:
            print(
                "Please enter a valid "
                "integer.\n"
            )