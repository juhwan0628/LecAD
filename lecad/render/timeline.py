
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import math


@dataclass(frozen=True)
class RenderEvent:
    id: str
    reference_timestamp_s: float
    insertion_timestamp_s: float
    audio_path: str
    audio_duration_s: float
    frame_path: str
    description: str


def build_render_events(events: list[dict[str, Any]]) -> list[RenderEvent]:
    out: list[RenderEvent] = []
    for event in events:
        if not event.get("approved"):
            continue
        audio_path = event.get("audio")
        frame_path = event.get("frame") or ""
        duration = event.get("audio_duration_s")
        insertion = event.get("insertion_timestamp_s")
        reference = event.get("reference_timestamp_s", event.get("timestamp_s"))
        description = event.get("description")
        if not all([audio_path, frame_path or event.get("type") == "slide_change", duration is not None, insertion is not None, reference is not None, description]):
            raise ValueError(f"incomplete approved render event: {event.get('id')}")
        reference, insertion, duration = float(reference), float(insertion), float(duration)
        if not all(math.isfinite(t) for t in (reference, insertion, duration)) or min(reference, insertion) < 0 or duration <= 0:
            raise ValueError(f"invalid render timing: {event.get('id')}")
        out.append(RenderEvent(
            id=str(event["id"]),
            reference_timestamp_s=reference,
            insertion_timestamp_s=insertion,
            audio_path=str(audio_path),
            audio_duration_s=duration,
            frame_path=str(frame_path),
            description=str(description),
        ))
    out.sort(key=lambda e: e.insertion_timestamp_s)
    return out
