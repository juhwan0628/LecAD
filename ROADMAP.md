# Roadmap

## P0 — Production AI stage
- [x] Implement Codex CLI multimodal `VisionProvider` plus OpenAI API alternative.
- [x] Implement Gemini TTS, OpenAI TTS, and Edge demo fallback.
- [x] Store provider/model metadata in enriched manifests.
- [x] Add retries, timeout handling, and structured provider errors.
- [x] Add separate gate vs. description prompts; final tuning remains after golden-sample evaluation.

## P0 — Golden-sample validation
- [ ] Chapter 1 spatial-reference clip.
- [ ] Chapter 2 GPU graph clip.
- [ ] Chapter 3 color/map clip.
- [ ] Human-review rubric for correctness, sufficiency, concision, hallucination, timing.
- [ ] Decide production model based on LecAD-specific results.

## P1 — Render robustness
- [ ] Normalize source rotation/resolution/audio stream edge cases.
- [ ] Validate render event collisions and minimum separation.
- [x] Speak description text only; remove narration labels and prefixes.
- [x] Reuse one TTS cue for "슬라이드 전환" across transitions and reruns.
- [ ] Full-lecture render smoke test.

## P1 — Hackathon demo
- [ ] Create before/after clips for the same lecture interval.
- [ ] Render one polished full output or representative demo video.
- [x] Add one-command full pipeline via `python -m lecad --full`.
- [ ] Document expected runtime and API cost.

## Deferred
- [ ] On-demand description.
- [ ] LMS integration.
- [ ] Real-time inference.
- [ ] Pointer/mouse tracking.
- [ ] Multi-provider production fallback.
