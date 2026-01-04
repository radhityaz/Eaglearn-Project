const { _electron: electron, test, expect } = require('@playwright/test');
const path = require('path');

test('Simple launch test', async () => {
  console.log('Launching electron...');
  // Coba gunakan executable path eksplisit
  const electronPath = path.join(__dirname, '../../node_modules/electron/dist/electron.exe');
  console.log('Executable:', electronPath);
  
  const electronApp = await electron.launch({
    executablePath: electronPath,
    args: [path.join(__dirname, '../../main.js'), '--remote-debugging-port=9223'],
  });
  console.log('Electron launched');
  const appPath = await electronApp.evaluate(async ({ app }) => {
    return app.getAppPath();
  });
  console.log('App path:', appPath);
  await electronApp.close();
});