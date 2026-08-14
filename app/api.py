from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from app.core.config import settings
from app.models.schemas import (
    GenerateRequest,
    ScriptPreviewRequest,
    ScriptPreviewResponse,
    TaskInfo,
    VoicePreviewRequest,
)
from app.providers.base import ProviderError
from app.providers.registry import provider_registry
from app.services.media import AUDIO_EXT, IMAGE_EXT, VIDEO_EXT
from app.services.script import generate_script
from app.services.tasks import task_manager
from app.services.tts import synthesize

router = APIRouter(prefix="/api")
ALLOWED_UPLOADS = VIDEO_EXT | IMAGE_EXT | AUDIO_EXT
VOICES = [
    {"id": "ar-SA-HamedNeural", "name": "Hamed — Arabic (Saudi)"},
    {"id": "ar-SA-ZariyahNeural", "name": "Zariyah — Arabic (Saudi)"},
    {"id": "ar-EG-ShakirNeural", "name": "Shakir — Arabic (Egypt)"},
    {"id": "ar-EG-SalmaNeural", "name": "Salma — Arabic (Egypt)"},
    {"id": "ar-AE-HamdanNeural", "name": "Hamdan — Arabic (UAE)"},
    {"id": "ar-AE-FatimaNeural", "name": "Fatima — Arabic (UAE)"},
    {"id": "en-US-AndrewNeural", "name": "Andrew — English (US)"},
    {"id": "en-US-AvaNeural", "name": "Ava — English (US)"},
    {"id": "en-GB-RyanNeural", "name": "Ryan — English (UK)"},
    {"id": "en-GB-SoniaNeural", "name": "Sonia — English (UK)"},
]
VOICE_IDS = {voice["id"] for voice in VOICES}


@router.get("/health")
def health() -> dict:
    return {
        "ok": True,
        "app": settings.app_name,
        "ffmpeg": bool(shutil.which(settings.ffmpeg_bin)),
        "ffprobe": bool(shutil.which(settings.ffprobe_bin)),
    }


@router.get("/providers")
def providers():
    return provider_registry.list()


@router.get("/providers/ollama/models")
def ollama_models() -> dict[str, list[str]]:
    return {"models": provider_registry.ollama_models()}


@router.post("/providers/{provider_id}/login")
def provider_login(provider_id: str) -> dict:
    try:
        message = provider_registry.open_login(provider_id)
    except ProviderError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Unable to open provider login: {exc}") from exc
    return {"ok": True, "message": message}


@router.get("/voices")
def voices() -> list[dict[str, str]]:
    return VOICES


@router.post("/scripts/preview", response_model=ScriptPreviewResponse)
def script_preview(request: ScriptPreviewRequest) -> ScriptPreviewResponse:
    try:
        provider_registry.get(request.provider)
    except ProviderError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    try:
        script = generate_script(
            request.provider,
            request.topic,
            request.language,
            request.duration,
            model=request.ollama_model if request.provider == "ollama" else None,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    words = len(script.split())
    estimated_seconds = max(1, round(words / 2.15))
    return ScriptPreviewResponse(script=script, word_count=words, estimated_seconds=estimated_seconds)


@router.post("/voices/preview")
def voice_preview(request: VoicePreviewRequest):
    if request.voice not in VOICE_IDS:
        raise HTTPException(status_code=422, detail="Unsupported voice")
    preview_id = f"preview-{uuid.uuid4().hex}.mp3"
    path = settings.uploads_dir / preview_id
    try:
        synthesize(request.text, request.voice, path)
    except Exception as exc:
        path.unlink(missing_ok=True)
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return FileResponse(
        path,
        media_type="audio/mpeg",
        filename="voice-preview.mp3",
        background=BackgroundTask(path.unlink, missing_ok=True),
    )


@router.post("/uploads")
async def upload(files: list[UploadFile] = File(...)) -> list[dict[str, str]]:
    if not files:
        raise HTTPException(status_code=400, detail="At least one file is required")
    if len(files) > settings.max_upload_files:
        raise HTTPException(status_code=413, detail=f"You can upload at most {settings.max_upload_files} files at once")

    max_bytes = settings.max_upload_mb * 1024 * 1024
    saved: list[dict[str, str]] = []
    try:
        for file in files:
            suffix = Path(file.filename or "").suffix.lower()
            if suffix not in ALLOWED_UPLOADS:
                raise HTTPException(status_code=415, detail=f"Unsupported file type: {suffix or 'unknown'}")
            data = await file.read(max_bytes + 1)
            if len(data) > max_bytes:
                raise HTTPException(status_code=413, detail=f"File exceeds {settings.max_upload_mb} MB")
            file_id = f"{uuid.uuid4().hex}{suffix}"
            target = settings.uploads_dir / file_id
            target.write_bytes(data)
            saved.append({"id": file_id, "name": file.filename or file_id})
        return saved
    except HTTPException:
        for item in saved:
            (settings.uploads_dir / item["id"]).unlink(missing_ok=True)
        raise
    finally:
        for file in files:
            await file.close()


@router.post("/tasks", response_model=TaskInfo)
def create_task(request: GenerateRequest) -> TaskInfo:
    if request.voice not in VOICE_IDS:
        raise HTTPException(status_code=422, detail="Unsupported voice")
    try:
        provider_registry.get(request.provider)
    except ProviderError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return task_manager.create(request)


@router.get("/tasks", response_model=list[TaskInfo])
def list_tasks() -> list[TaskInfo]:
    return task_manager.list()


@router.get("/tasks/{task_id}", response_model=TaskInfo)
def get_task(task_id: str) -> TaskInfo:
    task = task_manager.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.delete("/tasks/{task_id}", response_model=TaskInfo)
def cancel_task(task_id: str) -> TaskInfo:
    task = task_manager.cancel(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.get("/tasks/{task_id}/artifacts/{filename}")
def task_artifact(task_id: str, filename: str):
    if Path(task_id).name != task_id or Path(filename).name != filename:
        raise HTTPException(status_code=400, detail="Invalid path")
    allowed = {
        "script.txt": "text/plain; charset=utf-8",
        "captions.srt": "application/x-subrip; charset=utf-8",
        "request.json": "application/json",
    }
    media_type = allowed.get(filename)
    if not media_type:
        raise HTTPException(status_code=404, detail="Artifact not found")
    task = task_manager.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    path = (settings.tasks_dir / task_id / filename).resolve()
    if path.parent != (settings.tasks_dir / task_id).resolve() or not path.is_file():
        raise HTTPException(status_code=404, detail="Artifact not found")
    return FileResponse(path, media_type=media_type, filename=filename)


@router.get("/tasks/{task_id}/files/{filename}")
def task_file(task_id: str, filename: str):
    if Path(task_id).name != task_id or Path(filename).name != filename:
        raise HTTPException(status_code=400, detail="Invalid path")
    task = task_manager.get(task_id)
    if not task or filename not in task.output_files:
        raise HTTPException(status_code=404, detail="File not found")
    path = (settings.tasks_dir / task_id / filename).resolve()
    if path.parent != (settings.tasks_dir / task_id).resolve() or not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path, media_type="video/mp4", filename=filename)
