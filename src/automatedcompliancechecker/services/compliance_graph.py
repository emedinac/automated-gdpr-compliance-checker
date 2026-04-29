"""
LangGraph-based GDPR compliance analysis pipeline.

Graph flow:
  chunk_document -> analyse_articles -> END
"""

import json
import logging
import os
import re
import time
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from langgraph.graph import END, StateGraph

from automatedcompliancechecker.models.schemas import ClauseIssue, GraphState
from automatedcompliancechecker.utils.document_parser import (
    chunk_document,
    find_problematic_sentence,
    keyword_prescan,
)
from automatedcompliancechecker.utils.gdpr_articles import GDPR_ARTICLES

logger = logging.getLogger(__name__)

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


# ── Graph nodes ──────────────────────────────────────────────────────────────


def node_chunk_document(state: GraphState) -> GraphState:
    chunks = chunk_document(state.text, chunk_size=600, overlap=80)
    return GraphState(text=state.text, chunks=chunks)


def node_analyse_articles(state: GraphState) -> GraphState:
    llm = get_llm()
    issues: list[dict] = []
    articles_violated: set[str] = set()

    for article in GDPR_ARTICLES:
        article_issues = _analyse_article(article, state.chunks, llm)
        if article_issues:
            issues.extend(article_issues)
            articles_violated.add(article["id"])

    return GraphState(
        text=state.text,
        chunks=state.chunks,
        issues=issues,
        articles_violated=list(articles_violated),
    )


def _analyse_article(article: dict, chunks: list[dict], llm: ChatOllama) -> list[dict]:
    relevant_chunks = [c for c in chunks if keyword_prescan(c["text"], article["risk_keywords"])]
    found_issues = []
    seen_locations: set[str] = set()

    for chunk in relevant_chunks[:5]:
        if chunk["location"] in seen_locations:
            continue
        seen_locations.add(chunk["location"])

        issue = _llm_classify(chunk, article, llm)
        if issue:
            found_issues.append(issue)
        if len(found_issues) >= 2:
            break

    return found_issues


def _llm_classify(chunk: dict, article: dict, llm: ChatOllama) -> dict | None:
    requirements_text = "\n".join(f"- {r}" for r in article["requirements"])
    user_prompt = (
        f"GDPR Article: {article['id']} — {article['title']}\n\n"
        f"Requirements:\n{requirements_text}\n\n"
        f"Document excerpt (location: {chunk['location']}):\n---\n{chunk['text'][:1200]}\n---\n\n"
        "Does this excerpt violate any of the above requirements?"
    )

    try:
        response = llm.invoke([SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=user_prompt)])
        raw = response.content if isinstance(response.content, str) else json.dumps(response.content)
        data = json.loads(re.sub(r"```json|```", "", raw).strip())

        if not data.get("is_violation"):
            return None

        return {
            "article_id": article["id"],
            "article_title": article["title"],
            "issue_description": data.get("issue_description", "Potential violation detected"),
            "problematic_text": find_problematic_sentence(chunk["text"], article["risk_keywords"])
            or chunk["text"][:200],
            "location": chunk["location"],
            "risk_level": data.get("risk_level", "medium"),
            "recommendation": data.get("recommendation", "Review and update clause for GDPR compliance"),
        }
    except Exception as e:
        logger.warning(f"LLM classification failed for {article['id']}: {e}")
        return None


# ── Graph construction ───────────────────────────────────────────────────────


def build_compliance_graph():
    graph = StateGraph(GraphState)
    graph.add_node("chunk_document", node_chunk_document)
    graph.add_node("analyse_articles", node_analyse_articles)
    graph.set_entry_point("chunk_document")
    graph.add_edge("chunk_document", "analyse_articles")
    graph.add_edge("analyse_articles", END)
    return graph.compile()


COMPLIANCE_GRAPH = build_compliance_graph()


# ── Public API ───────────────────────────────────────────────────────────────


def run_compliance_analysis(text: str) -> dict[str, Any]:
    t0 = time.time()
    final_state = COMPLIANCE_GRAPH.invoke(GraphState(text=text))
    return {**final_state, "processing_time_seconds": round(time.time() - t0, 2)}
