from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

from .base import DescriptionResult, GateResult
from .prompts import SCRIPT_RULES


def _parse_json_text(text: str) -> dict:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        if stripped.startswith("json"):
            stripped = stripped[4:].lstrip()
    try:
        data = json.loads(stripped)
    except json.JSONDecodeError as exc:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start < 0 or end <= start:
            raise RuntimeError(f"Codex did not return valid JSON: {text[:500]}") from exc
        data = json.loads(stripped[start:end + 1])
    if not isinstance(data, dict):
        raise RuntimeError("Codex result must be a JSON object")
    return data


class CodexVisionProvider:
    """Use the authenticated Codex CLI as LecAD's multimodal reasoning backend.

    This consumes the user's ChatGPT/Codex quota rather than making a metered
    vision API call. The provider deliberately performs gate + AD generation in
    one Codex invocation and caches the result for describe().
    """

    def __init__(
        self,
        *,
        model: str | None = None,
        reasoning_effort: str | None = None,
        executable: str = "codex",
    ):
        self.model = model or os.environ.get("LECAD_CODEX_MODEL") or "gpt-5.6-terra"
        self.reasoning_effort = (
            reasoning_effort
            or os.environ.get("LECAD_CODEX_REASONING_EFFORT")
            or "low"
        )
        self.executable = executable
        self._last_key: tuple[str, str, str] | None = None
        self._last_result: dict | None = None

    @staticmethod
    def _prompt(utterance: str, context_text: str) -> str:
        return f"""You generate Korean audio description for a blind university student from one lecture frame and transcript context.

Instructor utterance:
{utterance}

Timestamped transcript context (JSON):
{context_text}

{SCRIPT_RULES}
If no useful visual-only information remains or the target is uncertain, set is_visual_reference=false and ad_text="".

Return only JSON with exactly these keys:
{{"is_visual_reference":true,"target":"...","visual_facts":["directly visible fact"],"missing_information":["useful fact missing from speech"],"ad_text":"spoken Korean only","confidence":0.0,"rationale":"..."}}"""

    def _run(self, *, frame_path: Path, utterance: str, context_text: str) -> dict:
        key = (str(frame_path.resolve()), utterance, context_text)
        if key == self._last_key and self._last_result is not None:
            return self._last_result

        with tempfile.TemporaryDirectory(prefix="lecad-codex-") as tmp:
            output_path = Path(tmp) / "result.json"
            cmd = [
                self.executable,
                "exec",
                "--ephemeral",
                "--skip-git-repo-check",
                "-m",
                self.model,
                "-c",
                f'model_reasoning_effort="{self.reasoning_effort}"',
                "-i",
                str(frame_path.resolve()),
                "-o",
                str(output_path),
                self._prompt(utterance, context_text),
            ]
            proc = subprocess.run(
                cmd,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=float(os.environ.get("LECAD_CODEX_TIMEOUT_S", "120")),
            )
            if proc.returncode != 0:
                raise RuntimeError(
                    "Codex VLM failed: "
                    + (proc.stderr[-2000:] or proc.stdout[-2000:] or f"exit {proc.returncode}")
                )
            if not output_path.exists():
                raise RuntimeError("Codex VLM produced no output file")
            result = _parse_json_text(output_path.read_text(encoding="utf-8"))

        self._last_key = key
        self._last_result = result
        return result

    def gate(self, *, frame_path: Path, utterance: str, context_text: str) -> GateResult:
        data = self._run(
            frame_path=frame_path,
            utterance=utterance,
            context_text=context_text,
        )
        return GateResult(
            is_visual_reference=data.get("is_visual_reference"),
            target=None if data.get("target") is None else str(data.get("target")),
            reason=None if data.get("rationale") is None else str(data.get("rationale")),
            confidence=data.get("confidence"),
        )

    def describe(
        self,
        *,
        frame_path: Path,
        utterance: str,
        context_text: str,
        target: str | None,
    ) -> DescriptionResult:
        data = self._run(
            frame_path=frame_path,
            utterance=utterance,
            context_text=context_text,
        )
        return DescriptionResult.from_dict(data, "ad_text")
