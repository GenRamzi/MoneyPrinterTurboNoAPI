# Changelog

## 0.2.0

This release expands the local-first studio into a more complete and recoverable workflow.

The API now validates providers and voices, supports script preview with word-count and duration metadata, exposes safe project artifact downloads, and reports media-duration failures clearly. Provider command timeouts and operating-system errors are converted into readable provider results instead of uncaught subprocess failures.

The task engine now persists metadata atomically, restores task history after restart, marks interrupted work explicitly, supports cancellation, records artifact files, and cleans up cancellation state after completion. The web studio can propose a script before rendering, restore active work, retry transient polling errors, show historical outputs, and download scripts, subtitles, and request metadata alongside MP4 files.

The release also adds API and task-lifecycle tests, a sample environment file, CI linting, and expanded runtime documentation.
