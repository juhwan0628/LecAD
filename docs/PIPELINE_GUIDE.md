# LecAD — Lecture Audio Description Pipeline

LecAD converts an ordinary lecture recording into a new MP4 with short, context-aware audio descriptions inserted at moments where the instructor visually refers to the screen.

The hackathon MVP is intentionally **offline and render-first**:

```text
lecture.mp4
+ transcript.json
+ slides.json
       │
       ▼
deictic trigger detection
       │
       ▼
context package
(frame + current slide + timestamped transcript)
       │
       ▼
VLM relevance gate
       │
       ▼
VLM concise audio-description text
       │
       ▼
TTS audio
       │
       ▼
approved render manifest
       │
       ▼
FFmpeg freeze-frame insertion
       │
       ▼
lecture.lecad.mp4
```

The interactive/on-demand player is no longer the primary product path. It is retained only as an optional debugging surface.

### Script generation and reusable slide cues

The VLM receives timestamped transcript context separated into already-heard and
upcoming speech, plus previous descriptions on the same slide. It records visible
facts and missing information before producing a short spoken script. The Codex
path still performs gate and description in one invocation.

TTS reads only the description, without `음성 해설`, `[음성해설]`, or script
headings. Legacy `LECAD_TTS_PREFIX` settings are ignored. Empty descriptions are
skipped. Slide changes use the fixed spoken cue `슬라이드 전환`, synthesized once
and reused for every transition and later runs in the same audio directory.
Changing the TTS provider, model, voice or rate creates a new cue file. Both AD
and slide cues pause the source while their audio plays.

Render parts use 30 FPS video, a common video time base, and 48 kHz stereo audio
before concatenation. Use `--from` and `--to` to restrict both descriptions and
slide cues when reviewing short samples.

## Why this architecture

The difficult part is not manual video editing. LecAD generates a deterministic timeline and renders the edit automatically.

When the instructor says something like:

> “오른쪽 그래프를 보면…”

LecAD:

1. detects the visual-reference utterance;
2. extracts the frame at the exact reference moment;
3. checks with a VLM whether a real visual target is present;
4. generates a short description of only that target;
5. synthesizes the description to speech;
6. waits until the instructor finishes the utterance;
7. freezes the lecture frame while AD plays;
8. resumes the original lecture from the same source timestamp.

This preserves the original lecture while adding only the missing visual context.

## Repository role

This project is one layer in the existing `01_lecture` toolchain:

```text
skku-lecture-downloader
        │
        └── lecture.mp4
              ├── lecture-transcriber ──> transcript.json
              ├── slide-extractor ──────> slides.json
              │
              └─────────────────────────> LecAD
                                           └── lecture.lecad.mp4
```

LecAD does **not** import those projects as Python packages. MP4 and JSON files are the integration boundary.

## Current implementation status

Implemented:

- conservative rule-based deictic candidate detection;
- word-level timestamp support when transcript schema v2 is available;
- approximate timestamp fallback for legacy segment-only transcripts;
- current-slide lookup;
- transcript context from 15 seconds before reference to 15 seconds after insertion;
- exact trigger-frame extraction;
- render manifest generation;
- separate reference/insertion timestamps;
- provider-neutral VLM and TTS interfaces;
- Codex CLI multimodal provider for VLM gate + AD generation (default: GPT-5.6 Terra, low reasoning);
- Gemini TTS provider (recommended production TTS);
- OpenAI vision/TTS providers as alternatives;
- Edge neural TTS no-key demo fallback;
- retry/error handling for API requests;
- confidence thresholding before AD generation;
- deterministic mock providers for development;
- FFmpeg source segmentation;
- freeze-frame AD clip generation;
- final MP4 concatenation;
- partial-range rendering for fast iteration;
- unit tests and smoke-tested end-to-end rendering.

Remaining before the hackathon demo:

- paste a real API key into `.env`;
- run golden-sample model/prompt evaluation;
- tune prompts/thresholds from those results;
- render and review the final demo video.

No additional pipeline code is required for the first real API run.

## Project layout

```text
lecad/
├── lecad/
│   ├── cli.py
│   ├── context.py
│   ├── triggers.py
│   ├── patterns.py
│   ├── manifest.py
│   ├── enrich.py
│   ├── providers/
│   │   ├── base.py
│   │   ├── factory.py
│   │   ├── mock.py
│   │   └── openai_provider.py
│   └── render/
│       ├── timeline.py
│       ├── media.py
│       └── renderer.py
├── config/
│   └── example.json
├── docs/
│   ├── ARCHITECTURE.md
│   ├── DEVELOPMENT.md
│   └── SCHEMAS.md
├── player/                  # optional debug UI
├── scripts/
│   └── check.sh
├── tests/
├── .env.example
└── pyproject.toml
```

## Setup

Requirements:

- Python 3.12+
- FFmpeg
- ffprobe

```bash
cd /home/ubuntu/workspace/01_lecture/lecad
python3 -m venv .venv
.venv/bin/pip install -e '.[test]'
./scripts/check.sh
```

## Production quick start — API key + one command

The default VLM path uses the already-authenticated Codex CLI, so no metered vision API key is required. The recommended production TTS path is Gemini TTS.

```bash
cp .env.example .env
```

For Gemini TTS, edit only:

```text
GEMINI_API_KEY=...
```

