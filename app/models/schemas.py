from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class TaskState(str, Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class ProviderInfo(BaseModel):
    id: str
    name: str
    icon: str
    kind: Literal["account", "local"]
    installed: bool
    authenticated: bool | None = None
    status: str
    login_hint: str | None = None
    install_hint: str | None = None


class VoicePreviewRequest(BaseModel):
    voice: str
    text: str = Field(default="مرحباً بك في MoneyPrinterTurbo NoAPI", min_length=2, max_length=220)


class ScriptPreviewRequest(BaseModel):
    topic: str = Field(min_length=2, max_length=1000)
    provider: str = "gemini"
    ollama_model: str | None = Field(default=None, max_length=200)
    language: str = "Arabic"
    duration: int = Field(default=45, ge=10, le=600)


class ScriptPreviewResponse(BaseModel):
    script: str
    word_count: int
    estimated_seconds: int


class GenerateRequest(BaseModel):
    topic: str = Field(min_length=2, max_length=1000)
    provider: str = "gemini"
    ollama_model: str | None = Field(default=None, max_length=200)
    language: str = "Arabic"
    script: str | None = None
    duration: int = Field(default=45, ge=10, le=600)
    aspect_ratio: Literal["9:16", "16:9", "1:1"] = "9:16"
    clip_duration: float = Field(default=4.0, ge=1.0, le=15.0)
    voice: str = "ar-SA-HamedNeural"
    subtitles: bool = True
    subtitle_position: Literal["bottom", "center"] = "bottom"
    subtitle_font_size: int = Field(default=22, ge=12, le=64)
    subtitle_color: str = Field(default="#FFFFFF", pattern=r"^#[0-9A-Fa-f]{6}$")
    subtitle_outline_color: str = Field(default="#000000", pattern=r"^#[0-9A-Fa-f]{6}$")
    subtitle_outline_width: int = Field(default=2, ge=0, le=8)
    material_ids: list[str] = Field(default_factory=list)
    bgm_id: str | None = None
    bgm_volume: float = Field(default=0.12, ge=0.0, le=1.0)
    batch_count: int = Field(default=1, ge=1, le=4)


class TaskInfo(BaseModel):
    id: str
    state: TaskState
    progress: int = 0
    created_at: str = ""
    message: str = ""
    output_files: list[str] = Field(default_factory=list)
    artifact_files: list[str] = Field(default_factory=list)
    error: str | None = None
