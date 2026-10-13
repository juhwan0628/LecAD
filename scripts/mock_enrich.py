#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from lecad.enrich import enrich_manifest
from lecad.providers.mock import MockVisionProvider, ToneTTSProvider


def read_json(path: Path):
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    p = argparse.ArgumentParser(description="Development-only LecAD AI-stage mock")
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--contexts", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--audio-dir", type=Path, required=True)
    args = p.parse_args()

    manifest = read_json(args.manifest)
    contexts = read_json(args.contexts)
    enriched = enrich_manifest(
        manifest,
        contexts,
        vision=MockVisionProvider(),
        tts=ToneTTSProvider(),
        audio_dir=args.audio_dir,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as f:
        json.dump(enriched, f, ensure_ascii=False, indent=2)
        f.write("\n")

    approved = sum(1 for e in enriched.get("events", []) if e.get("approved"))
    print(f"approved_events: {approved}")
    print(f"output: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
