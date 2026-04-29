# ── Builder ────────────────────────────────────────────────────────────────
FROM python:3.14-slim AS builder

WORKDIR /app

ENV POETRY_HOME=/opt/poetry \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app/src

# specify the Poetry version you want to use
ARG POETRY_VERSION=2.3.2 

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip \
    && pip install "poetry==${POETRY_VERSION}"

WORKDIR /app

COPY pyproject.toml poetry.lock ./

COPY README.md ./

COPY src/ ./src/

RUN poetry install --only main


# ── Runtime ────────────────────────────────────────────────────────────────
FROM python:3.14-slim AS runtime

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    libffi8 \
    && rm -rf /var/lib/apt/lists/*

# bring installed env from builder
COPY --from=builder /usr/local /usr/local

COPY pyproject.toml poetry.lock ./

COPY README.md ./

COPY src/ ./src/

RUN useradd -m appuser
USER appuser

EXPOSE 8000

CMD ["uvicorn", "automatedcompliancechecker.main:app", "--host", "0.0.0.0", "--port", "8000"]