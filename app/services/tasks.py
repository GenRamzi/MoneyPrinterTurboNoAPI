from __future__ import annotations

import json
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from app.core.config import settings
from app.models.schemas import GenerateRequest, TaskInfo, TaskState
from app.services.media import AUDIO_EXT, IMAGE_EXT, VIDEO_EXT, duration, make_background, render_final
from app.services.script import generate_script
from app.services.subtitles import write_srt
from app.services.tts import synthesize


class TaskManager:
    def __init__(self) -> None:
        self._tasks: dict[str, TaskInfo] = {}
        self._lock = threading.RLock()
        self._pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="mpt-video")

    def _set(self, task_id: str, **changes) -> None:
        with self._lock:
            task = self._tasks[task_id]
            self._tasks[task_id] = task.model_copy(update=changes)
            self._persist(self._tasks[task_id])

    def _persist(self, task: TaskInfo) -> None:
        folder = settings.tasks_dir / task.id
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "task.json").write_text(task.model_dump_json(indent=2), encoding="utf-8")

    def create(self, request: GenerateRequest) -> TaskInfo:
        task_id = str(uuid.uuid4())
        task = TaskInfo(id=task_id, state=TaskState.queued, progress=0, message="Queued")
        with self._lock:
            self._tasks[task_id] = task
            self._persist(task)
        self._pool.submit(self._run, task_id, request)
        return task

    def get(self, task_id: str) -> TaskInfo | None:
        with self._lock:
            task = self._tasks.get(task_id)
            if task:
                return task
        manifest = settings.tasks_dir / task_id / "task.json"
        if manifest.exists():
            try:
                task = TaskInfo.model_validate_json(manifest.read_text(encoding="utf-8"))
                with self._lock:
                    self._tasks[task_id] = task
                return task
            except Exception:
                return None
        return None

    def list(self) -> list[TaskInfo]:
        with self._lock:
            known = list(self._tasks.values())
        return sorted(known, key=lambda item: item.id, reverse=True)[:50]

    def _upload_path(self, material_id: str) -> Path | None:
        safe = Path(material_id).name
        if safe != material_id:
            return None
        candidate = (settings.uploads_dir / safe).resolve()
        if candidate.parent != settings.uploads_dir:
            return None
        return candidate if candidate.exists() else None

    def _run(self, task_id: str, request: GenerateRequest) -> None:
        folder = settings.tasks_dir / task_id
        folder.mkdir(parents=True, exist_ok=True)
        try:
            self._set(task_id, state=TaskState.running, progress=5, message="Preparing project")
            (folder / "request.json").write_text(
                json.dumps(request.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8"
            )

            script = (request.script or "").strip()
            if not script:
                self._set(task_id, progress=12, message=f"Writing script with {request.provider}")
                script = generate_script(request.provider, request.topic, request.language, request.duration)
            (folder / "script.txt").write_text(script, encoding="utf-8")

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
                self._set(task_id, progress=38, message="Creating subtitles")
                srt = write_srt(script, audio_seconds, folder / "captions.srt")

            outputs: list[str] = []
            for index in range(request.batch_count):
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
                )
                output = folder / f"video-{index + 1:02}.mp4"
                render_final(
                    background=background,
                    voice=voice_file,
                    output=output,
                    srt=srt,
                    subtitle_position=request.subtitle_position,
                    bgm=bgm,
                    bgm_volume=request.bgm_volume,
                )
                outputs.append(output.name)

            self._set(
                task_id,
                state=TaskState.completed,
                progress=100,
                message="Video ready",
                output_files=outputs,
            )
        except Exception as exc:
            self._set(
                task_id,
                state=TaskState.failed,
                progress=100,
                message="Generation failed",
                error=str(exc)[:2000],
            )


task_manager = TaskManager()
