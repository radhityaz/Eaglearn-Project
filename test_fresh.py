#!/usr/bin/env python3
"""
Fresh Testing Suite - No trust in previous tests
Complete validation from scratch
"""

import sys
import os
import time
import subprocess
import requests
from pathlib import Path

# Setup path
sys.path.insert(0, str(Path(__file__).parent))

class TestRunner:
    """Fresh test runner - verify everything from scratch"""

    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    def test(self, name, func):
        """Run a single test"""
        print(f"\n{'='*60}")
        print(f"TEST: {name}")
        print('='*60)
        try:
            result = func()
            if result:
                print(f"✅ PASS")
                self.passed += 1
            else:
                print(f"❌ FAIL")
                self.failed += 1
                self.errors.append(name)
            return result
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            self.failed += 1
            self.errors.append(f"{name} - {e}")
            return False

    def summary(self):
        """Print test summary"""
        print(f"\n{'='*60}")
        print("TEST SUMMARY")
        print('='*60)
        print(f"Passed: {self.passed}")
        print(f"Failed: {self.failed}")
        print(f"Total:  {self.passed + self.failed}")

        if self.errors:
            print("\nFailed tests:")
            for err in self.errors:
                print(f"  - {err}")

        if self.failed == 0:
            print("\n✅ ALL TESTS PASSED!")
            return True
        else:
            print(f"\n❌ {self.failed} TESTS FAILED!")
            return False

# Test functions
def test_python_version():
    """Verify Python version"""
    print(f"Python version: {sys.version}")
    major, minor = sys.version_info[:2]
    assert major == 3 and minor >= 11, f"Need Python 3.11+, got {major}.{minor}"
    return True

def test_critical_imports():
    """Test all critical imports work"""
    imports = {
        'flask': 'Flask',
        'cv2': 'OpenCV',
        'mediapipe': 'MediaPipe',
        'numpy': 'NumPy',
        'flask_socketio': 'Flask-SocketIO',
        'flask_cors': 'Flask-CORS',
    }

    for module, name in imports.items():
        try:
            __import__(module)
            print(f"  ✓ {name} imported")
        except ImportError as e:
            print(f"  ✗ {name} FAILED: {e}")
            return False

    return True

def test_app_module_loads():
    """Test app.py loads without errors"""
    try:
        import app
        print(f"  ✓ app module loaded")
        assert hasattr(app, 'app'), "No Flask app found"
        assert hasattr(app, 'state'), "No state found"
        assert hasattr(app, 'socketio'), "No socketio found"
        assert hasattr(app, 'SessionState'), "No SessionState class"
        assert hasattr(app, 'WebcamProcessor'), "No WebcamProcessor class"
        print(f"  ✓ All required attributes present")
        return True
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        return False

def test_state_initialization():
    """Test SessionState can be created and initialized"""
    from app import SessionState

    state = SessionState()

    # Check initial values
    checks = {
        'session_id is None': state.session_id is None,
        'is_running is False': state.is_running == False,
        'focus_percentage is 0.0': state.focus_percentage == 0.0,
        'head_yaw is 0.0': state.head_yaw == 0.0,
        'head_pitch is 0.0': state.head_pitch == 0.0,
        'head_roll is 0.0': state.head_roll == 0.0,
        'emotion is "neutral"': state.emotion == "neutral",
        'posture_score is 0.0': state.posture_score == 0.0,
    }

    for check, result in checks.items():
        print(f"  {'✓' if result else '✗'} {check}")
        if not result:
            return False

    return True

def test_state_mutation():
    """Test state can be mutated"""
    from app import SessionState

    state = SessionState()

    # Mutate state
    with state.lock:
        state.focus_percentage = 85.5
        state.head_yaw = 15.3
        state.emotion = "happy"
        state.posture_score = 92.1

    # Verify mutations
    assert state.focus_percentage == 85.5, f"focus_percentage: {state.focus_percentage}"
    assert state.head_yaw == 15.3, f"head_yaw: {state.head_yaw}"
    assert state.emotion == "happy", f"emotion: {state.emotion}"
    assert state.posture_score == 92.1, f"posture_score: {state.posture_score}"

    print(f"  ✓ All mutations successful")
    print(f"    Focus: {state.focus_percentage}%")
    print(f"    Yaw: {state.head_yaw}°")
    print(f"    Emotion: {state.emotion}")
    print(f"    Posture: {state.posture_score}%")

    return True

