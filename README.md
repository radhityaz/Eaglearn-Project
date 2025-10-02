# Eaglearn - AI-Powered Learning Monitoring System

## 🦅 Overview

**Eaglearn** adalah platform monitoring belajar mandiri yang memadukan computer vision, analisis audio, dan pelacakan produktivitas untuk membantu mahasiswa menjaga fokus, mendeteksi kelelahan, dan mengoptimalkan pola belajar. Sistem beroperasi sepenuhnya offline untuk menjaga privasi pengguna.

### Key Features (Wave 1)
- **Visual Engagement Tracking**: Real-time gaze estimation dan head pose detection
- **Stress & Fatigue Detection**: Audio stress analysis dan micro-expression recognition
- **Productivity Analytics**: On-task tracking dan break pattern identification
- **Privacy-First**: 100% offline processing dengan enkripsi AES-256
- **Resource-Efficient**: Dioptimalkan untuk laptop mid-range (Acer Nitro 5 AN515-58)

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

### Installation

```bash
# Clone repository
git clone <repository-url>
cd Eaglearn-Project

# Install Python dependencies
python -m venv venv
venv\Scripts\activate  # Windows
# atau
source venv/bin/activate  # Linux/Mac

pip install -r requirements.txt

# Install Node.js dependencies
npm install

# Run development mode
npm run dev
```

## 📁 Project Structure

```
Eaglearn-Project/
├── frontend/           # Electron desktop application
│   ├── src/           # Source code
│   ├── public/        # Static assets
│   └── main.js        # Electron main process
├── backend/           # Python AI processing
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

```bash
# Run Python tests
pytest tests/backend/

# Run JavaScript tests
npm test

# Run performance benchmarks
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