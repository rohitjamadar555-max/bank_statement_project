import re
from difflib import SequenceMatcher

import pandas as pd
import pdfplumber

from readers.ocr_reader import parse_statement_text, read_image_object


TEXT_TABLE_SETTINGS = {
    "vertical_strategy": "text",
    "horizontal_strategy": "text",
    "intersection_tolerance": 5,
}

HEADER_ALIASES = {
    "date": {"date", "transaction date", "txn date", "posting date", "value date"},
    "description": {
        "description", "transaction description", "transaction details",
        "details", "narration", "particulars", "remarks", "merchant",
    },
    "amount": {"amount", "transaction amount", "signed amount"},
    "debit": {"debit", "debit amount", "withdrawal", "withdrawal amount"},
    "credit": {"credit", "credit amount", "deposit", "deposit amount"},
    "balance": {"balance", "closing balance", "running balance"},
    "transaction_type": {"type", "transaction type", "txn type"},
}


def _repair_doubled_header_cell(value: object) -> str:
    """Repair duplicated or slightly truncated PDF table headings."""
    label = str(value or "").strip()
    if len(label) < 4 or len(label) % 2:
        return label

    if not all(label[index] == label[index + 1] for index in range(0, len(label), 2)):
        return label

    collapsed = label[::2]
    known_labels = set().union(*HEADER_ALIASES.values()) | {"transaction", "type"}
    if collapsed.casefold() in known_labels:
        return collapsed

    # Some PDF text layers duplicate most letters but also omit a few. For
    # example, "AAmmoouu" collapses to "Amou". Only fuzzy-match this damaged
    # paired-text pattern, and require a clear, high-confidence winner so
    # ordinary unknown headings are not silently reinterpreted.
    ranked = sorted(
        (
            (SequenceMatcher(None, collapsed.casefold(), candidate).ratio(), candidate)
            for candidate in known_labels
        ),
        reverse=True,
    )
    if ranked:
        best_score, best_label = ranked[0]
        next_score = ranked[1][0] if len(ranked) > 1 else 0.0
        if best_score >= 0.78 and best_score - next_score >= 0.12:
            return best_label

    return label


def _canonical_table_header(header: list[object]) -> list[str]:
    canonical = {}
    for standard_name, aliases in HEADER_ALIASES.items():
        canonical.update({alias: standard_name for alias in aliases})

    normalized = []
    for cell in header:
        repaired = _repair_doubled_header_cell(cell)
        label = re.sub(r"[\s_-]+", " ", repaired.casefold())
        normalized.append(canonical.get(label, label))
    return normalized


def _is_transaction_header(header: list[object] | None) -> bool:
    if not header:
        return False
    fields = set(_canonical_table_header(header))
    return (
        {"date", "description", "amount"}.issubset(fields)
        or {"date", "description", "debit", "credit"}.issubset(fields)
    )


def _has_corrupt_amount_cells(
    header: list[object] | None,
    rows: list[list[object]],
) -> bool:
    """Return true when PDF text extraction produced unusable amount text.

    Some PDFs draw digits with a custom font whose character map is missing or
    broken. pdfplumber can then return a currency symbol followed by NUL bytes
    instead of the amount that is visibly printed on the page. Those values
    should be recovered from a rendered page with OCR, not sent to the numeric
    normalizer.
    """
    if not header or not rows:
        return False

    canonical_header = _canonical_table_header(header)
    amount_indexes = [
        index
        for index, name in enumerate(canonical_header)
        if name in {"amount", "debit", "credit"}
    ]
    if not amount_indexes:
        return False

    for row in rows:
        for index in amount_indexes:
            if index >= len(row):
                continue
            value = row[index]
            if value is None or not str(value).strip():
                continue

            text = str(value).strip()
            if "\x00" in text:
                return True

            # A currency marker with no digits is another sign that the PDF
            # font map dropped the amount glyphs. Leave ordinary dash markers
            # in debit/credit columns alone; banks commonly use them for blanks.
            has_currency_marker = (
                any(symbol in text for symbol in ("â‚¹", "$", "â‚¬", "Â£"))
                or re.search(
                    r"\b(?:INR|USD|EUR|GBP|Rs\.?)\b",
                    text,
                    flags=re.IGNORECASE,
                ) is not None
            )
            if has_currency_marker and not re.search(r"\d", text):
                return True

    return False


