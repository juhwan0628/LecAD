from __future__ import annotations
from typing import Any


def build_manifest(slides_doc: dict[str, Any], contexts: list[dict[str, Any]]) -> dict[str, Any]:
    events: list[dict[str, Any]] = []
    for index, event in enumerate(slides_doc.get("events", []), 1):
        if event.get("type") == "slide_change":
            events.append({
                "id": f"s_{index:04d}",
                "type": "slide_change",
                "timestamp_s": float(event["timestamp_s"]),
                "reference_timestamp_s": float(event["timestamp_s"]),
                "insertion_timestamp_s": float(event["timestamp_s"]),
                "text": "슬라이드 전환",
            })
    for ctx in contexts:
        events.append({
            "id": ctx["id"],
            "type": "deictic",
            "timestamp_s": float(ctx["timestamp_s"]),
            "reference_timestamp_s": float(ctx["timestamp_s"]),
            "insertion_timestamp_s": float(ctx["segment_end_s"]),
            "utterance": ctx["utterance"],
            "confidence": ctx["confidence"],
            "slide_id": None if ctx.get("slide") is None else ctx["slide"]["slide_id"],
            "frame": ctx.get("frame"),
            "description": None,
            "audio": None,
            "audio_duration_s": None,
            "approved": None,
        })
    events.sort(key=lambda x: (x["timestamp_s"], 0 if x["type"] == "slide_change" else 1))
    return {
        "schema_version": 1,
        "source": slides_doc.get("source"),
        "events": events,
    }
