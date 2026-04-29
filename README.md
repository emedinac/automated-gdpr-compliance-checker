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
ollama pull gemma3:4b
# ollama pull gemma3:12b
poetry install
```

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
