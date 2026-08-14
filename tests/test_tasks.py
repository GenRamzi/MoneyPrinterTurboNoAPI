from __future__ import annotations

import shutil

from app.core.config import settings
from app.models.schemas import GenerateRequest, TaskState
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
