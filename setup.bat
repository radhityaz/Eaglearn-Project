@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "SILENT=0"
set "WITH_VLM=0"
for %%A in (%*) do (
  if /I "%%A"=="--silent" set "SILENT=1"
  if /I "%%A"=="--with-vlm" set "WITH_VLM=1"
)

if not exist ".venv_gpu\Scripts\python.exe" (
  py -3.11 -m venv .venv_gpu
  if errorlevel 1 (
    echo FAIL: create .venv_gpu
    if "%SILENT%"=="0" pause
    exit /b 2
  )
)

call ".venv_gpu\Scripts\activate.bat"
if errorlevel 1 (
  echo FAIL: activate .venv_gpu
  if "%SILENT%"=="0" pause
  exit /b 3
)

python -m pip install --upgrade pip
if errorlevel 1 (
  echo FAIL: pip upgrade
  if "%SILENT%"=="0" pause
  exit /b 4
)

python -m pip install -r requirements.txt
if errorlevel 1 (
  echo FAIL: install requirements.txt
  if "%SILENT%"=="0" pause
  exit /b 5
)

if "%WITH_VLM%"=="1" (
  if exist "requirements_vlm.txt" (
    python -m pip install -r requirements_vlm.txt
    if errorlevel 1 (
      echo FAIL: install requirements_vlm.txt
      if "%SILENT%"=="0" pause
      exit /b 6
    )
  )
)

call check_requirements.bat --silent
if errorlevel 1 (
  echo FAIL: check_requirements
  if "%SILENT%"=="0" pause
  exit /b 7
)

echo OK: setup complete
exit /b 0

