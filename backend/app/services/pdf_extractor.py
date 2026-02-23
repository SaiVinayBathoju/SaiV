"""PDF text extraction service (pypdf-only)."""

from io import BytesIO
from typing import Tuple

import traceback
from pypdf import PdfReader

from app.utils.chunking import clean_text
from app.utils.logging_config import get_logger

logger = get_logger("pdf")


def extract_text_from_pdf(file_content: bytes, filename: str = "document.pdf") -> Tuple[str, str]:
    """
    Extract text from PDF bytes using pypdf only.
    Returns (title, extracted_text).
    """
    try:
        reader = PdfReader(BytesIO(file_content))
    except Exception as e:
        traceback.print_exc()
        raise ValueError(f"Could not open PDF: {e}")

    if not reader.pages:
        raise ValueError("PDF appears to be empty")

    # Derive a human-readable title
    title = filename.rsplit(".", 1)[0] if "." in filename else filename
    try:
        if reader.metadata and getattr(reader.metadata, "title", None):
            meta_title = (reader.metadata.title or "").strip()
            if meta_title:
                title = meta_title
    except Exception:
        # Metadata is optional; don't fail extraction because of it
        traceback.print_exc()

    text_parts = []
    for page in reader.pages:
        try:
            page_text = page.extract_text() or ""
        except Exception:
            traceback.print_exc()
            page_text = ""
        if page_text:
            text_parts.append(page_text)

    full_text = "\n".join(text_parts)
    full_text = clean_text(full_text)

    if not full_text or not full_text.strip():
        raise ValueError(
            "Could not extract meaningful text from PDF. "
            "The file may be scanned (image-based) or encrypted."
        )

    return title, full_text
