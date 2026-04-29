from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ClauseIssue(BaseModel):
    article_id: str = Field(
        ...,
        description="GDPR article identifier that is potentially violated, e.g. 'Art.5', 'Art.6'.",
    )
    article_title: str = Field(
        ...,
        description="Full title of the GDPR article, e.g. 'Principles of processing personal data'.",
    )
    issue_description: str = Field(
        ...,
        description=(
            "Concise explanation of why this clause may violate the article. "
            "Be specific — reference the requirement that is missing or breached. Max 150 characters."
        ),
    )
    problematic_text: str = Field(
        ...,
        description=(
            "The exact excerpt from the document that triggered this issue. "
            "Do not paraphrase — copy the original text. Max 300 characters."
        ),
    )
    location: str = Field(
        ...,
        description="Human-readable location of the excerpt in the document, e.g. 'Paragraphs 3–5'.",
    )
    risk_level: RiskLevel = Field(
        ...,
        description=(
            "Severity of the violation: "
            "'low' = minor gap, unlikely to cause enforcement action; "
            "'medium' = notable gap, should be addressed; "
            "'high' = clear violation, likely to attract regulatory scrutiny; "
            "'critical' = severe violation such as no legal basis, unencrypted data, or no deletion mechanism."
        ),
    )
    recommendation: str = Field(
        ...,
        description=(
            "Specific, actionable fix for this clause. "
            "Reference the GDPR requirement it must satisfy. Max 150 characters."
        ),
    )


class ComplianceReport(BaseModel):
    document_name: str = Field(
        ...,
        description="Name or identifier of the analysed document.",
    )
    overall_score: int = Field(
        ...,
        ge=0,
        le=100,
        description=(
            "Compliance score from 0 to 100. "
            "100 = fully compliant, 0 = critically non-compliant. "
            "Deduct points per issue weighted by risk level."
        ),
    )
    overall_risk: RiskLevel = Field(
        ...,
        description="Aggregate risk level derived from the overall score and severity of issues found.",
    )
    summary: str = Field(
        ...,
        description=(
            "2–3 sentence plain-language summary of the compliance status. "
            "Mention the number of issues, which articles are affected, and the score."
        ),
    )
    issues: list[ClauseIssue] = Field(
        ...,
        description="List of individual compliance issues found, ordered by severity (critical first).",
    )
    articles_checked: list[str] = Field(
        ...,
        description="All GDPR article IDs that were checked during analysis.",
    )
    articles_violated: list[str] = Field(
        ...,
        description="Subset of articles_checked where at least one violation was found.",
    )
    processing_time_seconds: float = Field(
        ...,
        description="Time taken to complete the analysis in seconds.",
    )


class AnalysisRequest(BaseModel):
    text: str = Field(
        ...,
        min_length=50,
        description=(
            "Full text of the document to analyse, contract, privacy policy, or terms of service. "
            "Must be machine-readable text, not scanned image content."
        ),
    )
    document_name: Optional[str] = Field(
        default="unnamed_document",
        description="Optional display name for the document, used in the report output.",
    )
