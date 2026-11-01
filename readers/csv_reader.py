import csv
import io
import re

import pandas as pd

from normalizer import HEADER_ALIASES


DELIMITER_CANDIDATES = (",", ";", "\t", "|")
TRANSACTION_FIELDS = {"date", "description", "amount", "debit", "credit"}
PROTECTED_FIELDS_AFTER_DESCRIPTION = {
    "transaction_type",
    "amount",
    "debit",
    "credit",
    "balance",
    "payment_mode",
}
DATE_LIKE_PATTERN = re.compile(
    r"^\s*(?:"
    r"\d{4}[./-]\d{1,2}[./-]\d{1,2}"
    r"|\d{1,2}[./-]\d{1,2}[./-]\d{2,4}"
    r"|\d{1,2}[-/ ][A-Za-z]{3,9}[-/ ]\d{2,4}"
    r"|\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}"
    r"|[A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4}"
    r")\b"
)


def _normalized_header(value: object) -> str:
    return re.sub(r"[\s_-]+", " ", str(value).strip()).casefold()


def _header_fields(header: list[str]) -> tuple[set[str], dict[int, str]]:
    alias_lookup = {
        _normalized_header(alias): standard_name
        for standard_name, aliases in HEADER_ALIASES.items()
        for alias in aliases
    }
    mapped = {
        index: alias_lookup[name]
        for index, value in enumerate(header)
        if (name := _normalized_header(value)) in alias_lookup
    }
    return set(mapped.values()), mapped


def _is_transaction_header(header: list[str]) -> bool:
    fields, _ = _header_fields(header)
    return (
        {"date", "description", "amount"}.issubset(fields)
        or {"date", "description", "debit", "credit"}.issubset(fields)
    )


