@echo off
setlocal EnableExtensions

REM ========================================
REM Eaglearn Application Launcher
REM ========================================

echo Starting Eaglearn Application...
echo.

REM Activate virtual environment
set "VENV_DIR=.venv_gpu"
if exist "%VENV_DIR%\Scripts\activate.bat" goto :activate

echo Virtual environment not found. Please create .venv_gpu first.
pause
exit /b 1

:activate
if exist "%VENV_DIR%\Scripts\activate.bat" (
    call "%VENV_DIR%\Scripts\activate.bat"
    if errorlevel 1 goto :venv_activate_fail
) else (
    echo Virtual environment not found. Please create .venv or .venv_gpu first.
    pause
    exit /b 1
)

:venv_ok

REM Run application
python run.py

if errorlevel 1 goto :app_fail
goto :end

:venv_activate_fail
echo ERROR: Failed to activate virtual environment.
pause
exit /b 1

:app_fail
echo ERROR: Failed to start Eaglearn Application.
pause
exit /b 1

:end
exit /b 0
