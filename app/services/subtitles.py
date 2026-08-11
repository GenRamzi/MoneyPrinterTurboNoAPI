from __future__ import annotations

import re
from pathlib import Path


def _stamp(seconds: float) -> str:
    ms = max(0, int(round(seconds * 1000)))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def split_sentences(text: str) -> list[str]:
    chunks = re.split(r"(?<=[.!?؟。！？])\s+|\n+", text.strip())
    return [chunk.strip() for chunk in chunks if chunk.strip()]


def write_srt(text: str, duration: float, output: Path) -> Path:
    sentences = split_sentences(text) or [text.strip()]
    weights = [max(1, len(sentence.split())) for sentence in sentences]
    total = sum(weights)
    cursor = 0.0
    lines: list[str] = []
    for index, (sentence, weight) in enumerate(zip(sentences, weights, strict=True), start=1):
        segment = duration * (weight / total)
        start = cursor
        end = duration if index == len(sentences) else min(duration, cursor + segment)
        lines.extend([str(index), f"{_stamp(start)} --> {_stamp(end)}", sentence, ""])
        cursor = end
    output.write_text("\n".join(lines), encoding="utf-8")
    return output
