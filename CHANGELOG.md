# Changelog

## 0.3.0

This feature release adds an advanced Gradio studio mounted at `/studio`, while preserving the original web UI at `/`. The new interface supports script drafting, voice preview, uploads, batch generation, progress, cancellation, subtitle styling, and encoder selection.

The renderer now writes custom ASS subtitles by default, keeps SRT as a compatibility option, exposes GPU capability detection through `/api/gpu`, and selects NVIDIA NVENC, Intel QSV, VAAPI, or CPU/libx264 safely. Explicitly unavailable GPU backends fail with a clear validation error, while `auto` falls back to CPU.

The release adds GPU and ASS unit tests, a full-pipeline benchmark script, Gradio integration checks, and runtime documentation for enabling GPU acceleration.

## 0.2.1

This maintenance release makes `/api/health` report `ok: true` only when both FFmpeg and ffprobe are available. It adds a repository-level full-pipeline smoke test that submits a custom script, waits for task completion, downloads the MP4 and script artifact, and validates the generated media with ffprobe.

## 0.2.0

This release expands the local-first studio into a more complete and recoverable workflow.

The API now validates providers and voices, supports script preview with word-count and duration metadata, exposes safe project artifact downloads, and reports media-duration failures clearly. Provider command timeouts and operating-system errors are converted into readable provider results instead of uncaught subprocess failures.

The task engine now persists metadata atomically, restores task history after restart, marks interrupted work explicitly, supports cancellation, records artifact files, and cleans up cancellation state after completion. The web studio can propose a script before rendering, restore active work, retry transient polling errors, show historical outputs, and download scripts, subtitles, and request metadata alongside MP4 files.

The release also adds API and task-lifecycle tests, a sample environment file, CI linting, and expanded runtime documentation.
