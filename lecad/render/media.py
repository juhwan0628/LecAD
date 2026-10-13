
from __future__ import annotations

import json
import subprocess
from pathlib import Path


def probe_duration(path: Path) -> float:
    proc = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)],
        check=True, capture_output=True, text=True,
    )
    return float(json.loads(proc.stdout)["format"]["duration"])


def render_source_segment(source: Path, start_s: float, end_s: float, output: Path) -> Path:
    if end_s <= start_s:
        raise ValueError("source segment end must be after start")
    output.parent.mkdir(parents=True, exist_ok=True)
    duration = end_s - start_s
    cmd = [
        "ffmpeg", "-loglevel", "error", "-y",
        "-ss", f"{start_s:.3f}", "-i", str(source),
        "-t", f"{duration:.3f}",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-r", "30", "-pix_fmt", "yuv420p", "-video_track_timescale", "90000",
        "-c:a", "aac", "-b:a", "160k",
        "-ar", "48000", "-ac", "2",
        "-movflags", "+faststart",
        str(output),
    ]
    subprocess.run(cmd, check=True)
    return output


def render_ad_clip(frame: Path, audio: Path, duration_s: float, output: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-loglevel", "error", "-y",
        "-loop", "1", "-framerate", "30", "-i", str(frame),
        "-i", str(audio),
        "-t", f"{duration_s:.3f}",
        "-vf", "format=yuv420p",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-video_track_timescale", "90000",
        "-c:a", "aac", "-b:a", "160k",
        "-ar", "48000", "-ac", "2",
        "-shortest", "-movflags", "+faststart",
        str(output),
    ]
    subprocess.run(cmd, check=True)
    return output


def concat_mp4(parts: list[Path], output: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    list_file = output.with_suffix(".concat.txt")
    list_file.write_text(
        "".join(f"file '{p.resolve().as_posix()}'\n" for p in parts),
        encoding="utf-8",
    )
    try:
        subprocess.run([
            "ffmpeg", "-loglevel", "error", "-y",
            "-f", "concat", "-safe", "0", "-i", str(list_file),
            "-c", "copy", str(output)
        ], check=True)
    finally:
        list_file.unlink(missing_ok=True)
    return output
