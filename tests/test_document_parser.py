from automatedcompliancechecker.models.schemas import ClauseIssue, RiskLevel
from automatedcompliancechecker.utils.document_parser import (
    _deduplicate_issues,
    chunk_document,
    find_problematic_sentence,
    keyword_prescan,
)


def make_issue(article_id: str, text: str) -> ClauseIssue:
    return ClauseIssue(
        article_id=article_id,
        article_title="Lawfulness of processing",
        issue_description="Missing lawful basis.",
        problematic_text=text,
        location="Paragraphs 1-1",
        risk_level=RiskLevel.HIGH,
        recommendation="State the lawful basis for processing.",
    )


def test_keyword_prescan_is_case_insensitive():
    assert keyword_prescan("Users can request DELETION of their data.", ["deletion"])
    assert not keyword_prescan("This paragraph is unrelated.", ["consent"])


def test_find_problematic_sentence_returns_first_matching_sentence():
    text = "This sentence is harmless. Users cannot request deletion of their data. Another sentence follows."

    assert find_problematic_sentence(text, ["deletion"]) == "Users cannot request deletion of their data."


def test_chunk_document_splits_paragraphs_and_preserves_locations():
    text = "First paragraph has words.\n\nSecond paragraph has more words.\n\nThird paragraph closes."

    chunks = chunk_document(text, chunk_size=6, overlap=1)

    assert len(chunks) >= 2
    assert chunks[0]["location"].startswith("Paragraphs 1")
    assert chunks[0]["end"] == 1
    assert "First paragraph" in chunks[0]["text"]
    assert chunks[-1]["location"].startswith("Paragraphs")


def test_deduplicate_issues_keeps_first_unique_article_and_text_pair():
    duplicate_a = make_issue("Art.6", "We process data without consent.")
    duplicate_b = make_issue("Art.6", "We process data without consent.")
    distinct = make_issue("Art.5", "We process data without consent.")

    result = _deduplicate_issues([duplicate_a, duplicate_b, distinct])

    assert result == [duplicate_a, distinct]