Codex itself uses the existing ChatGPT/Codex login. For a no-key demo, set `LECAD_TTS_PROVIDER=edge`.

Then run the complete pipeline:

```bash
.venv/bin/python -m lecad --full \
  --transcript '../lecture-transcriber/outputs/<lecture>.transcript.json' \
  --slides '../slide-extractor/output/<lecture>.slides.json' \
  --video '../skku-lecture-downloader/downloads/<lecture>.mp4' \
  --output-dir './output/<lecture>' \
  --output-video './output/<lecture>.lecad.mp4'
```

That command performs:

```text
trigger detection
→ context/frame extraction
→ VLM relevance gate
→ VLM audio-description generation
→ TTS
→ manifest.approved.json
→ freeze-frame AD insertion
→ final MP4
```

Default model settings live in `.env.example` and can be overridden without code changes. For hackathon development, add `--from` and `--to` to render only a short interval.

## Current model choice

Golden-sample tests showed that GPT-5.6 Terra with low reasoning keeps useful graph/map/spatial grounding while reducing latency and usage compared with GPT-6 Astra. GPT-5.6 Luna is lighter and worked well on simple graph/map cases, but produced less reliable target metadata on some spatial cases, so Terra remains the default.

## Step 1 — build trigger/context artifacts

```bash
.venv/bin/python -m lecad \
  --transcript '../lecture-transcriber/outputs/<lecture>.transcript.json' \
  --slides '../slide-extractor/output/<lecture>.slides.json' \
  --video '../skku-lecture-downloader/downloads/<lecture>.mp4' \
  --output-dir './output/<lecture>'
```

Output:

```text
output/<lecture>/
├── triggers.json
├── contexts.json
├── manifest.json
└── frames/
    ├── d_0001.jpg
    └── ...
```

## Step 2 — AI enrichment

The production implementation uses these stable interfaces:

```python
VisionProvider.gate(...)
VisionProvider.describe(...)
TTSProvider.synthesize(...)
```

The rest of LecAD does not know or care which model vendor is used.

Expected flow:

```text
manifest.json + contexts.json
        │
        ▼
VisionProvider.gate()
        │
        ├── NO  -> approved=false
        │
        └── YES
             │
             ▼
      VisionProvider.describe()
             │
             ▼
       TTSProvider.synthesize()
             │
             ▼
manifest.approved.json
```

See `lecad/providers/base.py` and `docs/SCHEMAS.md`.

## Development-only mock AI stage

Before real APIs are connected, the provider boundary and renderer can be exercised end-to-end:

```bash
.venv/bin/python scripts/mock_enrich.py \
  --manifest './output/<lecture>/manifest.json' \
  --contexts './output/<lecture>/contexts.json' \
  --audio-dir './output/<lecture>/audio' \
  --output './output/<lecture>/manifest.mock-approved.json'
```

The mock vision provider approves every candidate and the mock TTS provider generates a short tone. This is only for wiring/render tests, never for the hackathon demo.

## Step 3 — render the final video

Once approved events contain generated descriptions and audio:

```bash
.venv/bin/python -m lecad \
  --render-manifest './output/<lecture>/manifest.approved.json' \
  --video '../skku-lecture-downloader/downloads/<lecture>.mp4' \
  --output-video './output/<lecture>.lecad.mp4'
```

For development, render only a short clip:

```bash
.venv/bin/python -m lecad \
  --render-manifest './output/<lecture>/manifest.approved.json' \
  --video '../skku-lecture-downloader/downloads/<lecture>.mp4' \
  --output-video './output/golden-graph.mp4' \
  --from 1025 \
  --to 1060
```

## Timing model

A deictic event uses two timestamps:

```text
reference_timestamp_s
    = frame shown to the VLM

insertion_timestamp_s
    = end of instructor utterance
      where generated AD is inserted
```

Example:

```json
{
  "id": "d_0005",
  "reference_timestamp_s": 1036.69,
  "insertion_timestamp_s": 1045.21
}
```

This prevents LecAD from interrupting the lecturer in the middle of a sentence.

## Golden development cases

Use these before rendering an entire lecture:

| Case | Approx. time | What it tests |
|---|---:|---|
| Chapter 1 — “오른쪽 그림…” | 807.3 s | spatial grounding |
| Chapter 2 — GPU performance figure | 1036.7 s | graph interpretation |
| Chapter 3 — “빨간 부분…” | 1284.2 s | color + map interpretation |

Model evaluation should prioritize:

1. reference correctness;
2. visual sufficiency;
3. concision;
4. hallucination avoidance;
5. insertion timing;
6. clear distinction between lecturer audio and generated AD.

## Development rules

- Do not put provider-specific formats into core manifests.
- Do not commit API keys or `.env`.
- Prefer transcript schema v2 word timestamps for final demos.
- Keep trigger detection conservative; VLM is a second-stage gate, not a substitute for every weak linguistic cue.
- Develop on 20–60 second golden clips.
- Run a full lecture render only when the short clips are stable.
- Keep the original lecture unchanged; generated assets belong under `output/`.

## More documentation

- `docs/ARCHITECTURE.md` — system boundaries and rendering model
- `docs/SCHEMAS.md` — JSON contracts between stages
- `docs/DEVELOPMENT.md` — day-to-day implementation workflow
