# ---- base image ----
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8999 \
    DATA_DIR=/data \
    PYTHONPATH=/app/src

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl build-essential && rm -rf /var/lib/apt/lists/*

# non-root user
RUN useradd -m -u 10001 appuser

WORKDIR /app

# dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# app code (src layout)
COPY --chown=appuser:appuser src/ ./src/

# runtime data dir
RUN mkdir -p /data && chown -R appuser:appuser /data
VOLUME ["/data"]

EXPOSE 8999

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD curl -fsS "http://127.0.0.1:${PORT}/api/health" || exit 1

USER appuser

# IMPORTANT: module path changed to manganotify.server:app
CMD ["uvicorn", "manganotify.server:app", "--host", "0.0.0.0", "--port", "8999"]
