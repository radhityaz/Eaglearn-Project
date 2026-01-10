@echo off
echo ========================================
echo COPY CUDNN FILES - SIMPLE VERSION
echo ========================================
echo.
echo This will copy cuDNN files to CUDA 11.8
echo.
pause

echo.
echo [1/3] Copying cuDNN DLL files...
copy /Y "D:\cudnn\cudnn-windows-x86_64-8.6.0.163_cuda11-archive\bin\cudnn64_8.dll" "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.8\bin\"
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to copy cudnn64_8.dll
    echo You may need to run this as Administrator!
    pause
    exit /b 1
)
echo OK: cudnn64_8.dll copied

echo.
echo [2/3] Copying cuDNN header file...
copy /Y "D:\cudnn\cudnn-windows-x86_64-8.6.0.163_cuda11-archive\include\cudnn.h" "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.8\include\"
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to copy cudnn.h
    pause
    exit /b 1
)
echo OK: cudnn.h copied

echo.
echo [3/3] Copying cuDNN library file...
copy /Y "D:\cudnn\cudnn-windows-x86_64-8.6.0.163_cuda11-archive\lib\x64\cudnn.lib" "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.8\lib\x64\"
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to copy cudnn.lib
    pause
    exit /b 1
)
echo OK: cudnn.lib copied

echo.
echo ========================================
echo ALL FILES COPIED SUCCESSFULLY!
echo ========================================
echo.
pause
