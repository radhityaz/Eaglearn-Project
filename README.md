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
- Opsi pembalikan sumbu Y gaze (`eye_tracking.invert_y`) untuk device tertentu
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

Alternatif minimal:

```powershell
.\run_app.bat
```

## Instalasi Lengkap

Lihat [INSTALL.md](file:///d:/Eaglearn-Project/INSTALL.md).

## Konfigurasi

- Konfigurasi utama: [config.yaml](file:///d:/Eaglearn-Project/config.yaml)
- Contoh env: [.env.example](file:///d:/Eaglearn-Project/.env.example)

Pengaturan penting:
- Jika arah top/bottom terbalik: ubah `eye_tracking.invert_y` (default: `true`)
- Threshold fokus: `focus.focused_threshold` dan `focus.distracted_threshold`

## API (Ringkas)

- `POST /api/session/start`
- `POST /api/session/stop`
- `GET /api/state`
- `GET /api/environment`
- `GET /api/logs/metrics/download`

WebSocket:
- `state_update`
- `frame_update`

## Logging

File yang disimpan di folder `logs/`:
- `app_YYYYMMDD.log`: log aplikasi Flask (rotating)
- `metrics_<session_id>.jsonl`: snapshot metrik per ~1 detik (bisa diunduh via `GET /api/logs/metrics/download`)

File non-log yang relevan:
- `calibrations/<user_id>.json`: data kalibrasi gaze

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

## Development

### Running Tests

```bash
pytest -q
```

### Code Quality

```bash
ruff check .
mypy app.py improved_webcam_processor.py state_manager.py mediapipe_processors/face_mesh_processor.py
```

## Kontribusi

- PR dan issue diterima. Sertakan langkah reproduksi, log, dan spesifikasi perangkat.

## Lisensi

Lihat [LICENSE](file:///d:/Eaglearn-Project/LICENSE).
