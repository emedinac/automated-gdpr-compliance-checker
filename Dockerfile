# ── Builder ─────────────────────────────────────────────
FROM python:3.14-slim AS builder

WORKDIR /app

ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app/src

ARG POETRY_VERSION=2.3.2

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc libffi-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip \
    && pip install "poetry==${POETRY_VERSION}"

COPY pyproject.toml poetry.lock ./
COPY src ./src
COPY README.md ./

RUN poetry install --only main --no-root


# ── Runtime ─────────────────────────────────────────────
FROM python:3.14-slim AS runtime

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src

RUN apt-get update && apt-get install -y --no-install-recommends \
    libffi8 curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/local /usr/local
COPY src ./src

RUN useradd -m appuser
USER appuser

EXPOSE 8000

CMD ["uvicorn", "automatedcompliancechecker.main:app", "--host", "0.0.0.0", "--port", "8000"]