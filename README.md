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

The default Compose file is portable and uses `MPT_GPU_BACKEND=auto`, falling back to CPU when no GPU runtime is available. Account-based CLI login is usually simpler when running the app directly on the host OS.

```bash
docker compose up --build
```

For NVIDIA GPU acceleration, install the NVIDIA Container Toolkit on the host and run the dedicated override:

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build
```

The NVIDIA override requests `gpus: all` and defaults to `MPT_GPU_BACKEND=nvenc`. For Linux hosts with Intel or AMD VAAPI, expose `/dev/dri` through the VAAPI override instead:

```bash
docker compose -f docker-compose.yml -f docker-compose.vaapi.yml up --build
```

The container still starts safely on CPU if the default file is used. Verify the active encoder with `curl http://localhost:8501/api/gpu`. Then open `http://localhost:8501`; the advanced Gradio studio is available at `http://localhost:8501/studio`.

## Advanced Gradio studio

The project includes a Gradio interface mounted at `/studio`. It provides script generation and editing, voice preview, uploads, batch creation, task progress, cancellation, ASS/SRT selection, subtitle styling, one-click subtitle templates, and GPU encoder selection. The original lightweight web studio remains available at `/`. See the comprehensive English [`USER_GUIDE.md`](docs/USER_GUIDE.md) for installation, Docker, templates, ASS, GPU, benchmarking, and troubleshooting.

## Current video workflow

Before rendering, the studio can ask the selected provider for a draft script and shows its approximate word count and spoken duration. The draft remains editable, so the final narration can be reviewed before voice generation starts. ASS is the default subtitle format for short-form videos and preserves custom font, color, outline, alignment, and RTL-friendly event timing; SRT remains available for compatibility.

1. Choose a connected AI account or an installed Ollama model.
2. Enter a topic or paste your own script.
3. Choose language, target duration, shot duration, aspect ratio, and voice.
4. Preview the voice if desired.
5. Configure subtitles and upload any number of images/videos. The renderer cycles them for the duration of the narration.
6. Optionally add background music.
7. Choose one to four output variants. The task engine renders variants with a bounded worker pool, preserves output order, and stores project artifacts under `storage/tasks/<task-id>`.

The template panel includes dedicated **Breaking News**, **Education Focus**, and **Education Highlight** styles in addition to the general creator templates. The live preview updates as the subtitle text or style controls change, before any FFmpeg work starts.

If no visual media is uploaded, the renderer creates a clean generated background so the pipeline remains usable without any stock-media API.

## Architecture

```text
web/                         Modern zero-build frontend
app/gradio_ui.py             Advanced Gradio studio mounted at /studio
app/main.py                  FastAPI entrypoint + SPA and Gradio hosting
app/api.py                   Providers, uploads, tasks, downloads, GPU status, previews
app/providers/               Official CLI account adapters + Ollama
app/services/script.py       AI script generation
app/services/tts.py          Edge neural TTS
app/services/subtitles.py    ASS/SRT timing and custom styling
app/services/subtitle_templates.py One-click subtitle style catalog
app/services/gpu.py          Encoder detection and GPU/CPU selection
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

Copy `.env.example` to `.env` or export the variables in your shell before starting the server. The most useful controls are `MPT_STORAGE` for the project directory, `MPT_MAX_UPLOAD_MB` and `MPT_MAX_UPLOAD_FILES` for upload limits, `MPT_MAX_CONCURRENT_TASKS` for independent task concurrency, and `MPT_MAX_BATCH_WORKERS` for parallel variants inside one task. `MPT_GPU_BACKEND=auto` selects NVIDIA NVENC, Intel QSV, or VAAPI when a usable runtime is detected; otherwise it safely uses CPU/libx264. Set `MPT_GPU_BACKEND=cpu` to force CPU or choose a specific backend to fail fast when that runtime is unavailable. No provider API keys are stored by this application.

### Task history and cancellation

Task manifests are written atomically under `storage/tasks/<task-id>/task.json`. Completed tasks are restored into the task history after a server restart, while tasks that were still queued or running are marked as interrupted instead of being shown as indefinitely active. The web studio also restores an active task from the browser session, retries temporary polling failures, and exposes a cancellation control for queued or running work.

### Quality gates

The continuous-integration workflow compiles the application, runs Ruff, and executes the complete pytest suite. The API tests cover runtime health reporting, upload validation, provider validation, voice validation, script preview, and artifact handling in addition to the existing media and schema tests.

### Project artifacts

Each completed task keeps its generated narration, request metadata, and optional ASS or SRT subtitles next to the MP4 outputs. The results panel exposes safe download links for these artifacts, which makes it easier to revise a script, archive a project, or reuse subtitles in another editor.

### Docker health check

The Docker image exposes `/api/health` as its runtime health endpoint. The endpoint returns `ok: true` only when both FFmpeg and ffprobe are available. Docker Compose restarts the service automatically and can report the container as healthy after FFmpeg and the FastAPI process are available.

### Full pipeline smoke test

After starting the application, run `MPT_SMOKE_URL=http://127.0.0.1:8501 ./scripts/smoke.sh`. The script submits a custom narration, waits for the background task, downloads the resulting MP4 and script artifact, and verifies the MP4 with ffprobe. It does not require a cloud provider because the narration is supplied in the request, but it does require FFmpeg, ffprobe, and network access for Edge neural TTS.

### Performance benchmark

Run `MPT_BENCH_URL=http://127.0.0.1:8501 MPT_BENCH_BATCH_COUNT=2 ./scripts/benchmark.sh` to measure the complete parallel batch path and print the selected backend, encoder, batch count, elapsed seconds, and task ID. On a host without a usable GPU runtime, the expected result is `backend=cpu encoder="CPU / libx264"`; when NVIDIA NVENC, Intel QSV, or VAAPI is available, `MPT_GPU_BACKEND=auto` selects the detected hardware encoder automatically.

### Automatic installation

Linux users can run `./scripts/install.sh`. Windows users can run `Set-ExecutionPolicy -Scope Process Bypass; .\\scripts\\install.ps1` or double-click `scripts\\install.bat`. The installers create `.venv`, install project dependencies, install or verify FFmpeg through the supported package manager, and report detected GPU runtimes.

See [`CHANGELOG.md`](CHANGELOG.md) for the release history and [`docs/performance.md`](docs/performance.md) for the measured benchmark and GPU limitations of the validation environment.

## License

MIT. Upstream copyright and license notice are retained as required by the original license.
