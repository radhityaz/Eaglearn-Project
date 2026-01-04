# Eaglearn - AI-Powered Learning Monitoring System

## 🦅 Overview

**Eaglearn** adalah platform monitoring belajar mandiri yang memadukan computer vision, analisis audio, dan pelacakan produktivitas untuk membantu mahasiswa menjaga fokus, mendeteksi kelelahan, dan mengoptimalkan pola belajar. Sistem beroperasi sepenuhnya offline untuk menjaga privasi pengguna.

**NEW:** Simplified, full-Python Flask application with clear state management and quantifiable metrics. See [SIMPLE_APP_README.md](SIMPLE_APP_README.md) for details.

### Key Features
- **✅ Real-time Analytics**: Head pose (Yaw/Pitch/Roll), facial emotion detection, posture analysis
- **✅ Clear Metrics**: All metrics quantified (percentages, degrees, ratios)
- **✅ Live Webcam Feed**: Real-time video with skeleton and emotion overlays
- **✅ Focus Monitoring**: 0-100% focus percentage with time tracking
- **✅ Privacy-First**: 100% local processing, no cloud sync
- **✅ Simple Architecture**: Single app.py + HTML5 frontend
- **✅ Full Python**: No Electron complexity - Flask backend only

## 🚀 Quick Start

### Prerequisites
- **OS**: Windows 11 23H2 atau Ubuntu 22.04 LTS
- **Python**: 3.11.x
- **Node.js**: 18.x atau lebih baru
- **Hardware**:
  - CPU: Intel i5 atau setara
  - GPU: NVIDIA GTX 1650 atau lebih baik (opsional tapi direkomendasikan)
  - RAM: Minimum 16GB
  - Kamera: 720p webcam

### Installation (Simplified Version)

```bash
# 1. Clone repository
git clone https://github.com/radhityaz/Eaglearn-Project
cd Eaglearn-Project

# 2. Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# or source venv/bin/activate  # Linux/Mac

# 3. Install dependencies
pip install -r requirements.txt
```

### Running the Application

**Single command to run:**
```bash
python run.py
```

Then open http://localhost:5000 in your browser.

### Alternative: Legacy FastAPI Backend (if needed)

If you want to run the legacy backend instead:
```bash
python start_backend.py
# Opens at http://localhost:8000
```

## 📁 Project Structure

```
Eaglearn-Project/
├── app.py                    # Main Flask application (new simplified version)
├── run.py                    # Application launcher
├── templates/
│   └── index.html           # Web dashboard
├── requirements.txt         # Python dependencies
├── backend/                 # Legacy FastAPI backend (optional)
│   ├── main.py
│   ├── api/
│   ├── ml/                  # Machine learning models
│   ├── db/                  # Database & encryption
│   └── ws/                  # WebSocket management
│   ├── core/          # Core modules (vision, audio, tracking)
│   ├── api/           # FastAPI server
│   ├── models/        # ML models
│   └── utils/         # Utilities
├── spec/              # Technical specifications
├── science-source/    # Research papers and references
├── tests/             # Test suites
└── docs/              # Documentation

```

## 🔬 Development Approach

Project ini mengikuti prinsip **Evidence-Driven Prototyping**:
- **Throwaway Prototypes**: Untuk eksplorasi fitur baru
- **Evolutionary Prototypes**: Untuk komponen produksi
- **Performance First**: Optimasi untuk hardware terbatas
- **Privacy by Design**: Data tidak pernah meninggalkan perangkat

## 🧪 Testing

### Unit Testing
```bash
# Backend Tests (Pytest)
pytest

# Frontend Tests (Jest)
cd frontend
npm test
```

### End-to-End Testing
```bash
# Menjalankan E2E tests dengan Playwright
cd frontend
npm run test:e2e
```

### Performance Benchmarks
```bash
python benchmarks/run_all.py
```

## 📊 Performance Targets

| Component | Target | Actual |
|-----------|--------|--------|
| End-to-end Latency | ≤200ms | TBD |
| CPU Usage (Idle) | <30% | TBD |
| GPU Usage (Active) | <60% | TBD |
| RAM Usage | <2GB | TBD |
| FPS (Video Processing) | ≥15 | TBD |

## 🔒 Privacy & Security

- **No Cloud**: Semua processing dilakukan on-device
- **Encryption**: AES-256 untuk semua data tersimpan
- **Auto-Purge**: Data otomatis dihapus setelah 30 hari
- **GDPR Compliant**: Sesuai dengan Article 5, 6, 7, dan 32

## 📚 Documentation

- [Technical Specifications](spec/00_index.md)
- [Requirements](spec/10_requirements.md)
- [Architecture](spec/65_solution_architecture.md)
- [API Documentation](docs/api.md)
- [User Guide](docs/user-guide.md)

## 🤝 Contributing

Project ini dalam tahap active development. Untuk kontribusi:
1. Baca [Development Guidelines](docs/development.md)
2. Ikuti prinsip Evidence-Driven Prototyping
3. Pastikan semua tests pass sebelum commit
4. Document setiap keputusan design

## 📄 License

[License Type TBD]

## 👥 Team

- System Designer: Kilo Code
- Developer: Eaglearn Team

## 🔗 Resources

- [Research Papers](science-source/)
- [Figma Designs](#) (via MCP)
- [Performance Benchmarks](benchmarks/)

---

**Status**: 🔨 Under Active Development (Wave 1)

Last Updated: 2025-01-02