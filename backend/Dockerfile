# syntax=docker/dockerfile:1

# Backend image: FastAPI service with the git CLI (GitPython shells out to git).
# Build context is the backend/ folder.
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PLATFORM_ROOT=/app \
    WORKSPACE_ROOT=/workspace \
    GIT_TERMINAL_PROMPT=0 \
    HOME=/home/appuser \
    # Repositories mounted from the host are often owned by another UID. Trust them explicitly.
    # Mounts are read-only in docker-compose and the Kubernetes manifests.
    GIT_CONFIG_COUNT=1 \
    GIT_CONFIG_KEY_0=safe.directory \
    GIT_CONFIG_VALUE_0=*

RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --home-dir /home/appuser --create-home app \
    && mkdir -p /workspace \
    && chown app:app /workspace

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

USER 10001:10001

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import sys, urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4).status == 200 else 1)"

# A single worker is required: event history, analysis history, and monitor state are held in memory.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
