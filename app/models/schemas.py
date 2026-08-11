from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class TaskState(str, Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"


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


class GenerateRequest(BaseModel):
    topic: str = Field(min_length=2, max_length=1000)
    provider: str = "gemini"
    language: str = "Arabic"
    script: str | None = None
    duration: int = Field(default=45, ge=10, le=600)
    aspect_ratio: Literal["9:16", "16:9", "1:1"] = "9:16"
    voice: str = "ar-SA-HamedNeural"
    subtitles: bool = True
    subtitle_position: Literal["bottom", "center"] = "bottom"
    material_ids: list[str] = Field(default_factory=list)
    bgm_id: str | None = None
    bgm_volume: float = Field(default=0.12, ge=0.0, le=1.0)
    batch_count: int = Field(default=1, ge=1, le=4)


class TaskInfo(BaseModel):
    id: str
    state: TaskState
    progress: int = 0
    message: str = ""
    output_files: list[str] = Field(default_factory=list)
    error: str | None = None
