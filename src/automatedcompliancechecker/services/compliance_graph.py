"""
LangGraph-based GDPR compliance analysis pipeline.

Graph flow:
  extract_chunks -> [for each article] keyword_filter -> llm_classify -> aggregate_results

Uses Ollama (local, free) with configurable model.
Falls back to rule-based analysis if Ollama is unavailable.
"""

import json
import logging
import os
import re
import time
from typing import Any, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from langgraph.graph import END, StateGraph

from automatedcompliancechecker.models.schemas import RiskLevel
from automatedcompliancechecker.utils.document_parser import (
    chunk_document,
    find_problematic_sentence,
    keyword_prescan,
)
from automatedcompliancechecker.utils.gdpr_articles import GDPR_ARTICLES

logger = logging.getLogger(__name__)

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:4b")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

SYSTEM_PROMPT = """You are a GDPR/DSGVO compliance expert. Analyse the given document excerpt and determine if it violates the specified GDPR article requirements.

Respond ONLY with a valid JSON object — no preamble, no markdown, no explanation outside JSON.

JSON schema:
{
  "is_violation": boolean,
  "risk_level": "low" | "medium" | "high" | "critical",
  "issue_description": "concise explanation of the violation (max 150 chars)",
  "recommendation": "specific fix recommendation (max 150 chars)"
}

Be strict but fair. Only flag actual violations, not missing-but-not-required clauses."""


class GraphState(TypedDict):
    text: str
    chunks: list[dict]
    issues: list[dict]
    articles_violated: list[str]
    error: str | None


def build_llm() -> ChatOllama | None:
    """Build Ollama LLM client. Returns None if unavailable."""
    try:
        llm = ChatOllama(
            model=OLLAMA_MODEL,
            base_url=OLLAMA_BASE_URL,
            temperature=0.0,
            format="json",
            timeout=60,
        )
        return llm
    except Exception as e:
        logger.warning(f"Ollama unavailable: {e}. Using rule-based fallback.")
        return None


LLM: ChatOllama | None = None


def get_llm():
    global LLM
    if LLM is None:
        LLM = build_llm()
    return LLM


# ── Graph nodes ─────────────────────────────────────────────────────────────


def node_chunk_document(state: GraphState) -> GraphState:
    """Split document text into overlapping chunks."""
    chunks = chunk_document(state["text"], chunk_size=600, overlap=80)
    return {**state, "chunks": chunks, "issues": [], "articles_violated": []}


def node_analyse_articles(state: GraphState) -> GraphState:
    """
    For each GDPR article, scan relevant chunks and classify violations.
    Uses LLM where available, falls back to keyword heuristics.
    """
    llm = get_llm()
    issues: list[dict] = []
    articles_violated: set[str] = set()

    for article in GDPR_ARTICLES:
        article_issues = _analyse_article(article, state["chunks"], llm)
        if article_issues:
            issues.extend(article_issues)
            articles_violated.add(article["id"])

    return {**state, "issues": issues, "articles_violated": list(articles_violated)}


def _analyse_article(
    article: dict, chunks: list[dict], llm: ChatOllama | None
) -> list[dict]:
    """Analyse one GDPR article across all relevant chunks."""
    relevant_chunks = [
        c for c in chunks if keyword_prescan(c["text"], article["risk_keywords"])
    ]
    if not relevant_chunks:
        return []

    found_issues = []
    seen_locations: set[str] = set()

    for chunk in relevant_chunks[:5]:  # Cap at 5 chunks per article to limit latency
        if chunk["location"] in seen_locations:
            continue
        seen_locations.add(chunk["location"])

        if llm:
            issue = _llm_classify(chunk, article, llm)
        else:
            issue = _rule_based_classify(chunk, article)

        if issue:
            found_issues.append(issue)
            if len(found_issues) >= 2:  # Max 2 issues per article
                break

    return found_issues


def _llm_classify(chunk: dict, article: dict, llm: ChatOllama) -> dict | None:
    """Use LLM to classify if chunk violates the article."""
    requirements_text = "\n".join(f"- {r}" for r in article["requirements"])
    user_prompt = f"""GDPR Article: {article["id"]} — {article["title"]}

Requirements:
{requirements_text}

Document excerpt (location: {chunk["location"]}):
---
{chunk["text"][:1200]}
---

Does this excerpt violate any of the above requirements?"""

    try:
        response = llm.invoke(
            [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=user_prompt)]
        )
        raw = response.content
        # Strip markdown fences if model ignores format=json
        raw = re.sub(r"```json|```", "", raw).strip()
        data = json.loads(raw)

        if not data.get("is_violation"):
            return None

        problematic_text = find_problematic_sentence(
            chunk["text"], article["risk_keywords"]
        )
        return {
            "article_id": article["id"],
            "article_title": article["title"],
            "issue_description": data.get(
                "issue_description", "Potential violation detected"
            ),
            "problematic_text": problematic_text or chunk["text"][:200],
            "location": chunk["location"],
            "risk_level": data.get("risk_level", "medium"),
            "recommendation": data.get(
                "recommendation", "Review and update clause for GDPR compliance"
            ),
        }
    except Exception as e:
        logger.warning(f"LLM classification failed for {article['id']}: {e}")
        return _rule_based_classify(chunk, article)


def _rule_based_classify(chunk: dict, article: dict) -> dict | None:
    """
    Heuristic fallback. Flags chunks with high-risk keyword density.
    Less precise than LLM but zero latency and zero cost.
    """
    text_lower = chunk["text"].lower()
    matched_keywords = [
        kw for kw in article["risk_keywords"] if kw.lower() in text_lower
    ]

    # Require at least 2 keyword hits to reduce false positives
    if len(matched_keywords) < 2:
        return None

    # High-risk patterns that strongly suggest violations
    red_flags = [
        ("cannot withdraw", RiskLevel.HIGH),
        ("irrevocable", RiskLevel.HIGH),
        ("indefinitely", RiskLevel.MEDIUM),
        ("any purpose", RiskLevel.HIGH),
        ("pre-ticked", RiskLevel.HIGH),
        ("implied consent", RiskLevel.MEDIUM),
        ("non-deletable", RiskLevel.HIGH),
        ("unencrypted", RiskLevel.CRITICAL),
    ]

    risk = RiskLevel.LOW
    for pattern, pattern_risk in red_flags:
        if pattern in text_lower:
            risk = pattern_risk
            break

    if risk == RiskLevel.LOW and len(matched_keywords) < 3:
        return None  # Not confident enough without LLM

    problematic_text = find_problematic_sentence(
        chunk["text"], article["risk_keywords"]
    )
    return {
        "article_id": article["id"],
        "article_title": article["title"],
        "issue_description": f"Potential {article['id']} issue: keywords [{', '.join(matched_keywords[:3])}] suggest non-compliance",
        "problematic_text": problematic_text or chunk["text"][:200],
        "location": chunk["location"],
        "risk_level": risk.value,
        "recommendation": f"Review clause against {article['id']} requirements: {article['requirements'][0]}",
    }


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
    """Run full GDPR compliance analysis. Returns raw state dict."""
    t0 = time.time()
    final_state = COMPLIANCE_GRAPH.invoke(
        {
            "text": text,
            "chunks": [],
            "issues": [],
            "articles_violated": [],
            "error": None,
        }
    )
    elapsed = round(time.time() - t0, 2)
    return {**final_state, "processing_time_seconds": elapsed}
