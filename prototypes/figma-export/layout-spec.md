# Dashboard Desktop Layout Spec  
_Label: EXPLORATORY (Throwaway)_  
_Source: Figma Dev Mode frame `30` (node `1:5`), exported 2025-10-04_

## 1. Kanvas & Grid

| Elemen | Node | Posisi (x, y) | Ukuran (W × H) | Padding / Gap | Catatan |
| --- | --- | --- | --- | --- | --- |
| Frame utama | 1:5 | (0, 0) | 1440 × 900 | Border 2px, radius 10px | Basis ukuran target desktop (≥1440px). |
| Margin internal | — | — | — | Top 60px (header), kiri sidebar 62px | Elemen konten dimulai setelah header & rail. |
| Grid implisit | — | — | 1338 × 840 (konten utama) | Kolom: 3 kartu KPI (435.33px), gap 16–25px | Tidak ada grid Figma eksplisit; gunakan ukuran komponen sebagai referensi. |

**Breakpoint**: Hanya varian desktop (1440px). Varian mobile berada pada frame lain (lihat node `30` sibling). Rekomendasi: tetapkan breakpoint utama di ≥1280px untuk fidelitas 95%+.

## 2. Header / Top Bar

| Elemen | Node | Posisi (x, y) | Ukuran (W × H) | Padding / Gap | Catatan |
| --- | --- | --- | --- | --- | --- |
| Top bar container | 1:6 | (-0.18, -0.45) | 1440 × 60 | Padding 10px, border 2px | Border hitam 2px, background transparan. |
| Logo + brand | 1:7 | (10, 10) | 196 × 40 | Gap logo-teks 20px | Gunakan ikon `topbar-logo.svg`, label `Lorem ipsum` (Inter 22px / Medium). |
| User cluster | 1:11 | (1259, 18) | 171 × 24 | Gap antar grup 12px | User name `Martina Wolna`, indicator `NO` masing-masing 24px ikon segitiga. |

## 3. Sidebar Icon Rail

| Elemen | Node | Posisi (x, y) | Ukuran (W × H) | Padding / Gap | Catatan |
| --- | --- | --- | --- | --- | --- |
| Rail container | 1:22 | (0.11, 59.55) | 62 × 840 | Padding kiri 8px, kanan 18px, vertikal 20px | Background putih, border 2px. |
| Ikon 1 (Star) | 1:23 | (8, 20) | 36 × 42.98 | Gap antar ikon 30px (44px tinggi) | Gunakan aset `sidebar-icon-01.svg` dst. Semua ikon 36 × 44 ± (21–24px konten). |
| Ikon terakhir | 1:38 | (8, 394.29) | 36 × 41.32 | — | Delapan ikon total; ikon ke-5–8 memiliki tinggi 41.32px. |

## 4. Kartu KPI Atas

| Elemen | Node | Posisi (x, y) | Ukuran (W × H) | Padding / Gap | Catatan |
| --- | --- | --- | --- | --- | --- |
| Container baris KPI | 1:41 | (20, 20) | 1338 × 87 | Gap antar kartu 25px | Empat kartu berbagi tinggi 87px. |
| KPI card (contoh) | 1:42 | (0, 0) | 315.75 × 87 | Padding 20px | Background putih, border 2px, radius 25px. |
| Label KPI | 1:44 | (0, 0) | 105 × 17 | — | Inter 14px / Medium, uppercase (`--typography-label-sidebar`). |
| Nilai KPI | 1:46 | (0, 23) | 21 × 19 | — | Inter 16px / SemiBold, uppercase (`--typography-heading-metric`). |
| Delta cluster | 1:47 | (191.75, 0) | 84 × 24 | Gap ikon 24px | Ikon panah `metric-arrow.svg`, delta 16px / Medium. |

## 5. Panel Konten Utama (Regions)

Terdapat tiga kolom (Region 1, 2, 3) dengan struktur seragam. Data berikut berlaku untuk tiap panel.

| Elemen | Node (Region 1) | Posisi relatif | Ukuran (W × H) | Padding / Gap | Catatan |
| --- | --- | --- | --- | --- | --- |
| Panel container | 1:83 | (0, 0) | 435.33 × 693 | Padding 20px (horizontal), 30px (top) | Border 2px, radius 30px. |
| Judul region | 1:84 | (20, 30) | 89 × 27 | — | Inter 22px / Medium. |
| KPI grup utama | 1:86 | (20, 73.63) | 395.33 × 45 | Gap antar blok 21px vertikal | Label 12px uppercase, value 16px uppercase. |
| Legend progress | 1:95 | (20, 135.25) | 395.33 × 43 | Gap label 8px, radius progress 14px | Warna: `#ccc5b9` dan `#fffcf2`, border 2px. |
| Subcard duo | 1:106 | (20, 194.88) | 395.33 × 65 | Two columns 191.67px | Background `#fffcf2` untuk positif, `#ccc5b9` untuk neutral. Radius 15px. |
| List KPI tambahan | 1:148–1:172 | y ≥ 358 | Lebar 395.33 × tinggi 60–65 | Padding 20px horizontal, 10px vertical | Konsisten tipografi & border. |

**Spacing antar panel**: 16px horizontal antar kolom (node 1:82). 20px padding luar.

## 6. Tipografi & Token Referensi

Gunakan token yang tersimpan di [`tokens.json`](prototypes/figma-export/tokens.json:1) untuk konsistensi Inter weight & transform.  
Semua border 2px solid hitam (`--color-border-strong`). Variasi background: lihat section colors pada file token.

## 7. Ikon & Aset

Seluruh ikon diekspor ke `prototypes/figma-export/icons/`:

- `topbar-logo.svg`, `topbar-indicator.svg`
- `sidebar-icon-01.svg` … `sidebar-icon-08.svg`
- `metric-arrow.svg`, `legend-in.svg`, `legend-out.svg`

Gunakan `legend-*.svg` sebagai bullet progress legend, `metric-arrow.svg` untuk panah delta (flip secara CSS untuk arah turun).

## 8. Ketergantungan & Kendala

- **Screenshot**: API `get_screenshot` untuk node `1:5` tidak mengembalikan data (No response). Dokumentasikan kebutuhan screenshot manual sebagai tindak lanjut.
- **Shadows**: Tidak terdeteksi shadow (penggunaan border kuat menggantikan elevasi).
- **Grid**: Frame tidak memakai grid layout Figma; gunakan ukuran tabel di atas sebagai sumber utama.

## 9. Rencana Evaluasi Lanjutan

- Validasi ulang nilai warna & ukuran melalui inspeksi langsung di Figma saat implementasi UI (target fidelitas ≥95%).
- Tambahkan mapping varian mobile (node lain) sebelum adaptasi responsif.
- Kumpulkan evidence lintas mode: setelah UI diimplementasikan, verifikasi via capture & overlay terhadap Figma untuk memenuhi prinsip evidence-driven.