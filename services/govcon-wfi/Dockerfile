FROM python:3.12-slim

WORKDIR /app

# System deps for asyncpg + clickhouse + uvicorn
RUN apt-get update \
 && apt-get install -y --no-install-recommends gcc libpq-dev \
 && rm -rf /var/lib/apt/lists/*

# Copy in just the files needed for the unified service.
COPY packages/py-schemas /app/packages/py-schemas
COPY packages/py-audit /app/packages/py-audit
COPY packages/py-events /app/packages/py-events
COPY packages/py-rules-sdk /app/packages/py-rules-sdk
COPY services/govcon-wfi /app/services/govcon-wfi

# Add packages to PYTHONPATH (no editable installs in slim image).
ENV PYTHONPATH=/app/packages/py-schemas:/app/packages/py-audit:/app/packages/py-events:/app/packages/py-rules-sdk:/app/services/govcon-wfi

RUN pip install --no-cache-dir \
    fastapi \
    "uvicorn[standard]" \
    structlog \
    pydantic \
    pydantic-settings \
    httpx \
    asyncpg \
    redis \
    apscheduler \
    feedparser \
    clickhouse-connect \
    pgvector

EXPOSE 8000

CMD ["uvicorn", "govcon_wfi.main:app", "--host", "0.0.0.0", "--port", "8000"]
