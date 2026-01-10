#!/usr/bin/env bash
set -euo pipefail

SILENT=0
if [[ "${1:-}" == "--silent" ]]; then SILENT=1; fi

PY="python3"
if [[ -x ".venv_gpu/bin/python" ]]; then PY=".venv_gpu/bin/python"; fi
if [[ -x ".venv_gpu/Scripts/python.exe" ]]; then PY=".venv_gpu/Scripts/python.exe"; fi

$PY -c "import sys; raise SystemExit(0 if sys.version_info[:2]>=(3,11) else 2)"

$PY -c "import importlib; mods=['flask','flask_socketio','cv2','mediapipe','numpy']; missing=[m for m in mods if importlib.util.find_spec(m) is None]; import sys; print('missing:', ','.join(missing) if missing else 'none'); raise SystemExit(3 if missing else 0)"

$PY -c "import pathlib; p=pathlib.Path('logs'); p.mkdir(exist_ok=True); f=p/'_write_test.tmp'; f.write_text('ok', encoding='utf-8'); f.unlink(); print('logs writable: ok')"

echo "OK: Requirements check passed"

