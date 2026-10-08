# Bank Statement Analyzer

A Python learning and portfolio project that reads a supported bank statement file, converts its transactions to a consistent format, assigns categories, and displays a summary in the terminal.

## What it does

- Lets you choose a statement file using a file picker.
- Reads supported CSV, Excel, PDF, and image files.
- Detects a configured statement format by comparing its column headings.
- Converts dates and amounts into the project's standard format.
- Supports statements with either one signed Amount column or separate Debit and Credit columns, when configured.
- Shows total transaction count, spending, income, and spending by category.
- Shows transactions that do not match a category rule, so you can improve the rules.
- Lists possible duplicate transactions for review. It does not delete them.
- Looks for possible recurring expenses based on descriptions and date intervals.
- Processes files locally in this Python program. It does not intentionally upload statement contents to a server.

## Project status

This is a working learning prototype. Results depend on the statement layout, bank configuration, file quality, and the rules in the project. Review results before using them to make financial decisions.

## Supported file types

The file detector shown in this project supports:

- `.csv` — comma-separated values
- `.xlsx` and `.xls` — Excel workbooks
- `.pdf` — text-based PDFs from which the reader can extract tables
- `.jpg`, `.jpeg`, and `.png` — images processed by the OCR reader

A file extension alone does not guarantee that every statement can be read. Each bank may arrange columns and rows differently. Scanned PDFs may need an OCR workflow; the current PDF reader is designed for extracting tables from text-based PDFs.

## Requirements

- Python 3.10 or newer
- The packages listed in `requirements.txt`
- Tesseract OCR installed separately to read image files

### Important: Tesseract for OCR

`pytesseract` is a Python wrapper; it is not the Tesseract OCR program.

To read image statements, install Tesseract for your operating system and make sure the project's `ocr_reader.py` can locate the Tesseract program. On Linux, one example installation command is:

```bash
sudo apt install tesseract-ocr
```

On Windows, install Tesseract OCR using a trusted installer. If Tesseract is not installed or cannot be found, image OCR will fail. CSV, Excel, and text-based PDF reading do not require Tesseract.

## Install and run

1. Open the project folder in VS Code.
2. Open the VS Code terminal using **Terminal → New Terminal**.
3. Confirm the terminal is in the folder containing `main.py` and `requirements.txt`.
4. Install the Python dependencies:

   ```powershell
   python -m pip install -r requirements.txt
   ```

5. Start the program:

   ```powershell
   python main.py
   ```

6. Choose a supported statement file in the file picker.
7. Read the results in the terminal.

If the `python` command is not recognized, try:

```powershell
py -m pip install -r requirements.txt
py main.py
```

## Project structure

```text
bank_statement_project/
├── main.py
├── normalizer.py
├── schema.py
├── requirements.txt
├── analysis/
│   ├── __init__.py
│   ├── categorize.py
│   ├── recurring.py
│   └── summary.py
├── config/
│   ├── __init__.py
│   └── bank_mappings.py
├── readers/
│   ├── __init__.py
│   ├── detector.py
│   ├── csv_reader.py
│   ├── excel_reader.py
│   ├── pdf_reader.py
│   └── ocr_reader.py
└── data/
    └── sample statement files
```

Some folders or files may differ as the project changes. The `__init__.py` files mark Python folders as packages.

## How the program is organized

- `main.py` coordinates the steps: select a file, read it, normalize it, and run the analysis.
- `readers/` contains code for reading each supported file type.
- `readers/detector.py` chooses a reader based on the file extension.
- `config/bank_mappings.py` describes how supported bank column names map to standard column names.
- `normalizer.py` converts raw reader output into a consistent transaction table.
- `schema.py` checks that normalized transaction data has required columns and valid values.
- `analysis/categorize.py` assigns categories using description keywords.
- `analysis/summary.py` calculates and prints totals.
- `analysis/recurring.py` estimates likely recurring expenses.

## Standard transaction columns

The normalized table uses these required columns:

