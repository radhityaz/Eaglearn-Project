@echo off
REM start-electron.cmd - clears conflicting env and launches Electron UI
setlocal
set ELECTRON_RUN_AS_NODE=
REM ensure fallback for consoles that set flag
set ELECTRON_NO_ATTACH_CONSOLE=1
set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%"
call node_modules\.bin\electron.cmd .
set EXIT_CODE=%ERRORLEVEL%
popd
endlocal & exit /b %EXIT_CODE%