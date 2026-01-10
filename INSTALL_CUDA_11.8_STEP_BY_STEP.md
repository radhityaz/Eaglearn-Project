# CUDA 11.8 Installation - Step-by-Step Guide

**Goal**: Install CUDA 11.8 + cuDNN 8.6 untuk enable TensorFlow GPU di Eaglearn

**Current Status**:
- ✅ GPU: RTX 3050 Laptop (4GB VRAM)
- ✅ Driver: 581.29 (latest)
- ⚠️ CUDA: 13.0 (need 11.8 for TensorFlow)

**Estimated Time**: 45 minutes

---

## 📥 STEP 1: Download Files (15 minutes)

### A. CUDA 11.8.0 Toolkit

**Link**: https://developer.nvidia.com/cuda-11-8-0-download-archive

**Steps**:
1. Click link di atas
2. Select:
   - **Operating System**: Windows
   - **Architecture**: x86_64
   - **Version**: 10 atau 11
   - **Installer Type**: **exe (network)** ← Recommended (smaller)
3. Click **Download**
4. File: `cuda_11.8.0_522.06_windows_network.exe` (~3 MB)
5. Save to: `D:\Downloads\` (atau folder downloads kamu)

**Alternative** (jika internet lambat):
- Pilih **exe (local)** = ~3 GB (full offline installer)

---

### B. cuDNN 8.6.0 for CUDA 11.x

**Link**: https://developer.nvidia.com/cudnn

⚠️ **PENTING**: Butuh **NVIDIA Developer Account** (gratis)

**Steps**:
1. Click link di atas
2. Click **Download cuDNN**
3. **Login** atau **Create Account** (gratis, 2 menit)
4. Accept License Agreement
5. Click **Download cuDNN v8.6.0 (October 3rd, 2022), for CUDA 11.x**
6. Click **Local Installer for Windows (Zip)**
7. File: `cudnn-windows-x86_64-8.6.0.163_cuda11-archive.zip` (~600 MB)
8. Save to: `D:\Downloads\`

**Wait for both downloads to complete before continuing!**

---

## 🗑️ STEP 2: Uninstall CUDA 13.0 (5 minutes)

⚠️ **Note**: CUDA runtime 13.0 yang terdeteksi di `nvidia-smi` adalah driver runtime, bukan toolkit. Kita perlu check apakah CUDA Toolkit 13.0 terinstall.

### Check if CUDA Toolkit Installed:

```cmd
# Open Command Prompt (Win+R, ketik "cmd")
nvcc --version
```

**If you see**:
```
nvcc: NVIDIA (R) Cuda compiler driver
...release 13.0...
```
→ **CUDA Toolkit 13.0 IS installed, need to uninstall**

**If you see**:
```
'nvcc' is not recognized...
```
→ **No CUDA Toolkit installed, skip to STEP 3** ✅

---

### If CUDA 13.0 Toolkit Found, Uninstall:

**Method A: Control Panel** (Recommended)

1. Open: `Control Panel` → `Programs and Features`
2. Search for "CUDA" in list
3. Uninstall ALL of these (if present):
   - ❌ NVIDIA CUDA Runtime 13.0
   - ❌ NVIDIA CUDA Development 13.0
   - ❌ NVIDIA CUDA Documentation 13.0
   - ❌ NVIDIA CUDA Samples 13.0
   - ❌ NVIDIA CUDA Visual Studio Integration 13.0
   - ✅ Keep: **NVIDIA Graphics Driver** (jangan uninstall!)
4. Click each → Uninstall → Follow prompts
5. Restart computer (recommended)

**Method B: Manual Cleanup** (Optional, if uninstall fails)

```cmd
# Open Command Prompt as Administrator (Win+X → Command Prompt (Admin))
rmdir /s /q "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.0"
```

---

## 📦 STEP 3: Install CUDA 11.8 (10 minutes)

**Prerequisites**: Both files downloaded

### Installation Steps:

1. **Run installer**:
   - Navigate to `D:\Downloads\`
   - **Right-click** → **Run as Administrator**
   - File: `cuda_11.8.0_522.06_windows_network.exe`

2. **NVIDIA Installer** will open:
   - Click **OK** to extract
   - Wait for extraction (~1 minute)

3. **License Agreement**:
   - Read (or skip 😄)
   - Click **Agree and Continue**

4. **Installation Options**:
   - **CRITICAL**: Select **Custom (Advanced)**
   - Click **Next**

5. **Component Selection** (IMPORTANT!):

   **UNCHECK these** (already have newer versions):
   - ❌ **Driver components** (your 581.29 is newer!)
   - ❌ **NVIDIA GeForce Experience** (already installed)
   - ❌ **PhysX** (not needed)
   - ❌ **NVIDIA Nsight** (not needed)

   **CHECK these** (needed for TensorFlow):
   - ✅ **CUDA Toolkit 11.8**
   - ✅ **CUDA Samples 11.8** (optional, useful for testing)
   - ✅ **CUDA Documentation 11.8** (optional)
   - ✅ **CUDA Visual Studio Integration** (if you use Visual Studio)

6. **Installation Location**:
   - Default is fine: `C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.8`
   - Click **Next**

7. **Install**:
   - Click **Next**
   - Wait for installation (~5-10 minutes)
   - ☕ Take a coffee break!

8. **Completion**:
   - Click **Close**
   - **DO NOT restart yet** (wait after cuDNN install)

---

## 📦 STEP 4: Install cuDNN 8.6 (5 minutes)

**Prerequisites**: CUDA 11.8 installed, cuDNN zip downloaded

### Installation Steps:

1. **Extract cuDNN zip**:
   - Navigate to `D:\Downloads\`
   - Right-click `cudnn-windows-x86_64-8.6.0.163_cuda11-archive.zip`
   - Click **Extract All...**
   - Extract to: `D:\Downloads\cudnn\`
   - Click **Extract**

2. **Verify extracted folder structure**:
   ```
   D:\Downloads\cudnn\cudnn-windows-x86_64-8.6.0.163_cuda11-archive\
   ├── bin\
   │   ├── cudnn64_8.dll
   │   ├── cudnn_ops_infer64_8.dll
   │   └── cudnn_cnn_infer64_8.dll
   ├── include\
   │   └── cudnn.h
   └── lib\
       └── x64\
           └── cudnn.lib
   ```

3. **Copy files to CUDA directory**:

   **Option A: Manual Copy** (Easiest)

   Open two File Explorer windows:

   **Window 1** (Source):
   - `D:\Downloads\cudnn\cudnn-windows-x86_64-8.6.0.163_cuda11-archive\`

   **Window 2** (Destination):
   - `C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.8\`

   **Copy these folders** (drag & drop):
   - Drag `bin` contents → merge with CUDA `bin` folder
   - Drag `include` contents → merge with CUDA `include` folder
   - Drag `lib\x64` contents → merge with CUDA `lib\x64` folder

   Click **Replace** if prompted

   **Option B: Command Line** (Advanced)

   Open Command Prompt **as Administrator**:
   ```cmd
   cd D:\Downloads\cudnn\cudnn-windows-x86_64-8.6.0.163_cuda11-archive

   xcopy bin\*.* "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.8\bin\" /Y
   xcopy include\*.* "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.8\include\" /Y
   xcopy lib\x64\*.* "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.8\lib\x64\" /Y
   ```

4. **Verify cuDNN files copied**:

   Check these files exist:
   - `C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.8\bin\cudnn64_8.dll` ✅
   - `C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.8\include\cudnn.h` ✅
   - `C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.8\lib\x64\cudnn.lib` ✅

---

## 🔄 STEP 5: Restart Computer (IMPORTANT!)

**Why restart?**
- Load new CUDA drivers
- Update system PATH
- Initialize GPU with new toolkit

**Steps**:
1. Save all work
2. Close all applications
3. Restart computer
4. **Come back after restart!** ←

---

## ✅ STEP 6: Verify Installation (5 minutes)

**After restart**, open **NEW** Command Prompt:

### A. Check CUDA Version

```cmd
nvcc --version
```

**Expected Output**:
```
nvcc: NVIDIA (R) Cuda compiler driver
Copyright (c) 2005-2022 NVIDIA Corporation
Built on Wed_Sep_21_10:41:10_Pacific_Daylight_Time_2022
Cuda compilation tools, release 11.8, V11.8.89
Build cuda_11.8.r11.8/compiler.31833905_0
```

✅ If you see **"release 11.8"** → SUCCESS!
❌ If you see error or different version → Something wrong

---

### B. Check nvidia-smi

```cmd
nvidia-smi
```

**Expected Output**:
```
CUDA Version: 11.8 (or higher like 13.0 is OK - this is driver version)
```

✅ GPU should still show → SUCCESS!

---

### C. Check Environment Variables

```cmd
echo %CUDA_PATH%
```

**Expected**:
```
C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.8
```

✅ Path contains "v11.8" → SUCCESS!

---

### D. Check PATH Variable

```cmd
echo %PATH%
```

**Expected** (should contain):
```
...CUDA\v11.8\bin;...CUDA\v11.8\libnvvp;...
```

✅ If you see "CUDA\v11.8" paths → SUCCESS!

---

## 🧪 STEP 7: Test TensorFlow GPU (5 minutes)

Navigate to Eaglearn project:

```cmd
cd D:\Eaglearn-Project
python test_gpu.py
```

**Expected Output** (SUCCESS):
```
============================================================
TensorFlow GPU Detection Test
============================================================

