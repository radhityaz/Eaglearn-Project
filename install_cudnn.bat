@echo off
echo ========================================
echo Installing cuDNN 8.6 to CUDA 11.8...
echo ========================================
echo.

echo Copying cuDNN bin files...
xcopy "D:\cudnn\cudnn-windows-x86_64-8.6.0.163_cuda11-archive\bin\*.*" "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.8\bin\" /Y /Q

echo Copying cuDNN include files...
xcopy "D:\cudnn\cudnn-windows-x86_64-8.6.0.163_cuda11-archive\include\*.*" "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.8\include\" /Y /Q

echo Copying cuDNN lib files...
xcopy "D:\cudnn\cudnn-windows-x86_64-8.6.0.163_cuda11-archive\lib\x64\*.*" "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.8\lib\x64\" /Y /Q

echo.
echo ========================================
echo Verifying cuDNN installation...
echo ========================================
echo.

if exist "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.8\bin\cudnn64_8.dll" (
    echo [OK] cudnn64_8.dll found!
) else (
    echo [ERROR] cudnn64_8.dll NOT found!
)

if exist "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.8\include\cudnn.h" (
    echo [OK] cudnn.h found!
) else (
    echo [ERROR] cudnn.h NOT found!
)

if exist "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.8\lib\x64\cudnn.lib" (
    echo [OK] cudnn.lib found!
) else (
    echo [ERROR] cudnn.lib NOT found!
)

echo.
echo ========================================
echo Installation complete!
echo Press any key to exit...
echo ========================================
pause
