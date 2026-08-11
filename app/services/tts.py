from __future__ import annotations

import asyncio
from pathlib import Path

import edge_tts


async def _save(text: str, voice: str, output: Path) -> None:
    communicate = edge_tts.Communicate(text=text, voice=voice)
    await communicate.save(str(output))


def synthesize(text: str, voice: str, output: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    asyncio.run(_save(text, voice, output))
    if not output.exists() or output.stat().st_size == 0:
        raise RuntimeError("TTS did not create audio output")
    return output
