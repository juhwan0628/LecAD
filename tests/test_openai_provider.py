import json
from pathlib import Path

from lecad.providers.openai_provider import (
    OpenAIVisionProvider,
    _extract_output_text,
    _parse_json_text,
)


class FakeClient:
    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.requests = []

    def responses(self, body):
        self.requests.append(body)
        return {"output": [{"content": [{"type": "output_text", "text": self.outputs.pop(0)}]}]}


def test_extract_output_text_from_response_items():
    payload = {"output": [{"content": [{"type": "output_text", "text": "hello"}]}]}
    assert _extract_output_text(payload) == "hello"


def test_parse_json_text_accepts_fenced_json():
    assert _parse_json_text('''```json
{"is_visual_reference": true}
```''')["is_visual_reference"] is True


def test_openai_vision_gate_and_description(tmp_path: Path):
    frame = tmp_path / "frame.jpg"
    frame.write_bytes(b"jpeg-ish")
    provider = OpenAIVisionProvider(api_key="test", model="test-model")
    provider.client = FakeClient([
        json.dumps({
            "is_visual_reference": True,
            "target": "오른쪽 그래프",
            "reason": "교수가 위치를 지칭함",
            "confidence": 0.95,
        }, ensure_ascii=False),
        json.dumps({"text": "오른쪽 그래프가 왼쪽보다 더 가파르게 상승합니다."}, ensure_ascii=False),
    ])

    gate = provider.gate(frame_path=frame, utterance="오른쪽 그래프를 보면", context_text="문맥")
    assert gate.is_visual_reference is True
    assert gate.target == "오른쪽 그래프"

    desc = provider.describe(
        frame_path=frame,
        utterance="오른쪽 그래프를 보면",
        context_text="문맥",
        target=gate.target,
    )
    assert desc.text == "오른쪽 그래프가 왼쪽보다 더 가파르게 상승합니다."
    assert provider.client.requests[0]["model"] == "test-model"
