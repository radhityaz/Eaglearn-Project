# Eaglearn Dashboard Guide

## Overview

The Eaglearn dashboard provides real-time monitoring of focus metrics through an intuitive web interface. All metrics are **quantifiable and measurable**.

## Dashboard Layout

### Left Panel: Webcam Feed
- **Live video stream** from your webcam
- **Overlay information** showing real-time processing
- **Status indicator** showing system state (Online/Offline)

### Right Panel: Key Metrics
- **Focus Level** (0-100%): Current focus percentage
- **Head Pose**: Yaw, Pitch, Roll angles
- **Status indicators**: Face detection, Body detection

### Bottom Panels: Detailed Metrics
- **Facial Metrics**: Emotion, Eye state, Mouth state
- **Body Pose**: Posture score, Pose confidence

## Metric Reference

### Focus Percentage (0-100%)

The main metric indicating how focused you are currently.

**Calculation factors:**
- Eye aspect ratio (are your eyes open?)
- Head pose (are you looking at screen?)
- Posture quality (good body position?)

**Interpretation:**
- **80-100%**: Excellent focus - well engaged
- **60-80%**: Good focus - maintaining attention
- **40-60%**: Moderate focus - some distractions
- **20-40%**: Low focus - frequently distracted
- **0-20%**: Very low focus - significant distractions

**Tips to improve:**
- Sit upright with good posture
- Keep your eyes on the screen
- Face directly toward camera
- Minimize phone/other distractions

### Head Pose Angles

Three angles measuring head rotation and tilt:

#### Yaw (Horizontal, Left-Right)
```
     -90°    0°     +90°
      ↖     ↓      ↗
    Looking Looking Looking
     Left  Ahead  Right
```

- **-90°**: Looking far left
- **-45°**: Looking left
- **0°**: Facing camera
- **+45°**: Looking right
- **+90°**: Looking far right

**Good for focus:** 0° ± 20° (mostly facing forward)

#### Pitch (Vertical, Up-Down)
```
     +90°   Looking Up
      ↑
      |     0° Facing forward
      ↓
     -90°   Looking Down
```

- **+90°**: Looking straight up
- **+45°**: Looking up
- **0°**: Facing camera
- **-45°**: Looking down
- **-90°**: Looking straight down

**Good for focus:** 0° ± 20° (mostly level)

#### Roll (Tilt, Left-Right Shoulder)
```
      ↙ -90°   0° ↓   +90° ↘
    Left Tilt  Upright  Right Tilt
```

- **-90°**: Head tilted far left
- **-45°**: Head tilted left
- **0°**: Head upright
- **+45°**: Head tilted right
- **+90°**: Head tilted far right

**Good for focus:** 0° ± 15° (minimal tilt)

### Facial Metrics

#### Emotion Detection
Current emotional state detected from facial expression:

- **Neutral**: Relaxed, focused expression
- **Happy**: Smiling, positive mood
- **Sad**: Frowning, negative mood
- **Angry**: Tense expression
- **Sleepy**: Eyes closed or very tired

**Confidence:** 0-100% how certain the system is about the emotion

#### Eye State (Eye Aspect Ratio)
Measurement of how wide your eyes are open (0-1).

- **0.0-0.2**: Eyes closed or mostly closed
- **0.2-0.4**: Eyes partially closed, drowsy
- **0.4-0.7**: Eyes open, normal state
- **0.7-1.0**: Eyes wide open, alert

#### Mouth State (Mouth Aspect Ratio)
Measurement of how open your mouth is (0-1).

- **0.0-0.3**: Mouth closed
- **0.3-0.6**: Mouth slightly open
- **0.6-1.0**: Mouth open (speaking, surprised, etc.)

### Body Pose Metrics

#### Posture Score (0-100%)
How good your body posture is.

**Calculation:**
- Head alignment with shoulders
- Shoulder alignment
- Back straightness

