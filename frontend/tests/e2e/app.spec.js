const { _electron: electron, test, expect } = require('@playwright/test');
const path = require('path');


test('Alur Kalibrasi dan Mulai Sesi', async () => {
  // Gunakan wrapper script untuk mengatasi masalah port 0
  const electronPath = path.join(__dirname, '../../electron-wrapper.cmd');
  
  const electronApp = await electron.launch({
    executablePath: electronPath,
    args: [path.join(__dirname, '../../main.js')],
    env: {
      ...process.env,
      PLAYWRIGHT_TEST: '1',
      ELECTRON_ENABLE_LOGGING: 'true'
    }
  });
  
  const window = await electronApp.firstWindow();

  // Tunggu aplikasi siap
  await window.locator('.app-shell').waitFor();

  // 1. Buka Kalibrasi
  await window.click('#open-calibration-btn');
  const modal = window.locator('#calibration-modal');
  await expect(modal).toBeVisible();

  // 2. Mulai Kalibrasi
  // Klik tombol Mulai
  await window.click('#calibration-action[data-step="start"]');
  
  // 3. Verifikasi Kalibrasi Berhasil
  // Menunggu tombol berubah menjadi 'Tutup' (indikasi sukses dari renderer.js)
  // Timeout diperpanjang karena melibatkan API call
  const closeButton = window.locator('#calibration-action[data-step="close"]');
  await expect(closeButton).toBeVisible({ timeout: 15000 });
  await expect(closeButton).toHaveText('Tutup');

  // 4. Tutup Modal
  await closeButton.click();
  await expect(modal).toBeHidden();

  // 5. Mulai Sesi
  await window.click('#start-session-btn');

  // 6. Verifikasi Sesi Berjalan
  // Tombol Stop harusnya enable
  const stopBtn = window.locator('#stop-session-btn');
  await expect(stopBtn).toBeEnabled({ timeout: 10000 });
  
  // Status harus berubah
  const statusBadge = window.locator('#session-status');
  await expect(statusBadge).toHaveText('Sesi aktif');

  await electronApp.close();
});