FROM node:22-bookworm-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    GRADIO_ANALYTICS_ENABLED=False \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-venv python3-pip ffmpeg ca-certificates tini \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /opt/venv
RUN npm install --global --no-audit --no-fund \
    @openai/codex @anthropic-ai/claude-code @google/gemini-cli \
    && npm cache clean --force

WORKDIR /app
COPY pyproject.toml README.md LICENSE CHANGELOG.md ./
COPY app ./app
COPY web ./web
COPY docs ./docs
COPY scripts ./scripts

RUN pip install . \
    && chmod +x scripts/*.sh \
    && mkdir -p /app/storage/uploads /app/storage/tasks

VOLUME ["/app/storage"]
EXPOSE 8501
STOPSIGNAL SIGTERM

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8501/api/health', timeout=3)"

ENTRYPOINT ["tini", "--"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8501"]
