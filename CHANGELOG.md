# Changelog

## 0.9.0-beta - 2026-01-09

### Added

- Tombol unduh metrics log sesi (JSONL)
- Pemisahan event SocketIO `state_update` dan `frame_update`
- Indikator environment di header UI (GPU/torch/VLM/python)
- Kompensasi head pose sederhana untuk stabilisasi gaze pasca-kalibrasi

### Changed

- Layout UI mengikuti sketsa: webcam kiri, focus+stats kanan, AI full-width di bawah
- Launcher Windows dipaksa memakai `.venv_gpu` untuk mencegah mismatch environment

### Fixed

- Serialisasi `emotion_scores` agar tidak mematikan realtime update
- Logging metrik dan time tracking tidak berjalan saat kalibrasi

### Known Issues

- TensorFlow GPU pada Windows bisa tampil `gpus: []` walau PyTorch CUDA aktif
- VLM membutuhkan dependency tambahan (`transformers`) dan bersifat opsional

### Security

- Upgraded: flask-cors→6.0.0, pillow→10.3.0, python-socketio→5.14.0, werkzeug→3.1.5
- Note: protobuf pinned by mediapipe/tensorflow (3.20.x); upgrade ditunda agar kompatibilitas terjaga pada beta
