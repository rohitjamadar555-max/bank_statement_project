import pandas as pd


def find_recurring(
    df: pd.DataFrame,
    min_occurrences: int = 3,
    day_tolerance: int = 5,
) -> pd.DataFrame:
    """Find repeated expenses with similar descriptions and regular intervals."""
    required = {"date", "description", "amount"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(
            f"Cannot find recurring expenses; missing columns: {sorted(missing)}"
        )

    if min_occurrences < 2:
        raise ValueError("min_occurrences must be at least 2.")
    if day_tolerance < 0:
        raise ValueError("day_tolerance cannot be negative.")

    columns = [
        "description",
        "schedule",
        "occurrences",
        "matching_intervals",
        "average_amount",
    ]

    expenses = df.loc[df["amount"] < 0, ["date", "description", "amount"]].copy()
    expenses["date"] = pd.to_datetime(expenses["date"], errors="coerce")
    expenses["description"] = (
        expenses["description"].astype("string").str.strip().str.casefold()
    )
    expenses = expenses.dropna(subset=["date", "description"])
    expenses = expenses.loc[expenses["description"].ne("")]

    schedule_days = {
        "weekly": 7,
        "monthly": 30,
        "every 2 months": 61,
        "yearly": 365,
    }

    found = []

    for description, group in expenses.groupby("description"):
        group = group.sort_values("date")
        # Keep same-day repeated transactions as separate rows; they don't form
        # a positive interval, so they won't falsely establish a schedule.
        dates = group["date"].drop_duplicates().reset_index(drop=True)

        if len(dates) < min_occurrences:
            continue

        gaps = dates.diff().dt.days.dropna()

        for schedule, expected_days in schedule_days.items():
            matching = gaps.between(
                expected_days - day_tolerance,
                expected_days + day_tolerance,
            )
            matching_intervals = int(matching.sum())

            if matching_intervals >= min_occurrences - 1:
                found.append(
                    {
                        "description": description,
                        "schedule": schedule,
                        "occurrences": len(dates),
                        "matching_intervals": matching_intervals,
                        "average_amount": round(float(group["amount"].mean()), 2),
                    }
                )
                break

    return pd.DataFrame(found, columns=columns).sort_values(
        "matching_intervals",
        ascending=False,
        ignore_index=True,
    )