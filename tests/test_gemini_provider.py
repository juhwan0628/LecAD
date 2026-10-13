import json
from pathlib import Path

from lecad.providers.gemini_provider import GeminiVisionProvider, _extract_text


class FakeGeminiClient:
    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.requests = []

    def generate_content(self, model, body):
        self.requests.append((model, body))
        return {"candidates": [{"content": {"parts": [{"text": self.outputs.pop(0)}]}}]}


def test_extract_text_from_gemini_candidate():
    payload = {"candidates": [{"content": {"parts": [{"text": "hello"}]}}]}
    assert _extract_text(payload) == "hello"


def test_gemini_vision_gate_and_description(tmp_path: Path):
    frame = tmp_path / "frame.jpg"
    frame.write_bytes(b"jpeg-ish")
    provider = GeminiVisionProvider(api_key="test", model="gemini-test")
    provider.client = FakeGeminiClient([
        json.dumps({
            "is_visual_reference": True,
            "target": "GPU 그래프",
            "reason": "그래프를 지칭함",
            "confidence": 0.9,
        }, ensure_ascii=False),
        json.dumps({"text": "초록색 GPU 선이 파란색 CPU 선보다 가파르게 올라갑니다."}, ensure_ascii=False),
    ])

    gate = provider.gate(frame_path=frame, utterance="이 그림은", context_text="문맥")
    assert gate.is_visual_reference is True
    assert gate.target == "GPU 그래프"

    desc = provider.describe(frame_path=frame, utterance="이 그림은", context_text="문맥", target=gate.target)
    assert "GPU" in desc.text
    assert provider.client.requests[0][0] == "gemini-test"
