#!/usr/bin/env bash
set -euo pipefail

PY=".venv_gpu/bin/python"
if [[ -x ".venv_gpu/Scripts/python.exe" ]]; then
  PY=".venv_gpu/Scripts/python.exe"
fi
if [[ ! -x "$PY" ]]; then
  echo "ERROR: .venv_gpu not found. Run ./setup.sh first."
  exit 1
fi

exec "$PY" run.py

