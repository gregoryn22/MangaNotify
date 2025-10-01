# ---- base image ----
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8999 \
    DATA_DIR=/data \
    PYTHONPATH=/app/src

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl build-essential && rm -rf /var/lib/apt/lists/*

# non-root user (Unraid standard: nobody:users)
RUN useradd -m -u 99 -g 100 appuser

WORKDIR /app

# dependencies
COPY requirements.in requirements.txt ./
RUN pip install --no-cache-dir pip-tools && pip-compile requirements.in && pip install --no-cache-dir -r requirements.txt

# app code (src layout)
COPY --chown=99:100 src/ ./src/

# runtime data dir
RUN mkdir -p /data && chown -R 99:100 /data
VOLUME ["/data"]

EXPOSE 8999

USER appuser

# IMPORTANT: module path changed to manganotify.server:app
CMD ["uvicorn", "manganotify.main:app", "--host", "0.0.0.0", "--port", "8999"]
