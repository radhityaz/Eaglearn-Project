// Figma-inspired Dashboard Renderer Script
// Handles all UI interactions and real-time updates

// Real-time session timer
let sessionStartTime = Date.now();
let sessionInterval;

function formatTime(milliseconds) {
  const seconds = Math.floor(milliseconds / 1000);
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;
  return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
}

function updateSessionTimer() {
  const elapsed = Date.now() - sessionStartTime;
  const timer = document.getElementById('session-timer');
  if (timer) {
    timer.textContent = formatTime(elapsed);
  }
}

// Start session timer
sessionInterval = setInterval(updateSessionTimer, 1000);

// Simulated real-time data updates
function generateRandomValue(min, max, isInt = false) {
  const value = Math.random() * (max - min) + min;
  return isInt ? Math.floor(value) : value.toFixed(1);
}

// Update KPI values with simulated data
function updateKPIValues() {
  // Engagement Score
  const engagementScore = document.querySelector('.kpi-card:nth-child(1) .number');
  if (engagementScore) {
    const currentValue = parseInt(engagementScore.textContent);
    const change = Math.random() > 0.7 ? Math.floor(Math.random() * 3) - 1 : 0;
    const newValue = Math.max(0, Math.min(100, currentValue + change));
    engagementScore.textContent = newValue;
  }

  // Stress Level
  const stressLevel = document.querySelector('.kpi-card:nth-child(2) .number');
  if (stressLevel) {
    const currentValue = parseInt(stressLevel.textContent);
    const change = Math.random() > 0.8 ? Math.floor(Math.random() * 5) - 2 : 0;
    const newValue = Math.max(0, Math.min(100, currentValue + change));
    stressLevel.textContent = newValue;
  }
}

// Update engagement chart with new data
function updateEngagementChart() {
  const bars = document.querySelectorAll('#engagement-chart .bar');
  
  // Shift existing bars to the left
  for (let i = 0; i < bars.length - 1; i++) {
    const nextHeight = bars[i + 1].style.height;
    const nextClass = bars[i + 1].className;
    bars[i].style.height = nextHeight;
    bars[i].className = nextClass;
  }
  
  // Add new bar at the end
  if (bars.length > 0) {
    const lastBar = bars[bars.length - 1];
    const randomHeight = generateRandomValue(30, 95, true) + '%';
    lastBar.style.height = randomHeight;
    
    const heightValue = parseInt(randomHeight);
    if (heightValue > 70) {
      lastBar.className = 'bar high';
    } else if (heightValue > 40) {
      lastBar.className = 'bar med';
    } else {
      lastBar.className = 'bar low';
    }
  }
}

// Update gaze position
function updateGazePosition() {
  const gazePos = document.getElementById('gaze-pos');
  if (gazePos && Math.random() > 0.7) {
    const positions = ['Center', 'Top-Left', 'Top-Right', 'Screen Edge', 'Off-Screen'];
    const randomPos = positions[Math.floor(Math.random() * positions.length)];
    gazePos.textContent = randomPos;
    
    const indicator = gazePos.nextElementSibling;
    if (indicator) {
      indicator.className = randomPos === 'Center' ? 'indicator good' : 
                           randomPos.includes('Screen') ? 'indicator warning' : 'indicator good';
    }
  }
}

// Update posture score
function updatePosture() {
  const posture = document.getElementById('posture');
  if (posture) {
    const currentValue = parseInt(posture.textContent);
    const change = Math.random() > 0.8 ? Math.floor(Math.random() * 5) - 2 : 0;
    const newValue = Math.max(60, Math.min(100, currentValue + change));
    posture.textContent = newValue;
    
    const changeElem = posture.nextElementSibling;
    if (changeElem && change !== 0) {
      changeElem.textContent = change > 0 ? `+${change}%` : `${change}%`;
      changeElem.className = change > 0 ? 'change positive' : 'change negative';
    }
  }
}

