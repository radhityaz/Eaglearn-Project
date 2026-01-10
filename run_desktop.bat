@echo off
setlocal EnableExtensions

REM ========================================
REM Eaglearn Desktop Application Launcher
REM ========================================

REM Set UTF-8 encoding for Python output
chcp 65001 >nul 2>&1
set PYTHONIOENCODING=utf-8

echo ========================================
echo Eaglearn Desktop Application
echo ========================================
echo Starting desktop application...
echo.

REM Require GPU virtual environment to avoid confusion
set "VENV_DIR=.venv_gpu"
if exist "%VENV_DIR%\Scripts\python.exe" goto :venv_ok

echo ERROR: GPU virtual environment not found: %VENV_DIR%
echo Please use the GPU environment to run Eaglearn Desktop.
echo Expected: %VENV_DIR%\Scripts\python.exe
pause
exit /b 1

REM Activate virtual environment
:venv_ok
call "%VENV_DIR%\Scripts\activate.bat"
if errorlevel 1 goto :venv_activate_fail

REM Check if pywebview is installed
python -c "import pywebview" >nul 2>&1
if errorlevel 1 goto :install_pywebview
goto :deps_ok

:install_pywebview
echo Installing desktop dependencies (pywebview)...
python -m pip install pywebview[cef] pywin32
if errorlevel 1 goto :deps_fail

:deps_ok
echo Starting desktop application...
echo.

REM Run the desktop application
python desktop_launcher.py

pause

exit /b 0

:venv_activate_fail
echo ERROR: Failed to activate virtual environment.
pause
exit /b 1

:deps_fail
echo ERROR: Failed to install desktop dependencies.
echo Please check your internet connection and try again.
pause
exit /b 1
