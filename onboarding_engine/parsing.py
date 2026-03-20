from __future__ import annotations

from pathlib import Path


def clean_text(text: str) -> str:
    return " ".join(text.replace("\r", "\n").split())


def extract_text_from_bytes(filename: str, data: bytes) -> str:
    from io import BytesIO

    suffix = Path(filename).suffix.lower()

    if suffix == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(BytesIO(data))
        pages = []
        for page in reader.pages:
            pages.append(page.extract_text() or "")
        return clean_text("\n".join(pages))

    if suffix == ".docx":
        from docx import Document

        doc = Document(BytesIO(data))
        paragraphs = [paragraph.text for paragraph in doc.paragraphs if paragraph.text.strip()]
        return clean_text("\n".join(paragraphs))

    try:
        return clean_text(data.decode("utf-8"))
    except UnicodeDecodeError:
        return clean_text(data.decode("latin-1", errors="ignore"))
