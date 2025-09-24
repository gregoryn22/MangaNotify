# ---- base image ----
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8999 \
    DATA_DIR=/data

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl && rm -rf /var/lib/apt/lists/*

# create app user
RUN useradd -m -u 10001 appuser

WORKDIR /app

# deps
COPY requirements.txt .
RUN pip install -r requirements.txt

# app
COPY . .

# create writable data dir for appuser
RUN mkdir -p /data && chown -R appuser:appuser /data
VOLUME ["/data"]  # ensures first-time volume gets correct ownership

EXPOSE 8999

# simple healthcheck
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD curl -fsS "http://127.0.0.1:${PORT}/api/health" || exit 1

USER appuser

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8999"]
