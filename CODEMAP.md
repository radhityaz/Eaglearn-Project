# Eaglearn Code Inventory - Level-0 (L0)

## Overview
Berikut adalah gambaran umum komponen utama dalam proyek Eaglearn, dengan fokus pada keandalan, maintainability, dan API contract drift berdasarkan area risiko prioritas.
### Komponen Utama
| Direktori | Peran | Anchor File |
|-----------|-------|-------------|
| [backend/](backend/) | Backend Python untuk AI processing (computer vision, audio analysis) | [backend/main.py](backend/main.py) |
| [frontend/](frontend/) | Desktop application Electron dengan UI dashboard | [frontend/renderer-figma.js](frontend/renderer-figma.js) |
| [prototypes/](prototypes/) | Prototipe awal dan dokumentasi teknis | [prototypes/EVIDENCE_001_WEBCAM.md](prototypes/EVIDENCE_001_WEBCAM.md) |
| [eaglearn-clone/](eaglearn-clone/) | Clone prototipe UI awal untuk referensi desain | [eaglearn-clone/index.html](eaglearn-clone/index.html) |
| [copy/focus-coach/](copy/focus-coach/) | Implementasi alternatif dari sistem pemantauan | [copy/focus-coach/main.py](copy/focus-coach/main.py) |
| [spec/](spec/) | Spesifikasi teknis dan arsitektur sistem | [spec/10_requirements.md](spec/10_requirements.md) |
| [docs/](docs/) | Dokumentasi sistem dan panduan pengguna | - |
| [tests/](tests/) | Suite test untuk komponen backend dan frontend | - |
## Directory Map (Level-0)
### backend/
**Peran**: Backend Python untuk processing AI (computer vision, audio analysis)
**Subfolder Penting**:
- [backend/ml/](backend/ml/) - Modul ML untuk vision (Gaze, Pose) dan audio (Stress)
- [backend/api/](backend/api/) - API server FastAPI (REST + WebSocket)
- [backend/ws/](backend/ws/) - WebSocket Manager & Heartbeat
- [backend/db/models.py](backend/db/models.py) - Model SQLAlchemy terenkripsi untuk sesi, metrik, kalibrasi
- [backend/db/migrations/](backend/db/migrations/) - Runner migrasi lightweight (`apply_migrations`)
- [backend/utils/](backend/utils/) - Utility dan helper
### frontend/
**Peran**: Desktop application Electron dengan UI dashboard
- [frontend/](frontend/) - Source code desktop app
- [frontend/renderer-figma.js](frontend/renderer-figma.js) - Renderer untuk mode Figma
- [frontend/package.json](frontend/package.json) - Konfigurasi Node.js
### prototypes/
**Peran**: Prototipe awal dan dokumentasi teknis
- [prototypes/figma-export/](prototypes/figma-export/) - Export Figma design assets
- [prototypes/webcam_capture_poc.py](prototypes/webcam_capture_poc.py) - Proof-of-concept webcam capture
### eaglearn-clone/
**Peran**: Clone prototipe UI awal untuk referensi desain
- [eaglearn-clone/assets/](eaglearn-clone/assets/) - Asset UI (ikon)
- [eaglearn-clone/styles.css](eaglearn-clone/styles.css) - Stylesheet dasar
### copy/focus-coach/
**Peran**: Implementasi alternatif dari sistem pemantauan
- [copy/focus-coach/focus_coach/](copy/focus-coach/focus_coach/) - Modul utama implementasi
### spec/
**Peran**: Spesifikasi teknis dan arsitektur sistem
- [spec/10_requirements.md](spec/10_requirements.md) - Kebutuhan sistem
- [spec/65_solution_architecture.md](spec/65_solution_architecture.md) - Arsitektur solusi
### docs/
**Peran**: Dokumentasi sistem dan panduan pengguna
- Tidak ada file dalam direktori ini
### tests/
**Peran**: Suite test untuk komponen backend dan frontend
**Subfolder Penting**:
### tests/
**Peran**: Suite test untuk komponen backend dan frontend
- [tests/test_retention.py](tests/test_retention.py) - Retention policy coverage
- [tests/test_models.py](tests/test_models.py) - Validasi model database & enkripsi
- [tests/test_api.py](tests/test_api.py) - End-to-end REST session/calibration flow
- [tests/test_api_negative.py](tests/test_api_negative.py) - Guardrail validation (consent, calibration, rate-limit)
## Components Summary
Berikut adalah ringkasan jumlah file per komponen:
| Komponen | Jumlah File | Ekstensi Dominan |
|----------|-------------|------------------|
| backend/ | 34 file | `.py` |
| frontend/ | 12 file | `.js`, `.css`, `.json` |
| prototypes/ | 12 file | `.py`, `.md` |
| eaglearn-clone/ | 14 file | `.html`, `.css`, `.svg` |
| copy/focus-coach/ | 8 file | `.py`, `.csv` |
| spec/ | 12 file | `.md` |
| docs/ | 0 file | - |
| tests/ | 4 file | `.py` |
## Non-code Exclusions
Berikut adalah pola/glob untuk konten non-kode:
- [science-source/](science-source/) (*.pdf) — sumber ilmiah, non-kode
- [eaglearn-clone/assets/icons/](eaglearn-clone/assets/icons/) (*.svg) — aset ikon
- [prototypes/figma-export/icons/](prototypes/figma-export/icons/) (*.svg), [prototypes/figma-export/screenshots/](prototypes/figma-export/screenshots/) — aset
## Risk Focus
Area risiko prioritas berdasarkan keandalan, maintainability, dan API contract drift:
### [backend/ml/](backend/ml/)
**Alasan relevansi**: Komponen ini berisi model computer vision utama (Gaze, Pose) dan audio analysis (Stress) yang merupakan inti sistem pemantauan. Karena akurasi dan latensi adalah kunci untuk pengalaman pengguna, perubahan pada API atau model dapat menyebabkan drift besar yang memengaruhi semua fitur visual. Komponen ini juga menggunakan library OpenCV dan Mediapipe yang rentan terhadap breaking changes.
### [frontend/renderer-figma.js](frontend/renderer-figma.js)
**Alasan relevansi**: File ini adalah bagian kritis dari UI rendering yang berfungsi dalam mode Figma untuk validasi paritas. Perubahan pada struktur DOM atau logika rendering dapat langsung memengaruhi validasi UI dan pengalaman pengguna. Karena ini adalah bagian dari prototype evolusioner, perubahan kecil dapat memicu perubahan besar pada UI dan fungsi yang terkait dengan paritas layout.
## Light Metrics
**Estimasi Metrik Ringan (berdasarkan jumlah file):**
- Total file: ~83
- File Python: ~30
- File JavaScript/CSS: ~26
- File Markdown: ~12
- File PDF: ~35
- File SVG: ~17
**Metode estimasi**: Menghitung jumlah file dalam setiap direktori utama dan kategorikan berdasarkan ekstensi file.
## Assumptions & Gaps
**Asumsi:**
1. Struktur direktori utama sudah mencerminkan arsitektur sistem
2. File anchor mencerminkan peran utama dari komponen
3. Komponen dengan jumlah file lebih banyak memiliki kompleksitas lebih tinggi
**Gap Data:**
1. Tidak ada informasi detail tentang ukuran dan kompleksitas file
2. Tidak ada informasi spesifik tentang dependency antar komponen
3. Belum ada analisis hotspot performa atau keamanan
4. Tidak ada informasi tentang CI/CD pipeline atau testing coverage
**Rencana Data Lanjutan:**
1. Analisis dependency antar modul Python dan JS
2. Profil performa dan resource usage per komponen
3. Identifikasi API contracts dan dokumentasi kontrak
4. Informasi tentang penggunaan memory dan CPU per modul
## Next Steps
Langkah selanjutnya untuk memperkaya inventory ini:
1. Identifikasi dan analisis hotspot arsitektur
2. Lakukan analisis RCA pada komponen kritis
3. Evaluasi API contracts dan dokumentasi kontrak
4. Buat roadmap maintenance dan upgrade
