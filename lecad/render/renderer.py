
from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from .media import concat_mp4, probe_duration, render_ad_clip, render_source_segment
from .timeline import RenderEvent
from ..context import extract_frame


def render_video(
    source: Path,
    events: list[RenderEvent],
    output: Path,
    *,
    clip_start_s: float = 0.0,
    clip_end_s: float | None = None,
    keep_workdir: bool = False,
) -> Path:
    source_duration = probe_duration(source)
    end_limit = source_duration if clip_end_s is None else min(float(clip_end_s), source_duration)
    start_limit = max(0.0, float(clip_start_s))
    if end_limit <= start_limit:
        raise ValueError("clip end must be after clip start")

    selected = [
        e for e in events
        if start_limit <= e.insertion_timestamp_s < end_limit
    ]

    workdir = Path(tempfile.mkdtemp(prefix="lecad-render-"))
    success = False
    try:
        parts: list[Path] = []
        cursor = start_limit
        serial = 0

        for event in selected:
            if event.insertion_timestamp_s > cursor:
                seg = workdir / f"{serial:04d}_source.mp4"
                render_source_segment(source, cursor, event.insertion_timestamp_s, seg)
                parts.append(seg)
                serial += 1

            ad = workdir / f"{serial:04d}_{event.id}_ad.mp4"
            frame = Path(event.frame_path) if event.frame_path else extract_frame(
                source, event.reference_timestamp_s, workdir / f"{serial:04d}_slide.jpg"
            )
            render_ad_clip(frame, Path(event.audio_path), event.audio_duration_s, ad)
            parts.append(ad)
            serial += 1
            cursor = event.insertion_timestamp_s

        if cursor < end_limit:
            seg = workdir / f"{serial:04d}_source.mp4"
            render_source_segment(source, cursor, end_limit, seg)
            parts.append(seg)

        if not parts:
            raise RuntimeError("no render parts produced")

        concat_mp4(parts, output)
        success = True
        return output
    finally:
        if success and not keep_workdir:
            shutil.rmtree(workdir, ignore_errors=True)
