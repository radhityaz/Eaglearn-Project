"""
Test Webcam Processor - Direct test without Flask
"""

import sys
import time
from app import state, webcam

print("=" * 60)
print("TESTING WEBCAM PROCESSOR")
print("=" * 60)

# Start the webcam
print("\n1. Starting webcam...")
if webcam.start():
    print("   ✅ Webcam started successfully")
else:
    print("   ❌ Webcam failed to start")
    sys.exit(1)

# Let it run for a few seconds
print("\n2. Letting it run for 5 seconds...")
print("   Check for any errors below:")
print("-" * 60)

for i in range(5):
    time.sleep(1)
    print(
        f"   Second {i + 1}: FPS={state.fps:.1f}, Face={state.face_detected}, Focus={state.focus_percentage:.0f}%"
    )

print("-" * 60)

# Stop the webcam
print("\n3. Stopping webcam...")
webcam.stop()
print("   ✅ Webcam stopped")

print("\n" + "=" * 60)
print("✅ WEBCAM PROCESSOR TEST PASSED!")
print("=" * 60)
print("\nThe camera feed should work in the app now.")
print("Open browser to: http://localhost:8080")
