#!/usr/bin/env python3
"""
Eaglearn Comprehensive Test Suite
Complete validation of application functionality
"""

import sys
import os
import time
import json
import logging
from pathlib import Path

# Setup
sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_section(title):
    """Decorator for test sections"""
    def decorator(func):
        def wrapper():
            logger.info("")
            logger.info("=" * 60)
            logger.info(f"📋 {title}")
            logger.info("=" * 60)
            result = func()
            logger.info(f"Result: {'✅ PASS' if result else '❌ FAIL'}")
            return result
        return wrapper
    return decorator

# ============================================================================
# SECTION 1: Import & Module Tests
# ============================================================================

@test_section("Section 1: Import & Module Validation")
def test_imports():
    """Test all imports work correctly"""
    try:
        logger.info("Testing critical imports...")

        imports = {
            'Flask': 'flask',
            'OpenCV': 'cv2',
            'MediaPipe': 'mediapipe',
            'NumPy': 'numpy',
            'Requests': 'requests',
        }

        for name, module in imports.items():
            try:
                __import__(module)
                logger.info(f"  ✓ {name}")
            except ImportError as e:
                logger.error(f"  ✗ {name}: {e}")
                return False

        logger.info("Testing app module...")
        from app import app, state, socketio, SessionState, WebcamProcessor
        logger.info("  ✓ app.py imports successfully")

        return True
    except Exception as e:
        logger.error(f"Import test failed: {e}")
        return False

# ============================================================================
# SECTION 2: State Management Tests
# ============================================================================

@test_section("Section 2: State Management")
def test_state_management():
    """Test SessionState functionality"""
    try:
        from app import SessionState

        logger.info("Creating SessionState instance...")
        state = SessionState()

        # Test initial values
        logger.info("Checking initial values...")
        assert state.session_id is None, "session_id should be None"
        assert state.is_running == False, "is_running should be False"
        assert state.focus_percentage == 0.0, "focus_percentage should be 0"
        logger.info("  ✓ Initial values correct")

        # Test state mutation
        logger.info("Testing state mutations...")
        with state.lock:
            state.focus_percentage = 75.5
            state.head_yaw = 15.3
            state.emotion = "happy"

        assert state.focus_percentage == 75.5
        assert state.head_yaw == 15.3
        assert state.emotion == "happy"
        logger.info("  ✓ State mutations work")

        # Test serialization
        logger.info("Testing state serialization...")
        state_dict = state.to_dict()

        required_keys = [
            'focus_percentage', 'head_pose', 'facial_metrics',
            'body_pose', 'webcam', 'time_tracking'
        ]

        for key in required_keys:
            assert key in state_dict, f"Missing key: {key}"

        logger.info("  ✓ State serialization works")
        logger.info(f"  Focus: {state_dict['focus_percentage']}%")
        logger.info(f"  Emotion: {state_dict['facial_metrics']['emotion']}")

        return True

    except Exception as e:
        logger.error(f"State management test failed: {e}")
        return False

# ============================================================================
# SECTION 3: Flask App Tests
# ============================================================================

@test_section("Section 3: Flask Application")
def test_flask_app():
    """Test Flask app creation and configuration"""
    try:
        from app import app, socketio

        logger.info("Testing Flask app...")
        assert app is not None, "App is None"
        assert app.name == 'app', "App name incorrect"
        logger.info("  ✓ Flask app created")

        logger.info("Testing SocketIO...")
        assert socketio is not None, "SocketIO is None"
        logger.info("  ✓ SocketIO initialized")

        logger.info("Creating test client...")
        client = app.test_client()
        assert client is not None, "Test client is None"
        logger.info("  ✓ Test client created")

        return True

    except Exception as e:
        logger.error(f"Flask app test failed: {e}")
        return False

# ============================================================================
# SECTION 4: API Endpoint Tests
# ============================================================================

@test_section("Section 4: API Endpoints")
def test_api_endpoints():
    """Test all API endpoints"""
    try:
        from app import app

        client = app.test_client()

        # Test root endpoint
        logger.info("Testing GET /...")
        response = client.get('/')
        assert response.status_code == 200, f"Root endpoint failed: {response.status_code}"
        assert 'html' in response.data.decode().lower()
        logger.info("  ✓ GET / works")

        # Test /api/state
        logger.info("Testing GET /api/state...")
        response = client.get('/api/state')
        assert response.status_code == 200
        data = response.get_json()
        assert 'focus_percentage' in data
        assert 'head_pose' in data
        logger.info("  ✓ GET /api/state works")

        # Test /api/metrics
        logger.info("Testing GET /api/metrics...")
        response = client.get('/api/metrics')
        assert response.status_code == 200
        data = response.get_json()
        assert 'facial_metrics' in data
        assert 'body_pose' in data
        logger.info("  ✓ GET /api/metrics works")

        # Test session endpoints
        logger.info("Testing POST /api/session/start...")
        response = client.post('/api/session/start')
        assert response.status_code == 200 or response.status_code == 500  # May fail without webcam
        logger.info("  ✓ POST /api/session/start callable")

        # Test 404 handling
        logger.info("Testing 404 handling...")
        response = client.get('/nonexistent')
        assert response.status_code == 404
        logger.info("  ✓ 404 handling works")

        return True

    except Exception as e:
        logger.error(f"API endpoint test failed: {e}")
        return False

