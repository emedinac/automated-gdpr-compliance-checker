from automatedcompliancechecker.models.schemas import ClauseIssue, RiskLevel
from automatedcompliancechecker.services.report_builder import build_report, compute_score, overall_risk


def make_issue(article_id: str = "Art.5", risk_level: RiskLevel = RiskLevel.HIGH) -> ClauseIssue:
    return ClauseIssue(
        article_id=article_id,
        article_title="Principles of processing personal data",
        issue_description="Processing lacks a clear lawful basis.",
        problematic_text="We collect personal data for any purpose indefinitely.",
        location="Paragraphs 1-1",
        risk_level=risk_level,
        recommendation="Define a lawful basis, purpose, and retention period.",
    )


def test_compute_score_starts_at_100_when_no_issues():
    assert compute_score([]) == 100


def test_compute_score_deducts_by_risk_level():
    issues = [
        make_issue(risk_level=RiskLevel.LOW),
        make_issue(risk_level=RiskLevel.HIGH),
        make_issue(risk_level=RiskLevel.CRITICAL),
    ]

    assert compute_score(issues) == 30


def test_overall_risk_thresholds():
    assert overall_risk(90) == RiskLevel.LOW
    assert overall_risk(70) == RiskLevel.MEDIUM
    assert overall_risk(45) == RiskLevel.HIGH
    assert overall_risk(20) == RiskLevel.CRITICAL


def test_build_report_sorts_issues_by_severity_and_builds_summary():
    raw_issues = [
        make_issue(article_id="Art.13", risk_level=RiskLevel.LOW).model_dump(),
        make_issue(article_id="Art.6", risk_level=RiskLevel.CRITICAL).model_dump(),
        make_issue(article_id="Art.5", risk_level=RiskLevel.HIGH).model_dump(),
    ]

    report = build_report(
        document_name="privacy-policy.txt",
        raw_issues=raw_issues,
        articles_violated=["Art.5", "Art.6", "Art.13"],
        processing_time=1.23,
    )

    assert report.document_name == "privacy-policy.txt"
    assert report.overall_score == 30
    assert report.overall_risk == RiskLevel.CRITICAL
    assert [issue.risk_level for issue in report.issues] == [
        RiskLevel.CRITICAL,
        RiskLevel.HIGH,
        RiskLevel.LOW,
    ]
    assert "Found 3 potential compliance issues" in report.summary