def _decode_csv_file(filepath: str) -> str:
    with open(filepath, "rb") as csv_file:
        content = csv_file.read()

    for encoding in ("utf-8-sig", "utf-16", "cp1252"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue

    # cp1252 maps every byte, so this is only a defensive fallback.
    return content.decode("latin-1")


def _parse_with_delimiter(text: str, delimiter: str) -> list[list[str]]:
    return list(
        csv.reader(
            io.StringIO(text, newline=""),
            delimiter=delimiter,
            strict=False,
        )
    )


def _choose_table(text: str) -> tuple[str, list[list[str]], int] | None:
    delimiters = list(DELIMITER_CANDIDATES)
    try:
        detected = csv.Sniffer().sniff(
            text[:8192], delimiters="".join(DELIMITER_CANDIDATES)
        ).delimiter
        delimiters.insert(0, detected)
    except csv.Error:
        pass

    choices = []
    seen = set()
    for delimiter in delimiters:
        if delimiter in seen:
            continue
        seen.add(delimiter)
        try:
            rows = _parse_with_delimiter(text, delimiter)
        except csv.Error:
            continue

        # Bank exports sometimes put account metadata before the transaction
        # table. Find a recognizable header instead of treating that preamble
        # as a two-column CSV header.
        for header_index, row in enumerate(rows[:50]):
            if not _is_transaction_header(row):
                continue

            fields, mapped = _header_fields(row)
            field_score = len(fields & TRANSACTION_FIELDS)
            following_rows = [
                item for item in rows[header_index + 1:]
                if any(str(cell).strip() for cell in item)
            ]
            width_score = sum(
                len(item) >= len(row)
                for item in following_rows[:50]
            )
            # Prefer the table with the most transaction headings and data
            # rows. The recognized header matters more than Sniffer's guess.
            score = field_score * 100 + min(width_score, 50)
            choices.append((score, delimiter, rows, header_index))

    if not choices:
        return None

    _, delimiter, rows, header_index = max(choices, key=lambda item: item[0])
    return delimiter, rows, header_index


def _looks_like_amount(value: str) -> bool:
    text = value.strip()
    return not text or text in {"-", "—", "–"} or re.search(r"\d", text) is not None


def _row_starts_with_date(row: list[str], date_index: int) -> bool:
    """Check whether a short row looks like a transaction, not a footer."""
    candidates = []
    if 0 <= date_index < len(row):
        candidates.append(row[date_index])
    if row:
        candidates.append(row[0])
    return any(DATE_LIKE_PATTERN.search(str(value)) for value in candidates)


def _repair_row(
    row: list[str],
    header: list[str],
    delimiter: str,
    row_number: int,
) -> list[str]:
    expected = len(header)
    if len(row) == expected:
        return row
    if len(row) < expected:
        raise ValueError(
            f"CSV row {row_number} has {len(row)} fields, but the transaction "
            f"header has {expected}. Check for a missing delimiter or an "
            "unfinished quoted value."
        )

    _, mapped = _header_fields(header)
    description_index = next(
        (index for index, name in mapped.items() if name == "description"),
        None,
    )
    protected_indexes = [
        index
        for index, name in mapped.items()
        if index > (description_index if description_index is not None else -1)
        and name in PROTECTED_FIELDS_AFTER_DESCRIPTION
    ]

    if description_index is None or not protected_indexes:
        raise ValueError(
            f"CSV row {row_number} has {len(row)} fields, but the transaction "
            f"header has {expected}. Extra values cannot be assigned safely."
        )

    tail_start = min(protected_indexes)
    tail_count = expected - tail_start
    description_end = len(row) - tail_count
    if description_end <= description_index:
        raise ValueError(
            f"CSV row {row_number} has extra fields, but its description and "
            "amount columns cannot be separated safely."
        )

    repaired = (
        row[:description_index]
        + [delimiter.join(row[description_index:description_end]).strip()]
        + row[description_end:]
    )
    if len(repaired) != expected:
        raise ValueError(
            f"CSV row {row_number} could not be aligned with its transaction "
            "header without losing data."
        )

    # Avoid quietly moving stray text into the amount or balance fields.
    for index, name in mapped.items():
        if name in {"amount", "debit", "credit", "balance"}:
            if not _looks_like_amount(repaired[index]):
                raise ValueError(
                    f"CSV row {row_number} contains unexpected text in the "
                    f"'{header[index]}' column; the row was not changed."
                )

    return repaired


def _read_irregular_csv(text: str) -> pd.DataFrame:
    selected = _choose_table(text)
    if selected is None:
        raise ValueError(
            "Could not find a CSV transaction header. Include Date and "
            "Description, plus Amount or both Debit and Credit columns."
        )

    delimiter, rows, header_index = selected
    header = [cell.strip() for cell in rows[header_index]]
    _, mapped = _header_fields(header)
    date_index = next(
        (index for index, name in mapped.items() if name == "date"),
        0,
    )
    table_rows = rows[header_index + 1:]
    parsed_rows = []

    for table_position, row in enumerate(table_rows):
        row_index = header_index + table_position + 2
        if not any(str(cell).strip() for cell in row):
            continue
        if _is_transaction_header(row):
            continue

        if len(row) < len(header) and not _row_starts_with_date(row, date_index):
            # Some statement exports append a one-cell totals/footer line.
            # Ignore it only at the end of the table; a short row in between
            # date-bearing transactions remains an error so we never skip a
            # potentially lost transaction.
            later_transaction = any(
                _row_starts_with_date(later, date_index)
                for later in table_rows[table_position + 1:]
                if any(str(cell).strip() for cell in later)
            )
            if not later_transaction:
                break

        parsed_rows.append(_repair_row(row, header, delimiter, row_index))

    if not parsed_rows:
        raise ValueError("The CSV transaction header was found, but it has no transaction rows.")

    return pd.DataFrame(parsed_rows, columns=header)


def read_csv_raw(filepath: str) -> pd.DataFrame:
    """Read a CSV statement into a DataFrame without normalizing it."""
    try:
        # Preserve the project's original behavior for well-formed CSV files.
        return pd.read_csv(filepath)
    except Exception as original_error:
        try:
            text = _decode_csv_file(filepath)
            return _read_irregular_csv(text)
        except Exception as recovery_error:
            raise ValueError(
                f"Could not read CSV file '{filepath}': {original_error}. "
                "The added recovery attempt also could not parse it: "
                f"{recovery_error}"
            ) from original_error
