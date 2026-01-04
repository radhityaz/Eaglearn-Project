#!/usr/bin/env python3
"""Quick test to check if webcam works"""

import cv2
import sys

print("Testing webcam...")

# Try to open webcam
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("❌ FAILED: Cannot open webcam")
    print("   Possible issues:")
    print("   - No webcam connected")
    print("   - Webcam in use by another app")
    print("   - Permission denied")
    sys.exit(1)

print("✅ Webcam opened successfully")

# Try to read frame
ret, frame = cap.read()

if not ret:
    print("❌ FAILED: Cannot read frame from webcam")
    cap.release()
    sys.exit(1)

print(f"✅ Frame captured: {frame.shape}")

# Check frame content
if frame is None or frame.size == 0:
    print("❌ FAILED: Frame is empty")
    cap.release()
    sys.exit(1)

print(f"✅ Frame valid: {frame.shape[1]}x{frame.shape[0]}")

# Release
cap.release()

print("\n" + "="*60)
print("WEBCAM TEST: SUCCESS ✅")
print("="*60)
print("Your webcam is working correctly!")
print("The black screen issue is NOT the webcam.")
print("Problem is likely in:")
print("  - Frame encoding")
print("  - SocketIO emission")
print("  - Browser receiving frames")
