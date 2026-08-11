# MoneyPrinterTurbo NoAPI

A modern, local-first rebuild of [MoneyPrinterTurbo](https://github.com/harry0703/MoneyPrinterTurbo) that removes the old **LLM Settings / API-key workflow** and replaces it with **connected AI accounts and local models**.

> Status: first functional rebuild. The UI, account-provider layer, local media pipeline, TTS, subtitles, task runner, and FFmpeg renderer are implemented. This repository intentionally does **not** scrape browser cookies or impersonate ChatGPT/Claude/Gemini web sessions.

## What changed

- New responsive web studio instead of the large Streamlit settings screen.
- No user API-key form.
- ChatGPT through the official **Codex CLI** after `codex login`.
- Claude through the official **Claude Code CLI** after account login.
- Gemini through the official **Gemini CLI** after Google login.
- Ollama as a fully local fallback with no cloud account.
- Prompt → script → neural TTS → SRT subtitles → media composition → MP4 pipeline.
- Local image/video uploads, background music, 9:16 / 16:9 / 1:1 output, and batch generation.
- FastAPI backend with task progress and downloadable results.
- No credential copying: account credentials stay where the official provider CLI stores them.

## Important meaning of “NoAPI”

“NoAPI” means **the user does not enter or manage an API key in this application**. Cloud models still communicate with their vendors through the vendor’s official authenticated software. ChatGPT, Claude, and Gemini subscriptions/usage rules still apply. Ollama is the option for fully local inference.

The app does not use unofficial cookie extraction, hidden browser endpoints, session-token copying, or credential harvesting.

## Requirements

- Python 3.11+
- FFmpeg + ffprobe available in `PATH`
- At least one AI provider below
- Internet access for cloud-account providers and Edge neural TTS

### ChatGPT

```bash
npm install -g @openai/codex
codex login
codex login status
```

### Gemini

```bash
npm install -g @google/gemini-cli
gemini
```

Inside Gemini CLI, choose **Login with Google**. After that, MoneyPrinterTurbo NoAPI uses Gemini CLI headless mode for script generation.

### Claude

```bash
npm install -g @anthropic-ai/claude-code
claude auth login
claude auth status
```

### Ollama (fully local)

Install Ollama, then:

```bash
ollama pull qwen3:8b
ollama list
```

Change the default local model with:

```bash
export MPT_OLLAMA_MODEL="qwen3:8b"
```

On Windows PowerShell:

```powershell
$env:MPT_OLLAMA_MODEL="qwen3:8b"
```

## Run locally

```bash
git clone https://github.com/GenRamzi/MoneyPrinterTurboNoAPI.git
cd MoneyPrinterTurboNoAPI
python -m venv .venv
```

Activate the virtual environment, then:

```bash
pip install -e .
python main.py
```

Open `http://127.0.0.1:8501`.

The UI can launch a provider login terminal on common desktop systems. If the app is running in Docker, a remote server, or a desktop environment where terminal launching is unavailable, it shows the exact login command instead.

## Docker

Docker is useful for the renderer and Ollama-oriented deployments. Account-based CLI login is usually simpler when running the app directly on the host OS.

```bash
docker compose up --build
```

Then open `http://localhost:8501`.

## Current video workflow

1. Choose a connected AI account.
2. Enter a topic or paste your own script.
3. Choose language, duration, aspect ratio, voice, and subtitle position.
4. Upload any number of images/videos; they are normalized and rotated across batch outputs.
5. Optionally add background music.
6. Generate. The task engine writes the script, voice, captions, intermediate media, and final MP4 files under `storage/tasks/<task-id>/`.

If no visual media is uploaded, the renderer creates a clean generated background so the pipeline remains usable without any stock-media API.

## Architecture

```text
web/                         Modern zero-build frontend
app/main.py                  FastAPI entrypoint + SPA hosting
app/api.py                   Providers, uploads, tasks, downloads
app/providers/               Official CLI account adapters
app/services/script.py       AI script generation
app/services/tts.py          Edge neural TTS
app/services/subtitles.py    SRT timing/generation
app/services/media.py        FFmpeg normalization/composition
app/services/tasks.py        Background job orchestration
storage/                     User uploads and generated projects
```

Provider adapters are intentionally isolated. Adding another provider only requires implementing the `TextProvider` interface; the creator UI consumes the registry automatically.

## Security decisions

- No API keys are accepted by the web UI.
- No browser cookies are requested, parsed, or stored.
- Login commands are fixed per provider; user input is never concatenated into an arbitrary shell command.
- Upload and task-download paths are normalized and constrained to application storage.
- Provider credentials remain managed by the official CLIs.
- Generated files are local unless the user deploys this server elsewhere.

## Differences from upstream

This is a clean architectural rebuild inspired by and derived from MoneyPrinterTurbo’s MIT-licensed concept and workflow. It is not a claim of affiliation with Harry or the AI vendors. See `NOTICE.md` and `LICENSE`.

The original project supports many API-backed LLM and stock-media providers. This rebuild deliberately prioritizes **account login, local inference, local materials, and a much simpler product surface** instead of reproducing API-key configuration screens.

## Development

```bash
pip install -e ".[dev]"
pytest -q
python -m compileall -q app
```

## License

MIT. Upstream copyright and license notice are retained as required by the original license.
