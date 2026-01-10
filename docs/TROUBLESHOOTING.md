# Troubleshooting

## Checklist Cepat

1. Lihat indikator environment di header UI
2. Pastikan menjalankan via `run_eaglearn.bat`
3. Pastikan webcam tidak dipakai aplikasi lain
4. Lihat `logs/` untuk error terbaru

## Masalah: GPU Disabled

- Pastikan process memakai `.venv_gpu`
- Pastikan `torch.cuda.is_available()` true
- Jika memakai Python global, bisa muncul error `WinError 193` dan GPU jadi OFF

## Masalah: VLM Not Available

- VLM opsional. Jika ingin aktif:
  - install `requirements_vlm.txt`
  - restart aplikasi

## Masalah: TensorFlow GPU = []

- Di Windows, TensorFlow GPU sering tidak tersedia pada setup default
- Ini tidak memblokir PyTorch CUDA maupun fitur utama Eaglearn

## Masalah: Kamera Hitam / Tidak Terbuka

- Cek izin kamera OS
- Tutup aplikasi lain yang memakai webcam (Zoom/Teams/Discord)
- Ganti `camera.backend` di `config.yaml`:
  - Windows: `dshow`
  - Linux: `v4l2` atau `default`

## Masalah: Kalibrasi Buruk Setelah Kepala Bergerak

- Duduk dengan jarak kamera stabil
- Hindari perubahan posisi kepala besar
- Jalankan ulang kalibrasi jika posisi duduk berubah signifikan

