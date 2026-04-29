"""
LangGraph-based GDPR compliance analysis pipeline.

Graph flow:
  chunk_document -> analyse_articles -> END
"""

import json
import structlog
import os
import re
import time
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from langgraph.graph import END, StateGraph

from automatedcompliancechecker.models.schemas import ClauseIssue, GraphState, LLMChunkResult
from automatedcompliancechecker.utils.document_parser import (
    chunk_document,
    keyword_prescan,
)
from automatedcompliancechecker.utils.gdpr_articles import GDPR_ARTICLES
from automatedcompliancechecker.utils.document_parser import _deduplicate_issues

logger = structlog.get_logger(__name__)

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:4b")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

SYSTEM_PROMPT = (
    "You are a GDPR/DSGVO compliance expert."
    " Analyse the given document excerpt and determine if it violates the specified GDPR article requirements."
    f" Respond ONLY with a valid JSON object matching this schema: {ClauseIssue.model_json_schema()}"
    " Be strict but fair. Only flag actual violations, not missing-but-not-required clauses."
)


def get_llm() -> ChatOllama:
    return ChatOllama(
        model=OLLAMA_MODEL,
        base_url=OLLAMA_BASE_URL,
        temperature=0.0,
        format="json",
    )


def node_chunk_document(state: GraphState) -> GraphState:
    chunks = chunk_document(state.text, chunk_size=600, overlap=80)
    return GraphState(text=state.text, chunks=chunks)


def node_analyse_articles(state: GraphState) -> GraphState:
    llm = get_llm()
    all_issues: list[ClauseIssue] = []

    for chunk in state.chunks:
        issues = _llm_classify_chunk(chunk, llm)
        all_issues.extend(issues)

    deduped = _deduplicate_issues(all_issues)
    logger.info(
        "deduped_issues",
        issues=[i.model_dump() for i in deduped],
    )
    return GraphState(
        text=state.text,
        chunks=state.chunks,
        issues=[i.model_dump() for i in deduped],
        articles_violated=sorted({i.article_id for i in all_issues}),
    )


def _analyse_article(article: dict, chunks: list[dict], llm: ChatOllama) -> list[ClauseIssue]:
    relevant_chunks = [c for c in chunks if keyword_prescan(c["text"], article["risk_keywords"])]
    found_issues: list[ClauseIssue] = []
    seen_locations: set[str] = set()

    for chunk in relevant_chunks[:5]:
        if chunk["location"] in seen_locations:
            continue
        seen_locations.add(chunk["location"])

        chunk_issues = _llm_classify_chunk(chunk, llm)
        found_issues.extend(chunk_issues)
        if len(found_issues) >= 2:
            break

    return found_issues


def _llm_classify_chunk(chunk: dict, llm: ChatOllama) -> list[ClauseIssue]:
    structured_llm = llm.with_structured_output(LLMChunkResult)

    articles_text = "\n\n".join(
        f"{a['id']} — {a['title']}\n" + "\n".join(f"- {r}" for r in a["requirements"]) for a in GDPR_ARTICLES
    )

    user_prompt = (
        "Evaluate the following document excerpt against these GDPR articles.\n\n"
        f"{articles_text}\n\n"
        f"Excerpt (location: {chunk['location']}):\n---\n{chunk['text'][:1200]}\n---\n\n"
        "Return ALL applicable violations. Multiple articles may be violated simultaneously."
        "For each violation:"
        "- article_id"
        "- exact requirement violated (quote it)"
        "- exact excerpt supporting it"
        "- short justification (max 1 sentence)"
        ""
        "Only return violations explicitly supported by the excerpt."
        "Do NOT infer beyond the text."
    )

    try:
        raw_result = structured_llm.invoke(
            [
                SystemMessage(content="You are a GDPR compliance expert."),
                HumanMessage(content=user_prompt),
            ]
        )
        logger.info("RAW LLM OUTPUT", data=raw_result)
        result = LLMChunkResult.model_validate(raw_result)
        logger.info("PARSED MODEL:", result.model_dump())
        return result.issues or []

    except Exception as e:
        logger.warning(f"Chunk classification failed: {e}")
        return []


def build_compliance_graph():
    graph = StateGraph(GraphState)
    graph.add_node("chunk_document", node_chunk_document)
    graph.add_node("analyse_articles", node_analyse_articles)
    graph.set_entry_point("chunk_document")
    graph.add_edge("chunk_document", "analyse_articles")
    graph.add_edge("analyse_articles", END)
    return graph.compile()


COMPLIANCE_GRAPH = build_compliance_graph()


def run_compliance_analysis(text: str) -> dict[str, Any]:
    t0 = time.time()
    final_state = COMPLIANCE_GRAPH.invoke(GraphState(text=text))
    return {**final_state, "processing_time_seconds": round(time.time() - t0, 2)}
