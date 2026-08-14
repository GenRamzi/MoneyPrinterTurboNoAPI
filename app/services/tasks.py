from __future__ import annotations

import json
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import settings
from app.models.schemas import GenerateRequest, TaskInfo, TaskState
from app.services.media import AUDIO_EXT, IMAGE_EXT, VIDEO_EXT, duration, make_background, render_final
from app.services.script import generate_script
from app.services.subtitles import write_srt
from app.services.tts import synthesize


class TaskCancelled(Exception):
    """Raised internally when a user cancels a queued or running task."""


class TaskManager:
    def __init__(self) -> None:
        self._tasks: dict[str, TaskInfo] = {}
        self._cancel_events: dict[str, threading.Event] = {}
        self._lock = threading.RLock()
        self._pool = ThreadPoolExecutor(
            max_workers=max(1, settings.max_concurrent_tasks),
            thread_name_prefix="mpt-video",
        )
        self._load_persisted()

    def _set(self, task_id: str, **changes) -> TaskInfo:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                raise KeyError(f"Unknown task: {task_id}")
            updated = task.model_copy(update=changes)
            self._tasks[task_id] = updated
            self._persist(updated)
            return updated

    def _persist(self, task: TaskInfo) -> None:
        folder = settings.tasks_dir / task.id
        folder.mkdir(parents=True, exist_ok=True)
        manifest = folder / "task.json"
        temporary = folder / "task.json.tmp"
        temporary.write_text(task.model_dump_json(indent=2), encoding="utf-8")
        temporary.replace(manifest)

    def _load_persisted(self) -> None:
        for manifest in settings.tasks_dir.glob("*/task.json"):
            try:
                task = TaskInfo.model_validate_json(manifest.read_text(encoding="utf-8"))
            except Exception:
                continue
            if task.state in {TaskState.queued, TaskState.running}:
                task = task.model_copy(
                    update={
                        "state": TaskState.failed,
                        "progress": 100,
                        "message": "Generation interrupted by a previous shutdown",
                        "error": "The task did not finish before the server stopped.",
                    }
                )
                self._persist(task)
            self._tasks[task.id] = task

    def create(self, request: GenerateRequest) -> TaskInfo:
        task_id = str(uuid.uuid4())
        task = TaskInfo(
            id=task_id,
            state=TaskState.queued,
            progress=0,
            message="Queued",
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        with self._lock:
            self._tasks[task_id] = task
            self._cancel_events[task_id] = threading.Event()
            self._persist(task)
        self._pool.submit(self._run, task_id, request)
        return task

    def get(self, task_id: str) -> TaskInfo | None:
        if Path(task_id).name != task_id:
            return None
        with self._lock:
            task = self._tasks.get(task_id)
            if task:
                return task
        manifest = settings.tasks_dir / task_id / "task.json"
        if not manifest.is_file():
            return None
        try:
            task = TaskInfo.model_validate_json(manifest.read_text(encoding="utf-8"))
        except Exception:
            return None
        with self._lock:
            self._tasks[task_id] = task
        return task

    def list(self) -> list[TaskInfo]:
        for manifest in settings.tasks_dir.glob("*/task.json"):
            task_id = manifest.parent.name
            if self.get(task_id) is None:
                continue
        with self._lock:
            tasks = list(self._tasks.values())
        return sorted(tasks, key=lambda item: item.created_at or item.id, reverse=True)[:50]

    def cancel(self, task_id: str) -> TaskInfo | None:
        task = self.get(task_id)
        if task is None:
            return None
        if task.state in {TaskState.completed, TaskState.failed, TaskState.cancelled}:
            return task
        with self._lock:
            event = self._cancel_events.setdefault(task_id, threading.Event())
            event.set()
        if task.state == TaskState.queued:
            return self._set(
                task_id,
                state=TaskState.cancelled,
                progress=100,
                message="Generation cancelled",
            )
        return self._set(task_id, message="Cancellation requested")

    def _check_cancelled(self, task_id: str) -> None:
        with self._lock:
            event = self._cancel_events.get(task_id)
        if event and event.is_set():
            raise TaskCancelled

    def _upload_path(self, material_id: str) -> Path | None:
        safe = Path(material_id).name
        if safe != material_id:
            return None
        candidate = (settings.uploads_dir / safe).resolve()
        if candidate.parent != settings.uploads_dir:
            return None
        return candidate if candidate.is_file() else None

    def _run(self, task_id: str, request: GenerateRequest) -> None:
        folder = settings.tasks_dir / task_id
        folder.mkdir(parents=True, exist_ok=True)
        try:
            self._check_cancelled(task_id)
            self._set(task_id, state=TaskState.running, progress=5, message="Preparing project")
            (folder / "request.json").write_text(
                json.dumps(request.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8"
            )

            self._check_cancelled(task_id)
            script = (request.script or "").strip()
            if not script:
                self._set(task_id, progress=12, message=f"Writing script with {request.provider}")
                model = request.ollama_model if request.provider == "ollama" else None
                script = generate_script(
                    request.provider,
                    request.topic,
                    request.language,
                    request.duration,
                    model=model,
                )
            (folder / "script.txt").write_text(script, encoding="utf-8")

            self._check_cancelled(task_id)
            self._set(task_id, progress=28, message="Generating voice-over")
            voice_file = synthesize(script, request.voice, folder / "voice.mp3")
            audio_seconds = max(1.0, duration(voice_file))

            visual_materials: list[Path] = []
            for item in request.material_ids:
                path = self._upload_path(item)
                if path and path.suffix.lower() in (VIDEO_EXT | IMAGE_EXT):
                    visual_materials.append(path)

            bgm = self._upload_path(request.bgm_id) if request.bgm_id else None
            if bgm and bgm.suffix.lower() not in AUDIO_EXT:
                bgm = None

            srt: Path | None = None
            if request.subtitles:
                self._check_cancelled(task_id)
                self._set(task_id, progress=38, message="Creating subtitles")
                srt = write_srt(script, audio_seconds, folder / "captions.srt")

            outputs: list[str] = []
            for index in range(request.batch_count):
                self._check_cancelled(task_id)
                base = 42 + int(index * (48 / max(1, request.batch_count)))
                self._set(
                    task_id,
                    progress=min(base, 88),
                    message=f"Rendering video {index + 1}/{request.batch_count}",
                )
                ordered = visual_materials[index:] + visual_materials[:index] if visual_materials else []
                background = make_background(
                    ordered,
                    folder / f"background-{index + 1:02}.mp4",
                    audio_seconds,
                    request.aspect_ratio,
                    clip_duration=request.clip_duration,
                )
                self._check_cancelled(task_id)
                output = folder / f"video-{index + 1:02}.mp4"
                render_final(
                    background=background,
                    voice=voice_file,
                    output=output,
                    srt=srt,
                    subtitle_position=request.subtitle_position,
                    subtitle_font_size=request.subtitle_font_size,
                    subtitle_color=request.subtitle_color,
                    subtitle_outline_color=request.subtitle_outline_color,
                    subtitle_outline_width=request.subtitle_outline_width,
                    bgm=bgm,
                    bgm_volume=request.bgm_volume,
                )
                self._check_cancelled(task_id)
                outputs.append(output.name)

            artifacts = ["request.json", "script.txt"]
            if srt:
                artifacts.append("captions.srt")
            self._set(
                task_id,
                state=TaskState.completed,
                progress=100,
                message="Video ready",
                output_files=outputs,
                artifact_files=artifacts,
            )
        except TaskCancelled:
            self._set(task_id, state=TaskState.cancelled, progress=100, message="Generation cancelled")
        except Exception as exc:
            self._set(task_id, state=TaskState.failed, progress=100, message="Generation failed", error=str(exc)[:2000])
        finally:
            with self._lock:
                self._cancel_events.pop(task_id, None)


task_manager = TaskManager()
