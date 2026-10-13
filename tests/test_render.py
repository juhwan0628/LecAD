
from pathlib import Path
import pytest

from lecad.render.timeline import build_render_events


def test_build_render_events_filters_unapproved_and_sorts():
    events = [
        {
            "id": "b", "approved": True, "reference_timestamp_s": 20,
            "insertion_timestamp_s": 25, "audio": "b.mp3", "audio_duration_s": 3,
            "frame": "b.jpg", "description": "b",
        },
        {
            "id": "skip", "approved": False,
        },
        {
            "id": "a", "approved": True, "reference_timestamp_s": 10,
            "insertion_timestamp_s": 15, "audio": "a.mp3", "audio_duration_s": 2,
            "frame": "a.jpg", "description": "a",
        },
    ]
    out = build_render_events(events)
    assert [e.id for e in out] == ["a", "b"]


def test_incomplete_approved_event_fails():
    with pytest.raises(ValueError):
        build_render_events([{"id": "x", "approved": True}])


@pytest.mark.parametrize("field,value", [("audio_duration_s", -1), ("audio_duration_s", 0),
                                        ("audio_duration_s", float("nan")), ("insertion_timestamp_s", -1)])
def test_invalid_render_timing_fails(field, value):
    event = {"id": "x", "approved": True, "reference_timestamp_s": 1,
             "insertion_timestamp_s": 2, "audio": "a.mp3", "audio_duration_s": 1,
             "frame": "a.jpg", "description": "설명"}
    event[field] = value
    with pytest.raises(ValueError):
        build_render_events([event])


def test_full_pipeline_renders_ad_and_reuses_slide_cues(tmp_path):
    import json
    import subprocess
    from lecad.cli import main
    source = tmp_path / "source.mp4"
    subprocess.run([
        "ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=blue:s=320x180:r=15:d=4",
        "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=44100:duration=4",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-ac", "2", str(source),
    ], check=True)
    transcript = tmp_path / "transcript.json"
    slides = tmp_path / "slides.json"
    transcript.write_text(json.dumps({"source": "source.mp4", "segments": [
        {"start": 1, "end": 2, "text": "이 그림을 보면"},
    ]}))
    slides.write_text(json.dumps({"source": "source.mp4", "slides": [
        {"slide_id": 1, "start_s": 0, "end_s": 3},
        {"slide_id": 2, "start_s": 3, "end_s": 4},
    ], "events": [{"type": "slide_change", "timestamp_s": t} for t in (0.5, 3)]}))
    outdir = tmp_path / "output"
    output = tmp_path / "result.mp4"
    assert main(["--full", "--provider", "mock", "--env-file", str(tmp_path / "missing.env"),
                 "--video", str(source), "--transcript", str(transcript), "--slides", str(slides),
                 "--output-dir", str(outdir), "--output-video", str(output)]) == 0
    events = json.loads((outdir / "manifest.approved.json").read_text())["events"]
    cues = [e for e in events if e["type"] == "slide_change"]
    assert len(cues) == 2 and cues[0]["audio"] == cues[1]["audio"]
    assert all(e["approved"] for e in events)
    probe = json.loads(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(output),
    ]))
    video = next(s for s in probe["streams"] if s["codec_type"] == "video")
    audio = next(s for s in probe["streams"] if s["codec_type"] == "audio")
    assert video["r_frame_rate"] == "30/1"
    assert audio["sample_rate"] == "48000" and audio["channels"] == 2
    assert abs(float(probe["format"]["duration"]) - 8.5) < 0.25
    decoded = subprocess.run(["ffmpeg", "-v", "error", "-i", str(output), "-f", "null", "-"], capture_output=True)
    assert decoded.returncode == 0 and not decoded.stderr
