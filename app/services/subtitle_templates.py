from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SubtitleTemplate:
    id: str
    name: str
    description: str
    subtitle_format: str
    position: str
    font_name: str
    font_size: int
    text_color: str
    outline_color: str
    outline_width: int


TEMPLATES: tuple[SubtitleTemplate, ...] = (
    SubtitleTemplate(
        "creator",
        "Creator Bold",
        "High-contrast white captions with a strong outline for vertical videos.",
        "ass",
        "bottom",
        "Arial",
        26,
        "#FFFFFF",
        "#000000",
        4,
    ),
    SubtitleTemplate(
        "neon",
        "Neon Highlight",
        "Bright cyan captions with a dark outline for energetic short-form content.",
        "ass",
        "center",
        "Arial",
        28,
        "#00F5FF",
        "#101020",
        3,
    ),
    SubtitleTemplate(
        "sunset",
        "Sunset Yellow",
        "Warm yellow captions designed to remain readable over dark footage.",
        "ass",
        "bottom",
        "Arial",
        27,
        "#FFD166",
        "#3A1F00",
        3,
    ),
    SubtitleTemplate(
        "minimal",
        "Minimal Clean",
        "Small, clean white captions with a subtle outline and no visual noise.",
        "ass",
        "bottom",
        "Arial",
        22,
        "#FFFFFF",
        "#000000",
        1,
    ),
    SubtitleTemplate(
        "top-news",
        "Top News",
        "Top-aligned bold captions for news, facts, and announcement formats.",
        "ass",
        "top",
        "Arial",
        25,
        "#FFFFFF",
        "#B00020",
        4,
    ),
    SubtitleTemplate(
        "compatibility",
        "SRT Compatibility",
        "Plain SRT output for editors and players that do not support ASS styling.",
        "srt",
        "bottom",
        "Arial",
        22,
        "#FFFFFF",
        "#000000",
        2,
    ),
)

TEMPLATE_BY_ID = {template.id: template for template in TEMPLATES}


def list_templates() -> list[dict[str, str | int]]:
    return [
        {
            "id": template.id,
            "name": template.name,
            "description": template.description,
            "format": template.subtitle_format,
            "position": template.position,
        }
        for template in TEMPLATES
    ]


def get_template(template_id: str) -> SubtitleTemplate:
    try:
        return TEMPLATE_BY_ID[template_id]
    except KeyError as exc:
        raise ValueError(f"Unknown subtitle template: {template_id}") from exc


def apply_template(template_id: str, *, include_subtitles: bool = True) -> dict[str, str | int | bool]:
    template = get_template(template_id)
    return {
        "subtitle_template": template.id,
        "subtitles": include_subtitles,
        "subtitle_format": template.subtitle_format,
        "subtitle_position": template.position,
        "subtitle_font_name": template.font_name,
        "subtitle_font_size": template.font_size,
        "subtitle_color": template.text_color,
        "subtitle_outline_color": template.outline_color,
        "subtitle_outline_width": template.outline_width,
    }
