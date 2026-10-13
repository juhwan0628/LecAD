from __future__ import annotations

import base64
import json
import os
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

from .base import TTSResult


class GeminiTTSProvider:
    """Gemini text-to-speech via the official generateContent REST endpoint."""

    extension = ".wav"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        voice: str | None = None,
        base_url: str = "https://generativelanguage.googleapis.com/v1beta",
    ):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or ""
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY (or GOOGLE_API_KEY) is required")
        self.model = model or os.environ.get("LECAD_GEMINI_TTS_MODEL") or "gemini-3.8-flash-lite-tts"
        self.voice = voice or os.environ.get("LECAD_GEMINI_TTS_VOICE") or "Kore"
        self.base_url = base_url.rstrip("/")

    def synthesize(self, *, text: str, output_path: Path) -> TTSResult:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        body = {
            "contents": [{
                "role": "user",
                "parts": [{
                    "text": text,
                    "speech_metadata": {
                        "style": "clear, calm, neutral Korean accessibility narration; concise and distinct from the lecturer"
                    },
                }],
            }],
            "generationConfig": {
                "responseModalities": ["AUDIO"],
                "speechConfig": {"voiceConfig": {"voice": self.voice}},
            },
        }
        req = urllib.request.Request(
            f"{self.base_url}/models/{self.model}:generateContent",
            data=json.dumps(body).encode("utf-8"),
            method="POST",
            headers={
                "x-goog-api-key": self.api_key,
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                payload = json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Gemini TTS HTTP {exc.code}: {detail[:1000]}") from exc

        try:
            encoded = payload["candidates"][0]["content"]["parts"][0]["inlineData"]["data"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(f"Gemini TTS returned no audio: {str(payload)[:1000]}") from exc
        output_path.write_bytes(base64.b64decode(encoded))

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
