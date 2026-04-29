import pytest

from automatedcompliancechecker.models.schemas import ClauseIssue, RiskLevel


@pytest.fixture
def sample_issue(article_id: str = "Art.5", risk_level: RiskLevel = RiskLevel.HIGH) -> ClauseIssue:
    return ClauseIssue(
        article_id=article_id,
        article_title="Principles of processing personal data",
        issue_description="Processing lacks a clear lawful basis.",
        problematic_text="We collect personal data for any purpose indefinitely.",
        location="Paragraphs 1-1",
        risk_level=risk_level,
        recommendation="Define a lawful basis, purpose, and retention period.",
    )
