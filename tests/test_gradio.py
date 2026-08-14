from __future__ import annotations

from app.gradio_ui import apply_subtitle_template, build_demo, preview_subtitle


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


def test_live_subtitle_preview_escapes_text_and_reflects_position():
    preview = preview_subtitle('<script>alert("x")</script>', "top", "Arial", 30, "#FFFFFF", "#000000", 2)
    assert "&lt;script&gt;" in preview
    assert "align-items:flex-start" in preview
    assert "font-size:30px" in preview
