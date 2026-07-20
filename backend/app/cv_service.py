from pathlib import Path

import fitz  # pymupdf

UPLOAD_FOLDER = Path(__file__).resolve().parent.parent / "uploads"


def extract_text_from_pdf(file_path: str) -> str:
    try:
        doc = fitz.open(file_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        print(f"✅ Extracted {len(text)} characters from PDF")
        return text.strip()
    except Exception as e:
        print(f"❌ PDF extraction error: {e}")
        return ""


def save_uploaded_file(file_content: bytes, filename: str) -> str:
    if UPLOAD_FOLDER.exists() and not UPLOAD_FOLDER.is_dir():
        raise NotADirectoryError(f"{UPLOAD_FOLDER} exists but is not a directory")

    UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

    file_path = UPLOAD_FOLDER / filename
    with open(file_path, "wb") as f:
        f.write(file_content)

    print(f"✅ File saved: {file_path}")
    return str(file_path)
