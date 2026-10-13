# Architecture

## Product contract

LecAD takes a lecture recording plus preprocessing metadata and produces a new lecture MP4 with generated audio description (AD) inserted automatically.

```text
lecture.mp4
  + transcript.json
  + slides.json
        |
        v
deictic trigger detector
        |
        v
context builder
  - exact reference frame
  - +/- 15 s transcript context
  - current slide
        |
        v
Vision Provider
  1. relevance gate
  2. concise AD generation
        |
        v
TTS Provider
        |
        v
approved render manifest
        |
        v
FFmpeg renderer
  source -> freeze frame + AD -> source
        |
        v
lecture.lecad.mp4
```

## Two timestamps

Each deictic event deliberately has two timestamps:

- `reference_timestamp_s`: the moment/frame the VLM should inspect.
- `insertion_timestamp_s`: the end of the instructor utterance, where AD is inserted so the lecturer is not interrupted mid-sentence.

## Package boundaries

`lecture-transcriber` and `slide-extractor` remain independent projects. LecAD integrates through MP4/JSON contracts rather than Python imports.

External AI services are isolated behind `VisionProvider` and `TTSProvider`. Changing model vendors should not change trigger detection, context generation, or rendering.

## Rendering strategy

For each approved AD event:

1. encode source video until `insertion_timestamp_s`;
2. freeze the `reference_timestamp_s` frame;
3. play generated AD audio over the frozen frame;
4. resume the source at the same source timestamp;
5. concatenate all normalized MP4 parts.

This increases final runtime by the sum of AD durations while preserving the original lecture content.

## Hackathon MVP non-goals

- real-time inference;
- interactive/on-demand AD as the primary product path;
- LMS integration beyond optional demo/debugging;
- mouse/pointer tracking;
- automatic silence-gap optimization;
- multiple production providers at once.

The existing web player is retained only as an optional debugging surface.
