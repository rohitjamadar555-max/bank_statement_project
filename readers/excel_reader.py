import pandas as pd


def read_excel_raw(filepath: str) -> pd.DataFrame:
    """Read the first worksheet of an Excel statement."""
    try:
        return pd.read_excel(filepath)
    except Exception as error:
        raise ValueError(
            f"Could not read Excel file '{filepath}': {error}"
        ) from error