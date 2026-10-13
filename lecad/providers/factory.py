from __future__ import annotations

import os

from .base import TTSProvider, VisionProvider
from .codex_provider import CodexVisionProvider
from .edge_tts import EdgeTTSProvider
from .gemini_provider import GeminiVisionProvider
from .gemini_tts import GeminiTTSProvider
from .mock import MockVisionProvider, ToneTTSProvider
from .openai_provider import OpenAITTSProvider, OpenAIVisionProvider


def _build_tts(name: str | None = None) -> TTSProvider:
    tts_name = (name or os.environ.get("LECAD_TTS_PROVIDER") or "gemini").strip().lower()

    if tts_name == "gemini":
        return GeminiTTSProvider()
    if tts_name == "openai":
        return OpenAITTSProvider()
    if tts_name == "edge":
        return EdgeTTSProvider()
    if tts_name == "mock":
        return ToneTTSProvider()

    raise ValueError(f"unsupported TTS provider: {tts_name}")


def build_providers(name: str | None = None) -> tuple[VisionProvider, TTSProvider]:
    provider = (name or os.environ.get("LECAD_PROVIDER") or "codex").strip().lower()

    if provider == "codex":
        return CodexVisionProvider(), _build_tts()

    if provider == "openai":
        return OpenAIVisionProvider(), OpenAITTSProvider()

    if provider == "gemini":
        return GeminiVisionProvider(), _build_tts()

    if provider == "mock":
        return MockVisionProvider(), ToneTTSProvider()

    raise ValueError(f"unsupported provider: {provider}")
