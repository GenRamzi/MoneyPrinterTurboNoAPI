from __future__ import annotations

import json
import math
import shutil
import subprocess
from pathlib import Path

from app.core.config import settings

VIDEO_EXT = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"}
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
AUDIO_EXT = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"}


def require_ffmpeg() -> None:
    if not shutil.which(settings.ffmpeg_bin) or not shutil.which(settings.ffprobe_bin):
        raise RuntimeError("FFmpeg and ffprobe are required. Install FFmpeg and make both commands available in PATH.")


def run_ffmpeg(args: list[str], cwd: Path | None = None) -> None:
    require_ffmpeg()
    p = subprocess.run(
        [settings.ffmpeg_bin, "-hide_banner", "-loglevel", "error", "-y", *args],
        text=True,
        capture_output=True,
        cwd=str(cwd) if cwd else None,
        check=False,
    )
    if p.returncode != 0:
        raise RuntimeError(p.stderr.strip() or "FFmpeg failed")


def duration(path: Path) -> float:
    require_ffmpeg()
    p = subprocess.run(
        [settings.ffprobe_bin, "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)],
        text=True,
        capture_output=True,
        check=False,
    )
    if p.returncode != 0:
        raise RuntimeError(p.stderr.strip() or "ffprobe failed")
    try:
        value = float(json.loads(p.stdout)["format"]["duration"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Unable to read media duration for {path.name}") from exc
    if not math.isfinite(value) or value <= 0:
        raise RuntimeError(f"Media has an invalid duration: {path.name}")
    return value


def dimensions(aspect_ratio: str) -> tuple[int, int]:
    return {"9:16": (1080, 1920), "16:9": (1920, 1080), "1:1": (1080, 1080)}[aspect_ratio]


def normalize_material(source: Path, target: Path, seconds: float, size: tuple[int, int]) -> Path:
    w, h = size
    vf = f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},fps=30,format=yuv420p"
    suffix = source.suffix.lower()
    if suffix in IMAGE_EXT:
        args = ["-loop", "1", "-i", str(source), "-t", f"{seconds:.3f}", "-vf", vf]
    elif suffix in VIDEO_EXT:
        args = ["-stream_loop", "-1", "-i", str(source), "-t", f"{seconds:.3f}", "-vf", vf]
    else:
        raise RuntimeError(f"Unsupported visual material: {source.name}")
    args += ["-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", str(target)]
    run_ffmpeg(args)
    return target


def make_background(
    materials: list[Path],
    target: Path,
    seconds: float,
    aspect_ratio: str,
    clip_duration: float = 4.0,
) -> Path:
    size = dimensions(aspect_ratio)
    if not materials:
        w, h = size
        run_ffmpeg([
            "-f", "lavfi", "-i", f"color=c=0x111318:s={w}x{h}:r=30:d={seconds:.3f}",
            "-vf", "format=yuv420p", "-an", "-c:v", "libx264", "-preset", "veryfast", str(target),
        ])
        return target

    valid = [path for path in materials if path.suffix.lower() in VIDEO_EXT | IMAGE_EXT]
    if not valid:
        return make_background([], target, seconds, aspect_ratio, clip_duration)

    segment_count = max(1, math.ceil(seconds / clip_duration))
    segments: list[Path] = []
    elapsed = 0.0
    for index in range(segment_count):
        remaining = max(0.1, seconds - elapsed)
        segment_seconds = min(clip_duration, remaining)
        source = valid[index % len(valid)]
        segment = target.parent / f"segment-{target.stem}-{index:03}.mp4"
        normalize_material(source, segment, segment_seconds, size)
        segments.append(segment)
        elapsed += segment_seconds
        if elapsed >= seconds - 0.05:
            break

    concat_file = target.parent / f"concat-{target.stem}.txt"
    concat_file.write_text("\n".join(f"file '{p.name}'" for p in segments), encoding="utf-8")
    run_ffmpeg(["-f", "concat", "-safe", "0", "-i", concat_file.name, "-c", "copy", target.name], cwd=target.parent)
    return target


def _ass_color(hex_color: str, alpha: str = "00") -> str:
    value = hex_color.lstrip("#")
    rr, gg, bb = value[0:2], value[2:4], value[4:6]
    return f"&H{alpha}{bb}{gg}{rr}"


def render_final(
    background: Path,
    voice: Path,
    output: Path,
    srt: Path | None = None,
    subtitle_position: str = "bottom",
    subtitle_font_size: int = 22,
    subtitle_color: str = "#FFFFFF",
    subtitle_outline_color: str = "#000000",
    subtitle_outline_width: int = 2,
    bgm: Path | None = None,
    bgm_volume: float = 0.12,
) -> Path:
    inputs = ["-i", str(background), "-i", str(voice)]
    filter_parts: list[str] = []
    video_map = "0:v:0"

    if srt:
        margin = 70 if subtitle_position == "bottom" else 650
        escaped = srt.name.replace("'", "\\'")
        primary = _ass_color(subtitle_color)
        outline = _ass_color(subtitle_outline_color)
        style = (
            f"FontName=Arial,FontSize={subtitle_font_size},PrimaryColour={primary},"
            f"OutlineColour={outline},BorderStyle=1,Outline={subtitle_outline_width},"
            f"Shadow=0,MarginV={margin},Alignment=2"
        )
        filter_parts.append(f"[0:v]subtitles='{escaped}':force_style='{style}'[vout]")
        video_map = "[vout]"

    if bgm:
        inputs += ["-stream_loop", "-1", "-i", str(bgm)]
        filter_parts.append(f"[2:a]volume={bgm_volume:.3f}[music];[1:a][music]amix=inputs=2:duration=first:dropout_transition=2[aout]")
        audio_map = "[aout]"
    else:
        audio_map = "1:a:0"

    args = [*inputs]
    if filter_parts:
        args += ["-filter_complex", ";".join(filter_parts)]
    args += [
        "-map", video_map, "-map", audio_map,
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(output),
    ]
    run_ffmpeg(args, cwd=output.parent)
    return output
