# MoneyPrinterTurbo NoAPI User Guide

MoneyPrinterTurbo NoAPI is a local-first short-video studio. It combines a FastAPI backend, the original lightweight browser studio, and an advanced Gradio studio mounted at `/studio`. The project does not ask the browser to provide provider API keys. Text generation uses the configured provider CLI or Ollama, while narration uses Edge neural TTS and video composition uses FFmpeg.

## 1. Requirements

| Requirement | Purpose | Required |
|---|---|---:|
| Python 3.11 or newer | Application runtime | Yes |
| FFmpeg and ffprobe | Media normalization, subtitle rendering, and validation | Yes |
| Node.js and the provider CLIs | Account-based text generation providers | Optional, depending on provider |
| Ollama | Local text generation | Optional |
| NVIDIA driver and NVIDIA Container Toolkit | NVIDIA GPU containers | Optional |
| `/dev/dri` access | VAAPI or Intel QSV on Linux | Optional |

The application can render on CPU when no usable GPU runtime is detected. A GPU encoder must be available both in FFmpeg and through the host runtime before it is selected automatically.

## 2. Installation on the Host

Clone the repository and install the package in editable mode:

```bash
git clone https://github.com/GenRamzi/MoneyPrinterTurboNoAPI.git
cd MoneyPrinterTurboNoAPI
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Install FFmpeg with your operating system package manager. On Debian or Ubuntu:

```bash
sudo apt-get update
sudo apt-get install -y ffmpeg
ffmpeg -version
ffprobe -version
```

Copy the environment template if you want to customize storage, concurrency, or rendering:

```bash
cp .env.example .env
```

The application continues to work without provider API keys. Provider login is handled by the official provider command-line tools when a provider requires authentication.

## 3. Starting the Application

Start the server with:

```bash
python main.py
```

The default endpoints are:

| URL | Purpose |
|---|---|
| `http://127.0.0.1:8501/` | Original lightweight web studio |
| `http://127.0.0.1:8501/studio` | Advanced Gradio studio |
| `http://127.0.0.1:8501/docs` | FastAPI interactive API documentation |
| `http://127.0.0.1:8501/api/health` | FFmpeg and ffprobe readiness |
| `http://127.0.0.1:8501/api/gpu` | Detected GPU encoders and selected backend |

The Gradio studio is mounted into the existing FastAPI application using `mount_gradio_app`, which is the integration pattern documented by Gradio.[1]

## 4. Using the Gradio Studio

Open `/studio` and begin by entering a topic. You can select a provider, language, target duration, aspect ratio, clip duration, voice, and optional Ollama model. You may click **Suggest Script** to request a draft, edit the result in the script field, or paste your own narration. The **Voice Preview** action synthesizes a short preview before you start a full render.

Upload images or videos as visual materials and optionally add background music. The renderer cycles through the selected visual materials to cover the narration duration. A completed task exposes the MP4 output together with the request JSON, the script, and the generated subtitle file.

The progress area reports the active task state and selected encoder. The **Cancel Task** button can cancel queued work immediately or request cancellation while a running render reaches its next safe checkpoint.

## 5. One-Click Subtitle Templates

The subtitle panel contains a template dropdown, a live preview text box, and an **Apply Template** button. Choose a template, press the button once, and the studio updates the subtitle format, position, font, size, text color, outline color, and outline width together. Edit the preview text or any style control to see the HTML preview update immediately before rendering.

| Template | Best for | Output |
|---|---|---|
| Creator Bold | General vertical short-form videos | ASS |
| Neon Highlight | Energetic content and gaming-style visuals | ASS |
| Sunset Yellow | Dark footage and warm editorial styles | ASS |
| Minimal Clean | Low-noise educational or product content | ASS |
| Top News | Facts, announcements, and news layouts | ASS |
| Breaking News | Urgent news reels and alerts | ASS |
| Education Focus | Lessons, explainers, and tutorials | ASS |
| Education Highlight | Definitions, formulas, and key takeaways | ASS |
| SRT Compatibility | Editors or players without ASS support | SRT |

You can apply a template and then manually refine any individual setting. ASS remains the default because it preserves styling information. SRT is provided as a compatibility output and does not carry the same visual style metadata.

## 6. ASS Subtitle Output

ASS files are generated with a complete script header, a selected play resolution, a named style, custom colors, outline width, alignment, margins, and timed dialogue events. The renderer uses the selected ASS file when burning captions into the final video. The generated `captions.ass` file is also downloadable from the results panel.

For Arabic and other right-to-left languages, keep a readable font installed on the rendering host. If the selected font is not available, FFmpeg/libass may substitute another font. Use a strong outline and high-contrast colors when the background contains moving footage.

## 7. GPU Acceleration on the Host

The renderer supports four backend requests:

| Value | Encoder | Behavior |
|---|---|---|
| `auto` | NVENC, QSV, VAAPI, or CPU | Selects the first usable hardware runtime and safely falls back to CPU |
| `cpu` | `libx264` | Forces software encoding |
| `nvenc` | `h264_nvenc` | Requires an NVIDIA GPU, driver, and usable NVIDIA runtime |
| `qsv` | `h264_qsv` | Requires Intel Quick Sync exposure and FFmpeg support |
| `vaapi` | `h264_vaapi` | Requires `/dev/dri` exposure and FFmpeg VAAPI support |

Set the backend with an environment variable:

