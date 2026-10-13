from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any
import re

from .patterns import RULES, NEGATIVE_RULES


@dataclass(frozen=True)
class TriggerCandidate:
    id: str
    type: str
    timestamp_s: float
    segment_start_s: float
    segment_end_s: float
    utterance: str
    score: int
    confidence: str
    matched_patterns: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _word_timestamp(segment: dict[str, Any], match_start: int, match_end: int) -> float:
    """Best-effort mapping from a text regex span to a word-level timestamp."""
    text = str(segment.get("text", "")).strip()
    compact = re.sub(r"\s+", "", text)
    span_start = len(re.sub(r"\s+", "", text[:match_start]))
    span_end = len(re.sub(r"\s+", "", text[:match_end]))
    cursor = 0
    for word in segment.get("words") or []:
        token = re.sub(r"\s+", "", str(word.get("text", word.get("word", ""))))
        if not token:
            continue
        start = compact.find(token, cursor)
        if start < 0:
            continue
        cursor = start + len(token)
        if start < span_end and cursor > span_start:
            return float(word["start"])

    # Fall back to proportional position inside the segment rather than the
    # segment start. This is still better aligned for legacy schema-v1 JSON.
    duration = max(0.0, float(segment["end"]) - float(segment["start"]))
    ratio = match_start / max(1, len(text))
    return float(segment["start"]) + duration * ratio


def detect_deictic_candidates(transcript: dict[str, Any], min_score: int = 3) -> list[TriggerCandidate]:
    candidates: list[TriggerCandidate] = []
    serial = 1
    for segment in transcript.get("segments", []):
        text = str(segment.get("text", "")).strip()
        if not text or any(rule.search(text) for rule in NEGATIVE_RULES):
            continue

        matches: list[tuple[str, int, re.Match[str]]] = []
        for rule in RULES:
            m = rule.regex.search(text)
            if m:
                matches.append((rule.name, rule.score, m))
        if not matches:
            continue

        score = sum(item[1] for item in matches)
        if score < min_score:
            continue
        first_match = min((m for _, _, m in matches), key=lambda m: m.start())
        timestamp = _word_timestamp(segment, first_match.start(), first_match.end())
        confidence = "high" if score >= 4 else "medium"
        candidates.append(
            TriggerCandidate(
                id=f"d_{serial:04d}",
                type="deictic",
                timestamp_s=round(timestamp, 3),
                segment_start_s=float(segment["start"]),
                segment_end_s=float(segment["end"]),
                utterance=text,
                score=score,
                confidence=confidence,
                matched_patterns=[name for name, _, _ in matches],
            )
        )
        serial += 1
    return candidates
