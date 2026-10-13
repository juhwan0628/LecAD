#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
.venv/bin/pytest -q
python3 -m compileall -q lecad
ffmpeg -version >/dev/null
ffprobe -version >/dev/null
echo "LecAD development checks passed."
