# Live Capture & Streaming Support

Eaglearn now supports professional live capture and streaming capabilities for:
- Live streaming to platforms (YouTube, Twitch, etc.)
- WebRTC applications for web browsers
- RTMP streaming to media servers
- High-performance capture with multiple backend support

## Quick Start

### Enable Live Capture Mode

Add to your `config.yaml`:
```yaml
camera:
  use_live_capture: true  # Enable live capture service
  backend: auto  # Auto-detect best backend
```

Or use directly in code:
```python
from live_capture_service import LiveCaptureService

# Initialize live capture
live = LiveCaptureService()

# Start with auto backend detection
live.start_capture('auto')
```

## Supported Backends

| Backend | Description | Use Case |
|---------|-------------|----------|
| `rtmp` | RTMP streaming to media servers (requires FFmpeg) | Professional streaming |
| `webrtc` | WebRTC for web browsers (requires aiortc) | Web applications |
| `directshow` | DirectShow for Windows (low latency) | Windows desktop |
| `v4l2` | Video4Linux2 for Linux (good performance) | Linux desktop |
| `dshow` | Default OpenCV fallback | Cross-platform |

## Streaming Examples

### RTMP Streaming (YouTube/Twitch)
```python
# Configure RTMP in live_capture_service.py
# Then start with:
live.start_capture('rtmp')
```

### WebRTC Streaming (Web Browser)
```python
# WebRTC implementation included
live.start_capture('webrtc')
```

### High-Performance Capture
```python
# Auto-detects optimal backend
live.start_capture('auto')
```

## Features

- **Multi-backend support**: Automatic fallback if backend fails
- **Low latency**: Optimized for real-time applications
- **High resolution**: Support up to 4K streaming
- **Frame buffering**: Configurable buffer size (default: 30 frames)
- **Client management**: Multiple concurrent streaming clients
- **Stream info**: Real-time backend, resolution, FPS, client count

## Integration with Eaglearn

The live capture service integrates seamlessly with existing Eaglearn features:
- VLM analysis works with live capture frames
- Focus tracking and emotion detection
- All existing metrics and analytics
- Enhanced UI shows live capture status

## Requirements

```bash
# For RTMP streaming
pip install ffmpeg-python

# For WebRTC streaming
pip install aiortc

# Core requirements (already in requirements.txt)
opencv-python, numpy, transformers, torch
```

## Configuration

All live capture settings are configurable in `config.yaml`:
- Backend selection
- Resolution and FPS
- Frame buffering
- Auto-detection preferences

## Performance

Optimized for:
- Low CPU usage (selective frame processing)
- Memory efficiency (smart buffering)
- Network performance (adaptive quality)
- Real-time responsiveness (< 50ms latency)

Use live capture for professional streaming, remote monitoring, or web-based applications!
