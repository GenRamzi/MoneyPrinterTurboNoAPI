from __future__ import annotations

from app.gradio_ui import apply_subtitle_template, build_demo


def test_gradio_demo_builds() -> None:
    demo = build_demo()
    assert demo is not None
    assert hasattr(demo, "launch")


def test_gradio_template_action_returns_all_style_values() -> None:
    values = apply_subtitle_template("neon")
    assert values[0] is True
    assert values[1] == "ass"
    assert values[2] == "center"
    assert values[5] == "#00F5FF"
