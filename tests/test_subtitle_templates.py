from __future__ import annotations

import pytest

from app.services.subtitle_templates import apply_template, get_template, list_templates


def test_template_catalog_contains_multiple_styles():
    templates = list_templates()
    assert len(templates) >= 5
    assert {"creator", "neon", "compatibility", "breaking-news", "education-focus", "education-highlight"} <= {item["id"] for item in templates}


def test_apply_template_returns_complete_style_payload():
    values = apply_template("neon")
    assert values["subtitle_format"] == "ass"
    assert values["subtitle_position"] == "center"
    assert values["subtitle_color"] == "#00F5FF"
    assert values["subtitle_outline_width"] == 3


def test_unknown_template_is_rejected():
    with pytest.raises(ValueError):
        get_template("does-not-exist")
