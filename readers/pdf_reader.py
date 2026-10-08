import pandas as pd
import pdfplumber


def read_pdf_raw(filepath: str) -> pd.DataFrame:
    """Extract tables from a text-based PDF statement."""
    header = None
    rows = []

    try:
        with pdfplumber.open(filepath) as pdf:
            for page in pdf.pages:
                table = page.extract_table()

                if not table:
                    continue

                if header is None:
                    header = table[0]
                    rows.extend(table[1:])
                elif table[0] == header:
                    rows.extend(table[1:])
                else:
                    rows.extend(table)
    except Exception as error:
        raise ValueError(
            f"Could not read PDF file '{filepath}': {error}"
        ) from error

    if not header or not rows:
        raise ValueError(
            "No table could be extracted from this PDF. "
            "It may be scanned or image-based."
        )

    return pd.DataFrame(rows, columns=header)