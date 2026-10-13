# Development workflow

## Environment

```bash
cd /home/ubuntu/workspace/01_lecture/lecad
python3 -m venv .venv
.venv/bin/pip install -e '.[test]'
./scripts/check.sh
```

FFmpeg and ffprobe must be available on PATH.

## Production configuration

The default VLM is `CodexVisionProvider`, which calls the authenticated Codex CLI with image input. The default model is GPT-5.6 Terra at low reasoning. For production speech, `GeminiTTSProvider` uses the Gemini REST API; OpenAI TTS remains an alternative and Edge TTS is the no-key demo fallback.

```bash
cp .env.example .env
```

For the recommended Codex + Gemini path, only the TTS API key is required:

```text
GEMINI_API_KEY=...
```

Optional model/voice/threshold overrides are documented in `.env.example`.

## One-command full pipeline

```bash
.venv/bin/python -m lecad --full \
  --transcript '../lecture-transcriber/outputs/<lecture>.transcript.json' \
  --slides '../slide-extractor/output/<lecture>.slides.json' \
  --video '../skku-lecture-downloader/downloads/<lecture>.mp4' \
  --output-dir './output/<lecture>' \
  --output-video './output/<lecture>.lecad.mp4'
```

This performs preprocessing, VLM gate, VLM AD generation, TTS, approved-manifest
generation, and final MP4 rendering.

For iteration, render only the target interval:

```bash
.venv/bin/python -m lecad --full \
  --transcript '../lecture-transcriber/outputs/<lecture>.transcript.json' \
  --slides '../slide-extractor/output/<lecture>.slides.json' \
  --video '../skku-lecture-downloader/downloads/<lecture>.mp4' \
  --output-dir './output/golden' \
  --output-video './output/golden.mp4' \
  --from 1025 --to 1060
```

When `--from` / `--to` are supplied in full or enrichment mode, LecAD now
limits VLM/TTS calls to deictic events whose insertion time falls in that range.
This keeps golden-sample iteration fast and inexpensive.

## Stage-by-stage debugging

Build trigger/context artifacts only:

```bash
.venv/bin/python -m lecad \
  --transcript '../lecture-transcriber/outputs/<lecture>.transcript.json' \
  --slides '../slide-extractor/output/<lecture>.slides.json' \
  --video '../skku-lecture-downloader/downloads/<lecture>.mp4' \
  --output-dir './output/<lecture>'
```

Enrich an existing manifest:

```bash
.venv/bin/python -m lecad \
  --enrich-manifest './output/<lecture>/manifest.json' \
  --contexts './output/<lecture>/contexts.json' \
  --output-dir './output/<lecture>'
```

Render an approved manifest:

```bash
.venv/bin/python -m lecad \
  --render-manifest './output/<lecture>/manifest.approved.json' \
  --video '../skku-lecture-downloader/downloads/<lecture>.mp4' \
  --output-video './output/demo.mp4'
```

## Provider boundary

Production and future providers implement:

- `VisionProvider.gate()`
- `VisionProvider.describe()`
- `TTSProvider.synthesize()`

Current implementations:

- `CodexVisionProvider`: Codex CLI image input; default GPT-5.6 Terra / low.
- `GeminiTTSProvider`: Gemini 3.8 Flash-Lite TTS by default.
- `OpenAIVisionProvider` / `OpenAITTSProvider`: API alternatives.
- `EdgeTTSProvider`: no-key demo fallback.
- `MockVisionProvider` + `ToneTTSProvider`: offline wiring tests.

Provider-specific responses never enter core rendering code.

## Golden samples

Use real lecture cases covering different visual-reference classes:

- Chapter 1 around 807.3 s — spatial reference, "오른쪽 그림..."
- Chapter 2 around 1036.7 s — GPU/CPU graph interpretation
- Chapter 3 around 1284.2 s — color/map interpretation, "빨간 부분..."

Before a full demo render, human-review these dimensions:

1. reference correctness;
2. visual sufficiency;
3. concision;
4. hallucination;
5. timing;
6. audio distinction from lecturer speech.

## Mock end-to-end verification

No API key is needed:

```bash
.venv/bin/python -m lecad --full --provider mock \
  --transcript '../lecture-transcriber/outputs/<lecture>.transcript.json' \
  --slides '../slide-extractor/output/<lecture>.slides.json' \
  --video '../skku-lecture-downloader/downloads/<lecture>.mp4' \
  --output-dir './output/mock' \
  --output-video './output/mock.mp4' \
  --from 1028 --to 1052
```

The mock VLM approves every candidate and mock TTS generates tones; it exists
only to verify orchestration and rendering.
