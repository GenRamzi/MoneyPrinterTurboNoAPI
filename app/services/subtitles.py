from __future__ import annotations

import re
from pathlib import Path



def _stamp(seconds: float) -> str:
    ms = max(0, int(round(seconds * 1000)))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def _ass_stamp(seconds: float) -> str:
    centiseconds = max(0, int(round(seconds * 100)))
    hours, centiseconds = divmod(centiseconds, 360000)
    minutes, centiseconds = divmod(centiseconds, 6000)
    seconds_value, centiseconds = divmod(centiseconds, 100)
    return f"{hours}:{minutes:02}:{seconds_value:02}.{centiseconds:02}"


def split_sentences(text: str) -> list[str]:
    chunks = re.split(r"(?<=[.!?؟。！？])\s+|\n+", text.strip())
    return [chunk.strip() for chunk in chunks if chunk.strip()]


def _segments(text: str, duration: float) -> list[tuple[float, float, str]]:
    sentences = split_sentences(text) or [text.strip()]
    sentences = [sentence for sentence in sentences if sentence]
    if not sentences:
        return [(0.0, max(0.1, duration), "")]
    weights = [max(1, len(sentence.split())) for sentence in sentences]
    total = sum(weights)
    cursor = 0.0
    result: list[tuple[float, float, str]] = []
    for index, (sentence, weight) in enumerate(zip(sentences, weights, strict=True)):
        segment = duration * (weight / total)
        start = cursor
        end = duration if index == len(sentences) - 1 else min(duration, cursor + segment)
        result.append((start, end, sentence))
        cursor = end
    return result


def write_srt(text: str, duration: float, output: Path) -> Path:
    lines: list[str] = []
    for index, (start, end, sentence) in enumerate(_segments(text, duration), start=1):
        lines.extend([str(index), f"{_stamp(start)} --> {_stamp(end)}", sentence, ""])
    output.write_text("\n".join(lines), encoding="utf-8")
    return output


def _ass_color(hex_color: str, alpha: str = "00") -> str:
    value = hex_color.lstrip("#")
    rr, gg, bb = value[0:2], value[2:4], value[4:6]
    return f"&H{alpha}{bb}{gg}{rr}"


def write_ass(
    text: str,
    duration: float,
    output: Path,
    *,
    position: str = "bottom",
    font_size: int = 22,
    text_color: str = "#FFFFFF",
    outline_color: str = "#000000",
    outline_width: int = 2,
    play_res: tuple[int, int] = (1080, 1920),
    font_name: str = "Arial",
) -> Path:
    alignment = {"bottom": 2, "center": 5, "top": 8}.get(position, 2)
    margin_v = {"bottom": 90, "center": 0, "top": 90}.get(position, 90)
    width, height = play_res
    header = [
        "[Script Info]",
        "ScriptType: v4.00+",
        "WrapStyle: 2",
        "ScaledBorderAndShadow: yes",
        f"PlayResX: {width}",
        f"PlayResY: {height}",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        (
            f"Style: Default,{font_name},{font_size},{_ass_color(text_color)},"
            f"{_ass_color(text_color)},{_ass_color(outline_color)},&H80000000,"
            f"0,0,0,0,100,100,0,0,1,{max(0, outline_width)},0,{alignment},60,60,{margin_v},1"
        ),
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    events = []
    for start, end, sentence in _segments(text, duration):
        safe_text = sentence.replace("\\", "\\\\").replace("\n", "\\N")
        events.append(
            f"Dialogue: 0,{_ass_stamp(start)},{_ass_stamp(end)},Default,,0,0,0,,{safe_text}"
        )
    output.write_text("\n".join([*header, *events, ""]), encoding="utf-8-sig")
    return output
