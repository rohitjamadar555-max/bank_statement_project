import pandas as pd


def total_spending(df: pd.DataFrame) -> float:
    """Return expenses as a positive total for easier reading."""
    expenses = df.loc[df["amount"] < 0, "amount"]
    return float(expenses.abs().sum())


def total_income(df: pd.DataFrame) -> float:
    """Return the total of positive transaction amounts."""
    income = df.loc[df["amount"] > 0, "amount"]
    return float(income.sum())


def spending_by_category(df: pd.DataFrame) -> pd.Series:
    """Return positive spending totals, ordered from largest to smallest."""
    expenses = df.loc[df["amount"] < 0].copy()
    expenses["amount"] = expenses["amount"].abs()

    if "category" not in expenses.columns:
        raise ValueError("Cannot group spending: 'category' is missing.")

    return expenses.groupby("category")["amount"].sum().sort_values(
        ascending=False
    )


def uncategorized_ratio(df: pd.DataFrame) -> float:
    """Return the percentage of transactions without a known category."""
    if df.empty:
        return 0.0

    if "category" not in df.columns:
        raise ValueError("Cannot count uncategorized transactions: 'category' is missing.")

    count = df["category"].eq("uncategorized").sum()
    return round(float(count / len(df) * 100), 2)


def generate_summary(df: pd.DataFrame) -> None:
    """Print a readable statement summary."""
    if "amount" not in df.columns:
        raise ValueError("Cannot create summary: 'amount' is missing.")

    print("===== BANK STATEMENT SUMMARY =====")
    print(f"Total transactions : {len(df)}")
    print(f"Total spending     : {total_spending(df):.2f}")
    print(f"Total income       : {total_income(df):.2f}")

    if "category" in df.columns:
        print(f"Uncategorized      : {uncategorized_ratio(df):.2f}% of transactions")
        print("\nSpending by category:")
        print(spending_by_category(df))