```bash
MPT_GPU_BACKEND=auto python main.py
```

Check the selected backend before rendering:

```bash
curl http://127.0.0.1:8501/api/gpu
```

When `auto` cannot find a usable GPU runtime, the response reports `selected: cpu`. Explicitly requesting an unavailable backend fails early with a clear validation message instead of starting a task that will fail later.

The available FFmpeg encoder list alone is not sufficient to prove that a GPU is usable. The application also checks the corresponding runtime: NVIDIA detection uses `nvidia-smi`, while VAAPI and QSV require `/dev/dri/renderD128`.

## 8. Docker CPU and GPU Modes

The default Compose file is portable and safe for CPU operation:

```bash
docker compose up --build
```

The app is then available at `http://localhost:8501` and the Gradio studio at `http://localhost:8501/studio`.

### NVIDIA GPU Containers

Install a compatible NVIDIA driver and the NVIDIA Container Toolkit on the host first. NVIDIA documents the host installation requirements in its official guide.[3] Docker Compose documents GPU service configuration separately.[2]

Use the repository override:

```bash
docker compose \
  -f docker-compose.yml \
  -f docker-compose.gpu.yml \
  up --build
```

The override requests `gpus: all` and defaults to `MPT_GPU_BACKEND=nvenc`. You can choose another supported value explicitly:

```bash
MPT_GPU_BACKEND=nvenc docker compose \
  -f docker-compose.yml \
  -f docker-compose.gpu.yml \
  up --build
```

If the container starts but `/api/gpu` reports CPU, inspect the host driver, `nvidia-smi`, the NVIDIA Container Toolkit installation, and the FFmpeg encoder list inside the container.

### VAAPI Containers

On a Linux host with Intel or AMD VAAPI, use the VAAPI override:

```bash
docker compose \
  -f docker-compose.yml \
  -f docker-compose.vaapi.yml \
  up --build
```

The override exposes `/dev/dri` and sets `MPT_GPU_BACKEND=vaapi`. The host user and container must have permission to access the render device.

## 9. Batch Processing and Parallel Rendering

Set the batch count in the Gradio studio to create multiple variants from the same narration. Visual materials are rotated between variants, and the rendering phase uses a bounded thread pool so several FFmpeg jobs can run concurrently without creating an unbounded number of processes. Configure the limits with `MPT_MAX_CONCURRENT_TASKS` for independent tasks and `MPT_MAX_BATCH_WORKERS` for variants within one task. Results remain ordered as `video-01.mp4`, `video-02.mp4`, and so on even when individual renders finish at different times.

The best worker count depends on the host. CPU-only machines should use a small value such as 1 or 2. A GPU encoder may support more concurrent renders, but VRAM, disk throughput, and thermals still limit useful parallelism.

## 10. Automatic Installation

On Debian/Ubuntu or Homebrew-based Linux/macOS environments, run:

```bash
./scripts/install.sh
```

On Windows PowerShell, run:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\\scripts\\install.ps1
```

Windows users can also double-click `scripts\\install.bat`. The scripts create `.venv`, install the project and development dependencies, install or verify FFmpeg where the supported package manager is available, and report whether NVIDIA or VAAPI/QSV hardware appears to be available. NVIDIA drivers and container runtimes remain host prerequisites and are not silently replaced by the installer.

## 11. Measuring Performance

Run the full-pipeline smoke test after starting the service:

```bash
MPT_SMOKE_URL=http://127.0.0.1:8501 ./scripts/smoke.sh
```

Run the benchmark to measure task creation, TTS, ASS generation, FFmpeg rendering, and encoder selection:

```bash
MPT_BENCH_URL=http://127.0.0.1:8501 ./scripts/benchmark.sh
```

The benchmark prints the selected backend, encoder label, elapsed seconds, and task ID. Do not compare CPU and GPU timings from different machines as a controlled speedup claim. Measure both modes on the same host, with the same script, aspect ratio, duration, materials, and batch count.

## 12. Troubleshooting

If `/api/health` reports `ok: false`, install FFmpeg and ffprobe or correct `FFMPEG_BIN` and `FFPROBE_BIN`. If a provider cannot generate text, run its official login command and verify that the CLI works in the same user environment as the server. If the Gradio page is unavailable, confirm that the server started without import errors and that the installed package includes `gradio==6.24.0`.

If ASS captions are not visible in the final MP4, verify that the selected font exists on the host and that the source text is non-empty. Download `captions.ass` from the task artifacts and inspect its `[V4+ Styles]` and `[Events]` sections.

If a GPU backend fails, first set `MPT_GPU_BACKEND=auto` to confirm that the project can fall back to CPU. Then verify the runtime device, drivers, FFmpeg encoder support, and container GPU exposure. An encoder name printed by FFmpeg without a visible device does not guarantee that hardware encoding can run.

## 13. Development Checks

Run the complete local quality gate before submitting changes:

```bash
python3 -m compileall -q app tests
pytest -q
ruff check .
node --check web/assets/app.js
bash -n scripts/smoke.sh
bash -n scripts/benchmark.sh
```

## References

[1]: https://www.gradio.app/docs/gradio/mount_gradio_app "Gradio mount_gradio_app documentation"
[2]: https://docs.docker.com/compose/how-tos/gpu-support/ "Docker Compose GPU support"
[3]: https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html "NVIDIA Container Toolkit installation guide"
