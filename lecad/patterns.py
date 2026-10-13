from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class PatternRule:
    name: str
    regex: re.Pattern[str]
    score: int


def _rx(pattern: str) -> re.Pattern[str]:
    return re.compile(pattern, re.IGNORECASE)


# These rules intentionally prefer precision over recall. Generic discourse uses
# such as "장기적으로 보면" and "여기까지" are not candidates on their own.
RULES: tuple[PatternRule, ...] = (
    PatternRule("explicit_visual_noun", _rx(r"(?<![가-힣A-Za-z0-9])이\s*(?:그림|그래프|표|도표|수식|사진|이미지|지도|화면|슬라이드)"), 4),
    PatternRule("spatial_reference", _rx(r"(?:왼쪽|오른쪽|위쪽|아래쪽|상단|하단)(?:에|의|에서|을|를)?(?:\s+[^.!?]{0,18})?(?:그림|그래프|표|도표|사진|이미지|보면|보시면)"), 4),
    PatternRule("displayed_reference", _rx(r"(?:여기|저기)(?:에|에서|서|의)?\s*(?:나와\s*있는|보이는|있는)\s*[^.!?]{0,22}"), 3),
    PatternRule("named_visual_here", _rx(r"(?:여기|저기)(?:에|에서|서|의)?\s*(?:그림|그래프|표|도표|수식|사진|이미지|지도|화면)"), 4),
    PatternRule("viewing_now", _rx(r"지금\s*(?:보고\s*있는|보는)\s*(?:이\s*)?(?:그림|그래프|표|도표|사진|이미지|지도|화면)"), 5),
    PatternRule("look_here", _rx(r"(?:여기|저기)(?:에|에서|서)?\s*(?:보면|보시면|보시다시피|살펴보면)"), 2),
)

NEGATIVE_RULES: tuple[re.Pattern[str], ...] = (
    _rx(r"여기까지"),
    _rx(r"(?:장기적|전체적|일반적|윤리적|측면|관점|기준).*보면"),
)
