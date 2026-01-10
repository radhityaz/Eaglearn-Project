@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "SILENT=0"
if /I "%~1"=="--silent" set "SILENT=1"

if exist ".venv_gpu\Scripts\python.exe" (
  set "PY=.venv_gpu\Scripts\python.exe"
) else (
  set "PY=python"
)

%PY% -c "import sys; exit(0 if sys.version_info[:2]>=(3,11) else 2)"
if errorlevel 1 (
  echo FAIL: Python 3.11+ required
  if "%SILENT%"=="0" pause
  exit /b 2
)

%PY% -c "import importlib; mods=['flask','flask_socketio','cv2','mediapipe','numpy']; missing=[m for m in mods if importlib.util.find_spec(m) is None]; import sys; print('missing:', ','.join(missing) if missing else 'none'); sys.exit(3 if missing else 0)"
if errorlevel 1 (
  echo FAIL: Missing required Python packages
  if "%SILENT%"=="0" pause
  exit /b 3
)

%PY% -c "import os, sys; import torch; ok=torch.cuda.is_available(); print('torch', getattr(torch,'__version__',None), 'cuda', ok, 'count', torch.cuda.device_count() if ok else 0); sys.exit(0)"
%PY% -c "import sys; import tensorflow as tf; g=tf.config.list_physical_devices('GPU'); print('tf', getattr(tf,'__version__',None), 'gpu_count', len(g)); sys.exit(0)" 1>nul 2>nul

%PY% -c "import os, sys; import pathlib; p=pathlib.Path('logs'); p.mkdir(exist_ok=True); f=p/'_write_test.tmp'; f.write_text('ok', encoding='utf-8'); f.unlink(); print('logs writable: ok'); sys.exit(0)"
if errorlevel 1 (
  echo FAIL: Cannot write to logs directory
  if "%SILENT%"=="0" pause
  exit /b 4
)

echo OK: Requirements check passed
exit /b 0

