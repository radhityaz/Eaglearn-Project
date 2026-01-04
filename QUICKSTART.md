# Eaglearn Quick Start Guide

## ⚡ 30-Second Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run application
python run.py

# 3. Open browser
# Visit http://localhost:5000
```

## 🎯 First Run

1. **Click "Start Monitoring"** button
2. **Allow webcam access** when prompted
3. **Watch the dashboard** for real-time metrics

## 📊 Understanding the Metrics

### Focus Percentage
Your current focus level (0-100%). Higher is better.

### Head Pose (Yaw, Pitch, Roll)
Which direction your head is facing:
- **Yaw (↔)**: -90° = looking left, +90° = looking right
- **Pitch (↑↓)**: -90° = looking down, +90° = looking up
- **Roll (⟲)**: -90° = tilted left, +90° = tilted right

### Emotion
What emotion is detected: Happy, Sad, Angry, Sleepy, Neutral

### Posture Score
How good your posture is (0-100%). Better posture = higher score.

## 🐛 Troubleshooting

| Problem | Solution |
|---------|----------|
| No webcam feed | Check permissions: Settings → Privacy → Camera |
| App won't start | Reinstall: `pip install --upgrade -r requirements.txt` |
| Metrics not updating | Ensure good lighting and face is visible |
| Low FPS | Close other apps to free CPU resources |

## 📚 Learn More

- See `SIMPLE_APP_README.md` for full documentation
- Check `test_app.py` for example API usage

## 🚀 Ready to Go!

Your simplified, full-Python focus monitoring system is ready to use.

**Next Steps:**
- Run the app in production with proper SSL certificates
- Configure database for session persistence (optional)
- Customize metrics thresholds
- Add custom training data

Enjoy monitoring! 📚✨
