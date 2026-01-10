# Eaglearn

Eaglearn adalah sistem monitoring fokus real-time untuk aktivitas belajar/kerja berbasis webcam (gaze, head pose, micro-expressions, posture, dan emotion) dengan UI live.

## Use Case

- Belajar mandiri: deteksi distraksi, drowsiness, dan pola fokus
- Kelas daring: observasi engagement secara non-intrusif
- Deep work: pantau fokus dan mental effort selama sesi

## Fitur Utama

- Face & eye tracking (MediaPipe FaceMesh + iris)
- Head pose (yaw/pitch/roll) + rule-based stress/confusion/drowsiness
- Focus score + time tracking (focused/unfocused time)
- Calibration gaze (wizard) + kompensasi head pose sederhana
- Logging metrik sesi (JSONL) + tombol “Simpan Log”
- Mode pause (privacy)

## Arsitektur (Ringkas)

```text
Browser UI (templates/index.html)
  ├─ WebSocket: state_update + frame_update
  └─ REST: /api/session/*, /api/state, /api/environment, /api/logs/*

Flask + SocketIO (app.py)
  └─ ImprovedWebcamProcessor (improved_webcam_processor.py)
      ├─ FaceMeshProcessor (mediapipe_processors/face_mesh_processor.py)
      ├─ PoseProcessor (mediapipe_processors/pose_processor.py)
      ├─ DeepFaceEmotionDetector (mediapipe_processors/deepface_emotion_detector.py)
      └─ CalibrationManager (calibration.py)
```

## Quick Start (Windows)

Skenario pre-release beta memakai `.venv_gpu` untuk menghindari mismatch environment.

```powershell
.\run_eaglearn.bat
```

Aplikasi berjalan di:
- Web: `http://localhost:8080`

## Instalasi Lengkap

Lihat [INSTALL.md](file:///d:/Eaglearn-Project/INSTALL.md).

## Konfigurasi

- Konfigurasi utama: [config.yaml](file:///d:/Eaglearn-Project/config.yaml)
- Contoh env: [.env.example](file:///d:/Eaglearn-Project/.env.example)

## API (Ringkas)

- `POST /api/session/start`
- `POST /api/session/stop`
- `GET /api/state`
- `GET /api/environment`
- `GET /api/logs/metrics/download`

WebSocket:
- `state_update`
- `frame_update`

## Panduan Darurat (Troubleshooting Flow)

```text
UI tidak update?
  ├─ cek env indicator: GPU/torch/VLM/py
  ├─ reload halaman
  ├─ cek camera: izin kamera + device index
  └─ lihat logs/app_YYYYMMDD.log

Kamera hitam?
  ├─ ganti backend camera: dshow/default
  ├─ tutup aplikasi lain yang pakai webcam
  └─ restart aplikasi

FPS rendah?
  ├─ turunkan resolusi kamera
  ├─ naikkan frame_skip_base
  └─ pastikan jalan pakai .venv_gpu
```

Troubleshooting lengkap: [docs/TROUBLESHOOTING.md](file:///d:/Eaglearn-Project/docs/TROUBLESHOOTING.md)

Dokumen operasional VLM: [docs/VLM_OPERATIONAL.md](file:///d:/Eaglearn-Project/docs/VLM_OPERATIONAL.md)

## Known Issues (Beta)

- TensorFlow GPU di Windows sering tidak tersedia (gpus: `[]`), sementara PyTorch CUDA tetap bisa aktif.
- VLM bersifat opsional dan membutuhkan dependency tambahan (`transformers`).

## Kontribusi

- PR dan issue diterima. Sertakan langkah reproduksi, log, dan spesifikasi perangkat.

## Lisensi

Lihat [LICENSE](file:///d:/Eaglearn-Project/LICENSE).
- Check confidence threshold in config
- See logs for error messages

## Requirements

### Core Dependencies

- Python 3.11+
- Flask 3.0+
- Flask-SocketIO 5.3+
- OpenCV 4.8+
- MediaPipe 0.10+

### ML Dependencies

- DeepFace 0.0.79+ (emotion detection)
- TensorFlow 2.15+ (DeepFace backend)
- PyTorch + torchvision (EfficientNet)

### Optional

- CUDA-capable GPU (for acceleration)
- POSTER++ weights (for 90% accuracy emotion detection)

## Development

### Running Tests

```bash
pytest tests/
```

### Code Quality

```bash
# Format code
black app.py mediapipe_processors/

# Lint code
pylint app.py
```

## License

See LICENSE file.

## Acknowledgments

- [MediaPipe](https://google.github.io/mediapipe/) - Face & pose detection
- [DeepFace](https://github.com/serengil/deepface) - Emotion recognition
- [PyTorch](https://pytorch.org/) - EfficientNet models
- [POSTER++](https://github.com/AnnamTk/POSTER) - SOTA emotion detection (optional)
