#!/usr/bin/env bash
set -euo pipefail

SILENT=0
WITH_VLM=0
for arg in "$@"; do
  if [[ "$arg" == "--silent" ]]; then SILENT=1; fi
  if [[ "$arg" == "--with-vlm" ]]; then WITH_VLM=1; fi
done

PY="python3.11"
if command -v python3.11 >/dev/null 2>&1; then PY="python3.11"; elif command -v python3 >/dev/null 2>&1; then PY="python3"; fi

if [[ ! -d ".venv_gpu" ]]; then
  $PY -m venv .venv_gpu
fi

source .venv_gpu/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if [[ "$WITH_VLM" == "1" && -f "requirements_vlm.txt" ]]; then
  python -m pip install -r requirements_vlm.txt
fi

bash check_requirements.sh --silent || exit 7
echo "OK: setup complete"

