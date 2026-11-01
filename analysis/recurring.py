import pandas as pd


def find_recurring(
    df: pd.DataFrame,
    min_occurrences: int = 3,
    day_tolerance: int = 5,
    amount_tolerance_percent: float = 10.0,
) -> pd.DataFrame:
    """Detect repeated income and expenses with confidence levels."""

    required = {"date", "description", "amount"}
    missing = required - set(df.columns)

    if missing:
        raise ValueError(
            f"Cannot find recurring transactions; missing columns: {sorted(missing)}"
        )

    if min_occurrences < 2:
        raise ValueError("min_occurrences must be at least 2.")

    if day_tolerance < 0 or amount_tolerance_percent < 0:
        raise ValueError("Tolerances cannot be negative.")

    columns = [
        "description",
        "schedule",
        "occurrences",
        "matching_intervals",
        "average_amount",
        "type",
        "confidence",
         "next_expected_date",
    ]

    transactions = df.loc[
        pd.to_numeric(df["amount"], errors="coerce").ne(0),
        ["date", "description", "amount"],
    ].copy()

    transactions["date"] = pd.to_datetime(
        transactions["date"], errors="coerce"
    )
    transactions["amount"] = pd.to_numeric(
        transactions["amount"], errors="coerce"
    )

    transactions["description"] = (
        transactions["description"]
        .astype("string")
        .str.casefold()
        .str.replace(r"[^a-z0-9]+", " ", regex=True)
        .str.strip()
    )

    transactions = transactions.dropna(
        subset=["date", "description", "amount"]
    )
    transactions = transactions.loc[
        transactions["description"].ne("")
    ]

    transactions["type"] = transactions["amount"].apply(
        lambda amount: "income" if amount > 0 else "expense"
    )

    schedules = [
        ("daily repeated", 1, 0),
        ("near-daily repeated", 2, 1),
        ("weekly", 7, day_tolerance),
        ("monthly", 30, day_tolerance),
        ("every 2 months", 61, day_tolerance),
        ("yearly", 365, day_tolerance),
    ]

    found = []

    for transaction_type, type_group in transactions.groupby("type"):

        for description, group in type_group.groupby("description"):
            group = group.sort_values("date").copy()

            median_amount = abs(float(group["amount"].median()))

            if median_amount == 0:
                continue

            deviation = (
                (group["amount"].abs() - median_amount).abs()
                / median_amount
            ) * 100

            group = group.loc[
                deviation <= amount_tolerance_percent
            ]

            daily_amounts = (
                group.groupby("date")["amount"]
                .mean()
                .sort_index()
            )

            dates = list(daily_amounts.index)

            # Two matching occurrences are enough for a possible pattern.
            if len(dates) < 2:
                continue

            used_dates = set()

            gaps = [
                (dates[i] - dates[i - 1]).days
                for i in range(1, len(dates))
            ]

            for schedule, expected_days, tolerance in schedules:
                matching = [
                    abs(gap - expected_days) <= tolerance
                    for gap in gaps
                ]

                start = 0

                while start < len(matching):
                    if not matching[start]:
                        start += 1
                        continue

                    end = start

                    while (
                        end + 1 < len(matching)
                        and matching[end + 1]
                    ):
                        end += 1

                    run_dates = dates[start:end + 2]

                    available_dates = [
                        date for date in run_dates
                        if date not in used_dates
                    ]

                    available_intervals = sum(
                        1
                        for i in range(start, end + 1)
                        if dates[i] not in used_dates
                        and dates[i + 1] not in used_dates
                    )

                    if (
                        len(available_dates) >= 2
                        and available_intervals >= 1
                    ):
                        selected = group.loc[
                            group["date"].isin(available_dates)
                        ]

                        occurrence_count = len(available_dates)

                        if occurrence_count >= 4:
                            confidence = "Strong"
                        elif occurrence_count >= min_occurrences:
                            confidence = "Likely"
                        else:
                            confidence = "Possible"

                        last_date = max(available_dates)

                        if schedule == "daily repeated":
                            next_date = last_date + pd.Timedelta(days=1)
                        elif schedule == "near-daily repeated":
                            next_date = last_date + pd.Timedelta(days=2)
                        elif schedule == "weekly":
                            next_date = last_date + pd.Timedelta(days=7)
                        elif schedule == "monthly":
                            next_date = last_date + pd.DateOffset(months=1)
                        elif schedule == "every 2 months":
                            next_date = last_date + pd.DateOffset(months=2)
                        elif schedule == "yearly":
                            next_date = last_date + pd.DateOffset(years=1)
                        else:
                            next_date = pd.NaT
                        found.append({
                            "description": description,
                            "schedule": schedule,
                            "occurrences": occurrence_count,
                            "matching_intervals": available_intervals,
                            "average_amount": round(
                                float(selected["amount"].mean()), 2
                            ),
                            "type": transaction_type,
                            "confidence": confidence,
                            "next_expected_date": (
                                next_date.date().isoformat()
                                if pd.notna(next_date)
                                else None
                            ),
                        })

                        used_dates.update(available_dates)

                    start = end + 1

    return pd.DataFrame(found, columns=columns).sort_values(
        ["matching_intervals", "occurrences"],
        ascending=False,
        ignore_index=True,
    )