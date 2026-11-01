# Bank Statement Analyzer

A Python learning and portfolio project that reads a supported bank statement file, converts its transactions to a consistent format, assigns categories, and displays a summary in the terminal.

## What it does

- Lets you choose a statement file using the terminal version, or upload one
  to the local Streamlit web app.
- Reads CSV, Excel, PDF, and common image files.
- Detects a configured statement format by comparing its column headings.
- Converts dates and amounts into the project's standard format.
- Supports statements with either one signed Amount column or separate Debit and Credit columns, when configured.
- Uses common Debit/Credit labels in a `Type` column to set an unsigned Amount's sign.
- Shows total transaction count, spending, income, and spending by category.
- Shows transactions that do not match a category rule, so you can improve the rules.
- Lists possible duplicate transactions for review. It does not delete them.
- Looks for possible recurring expenses based on descriptions and date intervals.
- When run on your computer, both versions process the statement on that
  computer. The Streamlit browser page sends the selected file to the local
  app server running on the same computer.

## Project status

This is a working learning prototype. Results depend on the statement layout, bank configuration, file quality, and the rules in the project. Review results before using them to make financial decisions.

## Supported file types

The file detector shown in this project supports:

- `.csv` — comma-separated values
- `.xlsx` and `.xls` — Excel workbooks
- `.pdf` — PDFs with extractable tables or simple transaction lines; scanned
  PDFs use local OCR when Tesseract is installed
- `.jpg`, `.jpeg`, and `.png` — images processed by the OCR reader

A file extension alone does not guarantee that every statement can be read.
The PDF reader tries table extraction, text lines, and then OCR. The OCR reader
currently expects each transaction's date, description, and amount to appear
on one line. Banks use different layouts, date formats, and debit/credit
conventions, so some statements still need a specific mapping or reader. Check
every parsed transaction before relying on the summary.

## Requirements

- Python 3.10 or newer
- The packages listed in `requirements.txt`
- Tesseract OCR installed separately to read image files and scanned PDFs

### Important: Tesseract for OCR

`pytesseract` is a Python wrapper; it is not the Tesseract OCR program.

To read image statements or scanned PDFs, install Tesseract for your
operating system and make sure the project's `ocr_reader.py` can locate the
Tesseract program. On Linux, one example installation command is:

```bash
sudo apt install tesseract-ocr
```

On Windows, install Tesseract OCR using a trusted installer. If Tesseract is
not installed or cannot be found, image and scanned-PDF OCR will fail. CSV,
Excel, and text-based PDF reading do not require Tesseract.

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

### Open the local web app

The Streamlit version runs on your computer and opens in a browser. From the
project folder, install the requirements and run:

```powershell
py -m pip install -r requirements.txt
py -m streamlit run streamlit_app.py
```

Open the local address printed in the terminal, usually `http://localhost:8501`.
The browser sends the selected file to the computer running Streamlit. The app
uses a temporary file while processing and deletes that file afterward. Do not
use real bank statements with a publicly hosted copy of this demo.

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

If no bank configuration matches, the normalizer can also recognize common
headings such as `Transaction Date`, `Narration`, `Details`, `Withdrawal`, and
`Deposit`. This helps with simple layouts, but unusual headings still need a
mapping in `config/bank_mappings.py`.

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

- The terminal program processes the selected statement on the computer
  running it. The local Streamlit app sends the selected file from the browser
  to the computer running Streamlit so it can process it.
- The Streamlit app writes a temporary copy for processing and deletes that
  temporary file when processing ends. This is not a guarantee that data has
  been erased from every place in memory or from a hosted server's logs/backups.
- Do not put real bank statements, account numbers, or personal transaction data in a public repository.
- Use fictional or anonymized data for demonstrations, screenshots, and examples.
- Do not add code that sends statement contents, OCR text, or account details to external services.
- Be careful when sharing terminal output: it may contain transaction descriptions or amounts.
- The program is for learning and portfolio demonstration, not financial, tax, or accounting advice.

## Import recovery behavior

The normal reader remains the first choice for well-formed files. Added
recovery steps are used only when the normal read fails:

- **CSV:** the fallback checks common delimiters and looks for a transaction
  header after any account-information preamble. It can rejoin extra
  delimiter-separated fields into the description when the amount columns
  still line up. A trailing one-cell, non-date footer is ignored only when no
  later dated transaction follows. An incomplete row that looks like a
  transaction still produces an error. Review the transaction count and
  amounts after import.
- **PDF:** when table extraction returns unreadable null characters in amount
  values, the reader renders the PDF pages and tries local Tesseract OCR. OCR
  can misread text; inspect the results. Tesseract must be installed for this
  fallback.
- **OCR transaction direction:** recognized Debit/Dr/Withdrawal/Payment labels
  make amounts negative, while Credit/Cr/Deposit/Received labels make amounts
  positive.

