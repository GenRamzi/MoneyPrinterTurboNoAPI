from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    app_name: str = "MoneyPrinterTurbo NoAPI"
    host: str = os.getenv("MPT_HOST", "127.0.0.1")
    port: int = int(os.getenv("MPT_PORT", "8501"))
    storage_dir: Path = Path(os.getenv("MPT_STORAGE", ROOT / "storage")).resolve()
    max_upload_mb: int = int(os.getenv("MPT_MAX_UPLOAD_MB", "500"))
    max_upload_files: int = int(os.getenv("MPT_MAX_UPLOAD_FILES", "20"))
    max_concurrent_tasks: int = int(os.getenv("MPT_MAX_CONCURRENT_TASKS", "2"))
    default_provider: str = os.getenv("MPT_PROVIDER", "gemini")
    default_ollama_model: str = os.getenv("MPT_OLLAMA_MODEL", "qwen3:8b")
    ffmpeg_bin: str = os.getenv("FFMPEG_BIN", "ffmpeg")
    ffprobe_bin: str = os.getenv("FFPROBE_BIN", "ffprobe")
    gpu_backend: str = os.getenv("MPT_GPU_BACKEND", "auto").lower()
    ffmpeg_preset: str = os.getenv("MPT_FFMPEG_PRESET", "veryfast")
    ffmpeg_crf: int = int(os.getenv("MPT_FFMPEG_CRF", "21"))

    @property
    def uploads_dir(self) -> Path:
        return self.storage_dir / "uploads"

    @property
    def tasks_dir(self) -> Path:
        return self.storage_dir / "tasks"

    def ensure_dirs(self) -> None:
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self.tasks_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_dirs()
