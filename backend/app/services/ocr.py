import re
from pathlib import Path
from pypdf import PdfReader
from app.config import settings


def classify_document(filename: str, text: str) -> str:
    sample = f"{filename} {text}".lower()
    if any(word in sample for word in ("passport", "nationality", "date of birth")):
        return "passport"
    if any(word in sample for word in ("marksheet", "transcript", "semester", "grade", "percentage")):
        return "marksheet"
    if any(word in sample for word in ("income", "annual income", "earnings")):
        return "income_certificate"
    if any(word in sample for word in ("photo", "photograph", "selfie")):
        return "photo"
    return "unknown"


def extract_fields(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    percent = re.search(r"(?:percentage|aggregate|marks)\s*[:=-]?\s*(\d{1,3}(?:\.\d+)?)\s*%", text, re.I)
    if percent:
        fields["percentage"] = percent.group(1)
    name = re.search(r"(?:name|student name)\s*[:=-]\s*([A-Za-z .]{3,})", text, re.I)
    if name:
        fields["name"] = name.group(1).strip()
    return fields


def read_document(path: Path, filename: str) -> tuple[str, str, dict[str, str]]:
    suffix = path.suffix.lower()
    text = ""
    if suffix == ".pdf":
        text = "\n".join(page.extract_text() or "" for page in PdfReader(str(path)).pages)
    elif suffix in {".txt", ".csv"}:
        text = path.read_text(encoding="utf-8", errors="ignore")
    elif settings.use_paddle_ocr:
        # Delayed import keeps the demo install lightweight.
        from paddleocr import PaddleOCR
        ocr = PaddleOCR(use_angle_cls=True, lang="en")
        result = ocr.predict(str(path))
        text = "\n".join(item["rec_text"] for item in result[0])
    else:
        text = "Image submitted. Enable USE_PADDLE_OCR for scanned-image text extraction."
    return text, classify_document(filename, text), extract_fields(text)
