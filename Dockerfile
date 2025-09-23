# ---- base image ----
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# system deps (for building wheels + curl for healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl && rm -rf /var/lib/apt/lists/*

# create app user
RUN useradd -m -u 10001 appuser

WORKDIR /app

# ---- deps layer ----
COPY requirements.txt .
RUN pip install -r requirements.txt

# ---- app layer ----
COPY . .

# default runtime env
ENV PORT=8080 \
    FLASK_ENV=production \
    WATCHLIST_FILE=/data/watchlist.json

# expose container port
EXPOSE 8999

# simple healthcheck hitting Flask/Gunicorn
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD curl -fsS "http://127.0.0.1:${PORT}/api/health" || exit 1

# drop privileges
USER appuser

# run with gunicorn (WSGI)
# -k gthread keeps things simple; tweak workers/threads if needed
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8999"]

