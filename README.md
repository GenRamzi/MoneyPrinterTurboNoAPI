# MoneyPrinterTurbo NoAPI

A modern, local-first rebuild of [MoneyPrinterTurbo](https://github.com/harry0703/MoneyPrinterTurbo) that removes the old **LLM Settings / API-key workflow** and replaces it with **connected AI accounts and local models**.

> Status: functional rebuild with a new UI, account-provider layer, local media pipeline, TTS, subtitles, task runner, and FFmpeg renderer. This repository intentionally does **not** scrape browser cookies or impersonate ChatGPT/Claude/Gemini web sessions.

## What changed

- New responsive web studio instead of the large Streamlit settings screen.
- No user API-key form.
- ChatGPT through the official **Codex CLI** after `codex login`.
- Claude through the official **Claude Code CLI** after account login.
- Gemini through the official **Gemini CLI** after Google login.
- Ollama as a fully local fallback; the UI detects every locally installed Ollama model.
- Prompt → script → neural TTS → SRT subtitles → media composition → MP4 pipeline.
- Local image/video uploads, background music, 9:16 / 16:9 / 1:1 output, and batch generation.
- Configurable shot duration so uploaded media cycles naturally through longer videos.
- Subtitle position, font size, text color, outline color, and outline width controls.
- Voice preview before rendering.
- FastAPI backend with task progress and downloadable results.
- No credential copying: account credentials stay where the official provider CLI stores them.

## Important meaning of “NoAPI”

“NoAPI” means **the user does not enter or manage an API key in this application**. Cloud models still communicate with their vendors through the vendor’s official authenticated software. ChatGPT, Claude, and Gemini subscriptions/usage rules still apply. Ollama is the option for fully local inference.

The app does not use unofficial cookie extraction, hidden browser endpoints, session-token copying, or credential harvesting.

See [`docs/PROVIDERS.md`](docs/PROVIDERS.md) for the provider policy and extension guide.

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

Install Ollama and pull one or more models. Every model returned by `ollama list` appears in the creator UI.

```bash
ollama pull qwen3:8b
ollama list
```

The fallback model can also be changed with `MPT_OLLAMA_MODEL`.

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

Before rendering, the studio can ask the selected provider for a draft script and shows its approximate word count and spoken duration. The draft remains editable, so the final narration can be reviewed before voice generation starts.

1. Choose a connected AI account or an installed Ollama model.
2. Enter a topic or paste your own script.
3. Choose language, target duration, shot duration, aspect ratio, and voice.
4. Preview the voice if desired.
5. Configure subtitles and upload any number of images/videos. The renderer cycles them for the duration of the narration.
6. Optionally add background music.
7. Generate one to four output variants. The task engine stores project artifacts under `storage/tasks/<task-id>/`.

If no visual media is uploaded, the renderer creates a clean generated background so the pipeline remains usable without any stock-media API.

## Architecture

```text
web/                         Modern zero-build frontend
app/main.py                  FastAPI entrypoint + SPA hosting
app/api.py                   Providers, uploads, tasks, downloads, voice preview
app/providers/               Official CLI account adapters + Ollama
app/services/script.py       AI script generation
app/services/tts.py          Edge neural TTS
app/services/subtitles.py    SRT timing/generation
app/services/media.py        FFmpeg normalization/composition
app/services/tasks.py        Background job orchestration
docs/PROVIDERS.md            Provider/security policy
storage/                     User uploads and generated projects
```

Provider adapters are intentionally isolated. Adding another provider only requires implementing the `TextProvider` interface and registering it; the creator UI consumes provider state from the registry.

## Security decisions

- No API keys are accepted by the web UI.
- No browser cookies are requested, parsed, or stored.
- Login commands are fixed per provider; user input is never concatenated into an arbitrary login shell command.
- Upload and task-download paths are normalized and constrained to application storage.
- Provider credentials remain managed by the official CLIs.
- Temporary voice-preview files are removed after delivery.
- Generated project files are local unless the user deploys this server elsewhere.

## Deliberate NoAPI tradeoff

The upstream project can automatically search some stock-media services when API credentials are configured. This rebuild does not silently reintroduce those keys. It uses local image/video uploads plus a generated fallback background. A future stock-media connector should only be added when it can comply with that service's official authentication and usage terms.

## Attribution

This is a clean architectural rebuild inspired by and derived from MoneyPrinterTurbo’s MIT-licensed concept and workflow. It is not a claim of affiliation with Harry or the AI vendors. See `NOTICE.md` and `LICENSE`.

The original MIT copyright notice is retained.

## Development

```bash
pip install -e ".[dev]"
python -m compileall -q app
ruff check .
pytest -q
```

### Runtime configuration

Copy `.env.example` to `.env` or export the variables in your shell before starting the server. The most useful controls are `MPT_STORAGE` for the project directory, `MPT_MAX_UPLOAD_MB` and `MPT_MAX_UPLOAD_FILES` for upload limits, and `MPT_MAX_CONCURRENT_TASKS` for renderer concurrency. No provider API keys are stored by this application.

### Task history and cancellation

Task manifests are written atomically under `storage/tasks/<task-id>/task.json`. Completed tasks are restored into the task history after a server restart, while tasks that were still queued or running are marked as interrupted instead of being shown as indefinitely active. The web studio also restores an active task from the browser session, retries temporary polling failures, and exposes a cancellation control for queued or running work.

### Quality gates

The continuous-integration workflow compiles the application, runs Ruff, and executes the complete pytest suite. The API tests cover runtime health reporting, upload validation, provider validation, voice validation, script preview, and artifact handling in addition to the existing media and schema tests.

### Project artifacts

Each completed task keeps its generated narration, request metadata, and optional SRT subtitles next to the MP4 outputs. The results panel exposes safe download links for these artifacts, which makes it easier to revise a script, archive a project, or reuse subtitles in another editor.

### Docker health check

The Docker image exposes `/api/health` as its runtime health endpoint. Docker Compose restarts the service automatically and can report the container as healthy after FFmpeg and the FastAPI process are available.

See [`CHANGELOG.md`](CHANGELOG.md) for the release history.

## License

MIT. Upstream copyright and license notice are retained as required by the original license.
