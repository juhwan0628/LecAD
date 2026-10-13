from __future__ import annotations

import argparse
import json
from pathlib import Path

from .context import build_context
from .enrich import enrich_manifest
from .env import load_env_file
from .manifest import build_manifest
from .providers.factory import build_providers
from .render.renderer import render_video
from .render.timeline import build_render_events
from .triggers import detect_deictic_candidates


def _read_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")


def _resolve_event_paths(manifest: dict, manifest_path: Path) -> dict:
    base = manifest_path.resolve().parent
    out = {**manifest, "events": []}
    for event in manifest.get("events", []):
        current = dict(event)
        for key in ("frame", "audio"):
            value = current.get(key)
            if not value:
                continue
            p = Path(value)
            if not p.is_absolute():
                cwd_candidate = p.resolve()
                p = cwd_candidate if cwd_candidate.exists() else (base / p).resolve()
            current[key] = str(p)
        out["events"].append(current)
    return out


def _build_artifacts(
    *,
    transcript_path: Path,
    slides_path: Path,
    video_path: Path | None,
    output_dir: Path,
    context_radius: float,
    min_score: int,
) -> tuple[dict, list[dict]]:
    transcript = _read_json(transcript_path)
    slides = _read_json(slides_path)

    if transcript.get("source") != slides.get("source"):
        raise SystemExit(
            f"source mismatch: transcript={transcript.get('source')} slides={slides.get('source')}"
        )

    candidates = detect_deictic_candidates(transcript, min_score=min_score)
    frames_dir = output_dir / "frames"
    contexts = [
        build_context(
            c.to_dict(),
            transcript,
            slides,
            video=video_path,
            frame_dir=frames_dir if video_path else None,
            radius_s=context_radius,
        )
        for c in candidates
    ]
    manifest = build_manifest(slides, contexts)

    _write_json(output_dir / "triggers.json", [c.to_dict() for c in candidates])
    _write_json(output_dir / "contexts.json", contexts)
    _write_json(output_dir / "manifest.json", manifest)

    print(f"deictic_candidates: {len(candidates)}")
    print(f"slide_changes: {sum(1 for e in manifest['events'] if e['type'] == 'slide_change')}")
    print(f"artifact_dir: {output_dir}")
    return manifest, contexts



def _filter_ai_range(
    manifest: dict,
    contexts: list[dict],
    start_s: float,
    end_s: float | None,
) -> tuple[dict, list[dict]]:
    """Limit AD generation and slide cues to the requested source range."""
    if start_s <= 0 and end_s is None:
        return manifest, contexts

    def in_range(event: dict) -> bool:
        if event.get("type") not in {"deictic", "slide_change"}:
            return True
        t = float(event.get("insertion_timestamp_s", event.get("timestamp_s", 0.0)))
        return t >= start_s and (end_s is None or t < end_s)

    events = [dict(e) for e in manifest.get("events", []) if in_range(e)]
    wanted = {e.get("id") for e in events if e.get("type") == "deictic"}
    filtered_contexts = [ctx for ctx in contexts if ctx.get("id") in wanted]
    return {**manifest, "events": events}, filtered_contexts