def _table_quality(table: list[list[object]]) -> int:
    """Score a candidate table by its non-empty cells and usable rows."""
    if not table:
        return 0

    non_empty = sum(
        1
        for row in table
        for cell in row
        if cell is not None and str(cell).strip()
    )
    headings = " ".join(_canonical_table_header(table[0]))
    transaction_heading_count = sum(
        term in headings
        for term in (
            "date",
            "description",
            "details",
            "narration",
            "particulars",
            "amount",
            "debit",
            "credit",
            "withdrawal",
            "deposit",
            "balance",
        )
    )
    return (
        non_empty
        + max(0, len(table) - 1) * 2
        + transaction_heading_count * 15
    )


def _extract_page_table(page) -> list[list[object]] | None:
    """Try pdfplumber's normal and text-aligned table detection."""
    candidates = []
    for settings in (None, TEXT_TABLE_SETTINGS):
        try:
            if settings is None:
                tables = page.extract_tables()
            else:
                tables = page.extract_tables(table_settings=settings)
        except Exception:
            continue

        candidates.extend(table for table in tables if table)

    if not candidates:
        return None

    best = max(candidates, key=_table_quality)
    if len(best) < 2 or _table_quality(best) == 0:
        return None
    return best


def _append_table_rows(
    table: list[list[object]],
    header: list[object] | None,
    rows: list[list[object]],
) -> list[object] | None:
    """Add table data while removing repeated headings between PDF pages."""
    if not table:
        return header

    candidate_header = [
        _repair_doubled_header_cell(cell) if cell is not None else ""
        for cell in table[0]
    ]

    if header is None:
        header = candidate_header
        rows.extend(table[1:])
    elif _canonical_table_header(candidate_header) == _canonical_table_header(header):
        rows.extend(table[1:])
    elif _is_transaction_header(candidate_header):
        if not _is_transaction_header(header):
            # A title/metadata table was detected before the transaction table.
            header = candidate_header
            rows.clear()
            rows.extend(table[1:])
        else:
            raise ValueError(
                "This PDF contains transaction tables with different column "
                "headings. Export it as CSV/Excel if available, or add a "
                "reader for this bank's PDF layout."
            )
    else:
        rows.extend(table)

    return header


def read_pdf_raw(filepath: str) -> pd.DataFrame:
    """Read a PDF using table extraction, text extraction, then local OCR."""
    header = None
    rows = []
    page_text = []
    corrupt_amount_text = False

    try:
        with pdfplumber.open(filepath) as pdf:
            for page in pdf.pages:
                table = _extract_page_table(page)
                if table:
                    header = _append_table_rows(table, header, rows)

                text = page.extract_text() or ""
                if text.strip():
                    page_text.append(text)

            corrupt_amount_text = _has_corrupt_amount_cells(header, rows)

            if header and rows and not corrupt_amount_text:
                return pd.DataFrame(rows, columns=header)

            # Some bank PDFs expose their transaction lines as text but don't
            # expose a table that pdfplumber can detect.
            # If the table already proved that its amount text is corrupt, the
            # page's text layer is likely using the same broken font map.
            if not corrupt_amount_text:
                text_rows = parse_statement_text("\n".join(page_text))
                if not text_rows.empty:
                    return text_rows

            # Scanned PDFs have no useful text layer. Render each page locally
            # and pass it through the same OCR reader used for image files.
            ocr_pages = []
            for page_number, page in enumerate(pdf.pages, start=1):
                try:
                    page_image = page.to_image(resolution=300).original
                except Exception as error:
                    raise ValueError(
                        "This PDF has no readable transaction table or text, "
                        f"and page {page_number} could not be rendered for OCR: "
                        f"{error}"
                    ) from error

                try:
                    ocr_pages.append(
                        read_image_object(page_image, allow_picker=False)
                    )
                except ValueError as error:
                    # A page may contain a logo, instructions, or a heading
                    # instead of transaction rows. Keep trying other pages.
                    if "OCR ran, but it could not recognize" not in str(error):
                        raise

            ocr_pages = [frame for frame in ocr_pages if not frame.empty]
            if ocr_pages:
                return pd.concat(ocr_pages, ignore_index=True)

    except RuntimeError:
        # Keep the actionable Tesseract setup message visible to the user.
        raise
    except ValueError:
        raise
    except Exception as error:
        raise ValueError(
            f"Could not read PDF file '{filepath}'. The file may be damaged, "
            f"password-protected, or not a valid PDF. Details: {error}"
        ) from error

    raise ValueError(
        (
            "The PDF text layer contains unreadable amount characters, and "
            "OCR could not recover the transaction rows. Install Tesseract "
            "OCR if it is not installed, or use the bank's CSV/Excel export."
            if corrupt_amount_text
            else
            "No transaction rows could be read from this PDF. The PDF reader "
            "tries extractable tables, text lines, and OCR for scanned pages, "
            "but this statement's layout may need a bank-specific reader. "
            "If your bank provides a CSV or Excel export, try that instead."
        )
    )
