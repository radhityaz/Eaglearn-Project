# Eaglearn

Real-time focus monitoring system with emotion detection and eye tracking.

## Features

- **Real-time Face & Pose Detection** using MediaPipe
- **Emotion Recognition** using DeepFace (93% accuracy) and EfficientNet (87% accuracy)
- **Eye Tracking & Gaze Estimation** with iris refinement
- **Focus Score Calculation** based on head pose, eye state, and body posture
- **Distraction Detection** with detailed explanations
- **Privacy Controls** - pause/resume processing
- **Adaptive Performance** - automatically adjusts processing quality based on FPS

## Quick Start

### Installation

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Running the Application

```bash
python app.py
```

The application will start on `http://localhost:8080`

## Architecture

```
Eaglearn-Project/
├── app.py                          # Main Flask application
├── config.yaml                     # Configuration file
├── config_loader.py                # Configuration manager
├── calibration.py                  # User calibration system
├── improved_webcam_processor.py    # Modular webcam processor
├── mediapipe_processors/           # Modular ML processors
│   ├── face_mesh_processor.py      # Face & eye tracking
│   ├── pose_processor.py           # Body pose detection
│   ├── deepface_emotion_detector.py # Emotion detection (93%)
│   ├── efficientnet_emotion_detector.py # Fallback emotion detection (87%)
│   └── poster_emotion_detector.py  # POSTER++ detector (90%, optional)
├── templates/                      # HTML templates
│   └── index.html
└── calibrations/                   # User calibration data
```

## Configuration

Edit `config.yaml` to customize:

```yaml
camera:
  width: 640
  height: 480
  fps: 30
  backend: dshow  # dshow (Windows) or v4l2 (Linux)

performance:
  frame_skip_base: 3        # Process every Nth frame
  adaptive_quality:
    enabled: true           # Auto-adjust quality based on FPS
    target_fps: 25

emotion:
  detector: "deepface"      # Primary emotion detector
  confidence_threshold: 0.25

privacy:
  allow_pause: true         # Allow privacy mode
  local_processing_only: true
```

## Emotion Detection

### Priority Order

1. **DeepFace** (93% accurate)
   - Model: VGG-Face + Emotion weights
   - Detector: RetinaFace
   - Speed: 10-15 FPS (GPU accelerated)

2. **EfficientNet-B3** (87% accurate)
   - Model: PyTorch EfficientNet-B3
   - Source: Official torchvision
   - Speed: 50-60 FPS (faster)

3. **POSTER++** (90% accurate, optional)
   - Model: SOTA 2024 emotion detector
   - Requires: Google Drive download
   - See: `setup_poster++.md`

### Emotions Detected

- Happy
- Sad
- Angry
- Surprised
- Neutral
- Drowsy (rule-based)
- Confused (rule-based)
- Stressed (rule-based)

## Performance Optimization

### Adaptive Quality

The system automatically adjusts processing quality based on current FPS:

- **High FPS (>30)**: Increases frame skip for better performance
- **Low FPS (<20)**: Decreases frame skip for better accuracy

### Frame Skipping

- **Face & Eye Tracking**: Every frame
- **Pose Detection**: Every 6th frame
- **Emotion Detection**: Every 10th frame
- **Frame Emission**: Every 3rd frame

## API Endpoints

### Session Management

- `POST /api/session/start` - Start monitoring session
- `POST /api/session/stop` - Stop monitoring session
- `GET /api/state` - Get current application state
- `GET /api/metrics` - Get current metrics

### Calibration

- `POST /api/calibration/start` - Start calibration
- `POST /api/calibration/add-point` - Add calibration point
- `POST /api/calibration/calculate` - Calculate calibration
- `GET /api/calibration/status` - Get calibration status

### Configuration

- `GET /api/config` - Get current configuration
- `POST /api/config/reload` - Reload configuration

### WebSocket Events

- `connect` - Client connected
- `disconnect` - Client disconnected
- `frame_update` - Frame + state data
- `calibration_start` - Start calibration
- `calibration_complete` - Save calibration data

## Focus Scoring

The focus score (0-100) is calculated from:

1. **Face Detection** (30 points) - Face must be visible
2. **Eye Aspect Ratio** (20 points) - Eyes must be open
3. **Head Pose** (25 points) - Must look at screen
4. **Body Posture** (15 points) - Upright posture
5. **Mouth Aspect Ratio** (10 points) - Not yawning

### Status Thresholds

- **Focused**: ≥80 points
- **Distracted**: 50-79 points
- **Drowsy**: <50 points

## Troubleshooting

### Webcam Issues

**Problem**: Black screen or camera not opening

**Solution**:
- Check camera backend in `config.yaml`
- Windows: Use `dshow`
- Linux: Use `v4l2`

### Low FPS

**Problem**: Laggy video, FPS < 20

**Solution**:
- Increase `frame_skip_base` in config
- Disable pose detection if not needed
- Lower camera resolution
- Use GPU acceleration (requires CUDA)

### Emotion Detection Not Working

**Problem**: Always shows "neutral"

**Solution**:
- Check if DeepFace is installed: `pip show deepface`
- Install TensorFlow: `pip install tensorflow tf-keras`
- Check confidence threshold in config
- See logs for error messages

## Requirements

### Core Dependencies

- Python 3.11+
- Flask 3.0+
- Flask-SocketIO 5.3+
- OpenCV 4.8+
- MediaPipe 0.10+

### ML Dependencies

- DeepFace 0.0.79+ (emotion detection)
- TensorFlow 2.15+ (DeepFace backend)
- PyTorch + torchvision (EfficientNet)

### Optional

- CUDA-capable GPU (for acceleration)
- POSTER++ weights (for 90% accuracy emotion detection)

## Development

### Running Tests

```bash
pytest tests/
```

### Code Quality

```bash
# Format code
black app.py mediapipe_processors/

# Lint code
pylint app.py
```

## License

See LICENSE file.

## Acknowledgments

- [MediaPipe](https://google.github.io/mediapipe/) - Face & pose detection
- [DeepFace](https://github.com/serengil/deepface) - Emotion recognition
- [PyTorch](https://pytorch.org/) - EfficientNet models
- [POSTER++](https://github.com/AnnamTk/POSTER) - SOTA emotion detection (optional)
