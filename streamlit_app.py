from pathlib import Path
import tempfile

import streamlit as st

from analysis.categorize import add_categories
from analysis.recurring import find_recurring
from analysis.summary import (
    total_spending,
    total_income,
    spending_by_category,
    uncategorized_ratio,
)
from config.bank_mappings import BANK_CONFIGS
from normalizer import (
    detect_bank_config,
    find_duplicate_candidates,
    normalize,
)
from readers.csv_reader import read_csv_raw
from readers.detector import detect_format
from readers.excel_reader import read_excel_raw
from readers.ocr_reader import read_image_raw
from readers.pdf_reader import read_pdf_raw


def read_statement(filepath):
    file_format = detect_format(filepath)

    if file_format == "csv":
        return read_csv_raw(filepath)
    if file_format == "excel":
        return read_excel_raw(filepath)
    if file_format == "pdf":
        return read_pdf_raw(filepath)
    if file_format == "image":
        return read_image_raw(filepath, allow_picker=False)

    raise ValueError(f"Unsupported file format: {file_format}")


st.set_page_config(page_title="Bank Statement Analyzer", page_icon="💳")
st.title("💳 Bank Statement Analyzer")
st.write(
    "Upload a CSV, Excel, PDF, or statement image. Scanned PDFs and images "
    "need Tesseract OCR installed."
)

st.warning(
    "Demo only: use fictional or anonymized statements. "
    "An uploaded file is sent to the server running this website."
)

uploaded_file = st.file_uploader(
    "Choose a statement",
    type=["csv", "xlsx", "xls", "pdf", "jpg", "jpeg", "png"],
)

st.caption(
    "OCR can misread dates or amounts. Review every result carefully. "
    "If available, a CSV or Excel export is usually easier to read."
)

if uploaded_file is not None:
    temp_path = None

    try:
        suffix = Path(uploaded_file.name).suffix

        with tempfile.NamedTemporaryFile(
            suffix=suffix,
            delete=False,
        ) as temp_file:
            temp_file.write(uploaded_file.getvalue())
            temp_path = temp_file.name

        raw_data = read_statement(temp_path)
        bank_name, bank_config = detect_bank_config(raw_data, BANK_CONFIGS)

        transactions = normalize(
            raw_data,
            bank_config,
            source_file=uploaded_file.name,
        )
        categorized = add_categories(transactions)

        st.success(f"Statement format detected: {bank_name}")

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Transactions", len(categorized))
        col2.metric("Spending", f"{total_spending(categorized):.2f}")
        col3.metric("Income", f"{total_income(categorized):.2f}")
        col4.metric("Uncategorized", f"{uncategorized_ratio(categorized):.2f}%")

        st.subheader("Spending by category")
        category_totals = (
            spending_by_category(categorized)
            .rename("spending")
            .rename_axis("category")
            .reset_index()
        )
        st.dataframe(category_totals)

        duplicates = find_duplicate_candidates(categorized)
        st.subheader("Possible duplicates")
        if duplicates.empty:
            st.info("No possible duplicates found.")
        else:
            st.dataframe(duplicates)

        recurring = find_recurring(categorized)
        st.subheader("Recurring transactions")
        if recurring.empty:
            st.info("No recurring transactions detected yet.")
        else:
            st.dataframe(recurring)

        st.subheader("Transactions")
        st.dataframe(categorized)

    except Exception as error:
        st.error(f"Could not process this file: {error}")

    finally:
        if temp_path is not None:
            Path(temp_path).unlink(missing_ok=True)