def test_state_serialization():
    """Test state can be serialized to dict"""
    from app import SessionState

    state = SessionState()
    state_dict = state.to_dict()

    # Check required keys
    required_keys = [
        'session_id', 'is_running', 'focus_percentage',
        'head_pose', 'facial_metrics', 'body_pose',
        'webcam', 'time_tracking'
    ]

    for key in required_keys:
        if key not in state_dict:
            print(f"  ✗ Missing key: {key}")
            return False
        print(f"  ✓ {key}")

    # Check nested structures
    assert 'yaw' in state_dict['head_pose'], "Missing head_pose.yaw"
    assert 'pitch' in state_dict['head_pose'], "Missing head_pose.pitch"
    assert 'emotion' in state_dict['facial_metrics'], "Missing facial_metrics.emotion"
    assert 'posture_score' in state_dict['body_pose'], "Missing body_pose.posture_score"

    print(f"  ✓ All nested structures present")
    return True

def test_flask_app_creation():
    """Test Flask app is created properly"""
    from app import app, socketio

    assert app is not None, "App is None"
    assert app.name == 'app', f"App name is {app.name}, expected 'app'"
    assert socketio is not None, "SocketIO is None"

    print(f"  ✓ Flask app created")
    print(f"  ✓ App name: {app.name}")
    print(f"  ✓ SocketIO initialized")

    return True

def test_flask_routes_exist():
    """Test Flask routes are registered"""
    from app import app

    routes = []
    for rule in app.url_map.iter_rules():
        routes.append((rule.rule, list(rule.methods)))

    print(f"  Found {len(routes)} routes:")
    for route, methods in routes:
        print(f"    {route} - {methods}")

    # Check critical routes exist
    route_paths = [r[0] for r in routes]
    required = ['/', '/api/state', '/api/metrics', '/api/session/start', '/api/session/stop']

    for req in required:
        if req not in route_paths:
            print(f"  ✗ Missing route: {req}")
            return False

    print(f"  ✓ All required routes present")
    return True

def test_api_endpoints_callable():
    """Test API endpoints can be called"""
    from app import app

    client = app.test_client()

    tests = [
        ('GET', '/', 200, 'html'),
        ('GET', '/api/state', 200, 'json'),
        ('GET', '/api/metrics', 200, 'json'),
    ]

    for method, path, expected_code, content_type in tests:
        response = client.get(path) if method == 'GET' else client.post(path)

        if response.status_code != expected_code:
            print(f"  ✗ {method} {path}: got {response.status_code}, expected {expected_code}")
            return False

        if content_type == 'json':
            data = response.get_json()
            if not data:
                print(f"  ✗ {method} {path}: no JSON data")
                return False

        print(f"  ✓ {method} {path} - {response.status_code}")

    return True

def test_api_state_response():
    """Test /api/state returns correct structure"""
    from app import app

    client = app.test_client()
    response = client.get('/api/state')
    data = response.get_json()

    # Verify structure
    assert 'focus_percentage' in data
    assert 'head_pose' in data
    assert 'facial_metrics' in data
    assert 'body_pose' in data

    # Verify types
    assert isinstance(data['focus_percentage'], (int, float))
    assert isinstance(data['head_pose'], dict)
    assert isinstance(data['facial_metrics'], dict)
    assert isinstance(data['body_pose'], dict)

    print(f"  ✓ Response structure correct")
    print(f"    Focus: {data['focus_percentage']}%")
    print(f"    Head Pose: Yaw={data['head_pose']['yaw']}°")
    print(f"    Emotion: {data['facial_metrics']['emotion']}")

    return True

