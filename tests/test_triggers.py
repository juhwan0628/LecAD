from lecad.triggers import detect_deictic_candidates


def doc(text, words=None):
    return {"segments": [{"start": 10.0, "end": 20.0, "text": text, "words": words or []}]}


def test_explicit_visual_reference_is_detected():
    out = detect_deictic_candidates(doc("이 그림은 GPU 성능 발전을 보여줍니다"))
    assert len(out) == 1
    assert out[0].confidence == "high"


def test_suffix_false_positive_is_rejected():
    assert detect_deictic_candidates(doc("인공지능이 이미지를 생성한 겁니다")) == []
    assert detect_deictic_candidates(doc("인공지능이 그림을 생성했습니다")) == []


def test_generic_discourse_is_rejected():
    assert detect_deictic_candidates(doc("장기적으로 보면 협력은 협력을 낳습니다")) == []
    assert detect_deictic_candidates(doc("오늘은 여기까지 강의를 마치겠습니다")) == []


def test_word_timestamp_is_used():
    words = [
        {"start": 12.0, "end": 12.2, "text": "이"},
        {"start": 12.2, "end": 12.7, "text": "그림은"},
    ]
    out = detect_deictic_candidates(doc("이 그림은 GPU 그래프입니다", words))
    assert out[0].timestamp_s == 12.0


def test_repeated_word_maps_to_matched_occurrence():
    words = [
        {"text": "이", "start": 10, "end": 11},
        {"text": "결과와", "start": 11, "end": 12},
        {"text": "이", "start": 16, "end": 17},
        {"text": "그림을", "start": 17, "end": 18},
        {"text": "비교합니다", "start": 18, "end": 20},
    ]
    assert detect_deictic_candidates(doc("이 결과와 이 그림을 비교합니다", words))[0].timestamp_s == 16
