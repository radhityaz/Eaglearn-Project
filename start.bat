@echo off
REM Eaglearn Flask Application Launcher for Windows
REM Double-click this file to start the application

echo.
echo ============================================================
echo Eaglearn - Focus Monitoring Application
echo ============================================================
echo.
echo Starting Flask server...
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.11 or higher
    pause
    exit /b 1
)

REM Check if in virtual environment
if not defined VIRTUAL_ENV (
    echo.
    echo WARNING: Not in virtual environment
    echo Consider activating venv first: venv\Scripts\activate
    echo.
    timeout /t 3 >nul
)

REM Run the application
python run.py

REM If script ends, pause to show error messages
if errorlevel 1 (
    echo.
    echo ERROR: Application failed to start
    pause
)
