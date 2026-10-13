from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
import math


@dataclass(frozen=True)
class GateResult:
    is_visual_reference: bool
    target: str | None = None
    reason: str | None = None
    confidence: float | None = None

    def __post_init__(self):
        if not isinstance(self.is_visual_reference, bool):
            raise ValueError("is_visual_reference must be a boolean")
        if self.confidence is not None and (
            not isinstance(self.confidence, (int, float)) or isinstance(self.confidence, bool)
            or not math.isfinite(self.confidence) or not 0 <= self.confidence <= 1
        ):
            raise ValueError("gate confidence must be between 0 and 1")


@dataclass(frozen=True)
class DescriptionResult:
    text: str
    visual_facts: tuple[str, ...] = ()
    missing_information: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, data: dict, text_key: str = "text") -> DescriptionResult:
        text = data.get(text_key, "")
        if not isinstance(text, str):
            raise ValueError("model description must be a string")
        facts = data.get("visual_facts", [])
        missing = data.get("missing_information", [])
        for values in (facts, missing):
            if not isinstance(values, list) or any(not isinstance(v, str) for v in values):
                raise ValueError("model visual facts must be lists of strings")
        return cls(text.strip(), tuple(facts), tuple(missing))


@dataclass(frozen=True)
class TTSResult:
    audio_path: Path
    duration_s: float


class VisionProvider(Protocol):
    """Provider-neutral contract for the VLM layer."""

    def gate(
        self,
        *,
        frame_path: Path,
        utterance: str,
        context_text: str,
    ) -> GateResult:
        ...

    def describe(
        self,
        *,
        frame_path: Path,
        utterance: str,
        context_text: str,
        target: str | None,
    ) -> DescriptionResult:
        ...


class TTSProvider(Protocol):
    """Provider-neutral contract for text-to-speech."""

    def synthesize(
        self,
        *,
        text: str,
        output_path: Path,
    ) -> TTSResult:
        ...
