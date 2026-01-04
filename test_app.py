#!/usr/bin/env python3
"""
Eaglearn Application Test Suite
Tests API endpoints and basic functionality
"""

import sys
import json
import time
import logging
from pathlib import Path

# Add project root
sys.path.insert(0, str(Path(__file__).parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_imports():
    """Test that all imports work"""
    logger.info("Testing imports...")
    try:
        import app
        import cv2
        import mediapipe as mp
        import flask
        import flask_socketio
        logger.info("✓ All imports successful")
        return True
    except Exception as e:
        logger.error(f"✗ Import failed: {e}")
        return False

def test_state_creation():
    """Test SessionState creation"""
    logger.info("Testing SessionState...")
    try:
        from app import SessionState
        state = SessionState()

        # Verify initial state
        assert state.session_id is None
        assert state.is_running == False
        assert state.focus_percentage == 0.0
        assert state.head_yaw == 0.0
        assert state.emotion == "neutral"

        logger.info("✓ SessionState created successfully")
        return True
    except Exception as e:
        logger.error(f"✗ SessionState test failed: {e}")
        return False

def test_state_to_dict():
    """Test state serialization"""
    logger.info("Testing state serialization...")
    try:
        from app import SessionState
        state = SessionState()
        state_dict = state.to_dict()

        # Verify all keys exist
        required_keys = [
            'session_id', 'is_running', 'focus_percentage',
            'head_pose', 'facial_metrics', 'body_pose',
            'webcam', 'time_tracking'
        ]

        for key in required_keys:
            assert key in state_dict, f"Missing key: {key}"

        logger.info(f"✓ State serialization successful")
        logger.info(f"  State structure: {json.dumps(state_dict, indent=2)[:500]}...")
        return True
    except Exception as e:
        logger.error(f"✗ State serialization test failed: {e}")
        return False

def test_flask_app():
    """Test Flask app creation"""
    logger.info("Testing Flask app...")
    try:
        from app import app, socketio

        # Create test client
        client = app.test_client()

        # Test root endpoint
        response = client.get('/')
        assert response.status_code == 200, f"Root endpoint failed: {response.status_code}"

        logger.info("✓ Flask app created successfully")
        return True
    except Exception as e:
        logger.error(f"✗ Flask app test failed: {e}")
        return False

def test_api_endpoints():
    """Test API endpoints"""
    logger.info("Testing API endpoints...")
    try:
        from app import app, state
        client = app.test_client()

        # Test /api/state endpoint
        response = client.get('/api/state')
        assert response.status_code == 200
        data = response.get_json()
        assert 'focus_percentage' in data

        # Test /api/metrics endpoint
        response = client.get('/api/metrics')
        assert response.status_code == 200
        data = response.get_json()
        assert 'head_pose' in data

        logger.info("✓ API endpoints working correctly")
        return True
    except Exception as e:
        logger.error(f"✗ API endpoints test failed: {e}")
        return False

def test_webcam_processor():
    """Test WebcamProcessor creation"""
    logger.info("Testing WebcamProcessor...")
    try:
        from app import WebcamProcessor, SessionState
        state = SessionState()
        processor = WebcamProcessor(state)

        assert processor.cap is None, "Camera should not be open initially"
        assert processor.running == False

        logger.info("✓ WebcamProcessor created successfully")
        return True
    except Exception as e:
        logger.error(f"✗ WebcamProcessor test failed: {e}")
        return False

def run_all_tests():
    """Run all tests"""
    logger.info("=" * 60)
    logger.info("Eaglearn Application Test Suite")
    logger.info("=" * 60)

    tests = [
        test_imports,
        test_state_creation,
        test_state_to_dict,
        test_flask_app,
        test_api_endpoints,
        test_webcam_processor,
    ]

    results = []
    for test in tests:
        try:
            result = test()
            results.append((test.__name__, result))
        except Exception as e:
            logger.error(f"Exception in {test.__name__}: {e}")
            results.append((test.__name__, False))

        logger.info("")

    # Print summary
    logger.info("=" * 60)
    logger.info("Test Summary")
    logger.info("=" * 60)

    passed = sum(1 for _, r in results if r)
    total = len(results)

    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        logger.info(f"{status} - {name}")

    logger.info("=" * 60)
    logger.info(f"Results: {passed}/{total} tests passed")
    logger.info("=" * 60)

    return passed == total

if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