// Update stress indicators
function updateStressIndicators() {
  const stressBars = document.querySelectorAll('.stress-item .fill');
  stressBars.forEach(bar => {
    if (Math.random() > 0.6) {
      const width = generateRandomValue(20, 70, true) + '%';
      bar.style.width = width;
      
      const widthValue = parseInt(width);
      bar.className = widthValue < 35 ? 'fill low' :
                      widthValue < 60 ? 'fill med' : 'fill high';
    }
  });
}

// Update fatigue level
function updateFatigueLevel() {
  const fatigueValue = document.querySelector('.fatigue-value');
  const fatigueStatus = document.querySelector('.fatigue-status');
  
  if (fatigueValue && Math.random() > 0.8) {
    const currentValue = parseInt(fatigueValue.textContent);
    const change = Math.floor(Math.random() * 5) - 2;
    const newValue = Math.max(0, Math.min(100, currentValue + change));
    fatigueValue.textContent = newValue + '%';
    
    if (fatigueStatus) {
      if (newValue < 30) fatigueStatus.textContent = 'Low';
      else if (newValue < 60) fatigueStatus.textContent = 'Moderate';
      else fatigueStatus.textContent = 'High';
    }
    
    // Update fatigue alert
    const alertBox = document.getElementById('fatigue-alert');
    if (alertBox) {
      const alert = alertBox.querySelector('.alert');
      if (newValue > 70 && alert) {
        alert.textContent = 'High fatigue detected - Take a break now';
        alert.className = 'alert warning';
      } else if (newValue > 50 && alert) {
        alert.textContent = 'Consider a 5-minute break';
        alert.className = 'alert warning';
      } else if (alert) {
        alertBox.style.display = 'none';
      }
    }
  }
}

// Button click handlers
function startFocusSession() {
  console.log('Starting focus session...');
  
  // Reset session timer
  sessionStartTime = Date.now();
  
  // Update UI to show focus mode active
  const badge = document.querySelector('.badge');
  if (badge) {
    badge.textContent = 'Focus Mode';
    badge.className = 'badge good';
  }
  
  // Show notification
  showNotification('Focus session started', 'success');
}

function showReport() {
  console.log('Generating report...');
  showNotification('Report generation in progress...', 'info');
  
  // Simulate report generation
  setTimeout(() => {
    showNotification('Report ready for download', 'success');
  }, 2000);
}

function calibrateGaze() {
  console.log('Starting gaze calibration...');
  showNotification('Follow the dots on screen for calibration', 'info');
}

function closeCameraModal() {
  const modal = document.getElementById('camera-modal');
  if (modal) {
    modal.classList.add('hidden');
    
    // Stop camera stream
    const video = document.getElementById('camera-preview');
    if (video && video.srcObject) {
      video.srcObject.getTracks().forEach(track => track.stop());
      video.srcObject = null;
    }
  }
}

// Notification system
function showNotification(message, type = 'info') {
  // Create notification element
  const notification = document.createElement('div');
  notification.className = `notification ${type}`;
  notification.style.cssText = `
    position: fixed;
    top: 80px;
    right: 20px;
    padding: 16px 24px;
    background: ${type === 'success' ? 'var(--success)' : 
                  type === 'error' ? 'var(--danger)' : 'var(--primary)'};
    color: white;
    border-radius: 8px;
    font-size: 14px;
    font-weight: 600;
    z-index: 1001;
    animation: slideIn 0.3s ease;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  `;
  notification.textContent = message;
  
  // Add animation
  const style = document.createElement('style');
  style.textContent = `
    @keyframes slideIn {
      from {
        transform: translateX(100%);
        opacity: 0;
      }
      to {
        transform: translateX(0);
        opacity: 1;
      }
    }
  `;
  document.head.appendChild(style);
  
  document.body.appendChild(notification);
  
  // Remove after 3 seconds
  setTimeout(() => {
    notification.style.animation = 'slideOut 0.3s ease';
    setTimeout(() => {
      notification.remove();
    }, 300);
  }, 3000);
}