- `date` — transaction date
- `description` — transaction details or merchant
- `amount` — signed transaction amount; expenses should be negative and income positive

Optional columns may include:

- `balance`
- `payment_mode`
- `currency`
- `source_file`

## Bank configurations

Bank formats are configured in `config/bank_mappings.py`. A configuration maps statement headings to standard column names.

The project examples use:

- `amount_mode: "signed"` when the statement has one Amount column with positive and negative values.
- `amount_mode: "debit_credit"` when the statement has separate Debit and Credit columns. The normalizer combines them into one signed amount column.

To support another bank layout, add a configuration that matches the actual headings and date format. Do not assume that a configuration for one bank will correctly interpret another bank's statement.

Dates such as `03/04/2026` are ambiguous: depending on the bank, this can mean March 4 or April 3. Configure the date format or day/month preference correctly.

## Categories

Categories are keyword-based and configured in `analysis/categorize.py`. For example, a description containing a configured food keyword may be categorized as `food`.

If a transaction appears as `uncategorized`, review its description and add an appropriate keyword to `CATEGORY_RULES`. A keyword rule can produce incorrect matches, so inspect new rules with sample data.

## Duplicate review

The duplicate finder reports rows that look alike based on transaction fields such as date, description, and amount. It is only a review aid. Two genuine purchases can have the same date, merchant, and amount, so the program should not automatically delete possible duplicates.

## Recurring expense estimates

The recurring expense finder looks for repeated expenses with similar descriptions and approximately regular date intervals. Its results are estimates. A real subscription might not be detected if the statement has too few months of history, varying merchant descriptions, or irregular billing dates.

## Privacy and safe use

- This local Python version is designed to process the selected statement on the computer running the program.
- Do not put real bank statements, account numbers, or personal transaction data in a public repository.
- Use fictional or anonymized data for demonstrations, screenshots, and examples.
- Do not add code that sends statement contents, OCR text, or account details to external services.
- Be careful when sharing terminal output: it may contain transaction descriptions or amounts.
- The program is for learning and portfolio demonstration, not financial, tax, or accounting advice.

## Troubleshooting

### `pip` or `python` is not recognized

Try the Python launcher in PowerShell:

```powershell
py -m pip install -r requirements.txt
py main.py
```

If neither `python` nor `py` is available, install Python and enable the option to add it to PATH.

### `requirements.txt` cannot be found

The terminal is probably not in the project folder. In VS Code, open the folder that contains `main.py` and `requirements.txt`, then open a new terminal.

### Unsupported file extension

The extension must be one of the types supported by `readers/detector.py`. Renaming a file to `.csv` or `.pdf` does not convert its contents into that format.

### The statement format or columns are not recognized

Check that the file has a header row and that its headings match a configuration in `config/bank_mappings.py`. Add a mapping for the bank's actual headings when needed.

### A date is reported as unreadable

Check the bank's date format setting. Ambiguous numeric dates require a configured day/month interpretation. OCR may also misread digits in image statements.

### An amount is reported as unreadable

Check the source value for symbols or formatting the normalizer does not support. If it is an image, OCR may have misread the amount.

### Tesseract is not found

Install the Tesseract OCR program separately and make sure `ocr_reader.py` can locate it. Installing the Python package `pytesseract` alone is not enough.

### PDF has no extracted table

The current PDF reader is intended for text-based PDFs with extractable tables. A scanned PDF is essentially an image and may need OCR support.

### No recurring expenses are shown

The statement may not contain enough repeated transactions at regular intervals. This is not necessarily an error.

## Resume description

**Bank Statement Analyzer — Python, pandas**

Built a local Python application that reads supported bank statement formats, normalizes transaction data, validates required fields, categorizes transactions using configurable keywords, summarizes spending and income, and identifies possible duplicates and recurring expenses for review.

Only list file formats and features you have personally tested. Do not claim universal bank compatibility or that OCR works unless you have tested it with Tesseract installed and configured.