def _enrich(
    *,
    manifest: dict,
    contexts: list[dict],
    output_dir: Path,
    provider_name: str | None,
) -> dict:
    vision, tts = build_providers(provider_name)
    enriched = enrich_manifest(
        manifest,
        contexts,
        vision=vision,
        tts=tts,
        audio_dir=output_dir / "audio",
    )
    approved_path = output_dir / "manifest.approved.json"
    _write_json(approved_path, enriched)
    approved = sum(1 for e in enriched.get("events", []) if e.get("approved"))
    print(f"approved_events: {approved}")
    print(f"approved_manifest: {approved_path}")
    return enriched


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="LecAD: lecture audio-description preprocessing, AI enrichment, and MP4 rendering"
    )
    p.add_argument("--transcript", type=Path)
    p.add_argument("--slides", type=Path)
    p.add_argument("--video", type=Path)
    p.add_argument("--output-dir", type=Path, default=Path("output"))
    p.add_argument("--context-radius", type=float, default=15.0)
    p.add_argument("--min-score", type=int, default=3)

    p.add_argument("--enrich-manifest", type=Path)
    p.add_argument("--contexts", type=Path)
    p.add_argument("--provider", choices=["codex", "openai", "gemini", "mock"], default=None)

    p.add_argument("--render-manifest", type=Path)
    p.add_argument("--output-video", type=Path)
    p.add_argument("--from", dest="clip_start", type=float, default=0.0)
    p.add_argument("--to", dest="clip_end", type=float)
    p.add_argument("--keep-render-workdir", action="store_true")

    p.add_argument(
        "--full",
        action="store_true",
        help="run preprocess -> AI enrichment -> render in one command",
    )
    p.add_argument(
        "--env-file",
        type=Path,
        default=Path(".env"),
        help="load API configuration from this .env file if it exists",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    load_env_file(args.env_file)

    if args.full:
        if not all([args.transcript, args.slides, args.video, args.output_video]):
            raise SystemExit("--full requires --transcript --slides --video --output-video")
        manifest, contexts = _build_artifacts(
            transcript_path=args.transcript,
            slides_path=args.slides,
            video_path=args.video,
            output_dir=args.output_dir,
            context_radius=args.context_radius,
            min_score=args.min_score,
        )
        manifest_for_ai, contexts_for_ai = _filter_ai_range(
            manifest, contexts, args.clip_start, args.clip_end
        )
        enriched = _enrich(
            manifest=manifest_for_ai,
            contexts=contexts_for_ai,
            output_dir=args.output_dir,
            provider_name=args.provider,
        )
        events = build_render_events(enriched.get("events", []))
        render_video(
            args.video,
            events,
            args.output_video,
            clip_start_s=args.clip_start,
            clip_end_s=args.clip_end,
            keep_workdir=args.keep_render_workdir,
        )
        print(f"render_events: {len(events)}")
        print(f"output_video: {args.output_video}")
        return 0

    if args.enrich_manifest:
        if not args.contexts:
            raise SystemExit("--contexts is required with --enrich-manifest")
        manifest = _resolve_event_paths(_read_json(args.enrich_manifest), args.enrich_manifest)
        contexts = _read_json(args.contexts)
        # Resolve context frame paths using the contexts file directory.
        context_base = args.contexts.resolve().parent
        for ctx in contexts:
            value = ctx.get("frame")
            if value and not Path(value).is_absolute():
                candidate = Path(value).resolve()
                ctx["frame"] = str(candidate if candidate.exists() else (context_base / value).resolve())
        output_dir = args.output_dir
        manifest, contexts = _filter_ai_range(
            manifest, contexts, args.clip_start, args.clip_end
        )
        _enrich(
            manifest=manifest,
            contexts=contexts,
            output_dir=output_dir,
            provider_name=args.provider,
        )
        return 0

    if args.render_manifest:
        if not args.video:
            raise SystemExit("--video is required with --render-manifest")
        if not args.output_video:
            raise SystemExit("--output-video is required with --render-manifest")
        render_manifest = _resolve_event_paths(
            _read_json(args.render_manifest),
            args.render_manifest,
        )
        render_events = build_render_events(render_manifest.get("events", []))
        render_video(
            args.video,
            render_events,
            args.output_video,
            clip_start_s=args.clip_start,
            clip_end_s=args.clip_end,
            keep_workdir=args.keep_render_workdir,
        )
        print(f"render_events: {len(render_events)}")
        print(f"output_video: {args.output_video}")
        return 0

    if not args.transcript or not args.slides:
        raise SystemExit(
            "--transcript and --slides are required unless using --full, --enrich-manifest, or --render-manifest"
        )

    _build_artifacts(
        transcript_path=args.transcript,
        slides_path=args.slides,
        video_path=args.video,
        output_dir=args.output_dir,
        context_radius=args.context_radius,
        min_score=args.min_score,
    )
    return 0
