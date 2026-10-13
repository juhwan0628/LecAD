# Data contracts

## Transcript

Preferred input is transcript schema v2 with word timestamps.

```json
{
  "schema_version": 2,
  "source": "lecture.mp4",
  "segments": [
    {
      "start": 100.0,
      "end": 108.0,
      "text": "오른쪽 그래프를 보면 ...",
      "words": [
        {"start": 100.2, "end": 100.5, "text": "오른쪽", "probability": 0.98}
      ]
    }
  ]
}
```

Legacy segment-only transcripts still work via approximate timestamp fallback, but v2 is preferred for rendering.

## Trigger candidate

```json
{
  "id": "d_0005",
  "type": "deictic",
  "timestamp_s": 1036.69,
  "segment_start_s": 1036.69,
  "segment_end_s": 1045.21,
  "utterance": "이 그림은 우리가 GPU와 성능 발전을 놓고 보는 겁니다",
  "score": 4,
  "confidence": "high",
  "matched_patterns": ["explicit_visual_noun"]
}
```

## Render manifest event

Before AI enrichment:

```json
{
  "id": "d_0005",
  "type": "deictic",
  "reference_timestamp_s": 1036.69,
  "insertion_timestamp_s": 1045.21,
  "frame": "frames/d_0005.jpg",
  "description": null,
  "audio": null,
  "audio_duration_s": null,
  "approved": null
}
```

After gate + description + TTS:

```json
{
  "id": "d_0005",
  "type": "deictic",
  "reference_timestamp_s": 1036.69,
  "insertion_timestamp_s": 1045.21,
  "frame": "frames/d_0005.jpg",
  "gate": {
    "is_visual_reference": true,
    "target": "GPU/CPU performance graphs",
    "confidence": 0.96
  },
  "visual_facts": ["GPU 선이 CPU 선보다 가파르게 상승합니다."],
  "missing_information": ["두 선의 기울기 차이"],
  "description": "두 그래프에서 GPU 성능 증가 폭이 CPU보다 훨씬 가파릅니다.",
  "audio": "audio/d_0005.mp3",
  "audio_duration_s": 4.2,
  "approved": true
}
```

Only `approved: true` events are rendered.

## Timestamped VLM context

New contexts include `before_text`, `after_text`, `overlapping_text`, and
`insertion_timestamp_s`. The context spans from 15 seconds before the reference
to 15 seconds after insertion. The VLM receives these fields as JSON along with
the reference/insertion timestamps and up to three previous descriptions on the
same slide. Legacy contexts with timestamped `segments` are partitioned during
enrichment; text-only legacy context is labeled `unpartitioned_text`.

`visual_facts` records image-grounded observations; `missing_information` records
the useful facts not already conveyed by speech. Only the cleaned `description`
is sent to TTS. Narration labels such as `[음성해설]` and `음성 해설.` are removed,
and empty scripts are skipped. `LECAD_TTS_PREFIX` is no longer used.

## Slide transition cue

```json
{
  "id": "s_0001",
  "type": "slide_change",
  "timestamp_s": 10.0,
  "reference_timestamp_s": 10.0,
  "insertion_timestamp_s": 10.0,
  "text": "슬라이드 전환",
  "description": "슬라이드 전환",
  "audio": "audio/slide_change-<settings-hash>.mp3",
  "audio_duration_s": 1.2,
  "approved": true
}
```

The cue requires no VLM call. All transitions share one synthesized audio file.
Subsequent runs with the same audio directory reuse it after checking its
duration; provider/model/voice/rate changes create a different file. A transition
without `frame` uses a frame extracted from the source at its reference timestamp.
Rendering freezes the frame during the cue, then resumes the lecture unchanged.
`--from` / `--to` filters both deictic and slide-change events before enrichment.
