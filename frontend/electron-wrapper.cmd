@echo off
setlocal enabledelayedexpansion

set "ARGS="
set "HAS_PORT=0"

:: Loop through all arguments
for %%x in (%*) do (
    set "ARG=%%x"
    
    :: Check if argument is the problematic port 0
    if "!ARG!"=="--remote-debugging-port=0" (
        set "ARGS=!ARGS! --remote-debugging-port=9222"
        set "HAS_PORT=1"
    ) else (
        set "ARGS=!ARGS! !ARG!"
    )
)

:: Call original electron with modified args
"D:\Eaglearn-Project\frontend\node_modules\electron\dist\electron.exe" %ARGS%