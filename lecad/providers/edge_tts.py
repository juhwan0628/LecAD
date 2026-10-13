from __future__ import annotations

import asyncio
import os
import subprocess
from pathlib import Path

from .base import TTSResult


class EdgeTTSProvider:
    """No-key development/demo fallback using edge-tts."""

    extension = ".mp3"

    def __init__(self, *, voice: str | None = None, rate: str | None = None):
        self.voice = voice or os.environ.get("LECAD_EDGE_TTS_VOICE") or "ko-KR-SunHiNeural"
        self.rate = rate or os.environ.get("LECAD_EDGE_TTS_RATE") or "+10%"
        self.model = "edge-tts"

    def synthesize(self, *, text: str, output_path: Path) -> TTSResult:
        try:
            import edge_tts
        except ImportError as exc:
            raise RuntimeError("edge-tts is not installed; pip install edge-tts") from exc

        output_path.parent.mkdir(parents=True, exist_ok=True)

        async def _run() -> None:
            communicate = edge_tts.Communicate(text=text, voice=self.voice, rate=self.rate)
            await communicate.save(str(output_path))

        asyncio.run(_run())
        proc = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=nw=1:nk=1",
                str(output_path),
            ],
            check=True, capture_output=True, text=True,
        )
        return TTSResult(output_path, float(proc.stdout.strip()))
