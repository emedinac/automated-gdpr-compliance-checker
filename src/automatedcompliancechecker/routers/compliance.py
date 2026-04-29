import structlog
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from automatedcompliancechecker.models.schemas import AnalysisRequest, ComplianceReport
from automatedcompliancechecker.services.compliance_graph import run_compliance_analysis
from automatedcompliancechecker.services.report_builder import build_report
from automatedcompliancechecker.utils.document_parser import extract_text_from_pdf

logger = structlog.get_logger(__name__)
router = APIRouter()

MAX_FILE_SIZE_MB = 10
MAX_TEXT_CHARS = 150_000


@router.post(
    "/analyse/text",
    response_model=ComplianceReport,
    summary="Analyse plain text document",
)
async def analyse_text(request: AnalysisRequest) -> ComplianceReport:
    """Submit raw text for GDPR compliance analysis."""
    text = request.text[:MAX_TEXT_CHARS]
    return _run(text, request.document_name or "text_input")


@router.post("/analyse/pdf", response_model=ComplianceReport, summary="Analyse PDF document")
async def analyse_pdf(
    file: Annotated[UploadFile, File(description="PDF file to analyse")],
    document_name: Annotated[str | None, Form()] = None,
) -> ComplianceReport:
    """Upload a PDF for GDPR compliance analysis."""
    if file.content_type not in ("application/pdf", "application/octet-stream"):
        raise HTTPException(status_code=415, detail="Only PDF files are accepted.")

    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        raise HTTPException(status_code=413, detail=f"File too large. Max {MAX_FILE_SIZE_MB}MB.")

    try:
        text = extract_text_from_pdf(content)
    except Exception as e:
        logger.error(f"PDF extraction failed: {e}")
        raise HTTPException(status_code=422, detail=f"Could not extract text from PDF: {e}")

    if len(text.strip()) < 50:
        raise HTTPException(
            status_code=422,
            detail="PDF appears to contain no extractable text (scanned image?).",
        )

    name = document_name or file.filename or "uploaded.pdf"
    return _run(text[:MAX_TEXT_CHARS], name)


def _run(text: str, document_name: str) -> ComplianceReport:
    """Shared analysis runner."""
    logger.info("analysis.started")
    try:
        logger.info(f"Running compliance analysis for document: {document_name} with text: {text[:100]}...")
        state = run_compliance_analysis(text)
    except Exception as e:
        logger.error(f"Analysis pipeline failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")

    return build_report(
        document_name=document_name,
        raw_issues=state.get("issues", []),
        articles_violated=state.get("articles_violated", []),
        processing_time=state.get("processing_time_seconds", 0.0),
    )
