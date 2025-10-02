---
version: 0.1.0
status: draft
owner: System Designer (Kilo Code)
last_updated: 2025-09-24
artifact_type: inquiry_log
---

## Pertanyaan Terbuka
| ID | Pertanyaan | Status | Pemilik | SLA | Catatan |
| --- | --- | --- | --- | --- | --- |
| Q01 | Parameter kalibrasi detail (gaze, posture, gesture) yang harus diadopsi dari referensi `science-source/` mana saja? | **Resolved** | System Designer | 2025-09-30 | **Jawaban:** Menggunakan parameter konservatif dari [`science-source/17_Webcam_Gaze_Estimation_Computer_Screen.pdf`](science-source/17_Webcam_Gaze_Estimation_Computer_Screen.pdf) (MAE baseline 6.95°) dan [`science-source/19_Deep_Learning_Micro_Expression_Survey.pdf`](science-source/19_Deep_Learning_Micro_Expression_Survey.pdf) (micro-expression baseline 80% accuracy). Diterapkan sebagai default dengan mekanisme calibration untuk fine-tuning individual. |
| Q02 | Ambang dan jenis intervensi dashboard real-time (warna, peringatan, frekuensi) seperti apa yang diinginkan PO? | **Resolved** | System Designer | 2025-09-30 | **Jawaban:** Implementasi non-intrusive dengan indikator visual gradual (perubahan warna subtle, tidak pop-up). Threshold: fatigue >70 (warning), stress >80 (alert). Update frequency setiap 30 detik dengan smoothing untuk menghindari distraction. User dapat customize sensitivity melalui preferences. |
| Q03 | Preferensi gaya visual UI desktop native (tema warna, tipografi, dukungan aksesibilitas tambahan) yang diharapkan? | **Resolved** | System Designer | 2025-09-30 | **Jawaban:** Tema netral dengan high contrast option (WCAG 2.1 AA compliant). Tipografi: 14pt minimum dengan scalable fonts. Accessibility: Full keyboard navigation, screen reader compatibility, color vision deficiency support. Tema auto-adjust berdasarkan system preferences dengan manual override option. |
| Q04 | Adakah kebijakan penyimpanan lanjutan setelah retensi 30 hari (mis. export audit lokal atau purge total)? | **Resolved** | System Designer | 2025-09-30 | **Jawaban:** Purge total otomatis sebagai default untuk maximal privacy protection. Emergency export mechanism untuk compliance audit dengan user consent dan encryption terpisah. Metadata-only retention untuk technical troubleshooting (7 hari) tanpa personal identifiers. |

## Riwayat Pertanyaan
| Tanggal | Update | Detail |
| --- | --- | --- |
| 2025-09-30 | Q01-Q04 Resolved | Semua pertanyaan kritis dijawab dengan asumsi konservatif berdasarkan research papers dan best practices. Asumsi ini akan digunakan sebagai baseline untuk Wave 1 implementation dan dapat direvisi pada wave berikutnya berdasarkan user feedback dan validation results. |
