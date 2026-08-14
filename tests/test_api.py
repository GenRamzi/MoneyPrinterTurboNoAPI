from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app


client = TestClient(app)


def test_health_exposes_runtime_capabilities() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] == (payload["ffmpeg"] and payload["ffprobe"])
    assert {"ffmpeg", "ffprobe"} <= payload.keys()


def test_health_is_false_when_ffmpeg_is_missing(monkeypatch) -> None:
    monkeypatch.setattr("app.api.shutil.which", lambda name: None if name == "ffmpeg" else "/usr/bin/ffprobe")
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["ok"] is False
    assert response.json()["ffmpeg"] is False
    assert response.json()["ffprobe"] is True


def test_upload_rejects_unsupported_extension() -> None:
    response = client.post(
        "/api/uploads",
        files={"files": ("notes.txt", b"not media", "text/plain")},
    )
    assert response.status_code == 415
    assert "Unsupported file type" in response.json()["detail"]


def test_upload_accepts_supported_media_and_returns_id() -> None:
    response = client.post(
        "/api/uploads",
        files={"files": ("poster.png", b"fake image bytes", "image/png")},
    )
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["name"] == "poster.png"
    (settings.uploads_dir / payload[0]["id"]).unlink(missing_ok=True)


def test_create_task_rejects_unknown_provider() -> None:
    response = client.post(
        "/api/tasks",
        json={"topic": "اختبار", "provider": "not-a-provider"},
    )
    assert response.status_code == 422
    assert "Unknown provider" in response.json()["detail"]


def test_voice_preview_rejects_unknown_voice() -> None:
    response = client.post(
        "/api/voices/preview",
        json={"voice": "unknown-voice", "text": "اختبار الصوت"},
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "Unsupported voice"


def test_script_preview_returns_generated_metadata(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.api.generate_script",
        lambda *args, **kwargs: "هذا نص قصير للتجربة قبل التصيير",
    )
    response = client.post(
        "/api/scripts/preview",
        json={"topic": "اختبار النص", "provider": "gemini", "duration": 20},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["script"] == "هذا نص قصير للتجربة قبل التصيير"
    assert payload["word_count"] == 6
    assert payload["estimated_seconds"] == 3


def test_missing_task_artifact_returns_not_found() -> None:
    response = client.get("/api/tasks/does-not-exist/artifacts/script.txt")
    assert response.status_code == 404
