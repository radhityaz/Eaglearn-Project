/**
 * Eaglearn Dashboard - Renderer Process
 * Handles UI interactions and updates
 */

// Performance monitoring interval
let monitoringInterval = null;
let sessionStartTime = Date.now();
let isMonitoring = false;

// Initialize dashboard when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    console.log('Eaglearn Dashboard Ready');
    
    // Initialize UI
    initializeUI();
    
    // Start resource monitoring
    startResourceMonitoring();
    
    // Start session timer
    startSessionTimer();
    
    // Setup event listeners
    setupEventListeners();
});

/**
 * Initialize UI components
 */
function initializeUI() {
    // Set initial states
    updateConnectionStatus('ready');
    
    // Initialize metrics with placeholder data
    updateMetric('gaze-focus', 'Centered');
    updateMetric('head-posture', 'Good');
    updateMetric('stress-level', '25');
    updateMetric('fatigue-score', '15');
    
    // Initialize progress bars
    updateProgressBar('stress-bar', 25);
    updateProgressBar('fatigue-bar', 15);
    
    // Simulated video preview status
    updatePreviewStatus(false);
}

/**
 * Setup event listeners
 */
function setupEventListeners() {
    // Camera preview toggle
    const togglePreviewBtn = document.getElementById('toggle-preview');
    if (togglePreviewBtn) {
        togglePreviewBtn.addEventListener('click', toggleCameraPreview);
    }
    
    // Calibrate button
    const calibrateBtn = document.getElementById('calibrate-btn');
    if (calibrateBtn) {
        calibrateBtn.addEventListener('click', startCalibration);
    }
    
    // Pause monitoring
    const pauseBtn = document.getElementById('pause-monitoring');
    if (pauseBtn) {
        pauseBtn.addEventListener('click', toggleMonitoring);
    }
    
    // Settings modal
    eaglearnAPI?.onOpenSettings(() => {
        showSettingsModal();
    });
    
    // Settings buttons
    const saveSettingsBtn = document.getElementById('save-settings');
    if (saveSettingsBtn) {
        saveSettingsBtn.addEventListener('click', saveSettings);
    }
    
    const closeSettingsBtn = document.getElementById('close-settings');
    if (closeSettingsBtn) {
        closeSettingsBtn.addEventListener('click', hideSettingsModal);
    }
}

/**
 * Start resource monitoring
 */
async function startResourceMonitoring() {
    // Update every 2 seconds
    setInterval(async () => {
        if (window.performance) {
            // Get resource usage from preload
            const resources = window.performance.getResourceUsage?.() || {
                memory: { rss: 0 },
                cpuUsage: { percentCPUUsage: 0 }
            };
            
            // Simulate CPU usage (since real API might not be available)
            const cpuUsage = Math.random() * 10 + 5; // 5-15%
            const memoryMB = Math.round(performance.memory?.usedJSHeapSize / 1024 / 1024) || 
                            Math.round(100 + Math.random() * 50);
            
            // Update UI
            updateResourceDisplay(cpuUsage, memoryMB);
            
            // Simulate metrics updates
            if (isMonitoring) {
                updateSimulatedMetrics();
            }
        }
    }, 2000);
}

/**
 * Update resource display
 */
function updateResourceDisplay(cpu, memory) {
    const cpuElement = document.getElementById('cpu-usage');
    const ramElement = document.getElementById('ram-usage');
    
    if (cpuElement) cpuElement.textContent = cpu.toFixed(1);
    if (ramElement) ramElement.textContent = memory;
}

/**
 * Update simulated metrics (for demo)
 */
function updateSimulatedMetrics() {
    // Simulate gaze focus changes
    const gazeStates = ['Left', 'Center', 'Right', 'On-Screen'];
    const randomGaze = gazeStates[Math.floor(Math.random() * gazeStates.length)];
    updateMetric('gaze-focus', randomGaze);
    
    // Simulate posture
    const postureStates = ['Good', 'Slouching', 'Leaning'];
    const randomPosture = postureStates[Math.floor(Math.random() * postureStates.length)];
    updateMetric('head-posture', randomPosture);
    
    // Simulate stress (gradual increase)
    const currentStress = parseInt(document.getElementById('stress-level')?.textContent || 25);
    const newStress = Math.min(100, currentStress + Math.random() * 5 - 2);
    updateMetric('stress-level', newStress.toFixed(0));
    updateProgressBar('stress-bar', newStress);
    
    // Simulate fatigue (gradual increase)
    const currentFatigue = parseInt(document.getElementById('fatigue-score')?.textContent || 15);
    const newFatigue = Math.min(100, currentFatigue + Math.random() * 3 - 1);
    updateMetric('fatigue-score', newFatigue.toFixed(0));
    updateProgressBar('fatigue-bar', newFatigue);
    
    // Update break pattern visualization
    updateBreakPattern();
}

/**
 * Start session timer
 */
