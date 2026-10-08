import os


FORMAT_MAP = {
    ".csv": "csv",
    ".xlsx": "excel",
    ".xls": "excel",
    ".pdf": "pdf",
    ".jpg": "image",
    ".jpeg": "image",
    ".png": "image",
}


def detect_format(filepath: str) -> str:
    """Return the reader type based on the file extension."""
    extension = os.path.splitext(filepath)[1].lower()

    if extension not in FORMAT_MAP:
        raise ValueError(f"Unsupported file extension: {extension}")

    return FORMAT_MAP[extension]