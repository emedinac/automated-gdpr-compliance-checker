import asyncio

import pytest
from fastapi import HTTPException

from automatedcompliancechecker.models.schemas import AnalysisRequest
from automatedcompliancechecker.routers import compliance


class FakeUploadFile:
    def __init__(
        self,
        content: bytes = b"%PDF",
        content_type: str = "application/pdf",
        filename: str = "sample.pdf",
    ):
        self._content = content
        self.content_type = content_type
        self.filename = filename

    async def read(self) -> bytes:
        return self._content


def test_analyse_text_returns_report(monkeypatch, sample_issue):
    monkeypatch.setattr(compliance, "require_model_ready", lambda: None)
    monkeypatch.setattr(
        compliance,
        "run_compliance_analysis",
        lambda text: {
            "issues": [sample_issue.model_dump()],
            "articles_violated": ["Art.5"],
            "processing_time_seconds": 0.4,
        },
    )

    report = asyncio.run(
        compliance.analyse_text(
            AnalysisRequest(
                document_name="sample.txt",
                text="This is a long enough policy text for validation. It intentionally contains risky wording.",
            )
        )
    )

    assert report.document_name == "sample.txt"
    assert report.overall_risk == "medium"
    assert report.articles_violated == ["Art.5"]


def test_analyse_text_returns_500_when_pipeline_fails(monkeypatch):
    monkeypatch.setattr(compliance, "require_model_ready", lambda: None)

    def fail_analysis(text: str) -> dict:
        raise RuntimeError("llm failed")

    monkeypatch.setattr(compliance, "run_compliance_analysis", fail_analysis)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            compliance.analyse_text(
                AnalysisRequest(text="This text is long enough to pass validation before the pipeline fails.")
            )
        )

    assert exc_info.value.status_code == 500
    assert "llm failed" in exc_info.value.detail


def test_analyse_pdf_rejects_non_pdf_upload():
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(compliance.analyse_pdf(FakeUploadFile(content_type="text/plain")))

    assert exc_info.value.status_code == 415


def test_analyse_pdf_rejects_large_file(monkeypatch):
    monkeypatch.setattr(compliance, "MAX_FILE_SIZE_MB", 0)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(compliance.analyse_pdf(FakeUploadFile(content=b"%PDF large")))

    assert exc_info.value.status_code == 413


def test_analyse_pdf_returns_422_when_text_cannot_be_extracted(monkeypatch):
    monkeypatch.setattr(compliance, "extract_text_from_pdf", lambda content: "")

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(compliance.analyse_pdf(FakeUploadFile()))

    assert exc_info.value.status_code == 422
    assert "no extractable text" in exc_info.value.detail


def test_analyse_pdf_returns_report(monkeypatch, sample_issue):
    monkeypatch.setattr(compliance, "require_model_ready", lambda: None)
    monkeypatch.setattr(
        compliance,
        "extract_text_from_pdf",
        lambda content: "This extracted privacy policy text is long enough to analyse.",
    )
    monkeypatch.setattr(
        compliance,
        "run_compliance_analysis",
        lambda text: {
            "issues": [sample_issue.model_dump()],
            "articles_violated": ["Art.5"],
            "processing_time_seconds": 0.8,
        },
    )

    report = asyncio.run(compliance.analyse_pdf(FakeUploadFile()))

    assert report.document_name == "sample.pdf"
    assert report.articles_violated == ["Art.5"]
