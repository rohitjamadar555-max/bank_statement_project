import os
import re
import shutil
from pathlib import Path

import pandas as pd
import pytesseract
from PIL import Image, ImageEnhance, ImageOps
from pytesseract.pytesseract import TesseractError, TesseractNotFoundError


# Matches a date, a description, and an amount on the same line.
DATE_PATTERN = (
    r"(?:"
    r"\d{4}[./-]\d{1,2}[./-]\d{1,2}"
    r"|\d{1,2}[./-]\d{1,2}[./-]\d{2,4}"
    r"|\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}"
    r"|[A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4}"
    r")"
)

CURRENCY_PATTERN = r"(?:₹|\$|€|£|INR|USD|EUR|GBP|Rs\.?)"
NUMBER_PATTERN = r"\d[\d,]*(?:\.\d{1,2})?"

AMOUNT_PATTERN = (
    rf"(?:"
    rf"\(\s*[+-]?\s*(?:{CURRENCY_PATTERN}\s*)?{NUMBER_PATTERN}\s*\)"
    rf"|[+-]?\s*(?:{CURRENCY_PATTERN}\s*)?{NUMBER_PATTERN}"
    rf")"
)

LINE_PATTERN = re.compile(
    rf"^\s*(?P<date>{DATE_PATTERN})"
    rf"\s+(?P<description>.+?)"
    rf"\s+(?P<amount>{AMOUNT_PATTERN})\s*$",
    re.IGNORECASE,
)

_CACHED_TESSERACT_PATH = None


def _saved_path_files():
    """Possible places where this project remembers a Tesseract location."""
    project_folder = Path(__file__).resolve().parents[1]

    return [
        Path.home() / ".bank_statement_project" / "tesseract_path.txt",
        project_folder / "config" / "tesseract_path.txt",
    ]


def _candidate_tesseract_paths():
    """Build a list of likely Tesseract locations on this computer."""
    candidates = []

    # Use a location already saved for this user or project.
    for saved_file in _saved_path_files():
        try:
            if saved_file.is_file():
                candidates.append(saved_file.read_text(encoding="utf-8").strip())
        except OSError:
            pass

    # Allow an administrator or user to configure a custom location.
    candidates.append(os.environ.get("TESSERACT_CMD"))

    # Check the computer's PATH.
    candidates.append(shutil.which("tesseract"))

    # Common Windows installation folders.
    for variable in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA"):
        folder = os.environ.get(variable)
        if folder:
            candidates.append(
                str(Path(folder) / "Tesseract-OCR" / "tesseract.exe")
            )

    # Common per-user Windows location, including the Dropbox location
    # used on the developer's computer.
    candidates.append(str(Path.home() / "Dropbox" / "tesseract.exe"))

    # Common macOS and Linux locations.
    candidates.extend([
        "/usr/bin/tesseract",
        "/usr/local/bin/tesseract",
        "/opt/homebrew/bin/tesseract",
        "/opt/local/bin/tesseract",
        "/snap/bin/tesseract",
    ])

    return candidates


def _verify_tesseract(path):
    """Check that a path points to a working Tesseract program."""
    if not path:
        return None

    try:
        candidate = Path(str(path).strip().strip('"')).expanduser()

        if not candidate.is_file():
            return None

        # Avoid accidentally trying to run an unrelated selected program.
        if candidate.name.lower() not in {"tesseract", "tesseract.exe"}:
            return None

        pytesseract.pytesseract.tesseract_cmd = str(candidate)
        pytesseract.get_tesseract_version()
        return str(candidate)

    except (OSError, TesseractError, TesseractNotFoundError):
        return None


def _remember_tesseract_path(path):
    """Save the selected location so it doesn't need to be chosen again."""
    for saved_file in _saved_path_files():
        try:
            saved_file.parent.mkdir(parents=True, exist_ok=True)
            saved_file.write_text(path, encoding="utf-8")
            return
        except OSError:
            # Try the other save location if this one is not writable.
            continue


def find_tesseract():
    """
    Find Tesseract automatically. If needed, ask the user to choose it once.
    """
    global _CACHED_TESSERACT_PATH

    if _CACHED_TESSERACT_PATH and Path(_CACHED_TESSERACT_PATH).is_file():
        return _CACHED_TESSERACT_PATH

    for candidate in _candidate_tesseract_paths():
        working_path = _verify_tesseract(candidate)
        if working_path:
            _CACHED_TESSERACT_PATH = working_path
            return working_path

    # Nothing was found automatically. Ask the user to locate the program.
    try:
        from tkinter import Tk, filedialog

        window = Tk()
        window.withdraw()
        selected_path = filedialog.askopenfilename(
            title="Locate the Tesseract OCR program",
            filetypes=[
                ("Tesseract program", "tesseract*"),
                ("All files", "*.*"),
            ],
        )
        window.destroy()

    except Exception as error:
        raise RuntimeError(
            "Tesseract was not found automatically, and the file picker "
            "could not open. Install Tesseract and add it to PATH, or set "
            "the TESSERACT_CMD environment variable to its full path."
        ) from error

    if not selected_path:
        raise RuntimeError(
            "Tesseract was not found. Install Tesseract, then select its "
            "program when asked. You only need to locate it once."
        )

    working_path = _verify_tesseract(selected_path)
    if not working_path:
        raise RuntimeError(
            "The selected file is not a working Tesseract program. "
            "Select tesseract.exe on Windows, or the tesseract program "
            "on macOS or Linux."
        )

    _remember_tesseract_path(working_path)
    _CACHED_TESSERACT_PATH = working_path
    return working_path


def read_image_raw(filepath: str) -> pd.DataFrame:
    """
    OCR a simple statement image.

    Each transaction must have its date, description, and amount on one line.
    Returns raw columns named Date, Description, and Amount.
    """
    tesseract_path = find_tesseract()
    pytesseract.pytesseract.tesseract_cmd = tesseract_path

    language = os.environ.get("TESSERACT_LANG", "eng")

    try:
        with Image.open(filepath) as source_image:
            image = ImageOps.exif_transpose(source_image).convert("RGB")
            image = ImageOps.grayscale(image)
            image = ImageEnhance.Contrast(image).enhance(1.5)

            text = pytesseract.image_to_string(
                image,
                lang=language,
                config="--psm 6",
            )

    except TesseractNotFoundError as error:
        raise RuntimeError(
            "Tesseract could not be started. Check that its program is "
            "installed and that the saved path still points to it."
        ) from error

    except TesseractError as error:
        raise RuntimeError(
            f"Tesseract could not read this image using language "
            f"'{language}'. Check that the language data is installed. "
            f"Details: {error}"
        ) from error

    except (OSError, ValueError) as error:
        raise ValueError(
            f"Could not open image file '{filepath}': {error}"
        ) from error

    rows = []

    for line in text.splitlines():
        match = LINE_PATTERN.match(line.strip())
        if not match:
            continue

        amount = match.group("amount").strip()

        # The normalizer handles currency signs such as ₹ and parentheses.
        # Remove "Rs." here because the project's amount parser may not know it.
        amount = re.sub(r"\bRs\.?\s*", "", amount, flags=re.IGNORECASE)

        rows.append({
            "Date": match.group("date").strip(),
            "Description": match.group("description").strip(),
            "Amount": amount,
        })

    if not rows:
        raise ValueError(
            "OCR ran, but it could not recognize any transaction rows. "
            "This reader expects each row to show a date, description, and "
            "amount together on one line. Some bank layouts may need a "
            "custom reader."
        )

    return pd.DataFrame(rows, columns=["Date", "Description", "Amount"])