import pandas as pd


REQUIRED_COLUMNS = ["date", "description", "amount"]
OPTIONAL_COLUMNS = ["balance", "payment_mode", "currency", "source_file"]


def _statement_rows(problem_mask: pd.Series) -> list[int]:
    """Return human-friendly row numbers; row 1 is assumed to be the header."""
    return [
        position + 2
        for position, has_problem in enumerate(problem_mask.tolist())
        if has_problem
    ]


def validate_schema(df: pd.DataFrame) -> None:
    """Check that normalized transactions have the expected columns and values."""
    missing_columns = [
        column for column in REQUIRED_COLUMNS if column not in df.columns
    ]
    if missing_columns:
        raise ValueError(f"Missing required column(s): {missing_columns}")

    if not pd.api.types.is_datetime64_any_dtype(df["date"]):
        raise TypeError("'date' column must contain dates.")

    if not pd.api.types.is_numeric_dtype(df["amount"]):
        raise TypeError("'amount' column must contain numbers.")

    bad_dates = df["date"].isna()
    if bad_dates.any():
        raise ValueError(
            "Missing or unreadable date(s) at statement row(s): "
            f"{_statement_rows(bad_dates)}"
        )

    bad_amounts = df["amount"].isna()
    if bad_amounts.any():
        raise ValueError(
            "Missing or unreadable amount(s) at statement row(s): "
            f"{_statement_rows(bad_amounts)}"
        )

    descriptions = df["description"].astype("string").str.strip()
    bad_descriptions = descriptions.isna() | descriptions.eq("")
    if bad_descriptions.any():
        raise ValueError(
            "Missing transaction description(s) at statement row(s): "
            f"{_statement_rows(bad_descriptions)}"
        )