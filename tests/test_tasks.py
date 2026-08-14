from __future__ import annotations

import shutil
from dataclasses import replace
import threading
import time

from app.core.config import settings
from app.models.schemas import GenerateRequest, TaskState
from app.services.gpu import EncoderSelection
from app.services.tasks import TaskManager


def test_queued_task_can_be_cancelled_and_restored() -> None:
    manager = TaskManager()
    manager._pool.submit = lambda *args, **kwargs: None
    task = manager.create(GenerateRequest(topic="اختبار دورة المهمة"))
    task_dir = settings.tasks_dir / task.id
    try:
        cancelled = manager.cancel(task.id)
        assert cancelled is not None
        assert cancelled.state == TaskState.cancelled
        restored = TaskManager().get(task.id)
        assert restored is not None
        assert restored.state == TaskState.cancelled
    finally:
        shutil.rmtree(task_dir, ignore_errors=True)
        manager._pool.shutdown(wait=False, cancel_futures=True)


def test_batch_variants_render_in_parallel_and_keep_order(monkeypatch) -> None:
    manager = TaskManager()
    manager._pool.submit = lambda *args, **kwargs: None
    active = 0
    peak = 0
    lock = threading.Lock()

    def fake_synthesize(script, voice, target):
        target.write_bytes(b"voice")
        return target

    def fake_make_background(materials, target, seconds, aspect_ratio, clip_duration=4.0, gpu_backend="auto"):
        target.write_bytes(b"background")
        return target

    def fake_render_final(**kwargs):
        nonlocal active, peak
        with lock:
            active += 1
            peak = max(peak, active)
        time.sleep(0.05)
        kwargs["output"].write_bytes(b"video")
        with lock:
            active -= 1
        return kwargs["output"]

    monkeypatch.setattr("app.services.tasks.resolve_encoder", lambda backend: EncoderSelection(backend, "cpu", "libx264", "CPU", False))
    monkeypatch.setattr("app.services.tasks.synthesize", fake_synthesize)
    monkeypatch.setattr("app.services.tasks.duration", lambda path: 1.0)
    monkeypatch.setattr("app.services.tasks.make_background", fake_make_background)
    monkeypatch.setattr("app.services.tasks.render_final", fake_render_final)
    monkeypatch.setattr("app.services.tasks.settings", replace(settings, max_batch_workers=2))

    task = manager.create(GenerateRequest(topic="parallel", script="One. Two.", batch_count=3))
    task_dir = settings.tasks_dir / task.id
    try:
        manager._run(task.id, GenerateRequest(topic="parallel", script="One. Two.", batch_count=3))
        result = manager.get(task.id)
        assert result is not None
        assert result.state == TaskState.completed
        assert result.output_files == ["video-01.mp4", "video-02.mp4", "video-03.mp4"]
        assert peak >= 2
    finally:
        shutil.rmtree(task_dir, ignore_errors=True)
        manager._pool.shutdown(wait=False, cancel_futures=True)
