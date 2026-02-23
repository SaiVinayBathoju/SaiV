"""Text chunking utilities for RAG pipeline."""

import re
from typing import List


def clean_text(text: str) -> str:
    """Clean and normalize extracted text."""
    if not text or not isinstance(text, str):
        return ""
    # Normalize whitespace
    text = re.sub(r"\s+", " ", text)
    # Remove excessive newlines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def chunk_text(
    text: str,
    chunk_size: int = 512,
    overlap: int = 50,
) -> List[str]:
    """
    Split text into overlapping chunks for embedding.
    Uses sentence boundaries when possible to avoid mid-sentence cuts.
    """
    text = clean_text(text)
    if not text:
        return []

    chunks: List[str] = []
    # Split on sentence boundaries (period, question mark, exclamation, newline)
    sentences = re.split(r"(?<=[.!?])\s+|\n+", text)
    sentences = [s.strip() for s in sentences if s.strip()]

    current_chunk: List[str] = []
    current_length = 0

    for sentence in sentences:
        sentence_len = len(sentence) + 1
        if current_length + sentence_len > chunk_size and current_chunk:
            chunk_text_str = " ".join(current_chunk)
            chunks.append(chunk_text_str)
            # Overlap: keep last sentences that fit in overlap
            overlap_text = ""
            for s in reversed(current_chunk):
                if len(overlap_text) + len(s) + 1 <= overlap:
                    overlap_text = s + " " + overlap_text if overlap_text else s
                else:
                    break
            current_chunk = [overlap_text.strip()] if overlap_text else []
            current_length = len(overlap_text)
        current_chunk.append(sentence)
        current_length += sentence_len

    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks
