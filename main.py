from analysis.categorize import add_categories, uncategorized_transactions
from analysis.recurring import find_recurring
from analysis.summary import generate_summary
from logging import root
from tkinter import Tk, filedialog
from pathlib import Path
from config.bank_mappings import BANK_CONFIGS
from normalizer import detect_bank_config, find_duplicate_candidates, normalize
from readers.csv_reader import read_csv_raw
from readers.detector import detect_format
from readers.excel_reader import read_excel_raw
from readers.ocr_reader import read_image_raw
from readers.pdf_reader import read_pdf_raw

def read_statement(filepath: str):
    file_format = detect_format(filepath)

    if file_format == "csv":
        return read_csv_raw(filepath)
    if file_format == "excel":
        return read_excel_raw(filepath)
    if file_format == "pdf":
        return read_pdf_raw(filepath)
    if file_format == "image":
        return read_image_raw(filepath)

    raise ValueError(f"No reader is available for format: {file_format}")


def main():
    root = Tk()
    root.withdraw()

    selected_file = filedialog.askopenfilename(
        title="Choose a bank statement",
        filetypes=[
            ("Supported statements", "*.csv *.xlsx *.xls *.pdf *.jpg *.jpeg *.png"),
            ("All files", "*.*"),
        ],
    )
    root.destroy()

    if not selected_file:
        print("No file selected. Exiting.")
        return

    statement_path = Path(selected_file)
    raw_df = read_statement(str(statement_path))

    config_name, bank_config = detect_bank_config(raw_df, BANK_CONFIGS)
    print(f"Detected statement format: {config_name}")

    transactions = normalize(
        raw_df,
        bank_config,
        source_file=statement_path.name,
    )
    possible_duplicates = find_duplicate_candidates(transactions)
    if not  possible_duplicates.empty:
        print("\nPossible duplicate transactions for review:")
        print(possible_duplicates.to_string(index=False))

    categorized = add_categories(transactions)
    generate_summary(categorized)

    unknown = uncategorized_transactions(categorized)
    if not unknown.empty:
        print("\nTransactions needing category rules:")
        print(
            unknown[["date", "description", "amount"]].to_string(index=False)
        )

    print("\nRepeated scheduled expenses:")
    recurring = find_recurring(categorized)
    if recurring.empty:
        print("No likely recurring expenses found.")
    else:
        print(recurring.to_string(index=False))

   

if __name__ == "__main__":
    main()