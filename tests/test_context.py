from lecad.context import build_context, find_slide, transcript_window, partition_transcript


def test_find_slide():
    slides = {"slides": [{"slide_id": 1, "start_s": 0, "end_s": 10}, {"slide_id": 2, "start_s": 10, "end_s": 20}]}
    assert find_slide(slides, 12)["slide_id"] == 2


def test_transcript_window_overlap():
    transcript = {"segments": [
        {"start": 0, "end": 5, "text": "a"},
        {"start": 9, "end": 12, "text": "b"},
        {"start": 30, "end": 35, "text": "c"},
    ]}
    assert [s["text"] for s in transcript_window(transcript, 10, 5)] == ["a", "b"]


def test_context_separates_speech_at_insertion_time():
    transcript = {"segments": [
        {"start": 0, "end": 5, "text": "축 설명"},
        {"start": 9, "end": 30, "text": "이 그림을 보면"},
        {"start": 30, "end": 35, "text": "결론 설명"},
    ]}
    ctx = build_context({"id": "d_1", "timestamp_s": 10, "segment_end_s": 30}, transcript, {})
    assert ctx["context"]["before_text"] == "축 설명 이 그림을 보면"
    assert ctx["context"]["after_text"] == "결론 설명"
    assert ctx["context"]["insertion_timestamp_s"] == 30


def test_overlap_does_not_treat_future_speech_as_already_heard():
    segments = [{"start": 0, "end": 10, "text": "앞 경계 뒤", "words": [
        {"text": "앞", "start": 0, "end": 4},
        {"text": "경계", "start": 4, "end": 6},
        {"text": "뒤", "start": 6, "end": 10},
    ]}]
    assert partition_transcript(segments, 5) == {
        "before_text": "앞", "after_text": "뒤", "overlapping_text": "경계",
    }
    segments[0].pop("words")
    assert partition_transcript(segments, 5) == {
        "before_text": "", "after_text": "", "overlapping_text": "앞 경계 뒤",
    }
