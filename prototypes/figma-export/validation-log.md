id: "validation-diff-dashboard-desktop-f3"
title: "Dashboard Desktop Validation Log"
version: "0.1.0"
owner: "UI Audit"
status: "draft"
updated_at: "2025-10-06"
tags: ["proto","finding","spec"]
links:
  - {type:"doc", target:"prototypes/figma-export/layout-spec.md"}
  - {type:"doc", target:"frontend/index.html"}
  - {type:"doc", target:"frontend/styles-figma.css"}
  - {type:"doc", target:"frontend/renderer-figma.js"}
assumptions: ["Tidak ada screenshot Figma node 1:5; pembandingan dilakukan melalui layout-spec.md dan artefak implementasi.", "UI diuji pada resolusi 1440×900 tanpa scaling tambahan."]
risks: ["severity:Med desc:Fidelity terhadap Figma dapat turun <95% jika deviasi tidak ditindak."]
privacy_level: "anon"
consent_ref: "NA"
retention_policy: "NA"
scrub_plan: "NA"
language: "id"

## Ringkasan Konteks & Metodologi

- Membandingkan struktur dan styling pada [`index.html`](frontend/index.html:1), [`styles-figma.css`](frontend/styles-figma.css:1), [`styles-tokens.css`](frontend/styles-tokens.css:1), dan [`renderer-figma.js`](frontend/renderer-figma.js:1) terhadap spesifikasi Figma di [`layout-spec.md`](prototypes/figma-export/layout-spec.md:1).
- Memetakan deviasi layout, token warna/spacing, serta perilaku skrip untuk memastikan fidelitas ≥95% sesuai target EXPLORATORY F3.
- Referensi token resmi bersumber dari [`tokens.json`](prototypes/figma-export/tokens.json:1); temuan menggunakan bukti baris silang untuk menjaga traceability.

## Temuan per Area

| Finding-ID | Deskripsi deviasi | Evidence (referensi baris Figma spec vs file implementasi) | Severity | Rekomendasi perbaikan | Link/ID terkait |
| --- | --- | --- | --- | --- | --- |
| FND-0001 | Header top bar memuat modul timer & status tambahan serta border hanya di sisi bawah; padding horizontal 20px menyebabkan tinggi >60px yang melenceng dari komposisi Figma. | [`layout-spec.md`](prototypes/figma-export/layout-spec.md:17)<br>[`index.html`](frontend/index.html:21)<br>[`styles-figma.css`](frontend/styles-figma.css:77) | Medium | Kembalikan komposisi header ke logo + user cluster saja, tetapkan padding 10px dan border 2px mengelilingi container agar tinggi konsisten 60px. | layout-spec §2 |
| FND-0002 | Sidebar rail diimplementasikan dengan label teks dan gap 25px, sementara spesifikasi meminta ikon-only dengan padding kanan 18px dan gap 30px. | [`layout-spec.md`](prototypes/figma-export/layout-spec.md:23)<br>[`index.html`](frontend/index.html:45)<br>[`styles-figma.css`](frontend/styles-figma.css:173) | Medium | Hilangkan label teks atau jadikan opsi terpisah, sesuaikan padding (8px kiri, 18px kanan) dan gap vertikal 30px untuk menjaga rasio ikon. | layout-spec §3 |
| FND-0003 | Deret KPI atas menggunakan grid 1fr tanpa lebar pasti 315.75px sehingga kartu melebar > spesifikasi ketika viewport >1338px. | [`layout-spec.md`](prototypes/figma-export/layout-spec.md:35)<br>[`styles-figma.css`](frontend/styles-figma.css:225) | Medium | Kunci lebar KPI card sesuai ukuran Figma (mis. 315.75px) atau set kolom menggunakan `grid-template-columns: repeat(4, 315.75px)` dengan gap 25px. | layout-spec §4 |
| FND-0004 | Panel region memakai `repeat(3, 1fr)` tanpa lebar 435.33px sehingga spacing horizontal 16px tidak terjaga ketika area utama berubah; list tambahan juga mengikuti lebar dinamis. | [`layout-spec.md`](prototypes/figma-export/layout-spec.md:45)<br>[`styles-figma.css`](frontend/styles-figma.css:313) | Medium | Terapkan lebar tetap per panel (435.33px) dan gunakan container dengan scroll horizontal jika diperlukan agar proporsi mengikuti layout Figma. | layout-spec §5 |
| FND-0005 | Token warna sekunder/tersier dan warna timeline menggunakan nilai RGBA manual yang tidak ada di `tokens.json`, menurunkan traceability (mis. `rgba(204, 197, 185, 0.6)`). | [`tokens.json`](prototypes/figma-export/tokens.json:10)<br>[`styles-tokens.css`](frontend/styles-tokens.css:16)<br>[`styles-figma.css`](frontend/styles-figma.css:532) | Medium | Konsolidasikan penggunaan warna ke token resmi (`--color-surface-neutral`, `--color-surface-subtle`) atau ajukan entry token baru melalui CR agar tidak ada nilai hard-coded. | tokens.json |
| FND-0006 | `renderer-figma.js` masih menjalankan timer sesi dan binding tombol (start focus/report), berlawanan dengan kebutuhan layout statis untuk validasi parity. | [`layout-spec.md`](prototypes/figma-export/layout-spec.md:5)<br>[`renderer-figma.js`](frontend/renderer-figma.js:65)<br>[`index.html`](frontend/index.html:475) | High | Matikan logika interaktif (timer, toggle state) atau pindahkan ke mode non-figma agar layar validasi tetap statis selama audit. | CR-FIGMA-STATIC (disarankan) |

## Dependensi Tooling & Catatan

- Screenshot Figma node `1:5` masih tidak tersedia (`get_screenshot` gagal) sehingga verifikasi visual bergantung pada inspeksi manual di Dev Mode; diperlukan akses Figma Dev Mode saat koreksi.
- Chrome DevTools atau figma-dev-mode direkomendasikan untuk overlay ukuran saat menyesuaikan lebar kartu/panel.
- Semua temuan berada dalam konteks artefak EXPLORATORY — perubahan kode harus melalui CR sebelum dipromosikan ke jalur EVOLUTIONARY.