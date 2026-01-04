/**
 * Eaglearn Desktop - Main Process
 * Optimized for low resource consumption
 */

if (process.env.ELECTRON_RUN_AS_NODE && !process.env.PLAYWRIGHT_TEST) {
  console.warn('[main] ELECTRON_RUN_AS_NODE detected, restarting...');
  const { spawn } = require('child_process');
  const electronPath = require('electron');
  const env = { ...process.env };
  delete env.ELECTRON_RUN_AS_NODE;
  
  const child = spawn(electronPath, ['.', ...process.argv.slice(2)], {
    cwd: __dirname,
    env,
    stdio: 'inherit'
  });
  
  child.on('close', (code) => process.exit(code));
  return;
}

const electron = require('electron');
const { app, BrowserWindow, ipcMain, Menu } = electron;
const path = require('path');

// DEBUG: Log startup args
console.log('[main] Startup args:', process.argv);
console.log('[main] Environment:', process.env);

const isDev = process.argv.includes('--dev');

// Resource optimization settings
app.commandLine.appendSwitch('disable-gpu-sandbox');
app.commandLine.appendSwitch('enable-accelerated-2d-canvas');
app.commandLine.appendSwitch('enable-gpu-rasterization');
app.commandLine.appendSwitch('disable-software-rasterizer');
app.commandLine.appendSwitch('max-old-space-size', '1024'); // Limit Node.js heap to 1GB

// Keep a global reference of the window object
let mainWindow;
let backendProcess;

/**
 * Create the main application window
 */
function createWindow() {
  // Create the browser window with optimized settings
  mainWindow = new BrowserWindow({
    width: 1600,
    height: 900,
    minWidth: 1400,
    minHeight: 800,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js'),
      backgroundThrottling: false, // Keep performance consistent
      webgl: true,
      experimentalFeatures: false
    },
    backgroundColor: '#1e1e1e',
    show: false, // Don't show until ready
    frame: true,
    titleBarStyle: 'default',
    icon: path.join(__dirname, 'assets', 'icon.png')
  });

  // Load the index.html
  mainWindow.loadFile('index.html');

  // Show window when ready
  mainWindow.once('ready-to-show', () => {
    mainWindow.maximize();
    mainWindow.show();
    
    // Set process priority to below normal on Windows
    if (process.platform === 'win32') {
      const { exec } = require('child_process');
      exec(`wmic process where ProcessId=${process.pid} call setpriority "below normal"`);
    }
  });

  // Open DevTools in development
  if (isDev) {
    mainWindow.webContents.openDevTools({ mode: 'detach' });
    
    // Enable live reload
    require('electron-reload')(__dirname, {
      electron: path.join(__dirname, 'node_modules', '.bin', 'electron'),
      hardResetMethod: 'exit'
    });
  }

  // Optimize garbage collection
  mainWindow.webContents.on('did-finish-load', () => {
    mainWindow.webContents.executeJavaScript('if (window.gc) window.gc();');
  });

  // Handle window closed
  mainWindow.on('closed', () => {
    mainWindow = null;
  });

  // Prevent navigation away from the app
  mainWindow.webContents.on('will-navigate', (event) => {
    event.preventDefault();
  });

  // Set up application menu
  setupMenu();
}

/**
 * Set up application menu
 */
function setupMenu() {
  const template = [
    {
      label: 'File',
      submenu: [
        {
          label: 'Settings',
          accelerator: 'CmdOrCtrl+,',
          click: () => {
            mainWindow.webContents.send('open-settings');
          }
        },
        { type: 'separator' },
        {
          label: 'Exit',
          accelerator: process.platform === 'darwin' ? 'Cmd+Q' : 'Ctrl+Q',
          click: () => {
            app.quit();
          }
        }
      ]
    },
    {
      label: 'View',
      submenu: [
        { role: 'reload' },
        { role: 'forcereload' },
        { type: 'separator' },
        { role: 'togglefullscreen' }
      ]
    }
  ];

  if (isDev) {
    template[1].submenu.push(
      { type: 'separator' },
      { role: 'toggledevtools' }
    );
  }

  const menu = Menu.buildFromTemplate(template);
  Menu.setApplicationMenu(menu);
}

/**
 * Start Python backend process
 */
function startBackend() {
  const { spawn } = require('child_process');
  const backendPath = path.join(__dirname, '..', 'backend', 'main.py');
  const projectRoot = path.join(__dirname, '..');
  
  // Start Python backend with resource limits
  backendProcess = spawn('python', [
    '-u', // Unbuffered output
    backendPath
  ], {
    env: {
      ...process.env,
      PYTHONPATH: projectRoot, // Set PYTHONPATH to project root
      PYTHONUNBUFFERED: '1',
      OMP_NUM_THREADS: '2', // Limit OpenMP threads
      MKL_NUM_THREADS: '2', // Limit MKL threads
      NUMEXPR_NUM_THREADS: '2' // Limit NumExpr threads
    }
  });

  backendProcess.stdout.on('data', (data) => {
    console.log(`Backend: ${data}`);
  });

  backendProcess.stderr.on('data', (data) => {
    console.error(`Backend Error: ${data}`);
  });

  backendProcess.on('close', (code) => {
    console.log(`Backend process exited with code ${code}`);
    backendProcess = null;
  });
}

/**
 * Stop Python backend process
 */
function stopBackend() {
  if (backendProcess) {
    backendProcess.kill('SIGTERM');
    backendProcess = null;
  }
}

// IPC Communication handlers
ipcMain.handle('get-system-info', async () => {
  const os = require('os');
  return {
    platform: process.platform,
    arch: process.arch,
    cpus: os.cpus().length,
    memory: os.totalmem(),
    freeMemory: os.freemem()
  };
});

ipcMain.handle('send-to-backend', async (event, message) => {
  // Implement backend communication
  // Using MessagePack for efficient serialization
  const msgpack = require('msgpack-lite');
  const packed = msgpack.encode(message);
  
  // Send to backend via IPC or HTTP
  // Return response
  return { status: 'ok', data: null };
});

// App event handlers
app.whenReady().then(() => {
  createWindow();
  
  // Start backend after a short delay
  setTimeout(() => {
    if (!isDev) { // Only auto-start in production
      startBackend();
    }
  }, 1000);
});

app.on('window-all-closed', () => {
  stopBackend();
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (mainWindow === null) {
    createWindow();
  }
});

app.on('before-quit', () => {
  stopBackend();
});

// Handle uncaught exceptions
process.on('uncaughtException', (error) => {
  console.error('Uncaught Exception:', error);
  // Log to file in production
});

process.on('unhandledRejection', (reason, promise) => {
  console.error('Unhandled Rejection at:', promise, 'reason:', reason);
  // Log to file in production
});

module.exports = { mainWindow };