import re
from typing import Optional

import pymupdf  # PyMuPDF


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract full text from PDF bytes."""
    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    text_parts = []
    for page in doc:
        text_parts.append(page.get_text())
    doc.close()
    return "\n".join(text_parts)


def chunk_document(text: str, chunk_size: int = 800, overlap: int = 100) -> list[dict]:
    """
    Split document into chunks with location metadata.
    Returns list of {text, location, paragraph_index}.
    """
    # Split into paragraphs first
    paragraphs = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]

    chunks = []
    current_chunk = []
    current_length = 0
    para_start = 0

    for para_idx, para in enumerate(paragraphs):
        words = para.split()
        if current_length + len(words) > chunk_size and current_chunk:
            chunk_text = " ".join(current_chunk)
            chunks.append(
                {
                    "text": chunk_text,
                    "location": f"Paragraphs {para_start + 1}–{para_idx}",
                    "paragraph_start": para_start,
                    "paragraph_end": para_idx,
                }
            )
            # Overlap: keep last paragraph in next chunk
            current_chunk = current_chunk[-overlap:] if overlap else []
            current_length = len(current_chunk)
            para_start = max(0, para_idx - 1)

        current_chunk.extend(words)
        current_length += len(words)

    if current_chunk:
        chunks.append(
            {
                "text": " ".join(current_chunk),
                "location": f"Paragraphs {para_start + 1}–{len(paragraphs)}",
                "paragraph_start": para_start,
                "paragraph_end": len(paragraphs),
            }
        )

    return chunks


def keyword_prescan(text: str, keywords: list[str]) -> bool:
    """Fast pre-filter: check if any keyword appears in text before calling LLM."""
    text_lower = text.lower()
    return any(kw.lower() in text_lower for kw in keywords)


def find_problematic_sentence(chunk_text: str, keywords: list[str]) -> Optional[str]:
    """Return the first sentence in chunk that contains a risk keyword."""
    sentences = re.split(r"(?<=[.!?])\s+", chunk_text)
    text_lower_sentences = [(s.lower(), s) for s in sentences]
    for lower, original in text_lower_sentences:
        if any(kw.lower() in lower for kw in keywords):
            return original[:300]  # Cap length
    return chunk_text[:200]
