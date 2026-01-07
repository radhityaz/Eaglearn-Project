@echo off
REM ========================================
REM Eaglearn Application Launcher
REM ========================================

echo Starting Eaglearn Application...
echo.

REM Activate virtual environment
call .venv\Scripts\activate.bat

REM Run the application
python app.py

pause
