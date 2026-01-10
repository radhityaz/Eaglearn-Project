@echo off
setlocal EnableExtensions

REM ========================================
REM Eaglearn Application Launcher
REM ========================================

REM Set UTF-8 encoding for Python output
chcp 65001 >nul 2>&1
set PYTHONIOENCODING=utf-8

echo Starting Eaglearn Application...
echo.

REM Require GPU virtual environment to avoid confusion
set "VENV_DIR=.venv_gpu"
if exist "%VENV_DIR%\Scripts\python.exe" goto :venv_ok

echo ERROR: GPU virtual environment not found: %VENV_DIR%
echo Please use the GPU environment to run Eaglearn.
echo Expected: %VENV_DIR%\Scripts\python.exe
pause
exit /b 1

REM Activate virtual environment
:venv_ok
call "%VENV_DIR%\Scripts\activate.bat"
if errorlevel 1 goto :venv_activate_fail

REM Ensure dependencies installed
python -c "import flask" >nul 2>&1
if not errorlevel 1 goto :deps_ok

echo Installing dependencies from requirements.txt...
python -m pip install --upgrade pip
if errorlevel 1 goto :deps_fail
python -m pip install -r requirements.txt
if errorlevel 1 goto :deps_fail

:deps_ok

REM Run the application
python run.py

pause

exit /b 0

:venv_activate_fail
echo ERROR: Failed to activate virtual environment.
pause
exit /b 1

:deps_fail
echo ERROR: Failed to install dependencies.
pause
exit /b 1
