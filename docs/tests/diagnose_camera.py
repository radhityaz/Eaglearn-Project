"""
Camera Feed Diagnostic Script
Helps identify why the camera feed isn't working in the application
"""

import sys
import cv2
import numpy as np
from config_loader import config

print("=" * 60)
print("CAMERA FEED DIAGNOSTIC")
print("=" * 60)

# Test 1: Check Configuration
print("\n1. Checking camera configuration...")
print(f"   Backend: {config.get('camera', 'backend', default='dshow')}")
print(f"   Resolution: {config.camera_width}x{config.camera_height}")
print(f"   FPS: {config.camera_fps}")

# Test 2: Try opening camera with configured backend
print("\n2. Testing camera with configured backend...")
backend_map = {
    'dshow': cv2.CAP_DSHOW,
    'default': 0,
    'v4l2': cv2.CAP_V4L2
}

backend = config.get('camera', 'backend', default='dshow')
cap_backend = backend_map.get(backend, 0)

print(f"   Opening with backend: {backend} (code: {cap_backend})")
cap = cv2.VideoCapture(0, cap_backend)

if not cap.isOpened():
    print(f"   ❌ FAILED: Cannot open with {backend}")
    print("   Trying default backend...")
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("   ❌ FAILED: Cannot open with default backend")
        print("\n🔍 POSSIBLE ISSUES:")
        print("   - Camera is being used by another application")
        print("   - Camera driver not installed properly")
        print("   - Camera not connected")
        print("   - Privacy settings blocking camera access")
        sys.exit(1)
    else:
        print("   ✅ SUCCESS: Opened with default backend")
else:
    print("   ✅ SUCCESS: Camera opened")

# Test 3: Configure camera properties
print("\n3. Configuring camera properties...")
cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.camera_width)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.camera_height)
cap.set(cv2.CAP_PROP_FPS, config.camera_fps)

actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
actual_fps = int(cap.get(cv2.CAP_PROP_FPS))

print(f"   Requested: {config.camera_width}x{config.camera_height} @ {config.camera_fps}fps")
print(f"   Actual: {actual_width}x{actual_height} @ {actual_fps}fps")

# Test 4: Read multiple frames
print("\n4. Testing frame capture (10 frames)...")
success_count = 0
for i in range(10):
    ret, frame = cap.read()
    if ret and frame is not None:
        success_count += 1
        if i == 0:
            print(f"   Frame 1: {frame.shape} - ✅")
    else:
        print(f"   Frame {i+1}: ❌ Failed to read")

print(f"   Success rate: {success_count}/10")

# Test 5: Test frame processing (mirror flip)
print("\n5. Testing frame processing...")
ret, frame = cap.read()
if ret and frame is not None:
    # Test mirror flip
    flipped = cv2.flip(frame, 1)
    print(f"   Original shape: {frame.shape}")
    print(f"   Flipped shape: {flipped.shape}")
    print("   ✅ Frame processing working")

    # Save a test frame
    cv2.imwrite('test_camera_frame.jpg', frame)
    print("   ✅ Test frame saved as 'test_camera_frame.jpg'")
else:
    print("   ❌ Cannot test frame processing")

# Test 6: Check if ImprovedWebcamProcessor can be imported
print("\n6. Testing ImprovedWebcamProcessor import...")
try:
    from improved_webcam_processor import ImprovedWebcamProcessor
    print("   ✅ ImprovedWebcamProcessor imported successfully")

    # Test initialization
    print("\n7. Testing ImprovedWebcamProcessor initialization...")
    from app import SessionState
    state = SessionState()
    processor = ImprovedWebcamProcessor(state)
    print("   ✅ ImprovedWebcamProcessor initialized")

    # Test start
    print("\n8. Testing ImprovedWebcamProcessor.start()...")
    if processor.start():
        print("   ✅ Processor started successfully")
        import time
        time.sleep(2)  # Let it run for 2 seconds

        # Check if it's still running
        if processor.running:
            print("   ✅ Processor is running")
        else:
            print("   ⚠️ Processor stopped unexpectedly")

        # Stop it
        processor.stop()
        print("   ✅ Processor stopped")
    else:
        print("   ❌ Processor failed to start")

except Exception as e:
    print(f"   ❌ Error: {e}")
    import traceback
    traceback.print_exc()

# Cleanup
cap.release()
print("\n" + "=" * 60)
print("DIAGNOSTIC COMPLETE")
print("=" * 60)

# Summary
print("\n📋 SUMMARY:")
if success_count >= 8:
    print("   ✅ Camera is working properly!")
    print("   📝 The issue might be with:")
    print("      - Browser connection to the Flask app")
    print("      - SocketIO communication")
    print("      - JavaScript in the web page")
else:
    print("   ❌ Camera has issues")
    print("   📝 Possible solutions:")
    print("      - Close other applications using the camera")
    print("      - Check Windows privacy settings")
    print("      - Reinstall camera drivers")
