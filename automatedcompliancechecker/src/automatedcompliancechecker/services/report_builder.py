"""
Convert raw analysis state -> structured ComplianceReport with score.
"""

from automatedcompliancechecker.models.schemas import ClauseIssue, ComplianceReport, RiskLevel
from automatedcompliancechecker.utils.gdpr_articles import GDPR_ARTICLES

RISK_WEIGHTS = {
    RiskLevel.LOW: 5,
    RiskLevel.MEDIUM: 15,
    RiskLevel.HIGH: 25,
    RiskLevel.CRITICAL: 40,
}

ALL_ARTICLE_IDS = [a["id"] for a in GDPR_ARTICLES]


def compute_score(issues: list[ClauseIssue]) -> int:
    """Score 0–100. Start at 100, deduct per issue weighted by risk."""
    if not issues:
        return 100
    deductions = sum(RISK_WEIGHTS.get(issue.risk_level, 10) for issue in issues)
    return max(0, 100 - deductions)


def overall_risk(score: int) -> RiskLevel:
    if score >= 80:
        return RiskLevel.LOW
    elif score >= 60:
        return RiskLevel.MEDIUM
    elif score >= 35:
        return RiskLevel.HIGH
    return RiskLevel.CRITICAL


def build_summary(score: int, issues: list[ClauseIssue], articles_violated: list[str]) -> str:
    if not issues:
        return "No significant GDPR compliance issues detected. Document appears broadly compliant."
    n = len(issues)
    arts = ", ".join(articles_violated[:5])
    if len(articles_violated) > 5:
        arts += f" +{len(articles_violated) - 5} more"
    return (
        f"Found {n} potential compliance issue{'s' if n > 1 else ''} "
        f"across {len(articles_violated)} GDPR article{'s' if len(articles_violated) > 1 else ''} "
        f"({arts}). Score: {score}/100."
    )


def build_report(
    document_name: str,
    raw_issues: list[dict],
    articles_violated: list[str],
    processing_time: float,
) -> ComplianceReport:
    issues = [
        ClauseIssue(
            article_id=i["article_id"],
            article_title=i["article_title"],
            issue_description=i["issue_description"],
            problematic_text=i["problematic_text"],
            location=i["location"],
            risk_level=RiskLevel(i["risk_level"]),
            recommendation=i["recommendation"],
        )
        for i in raw_issues
    ]

    # Sort by severity (critical first)
    severity_order = {RiskLevel.CRITICAL: 0, RiskLevel.HIGH: 1, RiskLevel.MEDIUM: 2, RiskLevel.LOW: 3}
    issues.sort(key=lambda x: severity_order.get(x.risk_level, 4))

    score = compute_score(issues)
    risk = overall_risk(score)

    return ComplianceReport(
        document_name=document_name,
        overall_score=score,
        overall_risk=risk,
        summary=build_summary(score, issues, articles_violated),
        issues=issues,
        articles_checked=ALL_ARTICLE_IDS,
        articles_violated=articles_violated,
        processing_time_seconds=processing_time,
    )
