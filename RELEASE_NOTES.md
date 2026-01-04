# Release Notes

## v1.0.0 - Eaglearn - Initial Release

**Release Date:** 2025-01-02

Kami dengan bangga mengumumkan rilis pertama dari **Eaglearn**, platform monitoring belajar mandiri berbasis AI yang dirancang untuk meningkatkan fokus dan produktivitas mahasiswa secara privat dan offline.

### ✨ Fitur Utama

*   **Real-time Student Engagement Analysis**
    *   Deteksi atensi visual menggunakan Gaze Estimation dan Head Pose Detection.
    *   Analisis tingkat stres melalui indikator audio dan ekspresi mikro (experimental).
    *   Semua pemrosesan dilakukan secara lokal (on-device) untuk menjaga privasi.

*   **Focus Coach**
    *   Timer **Pomodoro** terintegrasi yang dapat disesuaikan.
    *   **Smart Nudging**: Memberikan peringatan halus saat fokus terdeteksi menurun atau tanda-tanda kelelahan muncul.
    *   Saran istirahat cerdas berdasarkan pola kelelahan pengguna.

*   **Local Data Storage**
    *   Menggunakan **SQLite** terenkripsi untuk penyimpanan sesi belajar yang aman dan cepat.
    *   Data tidak pernah meninggalkan perangkat pengguna (100% Offline).

*   **Interactive Dashboard**
    *   Aplikasi desktop cross-platform (dibangun dengan **Electron**).
    *   Visualisasi data sesi belajar menggunakan grafik interaktif.
    *   Antarmuka yang bersih dan minim distraksi.

*   **Automated Testing Pipeline**
    *   Infrastruktur CI/CD yang kokoh untuk menjamin stabilitas.
    *   Unit testing komprehensif untuk Backend (Pytest) dan Frontend (Jest).
    *   End-to-End testing menggunakan Playwright.

### 🔧 Persyaratan Sistem

*   **OS:** Windows 11 / Ubuntu 22.04 LTS
*   **CPU:** Intel Core i5 Gen 10 / AMD Ryzen 5 4000 series atau lebih baru
*   **RAM:** 16 GB
*   **GPU:** NVIDIA GTX 1650 (Disarankan untuk performa AI optimal)
*   **Webcam:** 720p

### 🐛 Known Issues

*   Deteksi Gaze mungkin kurang akurat pada kondisi pencahayaan rendah ekstrem.
*   Inisialisasi pertama kali mungkin memakan waktu hingga 30 detik pada mesin tanpa GPU dedicated.