def test_webcam_processor_init():
    """Test WebcamProcessor initializes correctly"""
    from app import WebcamProcessor, SessionState

    state = SessionState()
    processor = WebcamProcessor(state)

    assert processor.cap is None, "Camera should be closed initially"
    assert processor.running == False, "Should not be running initially"
    assert processor.pose is not None, "Pose model not loaded"
    assert processor.face_detection is not None, "Face detection not loaded"
    assert processor.face_mesh is not None, "Face mesh not loaded"

    print(f"  ✓ WebcamProcessor initialized")
    print(f"  ✓ Camera closed: {processor.cap is None}")
    print(f"  ✓ Not running: {not processor.running}")
    print(f"  ✓ Pose model loaded")
    print(f"  ✓ Face detection loaded")
    print(f"  ✓ Face mesh loaded")

    return True

def test_mediapipe_models():
    """Test MediaPipe models can be initialized"""
    import mediapipe as mp

    # Test Pose
    pose = mp.solutions.pose.Pose(
        static_image_mode=False,
        model_complexity=1
    )
    assert pose is not None
    print(f"  ✓ MediaPipe Pose initialized")

    # Test Face Detection
    face = mp.solutions.face_detection.FaceDetection(
        model_selection=0,
        min_detection_confidence=0.5
    )
    assert face is not None
    print(f"  ✓ MediaPipe Face Detection initialized")

    # Test Face Mesh
    mesh = mp.solutions.face_mesh.FaceMesh(
        static_image_mode=False,
        max_num_faces=1
    )
    assert mesh is not None
    print(f"  ✓ MediaPipe Face Mesh initialized")

    return True

def test_opencv_available():
    """Test OpenCV is available and working"""
    import cv2
    import numpy as np

    # Create test image
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    assert img.shape == (100, 100, 3)

    # Test flip
    flipped = cv2.flip(img, 1)
    assert flipped.shape == img.shape

    # Test color conversion
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    assert gray.shape == (100, 100)

    print(f"  ✓ OpenCV image operations work")
    print(f"  ✓ cv2.flip() works")
    print(f"  ✓ cv2.cvtColor() works")

    return True

def test_file_structure():
    """Test all required files exist"""
    files = {
        'app.py': 'Main application',
        'run.py': 'Launcher',
        'templates/index.html': 'Dashboard',
        'requirements.txt': 'Dependencies',
        'README.md': 'Documentation',
    }

    for file_path, description in files.items():
        full_path = Path(__file__).parent / file_path
        if not full_path.exists():
            print(f"  ✗ Missing: {file_path}")
            return False
        print(f"  ✓ {file_path} - {description}")

    return True

def test_requirements_complete():
    """Test requirements.txt has all needed packages"""
    req_file = Path(__file__).parent / 'requirements.txt'
    content = req_file.read_text()

    required = ['flask', 'opencv', 'mediapipe', 'numpy', 'socketio']

    for pkg in required:
        if pkg.lower() not in content.lower():
            print(f"  ✗ Missing package: {pkg}")
            return False
        print(f"  ✓ {pkg}")

    return True

# Main test runner
def main():
    print("="*60)
    print("FRESH TESTING SUITE - NO TRUST IN PREVIOUS TESTS")
    print("="*60)
    print("\nStarting from scratch to verify everything works...\n")

    runner = TestRunner()

    # Run all tests
    runner.test("Python Version Check", test_python_version)
    runner.test("Critical Imports", test_critical_imports)
    runner.test("App Module Loads", test_app_module_loads)
    runner.test("State Initialization", test_state_initialization)
    runner.test("State Mutation", test_state_mutation)
    runner.test("State Serialization", test_state_serialization)
    runner.test("Flask App Creation", test_flask_app_creation)
    runner.test("Flask Routes Exist", test_flask_routes_exist)
    runner.test("API Endpoints Callable", test_api_endpoints_callable)
    runner.test("API State Response", test_api_state_response)
    runner.test("WebcamProcessor Init", test_webcam_processor_init)
    runner.test("MediaPipe Models", test_mediapipe_models)
    runner.test("OpenCV Available", test_opencv_available)
    runner.test("File Structure", test_file_structure)
    runner.test("Requirements Complete", test_requirements_complete)

    # Summary
    success = runner.summary()
    return success

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
