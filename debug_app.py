#!/usr/bin/env python3
"""
Debug script - Test everything step by step
"""

import sys
import cv2
import numpy as np

print("="*60)
print("EAGLEARN DEBUG - Step by Step Test")
print("="*60)

# Test 1: OpenCV
print("\n[1/6] Testing OpenCV...")
try:
    import cv2
    print(f"  ✓ OpenCV version: {cv2.__version__}")
except Exception as e:
    print(f"  ✗ OpenCV failed: {e}")
    sys.exit(1)

# Test 2: Webcam with DirectShow
print("\n[2/6] Testing Webcam (DirectShow)...")
try:
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print("  ✗ Cannot open webcam with DirectShow")
        print("  Trying default backend...")
        cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("  ✗ CRITICAL: Cannot open webcam at all!")
        print("\n  Possible fixes:")
        print("  1. Check if webcam is connected")
        print("  2. Close other apps using webcam (Zoom, Teams, etc)")
        print("  3. Check Windows Camera permissions")
        print("  4. Restart computer")
        sys.exit(1)

    print("  ✓ Webcam opened")

    ret, frame = cap.read()
    if not ret or frame is None:
        print("  ✗ CRITICAL: Cannot read frame!")
        cap.release()
        sys.exit(1)

    print(f"  ✓ Frame captured: {frame.shape}")
    cap.release()

except Exception as e:
    print(f"  ✗ Webcam test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 3: MediaPipe
print("\n[3/6] Testing MediaPipe...")
try:
    import mediapipe as mp

    # Test Pose
    pose = mp.solutions.pose.Pose()
    print("  ✓ MediaPipe Pose")

    # Test Face Detection
    face = mp.solutions.face_detection.FaceDetection()
    print("  ✓ MediaPipe Face Detection")

    # Test Face Mesh
    mesh = mp.solutions.face_mesh.FaceMesh()
    print("  ✓ MediaPipe Face Mesh")

except Exception as e:
    print(f"  ✗ MediaPipe failed: {e}")
    sys.exit(1)

# Test 4: Flask
print("\n[4/6] Testing Flask...")
try:
    from flask import Flask
    from flask_socketio import SocketIO

    test_app = Flask(__name__)
    test_socketio = SocketIO(test_app)

    print("  ✓ Flask")
    print("  ✓ Flask-SocketIO")

except Exception as e:
    print(f"  ✗ Flask failed: {e}")
    sys.exit(1)

# Test 5: Import app.py
print("\n[5/6] Testing app.py import...")
try:
    import app
    print("  ✓ app.py imported")
    print(f"  ✓ Flask app: {app.app.name}")
    print(f"  ✓ State: {type(app.state).__name__}")

except Exception as e:
    print(f"  ✗ app.py import failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 6: Create test image and process
print("\n[6/6] Testing image processing...")
try:
    # Create test frame
    test_frame = np.zeros((480, 640, 3), dtype=np.uint8)

    # Test encode
    ret, buffer = cv2.imencode('.jpg', test_frame)
    if not ret:
        print("  ✗ Cannot encode frame")
        sys.exit(1)

    import base64
    frame_b64 = base64.b64encode(buffer).decode('utf-8')

    print(f"  ✓ Frame encoding works")
    print(f"  ✓ Base64 length: {len(frame_b64)}")

except Exception as e:
    print(f"  ✗ Processing failed: {e}")
    sys.exit(1)

# Summary
print("\n" + "="*60)
print("ALL TESTS PASSED ✓")
print("="*60)
print("\nYour system is ready!")
print("\nNext steps:")
print("1. Run: python run.py")
print("2. Open: http://localhost:5000")
print("3. Click 'Start Monitoring'")
print("4. If still black screen, send me the browser console errors")
print("   (Press F12 in browser, go to Console tab)")
print("="*60)
