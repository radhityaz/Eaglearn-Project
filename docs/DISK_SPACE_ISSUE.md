# Disk Space Issue - PyTorch Installation Failed

## 🔴 Problem

**PyTorch installation failed: No space left on device**

```
ERROR: Could not install packages due to an OSError: [Errno 28] No space left on device
```

## 📊 Current Disk Status

**C: Drive:**
- Used: 346 GB
- Free: **2.27 GB** ⚠️
- Total: ~348 GB

**Required:**
- PyTorch GPU: 2.5 GB
- **Not enough space!**

---

## 🎯 Solutions

### **Option 1: Clean Up Disk Space** ⭐ RECOMMENDED

Free up at least 5GB for safe PyTorch installation.

#### A. Clean Temp Files

```cmd
# Run as Administrator
cleanmgr.exe

# Select:
✅ Temporary files
✅ Downloads folder
✅ Recycle Bin
✅ Thumbnails
✅ Windows Update Cleanup
```

#### B. Clear Python Cache

```bash
# Navigate to project
cd D:\Eaglearn-Project

# Clear pip cache
pip cache purge

# Clear Python __pycache__
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
```

#### C. Remove Old Python Packages

```bash
# List large packages
pip list --format=freeze | xargs pip show | grep -E "Location|Size"

# Remove unused packages (examples)
pip uninstall -y jupyter notebook pandas scikit-learn matplotlib
```

#### D. Clear Browser Cache

- Chrome: `chrome://settings/clearBrowserData`
- Edge: `edge://settings/clearBrowserData`
- Firefox: `about:preferences#privacy`

---

### **Option 2: Install PyTorch to D: Drive**

Move Python packages to D: drive where Eaglearn project is.

#### Steps:

```cmd
# 1. Create virtual environment on D:
cd D:\Eaglearn-Project
python -m venv .venv_pytorch

# 2. Activate
.venv_pytorch\Scripts\activate

# 3. Install PyTorch there
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121

# 4. Install other dependencies
pip install hsemotion opencv-python flask flask-socketio mediapipe deepface
```

---

### **Option 3: Use Lighter Alternative** ⚡ QUICK FIX

Skip full PyTorch, use **HSEmotion with CPU** temporarily.

```bash
# HSEmotion is much smaller (~100MB vs 2.5GB)
pip install hsemotion

# Use with CPU mode
from hsemotion.facial_emotions import HSEmotionRecognizer
model = HSEmotionRecognizer(model_name='enet_b0_8_best_vgaf', device='cpu')
```

**Trade-offs:**
- ✅ Works immediately
- ✅ Minimal disk space
- ❌ CPU-only (slower: 15-25 FPS)
- ❌ No GPU acceleration

---

### **Option 4: Keep Current Setup**

Continue using **DeepFace with CPU mode**.

**Pros:**
- ✅ Already working
- ✅ No disk space needed
- ✅ 95% accuracy

**Cons:**
- ❌ Slower (10-15 FPS)
- ❌ No CUDA 13 support

---

## 💡 Recommended Strategy

### **Short-term (Now):**

1. **Clean up 5GB** space using Option 1A-D
2. **Install PyTorch GPU** (2.5GB)
3. **Install HSEmotion** (~100MB)
4. **Test performance**

### **Long-term (Next week):**

1. Consider upgrading storage (SSD)
2. Or move Python environment to external drive
3. Regular cleanup schedule

---

## 🧹 Quick Cleanup Script

Save as `cleanup_disk.bat`:

```batch
@echo off
echo Cleaning up disk space...

REM Clear pip cache
echo [1/5] Clearing pip cache...
pip cache purge

REM Clear Python cache
echo [2/5] Clearing Python __pycache__...
for /d /r . %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"

REM Clear temp files
echo [3/5] Clearing temp files...
del /q /f /s %TEMP%\* 2>nul
del /q /f /s C:\Windows\Temp\* 2>nul

REM Empty recycle bin
echo [4/5] Emptying recycle bin...
rd /s /q C:\$Recycle.Bin 2>nul

REM Show results
echo [5/5] Cleanup complete!
echo.
echo Current disk space:
powershell -Command "Get-PSDrive C | Select-Object Used,Free | Format-List"

pause
```

---

## 📊 After Cleanup - Expected Space

| Item | Before | After | Freed |
|------|--------|-------|-------|
| Temp Files | ~500MB | 0MB | 500MB |
| Pip Cache | ~200MB | 0MB | 200MB |
| Browser Cache | ~1GB | 0MB | 1GB |
| Downloads | varies | varies | varies |
| **Total** | **2.27GB free** | **~4-6GB free** | **~2-4GB** |

---

## ⚙️ Alternative: External Drive Installation

If C: drive persistently full:

```bash
# 1. Create project on D: (already done!)
# 2. Use virtual environment on D:
cd D:\Eaglearn-Project
python -m venv .venv

# 3. All packages install to D: drive
# 4. C: drive stays clean
```

---

## 🎯 Next Steps

Choose one:

1. **[ ] Clean 5GB space** → Install PyTorch GPU → Best performance
2. **[ ] Use D: drive venv** → Install PyTorch there → Good solution
3. **[ ] Install HSEmotion CPU** → Quick fix → Acceptable performance
4. **[ ] Keep DeepFace CPU** → No changes → Current working state

**Recommendation:** Clean 5GB + Install PyTorch GPU = **Best of all worlds**

---

**Last Updated:** 2026-01-08
**Issue:** PyTorch GPU installation failed (disk full)
**Status:** Awaiting cleanup or alternative selection
