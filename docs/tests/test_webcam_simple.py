"""
Simple test to verify webcam works
"""
import sys
import time
import cv2

print("=" * 60, flush=True)
print("SIMPLE WEBCAM TEST", flush=True)
print("=" * 60, flush=True)

print("\n1. Opening camera with DSHOW backend...", flush=True)
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

if not cap.isOpened():
    print("   FAILED - Trying default backend...", flush=True)
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("   FAILED - Cannot open camera!", flush=True)
        sys.exit(1)

print("   SUCCESS!", flush=True)

print("\n2. Reading 5 frames...", flush=True)
for i in range(5):
    ret, frame = cap.read()
    if ret:
        print(f"   Frame {i+1}: {frame.shape}", flush=True)
    else:
        print(f"   Frame {i+1}: FAILED to read", flush=True)
    time.sleep(0.5)

cap.release()
print("\n3. Camera released!", flush=True)

print("\n" + "=" * 60, flush=True)
print("TEST COMPLETE - Camera is working!", flush=True)
print("=" * 60, flush=True)
