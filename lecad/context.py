from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any


def find_slide(slides_doc: dict[str, Any], timestamp_s: float) -> dict[str, Any] | None:
    for slide in slides_doc.get("slides", []):
        if float(slide["start_s"]) <= timestamp_s < float(slide["end_s"]):
            return slide
    return None


def transcript_window(transcript: dict[str, Any], timestamp_s: float, radius_s: float = 15.0) -> list[dict[str, Any]]:
    lo, hi = timestamp_s - radius_s, timestamp_s + radius_s
    return [
        s for s in transcript.get("segments", [])
        if float(s["end"]) >= lo and float(s["start"]) <= hi
    ]


def partition_transcript(segments: list[dict], insertion_s: float) -> dict[str, str]:
    before, after, overlapping = [], [], []
    for segment in segments:
        text = str(segment.get("text", "")).strip()
        if float(segment["end"]) <= insertion_s:
            before.append(text)
        elif float(segment["start"]) >= insertion_s:
            after.append(text)
        elif segment.get("words"):
            for word in segment["words"]:
                token = str(word.get("text", word.get("word", ""))).strip()
                target = before if float(word["end"]) <= insertion_s else after if float(word["start"]) >= insertion_s else overlapping
                target.append(token)
        else:
            overlapping.append(text)
    return {"before_text": " ".join(before), "after_text": " ".join(after), "overlapping_text": " ".join(overlapping)}


def extract_frame(video: Path, timestamp_s: float, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-loglevel", "error", "-y",
        "-ss", f"{timestamp_s:.3f}", "-i", str(video),
        "-frames:v", "1", "-q:v", "2", str(output_path),
    ]
    subprocess.run(cmd, check=True)
    if not output_path.exists():
        raise RuntimeError(f"frame extraction failed at {timestamp_s:.3f}s")
    return output_path


def build_context(
    candidate: dict[str, Any],
    transcript: dict[str, Any],
    slides_doc: dict[str, Any],
    *,
    video: Path | None = None,
    frame_dir: Path | None = None,
    radius_s: float = 15.0,
) -> dict[str, Any]:
    timestamp = float(candidate["timestamp_s"])
    slide = find_slide(slides_doc, timestamp)
    insertion = float(candidate["segment_end_s"])
    window = [s for s in transcript.get("segments", [])
              if float(s["end"]) >= timestamp - radius_s and float(s["start"]) <= insertion + radius_s]
    payload: dict[str, Any] = {
        **candidate,
        "slide": slide,
        "context": {
            "radius_s": radius_s,
            "segments": window,
            "text": " ".join(str(s.get("text", "")).strip() for s in window).strip(),
            "insertion_timestamp_s": insertion,
            **partition_transcript(window, insertion),
        },
    }
    if video is not None and frame_dir is not None:
        frame_path = frame_dir / f"{candidate['id']}.jpg"
        extract_frame(video, timestamp, frame_path)
        payload["frame"] = str(frame_path)
    return payload
