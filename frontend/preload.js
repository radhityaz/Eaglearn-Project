/**
 * Preload Script - Bridge between renderer and main process
 * Provides secure, limited API access to the renderer
 */

const { contextBridge, ipcRenderer } = require('electron');

// Expose protected APIs to the renderer process
contextBridge.exposeInMainWorld('eaglearnAPI', {
  // System information
  getSystemInfo: () => ipcRenderer.invoke('get-system-info'),
  
  // Backend communication
  sendToBackend: (message) => ipcRenderer.invoke('send-to-backend', message),
  
  // Settings
  onOpenSettings: (callback) => ipcRenderer.on('open-settings', callback),
  
  // Performance monitoring
  getMemoryUsage: () => process.memoryUsage(),
  
  // Version info
  versions: {
    node: process.versions.node,
    chrome: process.versions.chrome,
    electron: process.versions.electron
  }
});

// Resource monitoring utilities
contextBridge.exposeInMainWorld('performance', {
  // Get current resource usage
  getResourceUsage: () => {
    return {
      memory: process.memoryUsage(),
      cpuUsage: process.cpuUsage()
    };
  },
  
  // Request garbage collection (if exposed)
  requestGC: () => {
    if (global.gc) {
      global.gc();
      return true;
    }
    return false;
  }
});