# Eaglearn Development Guide

## 🚀 Quick Start

### Prerequisites
- **Python 3.11.x** (you have 3.11.9 ✅)
- **Node.js 18+** 
- **Git** (installed ✅)
- **Webcam** for testing computer vision features
- **Windows 11** or **Ubuntu 22.04 LTS**

### Step 1: Clone and Setup

```bash
# You've already done this ✅
cd D:\Eaglearn-Project

# Create Python virtual environment
python -m venv venv

# Activate virtual environment (Windows)
venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt
```

### Step 2: Install Node.js Dependencies

```bash
# Navigate to frontend
cd frontend

# Install Node packages
npm install

# Return to project root
cd ..
```

### Step 3: Test the Webcam Capture Prototype

```bash
# Make sure virtual environment is activated
venv\Scripts\activate

# Run the throwaway prototype
python prototypes\webcam_capture_poc.py
```

**Expected Results:**
- CPU usage: <15%
- RAM usage: <300MB
- Frame latency: <100ms
- Dynamic resolution switching should work

### Step 4: Run the Electron Frontend

```bash
cd frontend
npm start
```

The Electron app will launch showing the dashboard UI.

## 📊 Current Implementation Status

### ✅ Completed
1. **Git Repository** - Initialized with proper .gitignore
2. **Project Structure** - Frontend (Electron) + Backend (Python) architecture
3. **Development Environment** - Package configurations ready
4. **Webcam Capture PoC** - Throwaway prototype for testing

### 🔄 In Progress
- Lightweight gaze estimation with MediaPipe
- Audio stress analysis pipeline
- Resource governor implementation

### 📝 To Do
- Complete backend API server setup
- Implement IPC communication between frontend and backend
- Add gaze estimation module
- Integrate audio analysis
- Performance benchmarking suite

## 🧪 Testing Prototypes

### Webcam Capture Test
```bash
python prototypes\webcam_capture_poc.py
```
- Press 'q' to quit
- Press 'r' to reset metrics
- Watch for automatic resolution switching

### Expected Performance Metrics
| Component | Target | Current Status |
|-----------|--------|----------------|
| CPU Usage | <15% | To be tested |
| GPU Usage | <20% | To be tested |
| RAM Usage | <300MB | To be tested |
| Latency | <100ms | To be tested |

## 🏗️ Architecture Overview

```
Eaglearn-Project/
├── frontend/           # Electron Desktop App
│   ├── main.js        # Main process (resource optimized)
│   ├── preload.js     # Secure IPC bridge
│   ├── index.html     # Dashboard UI
│   └── styles.css     # GPU-accelerated styles
│
├── backend/           # Python AI Processing
│   ├── main.py        # FastAPI server with resource governor
│   ├── core/
│   │   ├── vision/    # Computer vision modules
│   │   ├── audio/     # Audio analysis modules
│   │   └── tracking/  # Productivity tracking
│   ├── api/           # API endpoints
│   └── utils/         # Shared utilities
│
└── prototypes/        # Test implementations
    └── webcam_capture_poc.py  # THROWAWAY: Performance testing
```

## 🔧 Development Workflow

### 1. Evidence-Driven Prototyping
Following your RULE document:
- **Throwaway Prototypes**: For exploration (current webcam PoC)
- **Evolutionary Prototypes**: For production components

### 2. Resource Constraints
Always consider:
- **CPU**: Max 40% usage (leaving 60% for user tasks)
- **GPU**: Max 50% usage
- **RAM**: Max 2GB for entire application
- **Process Priority**: Always "Below Normal"

### 3. Git Workflow
```bash
# Check status
git status

# Create feature branch
git checkout -b feature/component-name

# Commit with clear messages
git add .
git commit -m "feat: Description following conventional commits"

# Push to remote (when configured)
git push origin feature/component-name
```

## 🎯 Next Immediate Steps

1. **Test Webcam Prototype**
   ```bash
   python prototypes\webcam_capture_poc.py
   ```
   Document the performance results.

2. **Install Node Dependencies**
   ```bash
   cd frontend
   npm install
   ```

3. **Create Backend Supporting Files**
   - `backend/config/settings.py`
   - `backend/utils/resource_governor.py`
   - `backend/api/server.py`

4. **Run Initial Integration Test**
   Once dependencies are installed, test the frontend-backend communication.

## 📈 Performance Optimization Tips

1. **Python Optimization**
   - Use `opencv-python-headless` (no GUI overhead)
   - Implement lazy loading for heavy modules
   - Use process pooling for parallel tasks
   - Consider ONNX Runtime over TensorFlow

2. **Electron Optimization**
   - Disable unnecessary Chromium features
   - Use GPU acceleration for CSS animations
   - Implement virtual scrolling for large datasets
   - Debounce UI updates

3. **System-Wide**
   - Set process priority to "Below Normal"
   - Limit thread counts (OMP_NUM_THREADS=2)
   - Implement automatic quality degradation
   - Monitor thermal throttling

## 🐛 Troubleshooting

### Issue: Webcam not detected
```bash
# Check available cameras
python -c "import cv2; print(cv2.VideoCapture(0).isOpened())"
```

### Issue: High CPU usage
- Check if resolution is set too high
- Verify frame skipping is working
- Ensure process priority is set correctly

### Issue: Memory leaks
- Monitor with `psutil` during long runs
- Check for unreleased OpenCV resources
- Verify garbage collection is working

## 📚 Documentation Links

- [Project Specifications](spec/00_index.md)
- [Requirements Document](spec/10_requirements.md)
- [Architecture Design](spec/65_solution_architecture.md)
- [Research Papers](science-source/)

## 💡 Development Principles

Per your RULE document:
1. **Evidence over opinions** - Every decision backed by prototype results
2. **Contract-first** - Respect specifications, changes only via CR
3. **Minimal yet sufficient docs** - This guide is audit-ready
4. **Safety & privacy** - All processing offline, data encrypted
5. **Observability & testability** - Metrics in every component

## 🤝 Contributing

When adding new features:
1. Start with a throwaway prototype
2. Measure against performance targets
3. Document evidence and decisions
4. Create Change Request if specs need adjustment
5. Promote to evolutionary prototype only after validation

---

**Current Phase**: Wave 1 - Core Monitoring Implementation
**Prototype Status**: THROWAWAY (Webcam Capture)
**Next Milestone**: Validate performance targets