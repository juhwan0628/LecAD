from __future__ import annotations

import os
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

from .providers.base import TTSProvider, VisionProvider, TTSResult
from .context import partition_transcript
from .render.media import probe_duration


def clean_script(text: str) -> str:
    if not isinstance(text, str):
        raise ValueError("AD script must be text")
    # Strip narration labels only; retain the actual spoken description.
    label = r"(?:음성\s*해설|오디오\s*해설|대본|설명|audio\s*description|AD)"
    prefix = rf"^\s*(?:\*{{1,2}})?(?:\[\s*{label}\s*\]|\(\s*{label}\s*\)|{label}(?=\s|[.:：]|$))[\s.:：*]*"
    while True:
        cleaned = re.sub(prefix, "", text, count=1, flags=re.IGNORECASE)
        if cleaned == text:
            return " ".join(cleaned.split())
        text = cleaned


def _slide_audio(tts: TTSProvider, audio_dir: Path) -> TTSResult:
    settings = {key: getattr(tts, key, None) for key in ("model", "voice", "rate")}
    settings.update(provider=tts.__class__.__name__, text="슬라이드 전환")
    digest = hashlib.sha256(json.dumps(settings, sort_keys=True).encode()).hexdigest()[:16]
    path = audio_dir / f"slide_change-{digest}{getattr(tts, 'extension', '.mp3')}"
    if path.exists():
        try:
            duration = probe_duration(path)
            if duration > 0:
                return TTSResult(path, duration)
        except (subprocess.CalledProcessError, ValueError, KeyError):
            pass  # Regenerate corrupt/incomplete cached speech.
    return tts.synthesize(text="슬라이드 전환", output_path=path)


def enrich_manifest(
    manifest: dict[str, Any],
    contexts: list[dict[str, Any]],
    *,
    vision: VisionProvider,
    tts: TTSProvider,
    audio_dir: Path,
) -> dict[str, Any]:
    """Fill deictic events with gate, description and TTS results without mutating inputs."""
    context_by_id = {ctx["id"]: ctx for ctx in contexts}
    output = {
        **manifest,
        "generation": {
            "vision_provider": vision.__class__.__name__,
            "vision_model": getattr(vision, "model", None),
            "tts_provider": tts.__class__.__name__,
            "tts_model": getattr(tts, "model", None),
            "tts_voice": getattr(tts, "voice", None),
        },
        "events": [],
    }

    slide_audio = None
    descriptions_by_slide: dict[object, list[str]] = {}
    for index, event in enumerate(manifest.get("events", []), 1):
        current = dict(event)
        if current.get("type") == "slide_change":
            if slide_audio is None:
                slide_audio = _slide_audio(tts, audio_dir)
            timestamp = float(current["timestamp_s"])
            current.update(
                id=current.get("id") or f"s_{index:04d}",
                reference_timestamp_s=timestamp, insertion_timestamp_s=timestamp,
                text="슬라이드 전환", description="슬라이드 전환", approved=True,
                audio=str(slide_audio.audio_path), audio_duration_s=float(slide_audio.duration_s),
            )
            output["events"].append(current)
            continue
        if current.get("type") != "deictic":
            output["events"].append(current)
            continue

        ctx = context_by_id.get(current.get("id"))
        if ctx is None:
            raise ValueError(f"missing context for event: {current.get('id')}")

        frame = current.get("frame") or ctx.get("frame")
        if not frame:
            raise ValueError(f"missing frame for event: {current.get('id')}")

        frame_path = Path(frame)
        context = ctx.get("context", {})
        insertion = current.get("insertion_timestamp_s", ctx.get("segment_end_s"))
        details = {"reference_timestamp_s": current.get("reference_timestamp_s", ctx.get("timestamp_s")),
                   "insertion_timestamp_s": insertion}
        if insertion is not None and "segments" in context:
            details.update(partition_transcript(context["segments"], float(insertion)))
        else:
            details["unpartitioned_text"] = context.get("text", "")
        slide_id = current.get("slide_id")
        if slide_id is not None:
            details["previous_descriptions"] = descriptions_by_slide.get(slide_id, [])[-3:]
        context_text = json.dumps(details, ensure_ascii=False)
        utterance = str(current.get("utterance", ""))

        gate = vision.gate(
            frame_path=frame_path,
            utterance=utterance,
            context_text=context_text,
        )
        current["gate"] = {
            "is_visual_reference": gate.is_visual_reference,
            "target": gate.target,
            "reason": gate.reason,
            "confidence": gate.confidence,
        }
        threshold = float(os.environ.get("LECAD_GATE_MIN_CONFIDENCE", "0.6"))
        confidence_ok = gate.confidence is None or gate.confidence >= threshold
        current["approved"] = bool(gate.is_visual_reference and confidence_ok)

        if not current["approved"]:
            output["events"].append(current)
            continue

        description = vision.describe(
            frame_path=frame_path,
            utterance=utterance,
            context_text=context_text,
            target=gate.target,
        )
        text = clean_script(description.text)
        current["description"] = text
        current["visual_facts"] = list(description.visual_facts)
        current["missing_information"] = list(description.missing_information)
        if not text:
            current.update(approved=False, skip_reason="no useful spoken description", audio=None, audio_duration_s=None)
            output["events"].append(current)
            continue

        extension = getattr(tts, "extension", ".mp3")
        audio_path = audio_dir / f"{current['id']}{extension}"
        tts_result = tts.synthesize(text=text, output_path=audio_path)
        current["audio"] = str(tts_result.audio_path)
        current["audio_duration_s"] = float(tts_result.duration_s)
        if slide_id is not None:
            descriptions_by_slide.setdefault(slide_id, []).append(text)
        output["events"].append(current)

    return output
