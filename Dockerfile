FROM node:22-bookworm-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-venv python3-pip ffmpeg ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /opt/venv
RUN npm install -g @openai/codex @anthropic-ai/claude-code @google/gemini-cli

WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY app ./app
COPY web ./web
RUN pip install --no-cache-dir .

RUN mkdir -p /app/storage/uploads /app/storage/tasks
VOLUME ["/app/storage"]
EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8501/api/health', timeout=3)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8501"]
