from __future__ import annotations

from app.gradio_ui import build_demo


def test_gradio_demo_builds() -> None:
    demo = build_demo()
    assert demo is not None
    assert hasattr(demo, "launch")