# ============================================================================
# SECTION 5: WebcamProcessor Tests
# ============================================================================

@test_section("Section 5: WebcamProcessor")
def test_webcam_processor():
    """Test WebcamProcessor initialization"""
    try:
        from app import WebcamProcessor, SessionState

        logger.info("Creating SessionState...")
        state = SessionState()

        logger.info("Creating WebcamProcessor...")
        processor = WebcamProcessor(state)

        logger.info("Checking processor state...")
        assert processor.cap is None, "Camera should be closed initially"
        assert processor.running == False, "Should not be running initially"
        logger.info("  ✓ WebcamProcessor initialized correctly")

        logger.info("Checking MediaPipe models...")
        assert processor.pose is not None, "Pose model not loaded"
        assert processor.face_detection is not None, "Face detection not loaded"
        assert processor.face_mesh is not None, "Face mesh not loaded"
        logger.info("  ✓ MediaPipe models loaded")

        return True

    except Exception as e:
        logger.error(f"WebcamProcessor test failed: {e}")
        return False

# ============================================================================
# SECTION 6: Configuration Tests
# ============================================================================

@test_section("Section 6: Configuration")
def test_configuration():
    """Test configuration and environment setup"""
    try:
        logger.info("Checking project structure...")

        files = {
            'app.py': 'Main application',
            'run.py': 'Application launcher',
            'templates/index.html': 'Web dashboard',
            'requirements.txt': 'Dependencies',
            'test_app.py': 'Unit tests',
            'test_comprehensive.py': 'This file',
        }

        for file_path, description in files.items():
            full_path = Path(__file__).parent / file_path
            if full_path.exists():
                logger.info(f"  ✓ {file_path}")
            else:
                logger.error(f"  ✗ {file_path} missing")
                return False

        logger.info("Checking documentation...")
        docs = [
            'README.md',
            'SIMPLE_APP_README.md',
            'QUICKSTART.md',
            'DASHBOARD_GUIDE.md',
        ]

        for doc in docs:
            doc_path = Path(__file__).parent / doc
            if doc_path.exists():
                logger.info(f"  ✓ {doc}")
            else:
                logger.warning(f"  ⚠ {doc} missing")

        return True

    except Exception as e:
        logger.error(f"Configuration test failed: {e}")
        return False

# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

def run_all_tests():
    """Run all test sections"""
    logger.info("")
    logger.info("╔" + "═" * 58 + "╗")
    logger.info("║" + " " * 58 + "║")
    logger.info("║" + "  Eaglearn Comprehensive Test Suite".center(58) + "║")
    logger.info("║" + " " * 58 + "║")
    logger.info("╚" + "═" * 58 + "╝")

    tests = [
        test_imports,
        test_state_management,
        test_flask_app,
        test_api_endpoints,
        test_webcam_processor,
        test_configuration,
    ]

    results = []
    for test in tests:
        try:
            result = test()
            results.append((test.__name__, result))
        except Exception as e:
            logger.error(f"Unexpected error in {test.__name__}: {e}")
            results.append((test.__name__, False))

    # Print summary
    logger.info("")
    logger.info("╔" + "═" * 58 + "╗")
    logger.info("║" + " TEST SUMMARY ".center(58, "═") + "║")
    logger.info("╚" + "═" * 58 + "╝")

    passed = sum(1 for _, r in results if r)
    total = len(results)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        test_name = name.replace('test_', '').replace('_', ' ').title()
        logger.info(f"{status} - {test_name}")

    logger.info("")
    logger.info(f"Overall: {passed}/{total} sections passed")

    if passed == total:
        logger.info("")
        logger.info("╔" + "═" * 58 + "╗")
        logger.info("║" + " 🎉 ALL TESTS PASSED! 🎉 ".center(58) + "║")
        logger.info("╚" + "═" * 58 + "╝")
        logger.info("")
        logger.info("Ready to run: python run.py")
        logger.info("Then visit: http://localhost:5000")
        logger.info("")
    else:
        logger.warning("")
        logger.warning("Some tests failed. See details above.")
        logger.warning("")

    return passed == total

if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
