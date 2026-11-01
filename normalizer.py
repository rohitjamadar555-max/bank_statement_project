import re
import pandas as pd

from schema import OPTIONAL_COLUMNS, REQUIRED_COLUMNS, validate_schema


def _normalize_header(value: object) -> str:
    """Make column heading comparisons ignore case and extra spaces."""
    return re.sub(r"[\s_-]+", " ", str(value).strip()).casefold()


HEADER_ALIASES = {
    "date": (
        "date",
        "transaction date",
        "txn date",
        "posting date",
        "value date",
        "date time",
        "transaction date time",
    ),
    "description": (
        "description",
        "transaction description",
        "transaction details",
        "details",
        "narration",
        "particulars",
        "remarks",
        "merchant",
        "payee",
        "recipient",
    ),
    "amount": (
        "amount",
        "transaction amount",
        "signed amount",
    ),
    "debit": (
        "debit",
        "debit amount",
        "withdrawal",
        "withdrawal amount",
        "money out",
    ),
    "credit": (
        "credit",
        "credit amount",
        "deposit",
        "deposit amount",
        "money in",
    ),
    "balance": (
        "balance",
        "closing balance",
        "running balance",
    ),
    "transaction_type": (
        "type",
        "transaction type",
        "txn type",
    ),
    "payment_mode": (
        "payment mode",
        "mode",
        "channel",
        "payment method",
    ),
}


def _infer_common_config(df: pd.DataFrame) -> dict | None:
    """Build a safe mapping for common transaction heading names."""
    headers = {_normalize_header(column): column for column in df.columns}
    resolved = {}

    for standard_name, aliases in HEADER_ALIASES.items():
        for alias in aliases:
            actual_header = headers.get(_normalize_header(alias))
            if actual_header is not None:
                resolved[actual_header] = standard_name
                break

    standard_names = set(resolved.values())
    if not {"date", "description"}.issubset(standard_names):
        return None

    if {"debit", "credit"}.issubset(standard_names):
        amount_mode = "debit_credit"
    elif "amount" in standard_names:
        amount_mode = "signed"
    else:
        return None

    return {
        "column_map": resolved,
        "amount_mode": amount_mode,
        "date_format": None,
        "dayfirst": True,
        "currency": "INR",
    }


