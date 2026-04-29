# Automated GDPR Compliance Checker

Automated GDPR/DSGVO compliance analysis for contracts, privacy policies, and terms of service.

## Architecture

```
FastAPI -> LangGraph pipeline -> local LLM (ollama)
```

**LangGraph flow:**
```
chunk_document -> analyse_articles -> [aggregate] -> ComplianceReport
```

## Quick Start

### 0. Package Install (if you want to run it locally)

Install Poetry
```bash
curl -sSL https://install.python-poetry.org | python3 -
export PATH="$HOME/.local/bin:$PATH"
source ~/.bashrc
```

Install Ollama
```bash
# macOS / Linux
curl -fsSL https://ollama.ai/install.sh | sh
poetry install
```

The API checks Ollama on startup and triggers `/api/pull` for the configured model if it is missing. Ollama downloads the model into its persistent volume; the API starts immediately and returns `503` for analysis requests until the model is ready.

#### Configuration

| Env var | Default | Description |
|---------------|---------------|---------------|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `gemma3:4b` | Model to use |


### 1. Run the API

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Or with Docker:
```bash
docker compose up --build
```

### 2. Test endpoins and docs

```bash
# Health check
curl http://localhost:8000/health

# Analyse a PDF
curl -X POST http://localhost:8000/api/v1/analyse/pdf \
  -F "file=@privacy_policy.pdf"

# Analyse raw text
curl -X POST http://localhost:8000/api/v1/analyse/text \
  -H "Content-Type: application/json" \
  -d '{"text": "We collect personal data for any purpose indefinitely without consent...", "document_name": "test.txt"}'
```

Interactive docs: http://localhost:8000/docs

Output reference for the previous endpoint call.
```json
{
  "document_name": "text_input",
  "overall_score": 25,
  "overall_risk": "critical",
  "summary": "Found 3 potential compliance issues across 3 GDPR articles (Art.5, Art.6, Art.13). Score: 25/100.",
  "issues": [
    {
      "article_id": "Art.5",
      "article_title": "Principles of processing personal data",
      "issue_description": "Data must be processed lawfully, fairly, and transparently",
      "problematic_text": "We collect personal data for any purpose indefinitely without consent...",
      "location": "Paragraphs 1–1",
      "risk_level": "high",
      "recommendation": "The excerpt indicates indefinite collection without transparency or defined purpose, violating lawful and fair processing requirements."
    },
    {
      "article_id": "Art.6",
      "article_title": "Lawfulness of processing",
      "issue_description": "Processing requires a legal basis: consent, contract, legal obligation, vital interests, public task, or legitimate interests",
      "problematic_text": "We collect personal data for any purpose indefinitely without consent...",
      "location": "Paragraphs 1–1",
      "risk_level": "high",
      "recommendation": "The excerpt explicitly states absence of consent, meaning no valid legal basis for processing under Article 6."
    },
    {
      "article_id": "Art.13",
      "article_title": "Information to be provided (direct collection)",
      "issue_description": "Identity and contact details of controller, purposes and legal basis of processing, retention period",
      "problematic_text": "We collect personal data for any purpose indefinitely without consent...",
      "location": "Paragraphs 1–1",
      "risk_level": "high",
      "recommendation": "The statement implies missing transparency obligations such as purpose limitation and legal basis disclosure required under Article 13."
    }
  ],
  "articles_checked": [
    "Art.5",
    "Art.6",
    "Art.7",
    "Art.13",
    "Art.17",
    "Art.20",
    "Art.25",
    "Art.28",
    "Art.32",
    "Art.33",
    "Art.44-49"
  ],
  "articles_violated": [
    "Art.13",
    "Art.5",
    "Art.6"
  ],
  "processing_time_seconds": 6.68
}
```



## GDPR Articles Covered

Art.5, Art.6, Art.7, Art.13, Art.17, Art.20, Art.25, Art.28, Art.32, Art.33, Art.44-49

## Scoring

- **100–80**: Low risk — broadly compliant
- **79–60**: Medium risk — issues to address
- **59–35**: High risk — significant violations
- **<35**: Critical — immediate review required

## Run Tests

```bash
pytest tests/ -v
```

## Known Limitations

1. **Not legal advice.** This is a screening tool. Flag findings, don't rely on them as legal conclusions.
2. **Small LLMs hallucinate.** gemma3:4b will miss nuanced violations and occasionally flag false positives.
3. **Scanned PDFs not supported.** Text extraction requires machine-readable PDFs.
4. **English and German only.** GDPR keyword matching is EN/DE focused.
