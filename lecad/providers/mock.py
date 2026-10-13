from __future__ import annotations

from pathlib import Path
import subprocess

from .base import DescriptionResult, GateResult, TTSResult


class MockVisionProvider:
    """Development-only deterministic VLM replacement."""

    def gate(self, *, frame_path: Path, utterance: str, context_text: str) -> GateResult:
        return GateResult(
            is_visual_reference=True,
            target="mock visual target",
            reason="mock provider",
            confidence=1.0,
        )

    def describe(
        self,
        *,
        frame_path: Path,
        utterance: str,
        context_text: str,
        target: str | None,
    ) -> DescriptionResult:
        return DescriptionResult(
            text=f"화면에서 참조된 시각 요소를 설명합니다: {utterance}"
        )


class ToneTTSProvider:
    """Development-only TTS replacement that generates a short tone with FFmpeg."""

    extension = ".mp3"

    def __init__(self, duration_s: float = 1.5, frequency_hz: int = 880):
        self.duration_s = duration_s
        self.frequency_hz = frequency_hz

    def synthesize(self, *, text: str, output_path: Path) -> TTSResult:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [
                "ffmpeg", "-loglevel", "error", "-y",
                "-f", "lavfi",
                "-i", f"sine=frequency={self.frequency_hz}:duration={self.duration_s}",
                "-c:a", "mp3",
                str(output_path),
            ],
            check=True,
        )
        return TTSResult(audio_path=output_path, duration_s=self.duration_s)
