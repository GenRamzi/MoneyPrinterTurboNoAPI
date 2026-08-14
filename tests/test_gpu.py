from __future__ import annotations

from app.services import gpu


def test_auto_encoder_falls_back_to_cpu(monkeypatch):
    monkeypatch.setattr(gpu, "_nvidia_ready", lambda: False)
    monkeypatch.setattr(gpu, "_dri_ready", lambda: False)
    monkeypatch.setattr(gpu, "_has_encoder", lambda codec: True)
    selection = gpu.resolve_encoder("auto")
    assert selection.backend == "cpu"
    assert selection.codec == "libx264"
    assert selection.hardware is False


def test_explicit_unavailable_gpu_is_rejected(monkeypatch):
    monkeypatch.setattr(gpu, "_nvidia_ready", lambda: False)
    monkeypatch.setattr(gpu, "_dri_ready", lambda: False)
    monkeypatch.setattr(gpu, "_has_encoder", lambda codec: False)
    try:
        gpu.resolve_encoder("nvenc")
    except RuntimeError as exc:
        assert "unavailable" in str(exc)
    else:
        raise AssertionError("Expected unavailable GPU backend to fail")


def test_encoder_args_include_expected_codecs():
    assert "libx264" in gpu.encoder_args(gpu.resolve_encoder("cpu"))
