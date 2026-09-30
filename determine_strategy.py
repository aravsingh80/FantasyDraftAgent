def determine_strategy():
    while True:
        print("\nSelect draft strategy:")
        print("1. Balanced")
        print("2. RB Heavy")
        print("3. WR Heavy")

        choice = input(
            "Choice: "
        ).strip()

        if choice == "1":
            return "balanced"

        if choice == "2":
            return "rb-heavy"

        if choice == "3":
            return "wr-heavy"

        print(
            "Please enter 1, 2, or 3.\n"
        )