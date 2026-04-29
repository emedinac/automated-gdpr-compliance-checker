import hashlib
import re
from typing import Optional

from automatedcompliancechecker.models.schemas import ClauseIssue, RiskLevel
import pymupdf


def _deduplicate_issues(issues: list[ClauseIssue]) -> list[ClauseIssue]:
    seen = set()
    result = []

    for issue in issues:
        key_raw = f"{issue.article_id}:{issue.problematic_text}"
        key = hashlib.md5(key_raw.encode()).hexdigest()

        if key in seen:
            continue

        seen.add(key)
        result.append(issue)

    return result


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract full text from PDF bytes."""
    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    text_parts = []
    for page in doc:
        text_parts.append(page.get_text())
    doc.close()
    return "\n".join(text_parts)


def chunk_document(text: str, chunk_size: int = 800, overlap: int = 100) -> list[dict]:
    paragraphs = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]

    chunks = []
    window = []
    start = 0

    for i, para in enumerate(paragraphs):
        words = para.split()

        if len(window) + len(words) > chunk_size and window:
            chunks.append(
                {
                    "text": " ".join(window),
                    "location": f"Paragraphs {start + 1}–{i}",
                    "start": start,
                    "end": i,
                }
            )

            window = window[-overlap:]  # word-level overlap (OK now)
            start = max(0, i - 1)

        window.extend(words)

    if window:
        chunks.append(
            {
                "text": " ".join(window),
                "location": f"Paragraphs {start + 1}–{len(paragraphs)}",
                "start": start,
                "end": len(paragraphs),
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
