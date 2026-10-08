import pandas as pd


def read_csv_raw(filepath: str) -> pd.DataFrame:
    """Read a CSV statement into a DataFrame without normalizing it."""
    try:
        return pd.read_csv(filepath)
    except Exception as error:
        raise ValueError(
            f"Could not read CSV file '{filepath}': {error}"
        ) from error