**Interpretation:**
- **80-100%**: Excellent posture, well-aligned
- **60-80%**: Good posture, minor issues
- **40-60%**: Fair posture, some slouching
- **20-40%**: Poor posture, significant slouching
- **0-20%**: Very poor posture, needs correction

**Tips for better posture:**
- Sit back in chair, not at edge
- Feet flat on floor
- Monitor at eye level
- Back straight, not hunched
- Shoulders relaxed

#### Pose Confidence (0-100%)
How confident the system is about body pose detection.

- **80-100%**: Very confident, accurate measurements
- **60-80%**: Confident, reliable data
- **40-60%**: Moderate confidence
- **20-40%**: Low confidence, less reliable
- **0-20%**: Very low confidence, may be inaccurate

**What affects confidence:**
- Distance from camera
- Lighting conditions
- Body position (full body in frame)
- Clothing (contrast helps)

### Time Tracking

#### Focused Time
Total seconds spent in focused state (focus% > 60).

#### Unfocused Time
Total seconds spent in unfocused state (focus% < 60).

#### Distraction Events
Number of times focus suddenly dropped significantly.

#### Focus Ratio
Overall focus percentage: focused_time / (focused_time + unfocused_time)

**Example:**
- Focused Time: 120s
- Unfocused Time: 30s
- Focus Ratio: 120 / (120 + 30) = 80%

## How to Use the Dashboard

### Starting a Session

1. Click **"Start Monitoring"** button
2. Browser asks for webcam permission - **Allow**
3. Dashboard begins showing live metrics
4. Status indicator shows "Active" (green)

### During Session

- **Monitor focus percentage** in real-time
- **Check head pose** to ensure you're facing screen
- **Watch emotion** to catch when you're getting tired
- **Track posture** to maintain good position

### Stopping a Session

1. Click **"Stop Monitoring"** button
2. Recording stops
3. Session ends
4. Status indicator shows "Idle" (gray)

## Optimal Settings

### Webcam Position
- Mount at eye level
- 1-2 feet away from face
- Full body visible
- Good lighting from front

### Room Lighting
- **Ideal:** Natural light or soft artificial light
- **Avoid:** Direct sunlight (glare), very dim rooms
- **Best time:** Daytime with window light, or use desk lamp

### Camera Setup
- **Resolution:** 720p minimum, 1080p preferred
- **Frame rate:** 30 FPS ideal
- **Angle:** Slightly below eye level works best

## Troubleshooting

### Metrics Not Updating
- Ensure face is fully visible
- Check lighting (too dark won't work)
- Move closer to camera
- Ensure good image quality

### Pose Confidence Too Low
- Move into better light
- Make sure full body is in frame
- Wear contrasting clothing
- Sit further back if too close to camera

### Head Pose Angles Jumping
- Camera may be jittery
- Try steadying camera mount
- Ensure good light to reduce noise
- Close and reopen session

### High False Positive Emotions
- System learns over time
- Keep good lighting
- Ensure good face visibility
- More data = better accuracy

## Tips for Best Results

1. **Good lighting** - Most important factor
2. **Face visible** - Center in frame
3. **Steady camera** - Reduces jitter
4. **Good distance** - 1-2 feet optimal
5. **Minimal obstruction** - Sunglasses, hats affect detection
6. **Natural posture** - Sit normally, don't pose
7. **Regular sessions** - System improves with more data

## Data Privacy

- ✅ All processing happens locally
- ✅ No data is stored by default
- ✅ Webcam only active when you click "Start"
- ✅ Close browser tab to stop all processing
- ✅ No cloud sync or external transmission

## Performance

- **FPS:** 15-30 frames per second
- **Latency:** 100-200ms from capture to display
- **CPU Usage:** 20-40% on modern CPU
- **Memory:** 400-600MB during operation

## Next Features

- [ ] Audio analysis for stress detection
- [ ] Session saving and playback
- [ ] Historical reports
- [ ] Daily/weekly summaries
- [ ] Alerts for focus drops
- [ ] Custom metric thresholds