// Sidebar navigation
document.addEventListener('DOMContentLoaded', function() {
  const navItems = document.querySelectorAll('.nav-item');
  
  navItems.forEach(item => {
    item.addEventListener('click', function() {
      // Remove active from all items
      navItems.forEach(nav => nav.classList.remove('active'));
      // Add active to clicked item
      this.classList.add('active');
      
      // Show different dashboard views based on selection
      const title = this.getAttribute('title');
      console.log(`Switching to ${title} view`);
      showNotification(`${title} view loaded`, 'info');
    });
  });
  
  // Timeline tabs
  const tabs = document.querySelectorAll('.tab');
  tabs.forEach(tab => {
    tab.addEventListener('click', function() {
      tabs.forEach(t => t.classList.remove('active'));
      this.classList.add('active');
      
      const period = this.textContent;
      console.log(`Showing ${period} timeline`);
      updateTimelineView(period);
    });
  });
});

// Update timeline visualization
function updateTimelineView(period) {
  const timeBar = document.querySelector('.timeline-bar');
  const timeLabels = document.querySelector('.time-labels');
  
  if (!timeBar || !timeLabels) return;
  
  // Clear existing blocks
  timeBar.innerHTML = '';
  timeLabels.innerHTML = '';
  
  if (period === 'Today') {
    // Today view - hourly blocks
    const blocks = [
      { type: 'deep', width: '15%' },
      { type: 'regular', width: '10%' },
      { type: 'break', width: '5%' },
      { type: 'deep', width: '20%' },
      { type: 'break', width: '5%' },
      { type: 'regular', width: '15%' },
      { type: 'deep', width: '25%' },
      { type: 'break', width: '5%' }
    ];
    
    blocks.forEach(block => {
      const div = document.createElement('div');
      div.className = `time-block ${block.type}`;
      div.style.width = block.width;
      timeBar.appendChild(div);
    });
    
    ['9:00', '11:00', '1:00 PM', '3:00 PM', '5:00 PM'].forEach(label => {
      const span = document.createElement('span');
      span.textContent = label;
      timeLabels.appendChild(span);
    });
    
  } else if (period === 'Week') {
    // Week view - daily blocks
    const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
    days.forEach(() => {
      const div = document.createElement('div');
      const intensity = Math.random();
      div.className = `time-block ${intensity > 0.7 ? 'deep' : intensity > 0.4 ? 'regular' : 'break'}`;
      div.style.width = `${100 / 7}%`;
      timeBar.appendChild(div);
    });
    
    days.forEach(day => {
      const span = document.createElement('span');
      span.textContent = day;
      timeLabels.appendChild(span);
    });
    
  } else if (period === 'Month') {
    // Month view - weekly summary
    for (let i = 1; i <= 4; i++) {
      const div = document.createElement('div');
      const intensity = Math.random();
      div.className = `time-block ${intensity > 0.6 ? 'deep' : intensity > 0.3 ? 'regular' : 'break'}`;
      div.style.width = '25%';
      timeBar.appendChild(div);
    }
    
    ['Week 1', 'Week 2', 'Week 3', 'Week 4'].forEach(label => {
      const span = document.createElement('span');
      span.textContent = label;
      timeLabels.appendChild(span);
    });
  }
}

// Camera preview functionality
function openCameraModal() {
  const modal = document.getElementById('camera-modal');
  const video = document.getElementById('camera-preview');
  
  if (modal && video) {
    modal.classList.remove('hidden');
    
    // Request camera access
    navigator.mediaDevices.getUserMedia({ video: true })
      .then(stream => {
        video.srcObject = stream;
      })
      .catch(err => {
        console.error('Camera access denied:', err);
        showNotification('Camera access denied', 'error');
      });
  }
}

// Start periodic updates
setInterval(() => {
  updateKPIValues();
  updateEngagementChart();
  updateGazePosition();
  updatePosture();
  updateStressIndicators();
  updateFatigueLevel();
}, 5000); // Update every 5 seconds

// Initialize
console.log('Eaglearn Dashboard initialized with Figma-inspired design');
showNotification('Welcome to Eaglearn Analytics', 'info');