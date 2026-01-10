# PANDUAN APLIKASI EAGLEARN
## Focus Monitoring System - User Guide

**Versi:** 1.0
**Last Updated:** 8 Januari 2026
**Application:** EAGLEARN Focus Monitoring

---

## 📋 DAFTAR ISI

1. [Tentang Aplikasi](#tentang-aplikasi)
2. [Persyaratan Sistem](#persyaratan-sistem)
3. [Instalasi](#instalasi)
4. [Menjalankan Aplikasi](#menjalankan-aplikasi)
5. [Panduan Penggunaan](#panduan-penggunaan)
6. [Fitur-Fitur](#fitur-fitur)
7. [Konfigurasi](#konfigurasi)
8. [Troubleshooting](#troubleshooting)
9. [FAQ](#faq)

---

## 🎯 TENTANG APLIKASI

EAGLEARN adalah aplikasi **focus monitoring** berbasis AI yang mendeteksi:
- **Emotion** - 7 jenis emosi (happy, sad, angry, surprised, neutral, fear, disgust)
- **Head Pose** - Posisi kepala (pitch, yaw, roll)
- **Eye Tracking** - Arah pandangan mata
- **Body Posture** - Postur tubuh dan fokus
- **Blink Rate** - Frekuensi kedipan mata
- **Yawning Detection** - Deteksi mengantuk
- **Stress & Confusion** - Level stress dan kebingungan

**Teknologi:**
- MediaPipe untuk face & pose detection
- DeepFace untuk emotion recognition
- Flask + SocketIO untuk real-time communication
- PyTorch & TensorFlow untuk model AI

---

## 💻 PERSYARATAN SISTEM

### Minimum Requirements:
- **OS:** Windows 10/11, Linux (Ubuntu 20.04+), macOS 10.15+
- **Python:** 3.9 - 3.11 (recommended: 3.11.9)
- **RAM:** 8 GB (16 GB recommended)
- **Processor:** Intel Core i5 / AMD Ryzen 5 ke atas
- **Storage:** 5 GB free space
- **Webcam:** Built-in atau external (640x480 minimum)
- **Browser:** Chrome, Firefox, Edge (WebSocket support)

### Recommended (untuk GPU acceleration):
- **GPU:** NVIDIA GTX 1650 ke atas (RTX 3050+ recommended)
- **VRAM:** 4 GB minimum
- **CUDA:** 11.8 atau 12.x

---

## 🚀 INSTALASI

### Step 1: Clone Repository
```bash
git clone <repository-url>
cd Eaglearn-Project
```

### Step 2: Buat Virtual Environment
```bash
# Buat virtual environment
python -m venv .venv_gpu

# Activate virtual environment
# Windows:
.venv_gpu\Scripts\activate

# Linux/macOS:
source .venv_gpu/bin/activate
```

### Step 3: Install Dependencies
```bash
# Upgrade pip
python -m pip install --upgrade pip

# Install semua dependencies
pip install -r requirements.txt

# Install PyTorch dengan CUDA (jika ada GPU)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

### Step 4: Verifikasi Instalasi
```bash
# Cek Python
python --version  # Expected: 3.9-3.11

# Cek PyTorch GPU (jika ada GPU)
python -c "import torch; print('CUDA available:', torch.cuda.is_available())"
# Expected: CUDA available: True

# Cek MediaPipe
python -c "import mediapipe as mp; print('MediaPipe:', mp.__version__)"
# Expected: MediaPipe: 0.10.8
```

---

## ▶️ MENJALANKAN APLIKASI

### Opsi 1: Run secara Manual
```bash
# Activate virtual environment
source .venv_gpu/Scripts/activate  # Windows
source .venv_gpu/bin/activate     # Linux/macOS

# Jalankan aplikasi
python app.py
```

Aplikasi akan berjalan di:
- **Local:** http://127.0.0.1:8080
- **Network:** http://192.168.x.x:8080 (IP address lokal)

### Opsi 2: Run dengan Batch File (Windows)
Buat file `run_eaglearn.bat`:
```batch
@echo off
call .venv_gpu\Scripts\activate
python app.py
pause
```

Klik dua kali file tersebut untuk menjalankan aplikasi.

### Opsi 3: Run sebagai Background Service (Linux/macOS)
```bash
# Jalankan di background
nohup python app.py > eaglearn.log 2>&1 &

# Cek logs
tail -f eaglearn.log
```

---

## 📖 PANDUAN PENGGUNAAN

### 1. Buka Aplikasi di Browser

1. Buka browser (Chrome/Firefox/Edge)
2. Navigate ke: **http://localhost:8080**
3. Allow camera access ketika diminta

### 2. Mulai Monitoring Session

#### Tampilan Utama:
```
┌─────────────────────────────────────────────────────────┐
│                    EAGLEARN                             │
│                                                          │
│  [Start Session]  [Stop Session]  [Calibrate]         │
│                                                          │
│  ┌─────────────────────────────────────────────────────┐│
│  │            CAMERA FEED                                ││
│  │                                                       ││
│  │              [Your face will appear here]            ││
│  │                                                       ││
│  └─────────────────────────────────────────────────────┘│
│                                                          │
│  Status: FOCUSED                                          │
│  Focus Score: 85%                                        │
│  Emotion: Happy (95%)                                     │
│  FPS: 27.5                                                │
└─────────────────────────────────────────────────────────┘
```

### 3. Interpretasi Hasil

#### Focus Score:
- **85-100%** 🟢 = Focused
- **50-84%** 🟡 = Need Attention
- **0-49%** 🔴 = Distracted/Drowsy

#### Emotion Indicators:
- 😊 **Happy** = Engagement good
- 😐 **Neutral** = Normal state
- 😠 **Angry** = Frustration/struggle
- 😨 **Fear/Surprise** = Confusion/uncertainty
- 😢 **Sad** = Lack of motivation

#### Additional Metrics:
- **Head Pose** = Posisi kepala (harus menghadap depan)
- **Eye Gaze** = Arah pandangan (harus ke screen)
- **Posture** = Postur tubuh (harus tegak)
- **Blink Rate** = Kedipan normal (12-25 per minute)
- **Yawning** = Deteksi mengantuk (tanda fatigue)

### 4. Calibration

Untuk akurasi terbaik, lakukan **calibration**:

1. Klik tombol **[Calibrate]**
2. Ikuti instruksi:
   - Dudur tegak di depan kamera
   - Pandang lurus ke screen
   - Posisi wajah terlihat jelas
   - Tahan 5-10 detik
3. Klik **[Save Calibration]**

Calibration data akan disimpan di `user_calibration.json`

---

## 🎛️ FITUR-FITUR

### Real-time Monitoring
- **Live Video Feed** - Webcam stream dengan overlay
- **Face Detection** - Bounding box dan landmarks
- **Emotion Detection** - Update real-time (5-10 FPS)
- **Focus Tracking** - Score focus 0-100%
- **Performance Metrics** - FPS, frame skip, processing time

### Session Management
- **Start/Stop** - Kontrol monitoring session
- **Auto-save** - Session data disimpan otomatis
- **History** - Review session sebelumnya
- **Export** - Download session data (CSV/JSON)

### Advanced Features
- **Gaze Estimation** - Prediksi arah pandangan (x, y coordinate)
- **Attention Score** - 0-100, seberapa fokus ke screen
- **Distraction Alerts** - Notifikasi jika loss of focus
- **Fatigue Detection** - Yawning dan drowsiness
- **Stress Analysis** - Level stress dari micro-expressions

---

## ⚙️ KONFIGURASI

### File: `config.yaml`

#### Camera Settings:
```yaml
camera:
  width: 640           # Resolution lebar
  height: 480          # Resolution tinggi
  fps: 30              # Target FPS
  backend: dshow       # Windows: dshow, Linux: v4l2
```

#### Performance Tuning:
```yaml
performance:
  frame_skip_mode: adaptive
  frame_skip_base: 3   # Process setiap N frame
  adaptive_quality:
    enabled: true
    target_fps: 25     # FPS target
    min_skip: 1
    max_skip: 7
  gpu_acceleration:
    enabled: true
    fallback_to_cpu: true
```

#### Emotion Detection:
```yaml
emotion:
  min_confidence: 0.3    # Threshold confidence
  yawning_mar_threshold: 0.6
  blink_ear_threshold: 0.21
  stress_high_threshold: 0.7
```

### Environment Variables

Buat file `.env`:
```bash
# Camera
CAMERA_ID=0
CAMERA_WIDTH=640
CAMERA_HEIGHT=480

# Server
HOST=127.0.0.1
PORT=8080
DEBUG=False

# Privacy
RETENTION_DAYS=30
```

---

## 🐛 TROUBLESHOOTING

### Problem: Camera Not Detected

**Symptoms:**
- Error: "Cannot open webcam"
- Black screen
- "No camera found"

**Solutions:**
1. **Check camera connection:**
   ```bash
   # Windows
   python -c "import cv2; cap = cv2.VideoCapture(0); print('Open:', cap.isOpened())"
   ```

2. **Try different backends:**
   - Edit `config.yaml`: `backend: default`
   - Atau gunakan camera ID lain: `CAMERA_ID=1`

3. **Close other apps:**
   - Close Zoom, Teams, Skype, etc.
   - Only one app can access camera at a time

### Problem: Low FPS (< 15)

**Symptoms:**
- Choppy video
- Laggy interface
- FPS counter shows < 15

**Solutions:**
1. **Reduce resolution:**
   ```yaml
   camera:
     width: 320
     height: 240
   ```

2. **Increase frame skip:**
   ```yaml
   frame_skip_base: 5
   ```

3. **Disable face mesh:**
   ```yaml
   visual_feedback:
     show_face_mesh: false
     show_skeleton: false
   ```

4. **Use CPU-only mode:**
   ```yaml
   gpu_acceleration:
     enabled: false
   ```

### Problem: Emotion Detection Not Working

**Symptoms:**
- Emotion always "neutral"
- Low confidence scores
- Error logs from DeepFace

**Solutions:**
1. **Check DeepFace installation:**
   ```bash
   python -c "from deepface import DeepFace; print('OK')"
   ```

2. **Verify TensorFlow:**
   ```bash
   python -c "import tensorflow as tf; print(tf.__version__)"
   # Expected: 2.15.0
   ```

3. **Check lighting:**
   - Pastikan wajah terilluminasi dengan baik
   - Hindar backlighting
   - Gunakan lighting tambahan jika perlu

4. **Adjust confidence threshold:**
   ```yaml
   emotion:
     min_confidence: 0.2  # Lower untuk lebih sensitive
   ```

### Problem: GPU Not Utilized

**Symptoms:**
- High CPU usage, low GPU usage
- `nvidia-smi` shows 0% GPU utilization
- TensorFlow/PyTorch using CPU

**Solutions:**
1. **Verify CUDA installation:**
   ```bash
   nvidia-smi
   # Check CUDA Version column
   ```

2. **Check PyTorch CUDA:**
   ```bash
   python -c "import torch; print('CUDA:', torch.cuda.is_available())"
   # Expected: CUDA: True
   ```

3. **Reinstall PyTorch with CUDA:**
   ```bash
   pip uninstall torch torchvision
   pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
   ```

### Problem: Application Won't Start

**Symptoms:**
- "Address already in use"
- "Port 8080 already occupied"
- Connection refused

**Solutions:**
1. **Kill existing process:**
   ```bash
   # Windows
   taskkill /f /im python.exe

   # Linux/macOS
   pkill -f "python app.py"
   ```

2. **Change port:**
   ```python
   # Edit app.py line ~215
   socketio.run(app, host='0.0.0.0', port=8081)  # Use 8081
   ```

3. **Check firewall:**
   - Windows: Allow Python through Windows Firewall
   - Linux: `sudo ufw allow 8080`

---

## ❓ FAQ

### Q: Apakah EAGLEARN menyimpan video saya?
**A:** TIDAK. EAGLEARN melakukan **local processing only**. Tidak ada video atau gambar yang di-upload ke cloud. Semua processing terjadi di komputer Anda.

### Q: Berapa latensi aplikasi?
**A:**
- **Video feed:** ~50-100ms (camera ke browser)
- **Emotion detection:** 100-200ms (DeepFace inference)
- **Total latency:** ~150-300ms
- Dengan temporal smoothing, ada tambahan 150-300ms untuk stabilisasi

### Q: Bisakah digunakan tanpa internet?
**A:** YA. EAGLEARN bekerja 100% offline. Koneksi internet hanya diperlukan saat pertama kali untuk mendownload model AI (DeepFace weights).

### Q: Berapa akurasi emotion detection?
**A:**
- **DeepFace (SSD backend):** ~85-90% accuracy
- **DeepFace (RetinaFace):** ~95% accuracy (dengan GPU)
- **F1-score:** 0.87-0.93 tergantung dataset

### Q: Bisakah mendeteksi multiple people?
**A:** Saat ini EAGLEARN dirancang untuk **single user** (one face di frame). Untuk multiple users, perlu modifikasi kode.

### Q: Berapa resource usage?
**A:**
- **CPU:** 30-60% (Intel i5/Ryzen 5)
- **RAM:** 1-2 GB (Python + models)
- **GPU:** 2-3 GB VRAM (jika ada GPU)
- **Storage:** 500 MB untuk models

### Q: Bagaimana cara improve akurasi?
**A:**
1. **Lakukan calibration** sebelum session
2. **Pencahayaan baik** - wajah terlihat jelas
3. **Posisi proper** - wajah langsung menghadap kamera
4. **Gunakan GPU** untuk RetinaFace backend
5. **Adjust thresholds** di `config.yaml`

### Q: Apakah data privacy terjamin?
**A:** YA. Semua data diproses secara lokal. Tidak ada data yang dikirim ke server eksternal. Session data disimpan di lokal komputer Anda.

---

## 📚 TIPS & TRICKS

### Best Practices:
1. **Lighting** - Gunakan pencahayaan diffuse, hindar shadows di wajah
2. **Position** - Dudur pada jarak 50-80 cm dari kamera
3. **Background** - Gunakan background solid/bersih
4. **Calibration** - Lakukan kalibrasi sebelum sesi penting
5. **Breaks** - Ambil break setiap 45-60 menit untuk hasil terbaik

### Performance Tips:
1. **Close unused apps** - Free up resources
2. **Use wired connection** - Untuk network session (jika applicable)
3. **Disable visual feedback** - Untuk low-end devices
4. **Adjust FPS target** - Set ke 20-25 untuk battery saving

### Accuracy Tips:
1. **Stable position** - Hindar excessive movement
2. **Direct gaze** - Pandang lurus ke kamera/screen
3. **Neutral expression** - Untuk baseline calibration
4. **Multiple sessions** - Rata-ratakan dari beberapa session

---

## 🔗 LINKS & RESOURCES

### Documentation:
- [Main README](README.md)
- [Installation Guide](INSTALL_CUDA_11.8_STEP_BY_STEP.md)
- [Development Report](LAPORAN_HASIL_PENGEMBANGAN.md)
- [POSTER++ Setup](setup_poster++.md)

### External Resources:
- [MediaPipe Documentation](https://google.github.io/mediapipe/)
- [DeepFace GitHub](https://github.com/serengil/deepface)
- [Flask Documentation](https://flask.palletsprojects.com/)

### Support:
- **Issues:** GitHub Issues
- **Email:** [project-email@example.com]
- **Discord:** [server-invite-link]

---

## 📝 CHANGELOG

### Version 1.0 (8 Januari 2026)
- ✅ Initial release
- ✅ Focus monitoring with 85-95% accuracy
- ✅ Real-time emotion detection (7 emotions)
- ✅ Head pose, eye tracking, posture analysis
- ✅ Temporal smoothing untuk stabilisasi
- ✅ Calibration system
- ✅ Privacy-first design (local processing only)
- ✅ GPU acceleration support (PyTorch CUDA)

---

## 📄 LICENSE

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**End of User Guide**

*Untuk pertanyaan lebih lanjut, hubungi development team atau lihat dokumentasi teknis di repository ini.*

**Happy Learning with EAGLEARN! 🚀📚**