def _parse_amount(value: object, column_name: str, row_number: int) -> float:
    """Parse a bank amount and include its row number if it cannot be read."""
    if pd.isna(value) or str(value).strip() == "":
        return float("nan")

    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip()
    negative = text.startswith("(") and text.endswith(")")
    text = text.strip("()").strip()

    text = re.sub(r"[₹$€£]", "", text)
    text = re.sub(
        r"\bINR\b|\bUSD\b|\bEUR\b|\bGBP\b|\bRs\.?",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = text.replace(",", "").replace(" ", "")

    if text.startswith("-"):
        negative = True
        text = text[1:]

    try:
        number = float(text)
    except ValueError:
        raise ValueError(
            f"Unreadable value {value!r} in '{column_name}' "
            f"on statement row {row_number}"
        ) from None

    return -abs(number) if negative else number


def detect_bank_config(df: pd.DataFrame, configs: dict) -> tuple[str, dict]:
    """Choose the unique bank configuration with the most matching headings."""
    input_headers = {_normalize_header(column) for column in df.columns}
    matches = []

    for name, config in configs.items():
        expected_headers = {
            _normalize_header(column)
            for column in config["column_map"]
        }
        score = len(input_headers & expected_headers)

        required = {"date", "description"}
        if config.get("amount_mode", "signed") == "debit_credit":
            required.update({"debit", "credit"})
        else:
            required.add("amount")

        mapped_headers = {
            _normalize_header(raw_header): standard_header
            for raw_header, standard_header in config["column_map"].items()
        }
        present_fields = {
            mapped_headers[header]
            for header in input_headers
            if header in mapped_headers
        }

        if score and required.issubset(present_fields):
            matches.append((name, config, score))

    if not matches:
        inferred = _infer_common_config(df)
        if inferred is not None:
            return "common_columns", inferred
        raise ValueError(
            "Could not recognize a complete transaction layout in these "
            f"columns: {list(df.columns)}. Include Date, Description, and "
            "Amount, or both Debit and Credit columns."
        )

    best_score = max(score for _, _, score in matches)
    best_matches = [
        (name, config)
        for name, config, score in matches
        if score == best_score
    ]

    if len(best_matches) > 1:
        names = [name for name, _ in best_matches]
        raise ValueError(
            f"More than one bank format matches this file: {names}. "
            "Choose the correct configuration."
        )

    return best_matches[0]


def normalize(
    df: pd.DataFrame,
    config: dict,
    source_file: str | None = None,
) -> pd.DataFrame:
    """Convert raw bank columns into the project's standard transaction columns."""
    result = df.copy()

    # Match raw headings to configured headings, ignoring case and spaces.
    header_lookup = {_normalize_header(column): column for column in result.columns}
    rename_map = {}

    for raw_header, standard_header in config["column_map"].items():
        found_header = header_lookup.get(_normalize_header(raw_header))
        if found_header is not None:
            rename_map[found_header] = standard_header

    result = result.rename(columns=rename_map)

    missing = [
        column
        for column in ("date", "description")
        if column not in result.columns
    ]
    if missing:
        raise ValueError(f"Statement is missing required columns: {missing}")

    
            # Try common date formats, or use the format set for this bank.
    date_format = config.get("date_format")
    raw_dates = result["date"].astype("string").str.strip()

    if date_format:
        parsed_dates = pd.to_datetime(
            raw_dates,
            format=date_format,
            errors="coerce",
        )
    else:

        iso_mask = raw_dates.str.match(
        r"^\d{4}-\d{2}-\d{2}(?:[ T].*)?$",
        na=False,
    )

    parsed_dates = pd.Series(
        pd.NaT,
        index=result.index,
        dtype="datetime64[ns]",
    )

    # ISO dates: YYYY-MM-DD must not use dayfirst.
    parsed_dates.loc[iso_mask] = pd.to_datetime(
        raw_dates.loc[iso_mask],
        errors="coerce",
    )

    # Other formats follow the bank's dayfirst setting.
    parsed_dates.loc[~iso_mask] = pd.to_datetime(
        raw_dates.loc[~iso_mask],
        format="mixed",
        errors="coerce",
        dayfirst=config.get("dayfirst", True),
    )

    result["date"] = parsed_dates

     # Convert amount columns while keeping the statement row number in errors.
    amount_mode = config.get("amount_mode", "signed")

    if amount_mode == "debit_credit":
        if "debit" not in result.columns or "credit" not in result.columns:
            raise ValueError(
                "This configuration needs both Debit and Credit columns."
            )

        debit_values = [
            _parse_amount(value, "debit", row_number)
            for row_number, value in enumerate(result["debit"], start=2)
        ]
        credit_values = [
            _parse_amount(value, "credit", row_number)
            for row_number, value in enumerate(result["credit"], start=2)
        ]

        debit = pd.Series(debit_values, index=result.index)
        credit = pd.Series(credit_values, index=result.index)

        both_blank = debit.isna() & credit.isna()
        if both_blank.any():
            rows = [
                position + 2
                for position, is_blank in enumerate(both_blank.tolist())
                if is_blank
            ]
            raise ValueError(
                f"Both Debit and Credit are blank at statement row(s): {rows}"
            )

        result["amount"] = credit.fillna(0) - debit.fillna(0)
        result = result.drop(columns=["debit", "credit"])

    elif amount_mode == "signed":
        if "amount" not in result.columns:
            raise ValueError(
                "This configuration needs an Amount column."
            )

        result["amount"] = [
            _parse_amount(value, "amount", row_number)
            for row_number, value in enumerate(result["amount"], start=2)
        ]

    else:
        raise ValueError(f"Unsupported amount_mode: {amount_mode!r}")

    if "transaction_type" in result.columns:
        transaction_types = (
            result["transaction_type"]
            .astype("string")
            .str.strip()
            .str.casefold()
            .str.replace(r"\.+$", "", regex=True)
        )
        debit_types = {
            "debit", "dr", "withdrawal", "withdraw", "payment", "paid",
            "expense", "sent", "outgoing",
        }
        credit_types = {
            "credit", "cr", "deposit", "received", "receipt", "income",
            "refund", "incoming",
        }
        debit_mask = transaction_types.isin(debit_types)
        credit_mask = transaction_types.isin(credit_types)
        result.loc[debit_mask, "amount"] = -result.loc[debit_mask, "amount"].abs()
        result.loc[credit_mask, "amount"] = result.loc[credit_mask, "amount"].abs()
        result = result.drop(columns=["transaction_type"])

    if "balance" in result.columns:
        result["balance"] = [
            _parse_amount(value, "balance", row_number)
            for row_number, value in enumerate(result["balance"], start=2)
        ]

    result["description"] = result["description"].astype("string").str.strip()

    if "currency" not in result.columns:
        result["currency"] = config.get("currency")
    result["source_file"] = source_file

    for column in OPTIONAL_COLUMNS:
        if column not in result.columns:
            result[column] = pd.NA

    result = result[REQUIRED_COLUMNS + OPTIONAL_COLUMNS]

    # Sort transactions chronologically, oldest first.
    result = result.sort_values(
        by="date",
        ascending=True,
        na_position="last",
        kind="stable",
    ).reset_index(drop=True)

    validate_schema(result)

    return result



def find_duplicate_candidates(df: pd.DataFrame) -> pd.DataFrame:
    """Find exact duplicate transactions after normalizing formatting."""

    required = {"date", "description", "amount"}
    missing = required - set(df.columns)

    if missing:
        raise ValueError(
            f"Cannot find duplicates; missing columns: {sorted(missing)}"
        )

    normalized = pd.DataFrame(index=df.index)

    normalized["date"] = pd.to_datetime(
        df["date"], errors="coerce"
    ).dt.normalize()

    normalized["description"] = (
        df["description"]
        .astype("string")
        .str.casefold()
        .str.replace(r"[\W_]+", " ", regex=True)
        .str.strip()
        .str.replace(r"\s+", " ", regex=True)
    )

    normalized["amount"] = pd.to_numeric(
        df["amount"], errors="coerce"
    ).round(2)

    valid = normalized.notna().all(axis=1)

    duplicate_mask = (
        normalized.loc[valid]
        .duplicated(
            subset=["date", "description", "amount"],
            keep=False,
        )
    )

    result_mask = pd.Series(False, index=df.index)
    result_mask.loc[duplicate_mask.index] = duplicate_mask

    return df.loc[result_mask].sort_values(
        ["date", "description", "amount"]
    )