function startSessionTimer() {
    setInterval(() => {
        const elapsed = Date.now() - sessionStartTime;
        const hours = Math.floor(elapsed / 3600000);
        const minutes = Math.floor((elapsed % 3600000) / 60000);
        const seconds = Math.floor((elapsed % 60000) / 1000);
        
        const timeStr = `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
        
        const timerElement = document.getElementById('session-time');
        if (timerElement) {
            timerElement.textContent = timeStr;
        }
        
        // Update on-task and break time (simulated)
        const onTaskPercent = 0.75 + Math.random() * 0.1;
        const onTaskTime = Math.floor(elapsed * onTaskPercent / 60000);
        const breakTime = Math.floor(elapsed * (1 - onTaskPercent) / 60000);
        
        const onTaskElement = document.getElementById('on-task-time');
        const breakElement = document.getElementById('break-time');
        
        if (onTaskElement) onTaskElement.textContent = `${onTaskTime}min`;
        if (breakElement) breakElement.textContent = `${breakTime}min`;
    }, 1000);
}

/**
 * Toggle camera preview
 */
function toggleCameraPreview() {
    const video = document.getElementById('camera-preview');
    const button = document.getElementById('toggle-preview');
    
    if (video && button) {
        if (video.classList.contains('active')) {
            // Stop preview
            video.classList.remove('active');
            button.textContent = 'Show Preview';
            
            // Stop video stream
            if (video.srcObject) {
                video.srcObject.getTracks().forEach(track => track.stop());
                video.srcObject = null;
            }
        } else {
            // Start preview
            navigator.mediaDevices.getUserMedia({ 
                video: { 
                    width: 1280, 
                    height: 720,
                    facingMode: 'user'
                } 
            })
            .then(stream => {
                video.srcObject = stream;
                video.classList.add('active');
                button.textContent = 'Hide Preview';
            })
            .catch(err => {
                console.error('Camera access error:', err);
                alert('Could not access camera. Please check permissions.');
            });
        }
    }
}

/**
 * Update preview status
 */
function updatePreviewStatus(isActive) {
    const button = document.getElementById('toggle-preview');
    if (button) {
        button.textContent = isActive ? 'Hide Preview' : 'Show Preview';
    }
}

/**
 * Start calibration
 */
function startCalibration() {
    alert('Calibration would start here. Look at the dots on screen to calibrate gaze tracking.');
    updateConnectionStatus('calibrating');
    
    // Simulate calibration completion
    setTimeout(() => {
        updateConnectionStatus('ready');
        alert('Calibration complete!');
    }, 3000);
}

/**
 * Toggle monitoring
 */
function toggleMonitoring() {
    const button = document.getElementById('pause-monitoring');
    isMonitoring = !isMonitoring;
    
    if (button) {
        button.textContent = isMonitoring ? 'Pause' : 'Resume';
    }
    
    updateConnectionStatus(isMonitoring ? 'monitoring' : 'paused');
}

/**
 * Update connection status
 */
function updateConnectionStatus(status) {
    const statusElement = document.getElementById('connection-status');
    if (statusElement) {
        const dot = statusElement.querySelector('.dot');
        
        switch(status) {
            case 'ready':
                statusElement.innerHTML = '<span class="dot"></span> System Ready';
                break;
            case 'monitoring':
                statusElement.innerHTML = '<span class="dot active"></span> Monitoring Active';
                break;
            case 'paused':
                statusElement.innerHTML = '<span class="dot paused"></span> Monitoring Paused';
                break;
            case 'calibrating':
                statusElement.innerHTML = '<span class="dot calibrating"></span> Calibrating...';
                break;
            default:
                statusElement.innerHTML = '<span class="dot"></span> ' + status;
        }
    }
}

/**
 * Update a metric value
 */
function updateMetric(id, value) {
    const element = document.getElementById(id);
    if (element) {
        element.textContent = value;
    }
}

/**
 * Update progress bar
 */
function updateProgressBar(id, percentage) {
    const bar = document.getElementById(id);
    if (bar) {
        bar.style.width = `${Math.min(100, Math.max(0, percentage))}%`;
        
        // Change color based on value
        if (percentage < 30) {
            bar.style.background = 'var(--accent-primary)';
        } else if (percentage < 70) {
            bar.style.background = 'var(--accent-warning)';
        } else {
            bar.style.background = 'var(--accent-danger)';
        }
    }
}

/**
 * Update break pattern visualization
 */
function updateBreakPattern() {
    const container = document.getElementById('pattern-visualization');
    if (container && Math.random() > 0.9) {
        // Simple visualization
        const pattern = ['Work', 'Work', 'Work', 'Break', 'Work', 'Work', 'Break'];
        const html = pattern.map(p => 
            `<span style="display:inline-block; padding:2px 8px; margin:2px; 
                         background:${p === 'Work' ? '#4CAF50' : '#FFC107'}; 
                         border-radius:4px; font-size:12px;">${p}</span>`
        ).join('');
        container.innerHTML = html;
    }
}

/**
 * Show settings modal
 */
function showSettingsModal() {
    const modal = document.getElementById('settings-modal');
    if (modal) {
        modal.classList.remove('hidden');
    }
}

/**
 * Hide settings modal
 */
function hideSettingsModal() {
    const modal = document.getElementById('settings-modal');
    if (modal) {
        modal.classList.add('hidden');
    }
}

/**
 * Save settings
 */
function saveSettings() {
    // Get settings values
    const settings = {
        enableGaze: document.getElementById('enable-gaze')?.checked,
        enableAudio: document.getElementById('enable-audio')?.checked,
        enableProductivity: document.getElementById('enable-productivity')?.checked,
        cameraResolution: document.getElementById('camera-resolution')?.value,
        processingFps: document.getElementById('processing-fps')?.value
    };
    
    console.log('Saving settings:', settings);
    
    // Send to backend (when connected)
    if (window.eaglearnAPI) {
        eaglearnAPI.sendToBackend({
            type: 'UPDATE_SETTINGS',
            settings: settings
        });
    }
    
    hideSettingsModal();
    
    // Show confirmation
    updateConnectionStatus('Settings saved');
    setTimeout(() => updateConnectionStatus('ready'), 2000);
}

// Log that renderer is loaded
console.log('Eaglearn Renderer Loaded');
console.log('Available APIs:', {
    eaglearnAPI: typeof window.eaglearnAPI !== 'undefined',
    performance: typeof window.performance !== 'undefined'
});