from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.core.config import settings

SUPPORTED_BACKENDS = ("auto", "cpu", "nvenc", "vaapi", "qsv")


@dataclass(frozen=True)
class EncoderSelection:
    requested: str
    backend: str
    codec: str
    label: str
    hardware: bool


@lru_cache(maxsize=1)
def _ffmpeg_encoders() -> str:
    if not shutil.which(settings.ffmpeg_bin):
        return ""
    try:
        result = subprocess.run(
            [settings.ffmpeg_bin, "-hide_banner", "-encoders"],
            text=True,
            capture_output=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return result.stdout + "\n" + result.stderr


def _has_encoder(codec: str) -> bool:
    return codec in _ffmpeg_encoders()


def _nvidia_ready() -> bool:
    if not _has_encoder("h264_nvenc") or not shutil.which("nvidia-smi"):
        return False
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            text=True,
            capture_output=True,
            timeout=8,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0 and bool(result.stdout.strip())


def _dri_ready() -> bool:
    return Path("/dev/dri/renderD128").exists()


def gpu_status() -> dict:
    nvidia = _nvidia_ready()
    dri = _dri_ready()
    vaapi = dri and _has_encoder("h264_vaapi")
    qsv = dri and _has_encoder("h264_qsv")
    selected = resolve_encoder("auto")
    return {
        "requested": settings.gpu_backend,
        "selected": selected.backend,
        "label": selected.label,
        "hardware": selected.hardware,
        "available": {
            "cpu": True,
            "nvenc": nvidia,
            "vaapi": vaapi,
            "qsv": qsv,
        },
        "ffmpeg_encoders": {
            "h264_nvenc": _has_encoder("h264_nvenc"),
            "h264_vaapi": _has_encoder("h264_vaapi"),
            "h264_qsv": _has_encoder("h264_qsv"),
        },
        "note": (
            "GPU encoder selected automatically"
            if selected.hardware
            else "No usable GPU runtime detected; using CPU encoding"
        ),
    }


def resolve_encoder(requested: str = "auto") -> EncoderSelection:
    requested = (requested or "auto").lower().strip()
    if requested not in SUPPORTED_BACKENDS:
        raise ValueError(f"Unsupported GPU backend: {requested}")

    available = {
        "nvenc": _nvidia_ready(),
        "vaapi": _dri_ready() and _has_encoder("h264_vaapi"),
        "qsv": _dri_ready() and _has_encoder("h264_qsv"),
    }
    backend = requested
    if requested == "auto":
        backend = next((name for name in ("nvenc", "qsv", "vaapi") if available[name]), "cpu")
    elif requested != "cpu" and not available[requested]:
        raise RuntimeError(
            f"Requested GPU backend '{requested}' is unavailable. "
            "Use gpu_backend=auto or install the matching driver/runtime."
        )

    details = {
        "cpu": ("libx264", "CPU / libx264", False),
        "nvenc": ("h264_nvenc", "NVIDIA NVENC", True),
        "vaapi": ("h264_vaapi", "VAAPI", True),
        "qsv": ("h264_qsv", "Intel Quick Sync", True),
    }
    codec, label, hardware = details[backend]
    return EncoderSelection(requested, backend, codec, label, hardware)


def encoder_args(selection: EncoderSelection) -> list[str]:
    if selection.backend == "cpu":
        return ["-c:v", "libx264", "-preset", settings.ffmpeg_preset, "-crf", str(settings.ffmpeg_crf)]
    if selection.backend == "nvenc":
        return ["-c:v", "h264_nvenc", "-preset", "p4", "-cq", str(settings.ffmpeg_crf), "-pix_fmt", "yuv420p"]
    if selection.backend == "qsv":
        return ["-c:v", "h264_qsv", "-global_quality", str(settings.ffmpeg_crf), "-look_ahead", "1"]
    return ["-c:v", "h264_vaapi", "-qp", str(settings.ffmpeg_crf)]
