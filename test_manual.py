#!/usr/bin/env python3
"""
Manual Verification Test
Quick checks to verify app is working
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

print("="*60)
print("MANUAL VERIFICATION TEST")
print("="*60)

# Test 1: Import app
print("\n1. Testing app import...")
try:
    from app import app, state, socketio, SessionState, WebcamProcessor
    print("   ✅ app.py imported successfully")
except Exception as e:
    print(f"   ❌ Import failed: {e}")
    sys.exit(1)

# Test 2: Create state
print("\n2. Testing state creation...")
try:
    test_state = SessionState()
    assert test_state.focus_percentage == 0.0
    print("   ✅ SessionState created")
    print(f"      Focus: {test_state.focus_percentage}%")
    print(f"      Emotion: {test_state.emotion}")
except Exception as e:
    print(f"   ❌ State creation failed: {e}")
    sys.exit(1)

# Test 3: Mutate state
print("\n3. Testing state mutation...")
try:
    with test_state.lock:
        test_state.focus_percentage = 75.0
        test_state.emotion = "happy"
    assert test_state.focus_percentage == 75.0
    assert test_state.emotion == "happy"
    print("   ✅ State mutation works")
    print(f"      Focus: {test_state.focus_percentage}%")
    print(f"      Emotion: {test_state.emotion}")
except Exception as e:
    print(f"   ❌ State mutation failed: {e}")
    sys.exit(1)

# Test 4: Serialize state
print("\n4. Testing state serialization...")
try:
    state_dict = test_state.to_dict()
    assert 'focus_percentage' in state_dict
    assert 'head_pose' in state_dict
    assert 'facial_metrics' in state_dict
    print("   ✅ State serialization works")
    print(f"      Keys: {', '.join(list(state_dict.keys())[:5])}...")
except Exception as e:
    print(f"   ❌ Serialization failed: {e}")
    sys.exit(1)

# Test 5: Flask test client
print("\n5. Testing Flask test client...")
try:
    client = app.test_client()

    # Test root
    response = client.get('/')
    assert response.status_code == 200
    print("   ✅ GET / returns 200")

    # Test API
    response = client.get('/api/state')
    assert response.status_code == 200
    data = response.get_json()
    assert 'focus_percentage' in data
    print("   ✅ GET /api/state returns JSON")
    print(f"      Focus: {data['focus_percentage']}%")

except Exception as e:
    print(f"   ❌ Flask test failed: {e}")
    sys.exit(1)

# Test 6: WebcamProcessor
print("\n6. Testing WebcamProcessor...")
try:
    processor = WebcamProcessor(test_state)
    assert processor.cap is None
    assert processor.running == False
    assert processor.pose is not None
    print("   ✅ WebcamProcessor initialized")
    print(f"      Camera closed: {processor.cap is None}")
    print(f"      Pose model loaded: {processor.pose is not None}")
except Exception as e:
    print(f"   ❌ WebcamProcessor failed: {e}")
    sys.exit(1)

# Test 7: MediaPipe models
print("\n7. Testing MediaPipe models...")
try:
    import mediapipe as mp

    pose = mp.solutions.pose.Pose()
    face_det = mp.solutions.face_detection.FaceDetection()
    face_mesh = mp.solutions.face_mesh.FaceMesh()

    print("   ✅ All MediaPipe models loaded")
    print(f"      Pose: OK")
    print(f"      Face Detection: OK")
    print(f"      Face Mesh: OK")
except Exception as e:
    print(f"   ❌ MediaPipe failed: {e}")
    sys.exit(1)

# Test 8: OpenCV
print("\n8. Testing OpenCV...")
try:
    import cv2
    import numpy as np

    img = np.zeros((100, 100, 3), dtype=np.uint8)
    flipped = cv2.flip(img, 1)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    print("   ✅ OpenCV works")
    print(f"      Image ops: OK")
    print(f"      cv2.flip: OK")
    print(f"      cv2.cvtColor: OK")
except Exception as e:
    print(f"   ❌ OpenCV failed: {e}")
    sys.exit(1)

# Test 9: File structure
print("\n9. Testing file structure...")
try:
    files = ['app.py', 'run.py', 'templates/index.html', 'requirements.txt']
    for f in files:
        assert Path(f).exists(), f"Missing: {f}"
    print("   ✅ All required files exist")
    for f in files:
        print(f"      {f}")
except Exception as e:
    print(f"   ❌ File check failed: {e}")
    sys.exit(1)

# Summary
print("\n" + "="*60)
print("VERIFICATION SUMMARY")
print("="*60)
print("✅ All 9 verification tests PASSED")
print()
print("App is ready to run!")
print()
print("To start the application:")
print("  python run.py")
print()
print("Then open your browser to:")
print("  http://localhost:5000")
print("="*60)