📦 TensorFlow Version: 2.15.0

🔍 Searching for GPU devices...
✅ GPU DETECTED: 1 device(s) found!

GPU 0:
  Name: /physical_device:GPU:0
  Type: GPU

✅ GPU memory growth enabled successfully!
✅ GPU computation successful!

📚 Library Versions:
  CUDA: 11.8
  cuDNN: 8.6

============================================================
✅ GPU IS READY FOR EAGLEARN!
============================================================
```

✅ **If you see this** → CUDA 11.8 installation SUCCESS! 🎉

---

## 🚀 STEP 8: Test Eaglearn App (5 minutes)

```cmd
cd D:\Eaglearn-Project
python app.py
```

**Watch startup logs** for:

```
🚀 TensorFlow GPU detected: 1 device(s)
✅ GPU memory growth enabled for: /physical_device:GPU:0
🚀 Using RetinaFace backend (TensorFlow GPU accelerated)
🔧 Backend: retinaface | TensorFlow GPU: True
🔧 Confidence Threshold: 0.20
```

✅ **If you see GPU detected** → Eaglearn GPU WORKING! 🎉

**Open browser**: http://localhost:8080

Test emotion detection performance!

---

## 🎯 Expected Performance After Installation

| Metric | Before (CPU) | After (GPU) | Improvement |
|--------|--------------|-------------|-------------|
| **Backend** | SSD | RetinaFace | Better accuracy |
| **Accuracy** | ~85% | **~95%** | +10% |
| **FPS** | 10-15 | **20-25** | +67% speed |
| **Latency** | ~100ms | **~50ms** | 2x faster |
| **Confidence** | 0.25 | **0.20** | More sensitive |
| **GPU Usage** | 0% | **30-50%** | Utilized |

---

## 🐛 Troubleshooting

### Problem: "nvcc: command not found"

**Solution**:
1. Restart Command Prompt (or computer)
2. Check PATH environment variable
3. Manually add to PATH if needed:
   - System Properties → Environment Variables
   - Edit "Path" variable
   - Add: `C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.8\bin`

---

### Problem: "Could not load dynamic library 'cudnn64_8.dll'"

**Solution**:
1. Verify cuDNN files in `CUDA\v11.8\bin\`
2. Check file: `cudnn64_8.dll` exists
3. Restart computer
4. If still fails, re-copy cuDNN files

---

### Problem: TensorFlow still not detecting GPU

**Solution**:
1. Reinstall TensorFlow:
   ```cmd
   pip uninstall tensorflow tf-keras
   pip install tensorflow==2.15.0 tf-keras==2.15.0
   ```
2. Restart Command Prompt
3. Run `python test_gpu.py` again

---

### Problem: Installation fails with error

**Solution**:
1. Disable antivirus temporarily
2. Run installer as Administrator
3. Check disk space (need ~5GB free on C:)
4. Close NVIDIA processes in Task Manager
5. Try again

---

## 📞 Need Help?

**Check logs**:
- TensorFlow: `python test_gpu.py`
- nvidia-smi: Shows GPU status
- nvcc --version: Shows CUDA version

**Reference docs**:
- Full guide: `docs/CUDA_INSTALLATION_GUIDE.md`
- GPU optimization: `docs/GPU_OPTIMIZATION.md`

---

## ✅ Installation Checklist

Before continuing, verify ALL these:

- [  ] CUDA 11.8 downloaded
- [  ] cuDNN 8.6 downloaded
- [  ] CUDA 13.0 uninstalled (if was installed)
- [  ] CUDA 11.8 installed (Custom, without driver)
- [  ] cuDNN files copied to CUDA directory
- [  ] Computer restarted
- [  ] `nvcc --version` shows 11.8
- [  ] `test_gpu.py` detects GPU
- [  ] Eaglearn app runs with GPU

All checked? **Congratulations!** 🎉

---

**Ready to start? Let's do this!** 🚀

**Current Step**: Download CUDA 11.8 from link above!
