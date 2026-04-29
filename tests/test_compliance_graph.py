from automatedcompliancechecker.models.schemas import GraphState, LLMChunkResult
from automatedcompliancechecker.services import compliance_graph


def test_get_llm_uses_model_manager_configuration():
    llm = compliance_graph.get_llm()

    assert llm.model == compliance_graph.model_manager.model_name
    assert llm.base_url == compliance_graph.model_manager.base_url


def test_node_chunk_document_returns_chunks():
    state = compliance_graph.node_chunk_document(
        GraphState(text="First paragraph.\n\nSecond paragraph with more words.")
    )

    assert state.text
    assert state.chunks


def test_node_analyse_articles_deduplicates_issues(monkeypatch, sample_issue):
    calls = []

    def fake_classify(chunk, llm):
        calls.append(chunk)
        return [sample_issue, sample_issue]

    monkeypatch.setattr(compliance_graph, "get_llm", lambda: object())
    monkeypatch.setattr(compliance_graph, "_llm_classify_chunk", fake_classify)

    state = compliance_graph.node_analyse_articles(
        GraphState(text="text", chunks=[{"text": "chunk", "location": "Paragraphs 1-1"}])
    )

    assert len(calls) == 1
    assert len(state.issues) == 1
    assert state.articles_violated == ["Art.5"]


def test_analyse_article_filters_relevant_chunks(monkeypatch, sample_issue):
    chunks = [
        {"text": "Nothing useful here.", "location": "Paragraphs 1-1"},
        {"text": "Processing happens without consent.", "location": "Paragraphs 2-2"},
        {"text": "Again without consent.", "location": "Paragraphs 2-2"},
    ]
    article = {"risk_keywords": ["consent"]}

    monkeypatch.setattr(compliance_graph, "_llm_classify_chunk", lambda chunk, llm: [sample_issue])

    issues = compliance_graph._analyse_article(article, chunks, object())

    assert issues == [sample_issue]


def test_llm_classify_chunk_parses_structured_output(sample_issue):
    class FakeStructuredLlm:
        def invoke(self, messages):
            return LLMChunkResult(issues=[sample_issue])

    class FakeLlm:
        def with_structured_output(self, schema):
            return FakeStructuredLlm()

    result = compliance_graph._llm_classify_chunk(
        {"text": "Policy text", "location": "Paragraphs 1-1"},
        FakeLlm(),
    )

    assert result == [sample_issue]


def test_llm_classify_chunk_returns_empty_list_on_llm_error():
    class FakeStructuredLlm:
        def invoke(self, messages):
            raise RuntimeError("bad output")

    class FakeLlm:
        def with_structured_output(self, schema):
            return FakeStructuredLlm()

    result = compliance_graph._llm_classify_chunk(
        {"text": "Policy text", "location": "Paragraphs 1-1"},
        FakeLlm(),
    )

    assert result == []


def test_run_compliance_analysis_adds_processing_time(monkeypatch):
    class FakeGraph:
        def invoke(self, state):
            return {"issues": [], "articles_violated": [], "chunks": []}

    monkeypatch.setattr(compliance_graph, "COMPLIANCE_GRAPH", FakeGraph())

    result = compliance_graph.run_compliance_analysis("some document text")

    assert result["issues"] == []
    assert "processing_time_seconds" in result

