from pathlib import Path
import json
import wave

import pytest

from lecad.enrich import enrich_manifest
from lecad.providers.base import DescriptionResult, GateResult, TTSResult


class Vision:
    def gate(self, *, frame_path: Path, utterance: str, context_text: str):
        return GateResult(True, target="graph", confidence=0.9)

    def describe(self, *, frame_path: Path, utterance: str, context_text: str, target: str | None):
        return DescriptionResult("음성 해설. 그래프 설명")


class TTS:
    def synthesize(self, *, text: str, output_path: Path):
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text, encoding="utf-8")
        return TTSResult(output_path, 2.5)


def test_enrich_manifest_populates_approved_event(tmp_path: Path):
    manifest = {
        "events": [
            {
                "id": "d_0001",
                "type": "deictic",
                "utterance": "이 그래프를 보면",
                "frame": str(tmp_path / "frame.jpg"),
                "approved": None,
            }
        ]
    }
    contexts = [
        {
            "id": "d_0001",
            "context": {"text": "앞뒤 문맥"},
            "frame": str(tmp_path / "frame.jpg"),
        }
    ]

    out = enrich_manifest(
        manifest,
        contexts,
        vision=Vision(),
        tts=TTS(),
        audio_dir=tmp_path / "audio",
    )

    event = out["events"][0]
    assert event["approved"] is True
    assert event["description"] == "그래프 설명"
    assert Path(event["audio"]).read_text() == "그래프 설명"
    assert event["audio_duration_s"] == 2.5
    assert event["gate"]["target"] == "graph"


@pytest.mark.parametrize("text", [
    "[음성해설] 그래프 설명", "음성 해설. 음성 해설: 그래프 설명",
    "**음성 해설:** 그래프 설명", "대본: 그래프 설명", "(음성 해설) 그래프 설명",
])
def test_tts_receives_dialogue_only(tmp_path, monkeypatch, text):
    monkeypatch.setenv("LECAD_TTS_PREFIX", "음성 해설.")
    class LabelledVision(Vision):
        def describe(self, **kwargs):
            return DescriptionResult(text)
    out = enrich_manifest(
        {"events": [{"id": "d_1", "type": "deictic", "frame": "frame.jpg"}]},
        [{"id": "d_1"}], vision=LabelledVision(), tts=TTS(), audio_dir=tmp_path,
    )
    assert out["events"][0]["description"] == "그래프 설명"
    assert Path(out["events"][0]["audio"]).read_text() == "그래프 설명"


def test_empty_script_is_skipped_without_tts(tmp_path):
    class EmptyVision(Vision):
        def describe(self, **kwargs):
            return DescriptionResult("[음성해설]")
    out = enrich_manifest(
        {"events": [{"id": "d_1", "type": "deictic", "frame": "frame.jpg"}]},
        [{"id": "d_1"}], vision=EmptyVision(), tts=TTS(), audio_dir=tmp_path,
    )
    assert out["events"][0]["approved"] is False
    assert not list(tmp_path.iterdir())


def test_old_context_is_partitioned_for_vision(tmp_path):
    class ContextVision(Vision):
        def gate(self, **kwargs):
            data = json.loads(kwargs["context_text"])
            assert data["before_text"] == "이 그래프를 보면"
            assert data["after_text"] == "GPU가 빠릅니다"
            assert data["insertion_timestamp_s"] == 20
            return super().gate(**kwargs)
    enrich_manifest(
        {"events": [{"id": "d_1", "type": "deictic", "frame": "frame.jpg", "insertion_timestamp_s": 20}]},
        [{"id": "d_1", "context": {"segments": [
            {"start": 10, "end": 20, "text": "이 그래프를 보면"},
            {"start": 20, "end": 25, "text": "GPU가 빠릅니다"},
        ]}}], vision=ContextVision(), tts=TTS(), audio_dir=tmp_path,
    )


def test_previous_descriptions_are_scoped_to_same_slide(tmp_path):
    class ContextVision(Vision):
        def gate(self, **kwargs):
            data = json.loads(kwargs["context_text"])
            expected = ["그래프 설명"] if kwargs["utterance"] == "second" else []
            assert data["previous_descriptions"] == expected
            return super().gate(**kwargs)
    events = [{"id": key, "type": "deictic", "frame": "frame.jpg", "utterance": key, "slide_id": slide}
              for key, slide in [("first", 1), ("second", 1), ("third", 2)]]
    enrich_manifest({"events": events}, [{"id": e["id"]} for e in events],
                    vision=ContextVision(), tts=TTS(), audio_dir=tmp_path)


def test_slide_change_audio_is_reused_across_events_and_runs(tmp_path):
    class Speech:
        extension = ".wav"
        voice = "first"
        calls = []
        def synthesize(self, *, text, output_path):
            self.calls.append(text)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with wave.open(str(output_path), "wb") as audio:
                audio.setparams((1, 2, 8000, 0, "NONE", "not compressed"))
                audio.writeframes(b"\0\0" * 8000)
            return TTSResult(output_path, 1)
    tts = Speech()
    manifest = {"events": [{"type": "slide_change", "timestamp_s": t} for t in (5, 10)]}
    first = enrich_manifest(manifest, [], vision=Vision(), tts=tts, audio_dir=tmp_path)
    second = enrich_manifest(manifest, [], vision=Vision(), tts=tts, audio_dir=tmp_path)
    assert tts.calls == ["슬라이드 전환"]
    assert first["events"][0]["audio"] == first["events"][1]["audio"] == second["events"][0]["audio"]
    from lecad.render.timeline import build_render_events
    events = build_render_events(first["events"])
    assert [e.insertion_timestamp_s for e in events] == [5, 10]
    tts.voice = "second"
    third = enrich_manifest(manifest, [], vision=Vision(), tts=tts, audio_dir=tmp_path)
    assert tts.calls == ["슬라이드 전환", "슬라이드 전환"]
    assert third["events"][0]["audio"] != first["events"][0]["audio"]
