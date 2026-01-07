"""
Simple Camera Test - No ML dependencies
"""
import cv2
import sys

print("=" * 60)
print("SIMPLE CAMERA TEST")
print("=" * 60)

# Try opening camera with DirectShow backend
print("\n1. Testing DirectShow backend...")
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

if not cap.isOpened():
    print("   ❌ FAILED: Cannot open with DirectShow")
    print("\n2. Trying default backend...")
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
    print("   ✅ SUCCESS: Camera opened with DirectShow")

# Set camera properties
print("\n2. Setting camera properties...")
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
print(f"   Resolution: {actual_width}x{actual_height}")

# Test reading frames
print("\n3. Testing frame capture (10 frames)...")
for i in range(10):
    ret, frame = cap.read()
    if ret and frame is not None:
        if i == 0:
            print(f"   Frame 1: {frame.shape} - ✅")
    else:
        print(f"   Frame {i+1}: ❌ Failed to read")
        cap.release()
        sys.exit(1)

print("   ✅ All frames captured successfully")

# Save a test frame
cv2.imwrite('test_camera_simple.jpg', frame)
print("\n4. Test frame saved as 'test_camera_simple.jpg'")

cap.release()
print("\n" + "=" * 60)
print("✅ CAMERA IS WORKING!")
print("=" * 60)
print("\nIf camera feed still doesn't work in the app,")
print("the issue is likely with:")
print("   - Browser connection to Flask/SocketIO")
print("   - Frontend JavaScript")
print("   - ML processing errors")
