from __future__ import annotations

from pathlib import Path


def clean_text(text: str) -> str:
    return " ".join(text.replace("\r", "\n").split())


def extract_text_from_bytes(filename: str, data: bytes) -> str:
    from io import BytesIO

    suffix = Path(filename).suffix.lower()

    if suffix == ".pdf":
        try:
            from pypdf import PdfReader
            reader = PdfReader(BytesIO(data))
            pages = []
            for page in reader.pages:
                pages.append(page.extract_text() or "")
            return clean_text("\n".join(pages))
        except ImportError:
            print("Warning: pypdf not installed. Attempting to extract text as UTF-8 fallback.")
            # Fallback: try to extract text from PDF as raw bytes
            try:
                return clean_text(data.decode("utf-8", errors="ignore"))
            except Exception:
                return "[PDF file uploaded but could not extract text. Please paste content as text instead.]"

    if suffix == ".docx":
        try:
            from docx import Document
            doc = Document(BytesIO(data))
            paragraphs = [paragraph.text for paragraph in doc.paragraphs if paragraph.text.strip()]
            return clean_text("\n".join(paragraphs))
        except ImportError:
            print("Warning: python-docx not installed. Attempting to extract text as UTF-8 fallback.")
            # Fallback: try to extract text from DOCX as raw bytes
            try:
                return clean_text(data.decode("utf-8", errors="ignore"))
            except Exception:
                return "[DOCX file uploaded but could not extract text. Please paste content as text instead.]"

    # For .txt and other formats, try UTF-8 decoding
    try:
        return clean_text(data.decode("utf-8"))
    except UnicodeDecodeError:
        return clean_text(data.decode("latin-1", errors="ignore"))
