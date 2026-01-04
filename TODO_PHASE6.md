# Phase 6: Release & Documentation

Fase ini berfokus pada persiapan rilis versi 1.0.0, finalisasi dokumentasi, dan packaging aplikasi untuk distribusi.

## 📦 Packaging & Release
- [ ] **Build Installer**: Konfigurasi `electron-builder` untuk membuat installer Windows (.exe) dan opsional macOS (.dmg).
- [ ] **Signing**: (Opsional untuk Wave 1) Setup code signing jika sertifikat tersedia.
- [ ] **Release Assets**: Pastikan semua aset (ikon, splash screen) sudah siap dalam build produksi.

## 📄 Documentation
- [ ] **Finalisasi README.md**:
    - [ ] Perbarui instruksi instalasi (pip, npm).
    - [ ] Perbarui instruksi cara menjalankan aplikasi (prod vs dev).
    - [ ] Pastikan daftar Tech Stack akurat.
- [ ] **Buat RELEASE_NOTES.md**:
    - [ ] Draft rilis v1.0.0.
    - [ ] Highlight fitur utama: Gaze Tracking, Stress Detection, Productivity Metrics.
    - [ ] Known issues & limitations.
- [ ] **Technical Docs Update**:
    - [ ] Review `PHASE_0_ARCHITECTURE.md` apakah masih relevan dengan implementasi akhir.
    - [ ] Pastikan dokumentasi API di `docs/` (jika ada) atau inline comments sinkron dengan endpoint terakhir.

## 🧹 Cleanup & Final Checks
- [ ] **Code Cleanup**: Hapus komentar TODO yang sudah usang atau kode debug yang tidak perlu (misal: `print` statements berlebih).
- [ ] **Environment Check**: Pastikan `.env.example` mencakup semua variabel konfigurasi terbaru.
- [ ] **License**: Pastikan file LICENSE sudah benar.

## 🚀 Launch
- [ ] Tag versi `v1.0.0` di git.
- [ ] Buat Release di GitHub dengan melampirkan binary installer.