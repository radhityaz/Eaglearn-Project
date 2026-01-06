"""
Headless DeepFace Test - No GUI required
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import cv2
import numpy as np
from mediapipe_processors.deepface_emotion_detector import DeepFaceEmotionDetector
from config_loader import config

print("=" * 60)
print("🎭 DEEPFACE HEADLESS TEST")
print("=" * 60)

detector = DeepFaceEmotionDetector(config)

if not detector.available:
    print("\n❌ DeepFace NOT installed!")
    print("Run: pip install deepface tf-keras tensorflow")
    sys.exit(1)

print("\n✅ DeepFace is installed!")
print("\nOpening webcam...")

# Use DirectShow backend on Windows
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

if not cap.isOpened():
    print("\n❌ Cannot open webcam with DirectShow")
    print("Trying default backend...")
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ Still cannot open webcam!")
        sys.exit(1)

print("✅ Webcam opened!")
print("\nCapturing 5 frames for analysis...")
print("=" * 60)

for i in range(5):
    ret, frame = cap.read()
    if not ret:
        print(f"❌ Frame {i+1}: Cannot read!")
        continue

    print(f"\n📸 Frame {i+1}:")

    # Detect emotion
    result = detector.detect_emotion(frame)

    print(f"   Method: {result['method']}")

    if result['method'] == 'deepface':
        print(f"   Raw Emotion: {result.get('raw_emotion', 'N/A')}")
        print(f"   Mapped to: {result['emotion']} ({result['emotion_confidence']:.1%})")

        scores = result.get('emotion_scores', {})
        if scores:
            # Show top 3 emotions
            sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:3]
            for emotion, score in sorted_scores:
                print(f"      - {emotion}: {score:.1f}%")
    else:
        print(f"   ⚠️ Fallback: {result.get('warning', 'Unknown')}")

    if i < 4:
        import time
        time.sleep(1)  # Wait 1 second between frames

cap.release()

print("\n" + "=" * 60)
print("✅ Test complete!")
print("\n💡 If you see 'deepface' method with varied emotions, it's working!")
print("💡 If you see 'fallback' or always 'neutral', there's a problem.")
print("=" * 60)