These fallbacks improve support for common layouts, but they do not guarantee
that every bank export can be read correctly. Check the parsed transactions
before relying on totals.

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

### PDF has no extracted table or OCR finds no transactions

The PDF reader tries to extract a table, read simple transaction lines, and
then use Tesseract OCR for scanned pages. OCR currently expects the date,
description, and amount on the same line. If your bank's layout differs, use
its CSV or Excel export when available, or add a reader for that bank's layout.
Never assume an OCR result is correct without reviewing the dates and amounts.

### `.xls` workbook cannot be opened

Install all packages from `requirements.txt`. The `.xls` reader needs the
`xlrd` package, while `.xlsx` files use `openpyxl`.

### No recurring expenses are shown

The statement may not contain enough repeated transactions at regular intervals. This is not necessarily an error.

## Resume description

**Bank Statement Analyzer — Python, pandas**

Built a local Python application that reads supported bank statement formats, normalizes transaction data, validates required fields, categorizes transactions using configurable keywords, summarizes spending and income, and identifies possible duplicates and recurring expenses for review.

Only list file formats and features you have personally tested. Do not claim universal bank compatibility or that OCR works unless you have tested it with Tesseract installed and configured.

## Separate browser app (CSV + Excel, local processing)

The `browser_app/` folder contains a separate static browser version. It does not replace the terminal or Streamlit apps described above. The Streamlit privacy notes still apply to that older app: its selected file is sent to the computer running Streamlit for processing.

### Run the browser version on your computer

From the project folder, start a static file server:

```powershell
py -m http.server 8000 --directory browser_app
```

Then open `http://localhost:8000` in a browser. Stop the server with `Ctrl+C` when finished. This server provides the app's HTML, CSS, and JavaScript. The browser reads the chosen CSV or Excel file through its local File API; the app has no upload endpoint.

### Current support and review

- This version supports UTF-8 CSV, `.xlsx`, and `.xls` files up to 10 MB. CSV parsing tries comma, semicolon, tab, or pipe separators. For CSV and Excel worksheets, it looks for a transaction header in the first 40 rows.
- Select or change the header row and map Date, Description, and Amount, or Date, Description, Debit, and Credit. If headings are unfamiliar, choose the likely header row and map the columns manually. Choose the date order before analysis.
- Excel workbooks are read with the locally bundled SheetJS Community Edition library. Choose the worksheet to analyze; the app starts with the first worksheet. A worksheet is limited to 20,000 rows and 100 columns. Formula cells use saved workbook values; formulas are not recalculated.
- It shows transaction totals, suggested spending categories, possible duplicates, and rows it could not read. Categories are keyword suggestions; duplicate matches are not removed.
- Check every date and amount against the original. Bank exports vary, and a successful parse does not prove that values are correct.
- PDF, scanned PDF, image, OCR, and recurring-payment analysis are not implemented in this browser version yet. The separate Python app retains its existing readers and features.

### Browser privacy boundary

- In `browser_app/`, the selected file is read and processed in the browser tab. The spreadsheet reader is served from `browser_app/vendor/`; the app does not load a spreadsheet library from a CDN. The app does not include `fetch`, XMLHttpRequest, `sendBeacon`, analytics, external OCR, an account, a database, or browser storage for statement data. The page's Content Security Policy sets `connect-src 'none'`.
- The static website host still delivers the app files and may receive ordinary page request information, such as an IP address. The privacy goal is that statement contents and extracted transaction values are not sent in those requests. Browser extensions or device software with access to page content may still be able to read what is displayed.
- The **Clear file and results** button removes the app's references and visible results. A browser cannot promise a forensic wipe of device memory, operating-system caches, or screenshots.
- This describes the current source code. Before publishing, inspect the deployed site's browser Network panel while selecting, analyzing, and clearing a CSV or Excel file. Confirm that no request contains the file or its transaction values, and recheck after any code or hosting change. A static host can still serve changed code, so users must trust the published site and its release process.

Do not describe the browser version as supporting all statements or as absolutely private. Its current claim is limited to local processing by this source version, with the deployment and Network-panel check still required before public release.

### Browser spreadsheet library notice

The browser edition includes SheetJS Community Edition 0.20.3 at `browser_app/vendor/xlsx.full.min.js` so spreadsheet parsing does not require a runtime connection to a third-party CDN. Its Apache 2.0 license is included at `browser_app/vendor/LICENSE-sheetjs.txt`, and the required attribution is in `browser_app/vendor/NOTICE-sheetjs.txt`.

### Keep real statements out of Git

Keep real statement files outside the project folder. If you need a local-only folder inside the project, use `private_statements/` or `user_uploads/`; both are ignored by `.gitignore`. Ignore rules do not remove files already tracked by Git. Before pushing, review `git status --short` and `git ls-files`. If a real statement was already committed or pushed, deleting it in a later commit does not remove it from earlier Git history.
