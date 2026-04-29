# ── Builder ────────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

ENV POETRY_VERSION=2.1.4 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false

# system deps for native builds
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libffi-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# install poetry
RUN pip install "poetry==$POETRY_VERSION"

# copy dependency files first (cache layer)
COPY pyproject.toml poetry.lock ./

# install dependencies only (NO project yet)
RUN poetry install --only main --no-root

# now copy source
COPY src/ ./src/

# install project properly into site-packages
RUN poetry install --only main


# ── Runtime ────────────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# runtime system deps only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libffi8 \
    && rm -rf /var/lib/apt/lists/*

# copy only installed environment (clean)
COPY --from=builder /usr/local /usr/local

# optional: copy app (only needed if not packaged properly)
COPY src/ ./src/

RUN useradd -m appuser && chown -R appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "automatedcompliancechecker.main:app", "--host", "0.0.0.0", "--port", "8000"]