from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ClauseIssue(BaseModel):
    article_id: str
    article_title: str
    issue_description: str
    problematic_text: str
    location: str  # e.g. "Paragraph 3, sentence 2"
    risk_level: RiskLevel
    recommendation: str


class ComplianceReport(BaseModel):
    document_name: str
    overall_score: int = Field(..., ge=0, le=100, description="Compliance score 0-100")
    overall_risk: RiskLevel
    summary: str
    issues: list[ClauseIssue]
    articles_checked: list[str]
    articles_violated: list[str]
    processing_time_seconds: float


class AnalysisRequest(BaseModel):
    text: str = Field(..., min_length=50, description="Document text to analyse")
    document_name: Optional[str] = "unnamed_document"
