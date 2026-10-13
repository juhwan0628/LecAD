import json
import subprocess
from pathlib import Path

import pytest

from lecad.providers.codex_provider import CodexVisionProvider
from lecad.providers.base import GateResult, DescriptionResult


def test_codex_returns_grounding_without_second_call(tmp_path, monkeypatch):
    calls = []
    def run(cmd, **kwargs):
        calls.append(cmd)
        Path(cmd[cmd.index("-o") + 1]).write_text(json.dumps({
            "is_visual_reference": True, "target": "GPU 그래프", "confidence": 0.9,
            "visual_facts": ["초록색은 GPU"], "missing_information": ["색과 대상의 대응"],
            "ad_text": "초록색은 GPU를 나타냅니다.",
        }, ensure_ascii=False))
        return subprocess.CompletedProcess(cmd, 0, "", "")
    monkeypatch.setattr(subprocess, "run", run)
    provider = CodexVisionProvider()
    args = dict(frame_path=tmp_path / "frame.jpg", utterance="이 그래프", context_text="문맥")
    gate = provider.gate(**args)
    desc = provider.describe(**args, target=gate.target)
    assert desc.text == "초록색은 GPU를 나타냅니다."
    assert desc.visual_facts == ("초록색은 GPU",)
    assert desc.missing_information == ("색과 대상의 대응",)
    assert len(calls) == 1


def test_gate_rejects_string_booleans_and_invalid_confidence():
    with pytest.raises(ValueError):
        GateResult("false", confidence=0.9)
    for confidence in (float("nan"), -1, 2):
        with pytest.raises(ValueError):
            GateResult(True, confidence=confidence)


def test_description_rejects_non_script_payload():
    with pytest.raises(ValueError):
        DescriptionResult.from_dict({"text": {"script": "설명"}})
    with pytest.raises(ValueError):
        DescriptionResult.from_dict({"text": "설명", "visual_facts": "추측"})
