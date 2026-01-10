# INSTALL (Beta)

## Persyaratan Sistem Minimum

- OS: Windows 10/11, Linux, atau macOS
- Python: 3.11
- Webcam: 720p atau 480p
- RAM: 8 GB (disarankan 16 GB)
- CPU: 4 core modern
- GPU (opsional, disarankan): NVIDIA + CUDA untuk PyTorch

Catatan: TensorFlow GPU pada Windows sering tidak aktif (gpus `[]`) meskipun PyTorch CUDA aktif.

## Instalasi One-Click (Windows)

1. Pastikan folder `.venv_gpu` tersedia di root project
2. Jalankan:

```powershell
.\run_eaglearn.bat
```

Jika muncul error `.venv_gpu` tidak ditemukan, buat ulang environment sesuai standar internal tim.

## Instalasi Manual (Windows)

```powershell
.\.venv_gpu\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python run.py
```

## Instalasi Manual (Linux/macOS)

Gunakan environment Python 3.11 dan install dependency:

```bash
python3.11 -m venv .venv_gpu
source .venv_gpu/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python run.py
```

## Menjalankan (Linux/macOS)

```bash
./run_eaglearn.sh
```

Mode desktop (butuh dependency GUI untuk pywebview di OS terkait):

```bash
./run_desktop.sh
```

## Opsional: VLM

VLM adalah fitur opsional. Jika dibutuhkan:

```bash
python -m pip install -r requirements_vlm.txt
```

## Troubleshooting Umum

- Kamera hitam: tutup aplikasi lain yang memakai webcam, cek izin kamera OS, ganti `camera.backend` di `config.yaml`
- UI tidak update: pastikan `run_eaglearn.bat` dipakai, refresh browser, cek `logs/`
- VLM OFF: install `requirements_vlm.txt` dan restart
