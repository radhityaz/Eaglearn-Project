# Focus Coach CLI

`focus-coach` adalah utilitas baris perintah ringan untuk menganalisis log sesi belajar ala Eaglearn. Aplikasi ini membaca berkas CSV sederhana, menghitung durasi fokus vs jeda, mengevaluasi kualitas perhatian, dan menghasilkan ringkasan siap pakai. Paket ini juga dapat menghasilkan data simulasi untuk percobaan cepat.

## Fitur

- **Analisis Durasi** — Total waktu fokus, total waktu jeda, rata-rata dan rentang streak fokus.
- **Skor Perhatian** — Rata-rata skor perhatian dan variasinya berdasarkan sinyal berkala.
- **Heat Checks** — Jumlah dan momen terjadinya lonjakan stres.
- **Simulasi** — Generator dataset sintetis untuk menguji pipeline tanpa sensor sungguhan.

## Struktur Direktori

```
copy/focus-coach/
├── focus_coach/
│   ├── __init__.py
│   ├── analyzer.py
│   ├── cli.py
│   └── simulation.py
├── data/
│   └── sample_session.csv
├── main.py
├── README.md
└── tests/
    └── test_analyzer.py
```

## Instalasi

Gunakan Python 3.11+ (mengandalkan modul standar saja).

```bash
cd copy/focus-coach
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate untuk macOS/Linux
pip install --upgrade pip
```

Tidak ada dependensi eksternal tambahan.

## Penggunaan

### 1. Melihat bantuan

```bash
python main.py --help
```

### 2. Menganalisis log sesi

```bash
python main.py analyze data/sample_session.csv
```

Keluaran akan menampilkan ringkasan teks. Gunakan opsi `--json` untuk memperoleh JSON.

### 3. Menghasilkan data simulasi

```bash
python main.py simulate data/generated.csv --study-minutes 120 --focus-block 30 --break-block 8
```

Dataset akan tersimpan sebagai CSV lalu otomatis dianalisis sehingga Anda bisa melihat ringkasannya langsung.

## Format Data

`focus-coach` mengharapkan CSV dengan kolom:

| Kolom | Deskripsi |
| --- | --- |
| `timestamp` | cap waktu ISO8601 (UTC) |
| `event_type` | `focus_start`, `focus_end`, `break_start`, `break_end`, `attention`, `stress` |
| `value` | angka opsional untuk skor perhatian (0–100) atau deteksi stres (0/1) |

## Pengujian

```bash
python -m unittest discover -s tests
```

## Lisensi

Dirilis sebagai bagian dari prototipe internal Eaglearn. Belum ada lisensi publik.
