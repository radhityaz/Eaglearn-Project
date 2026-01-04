#!/usr/bin/env python3
"""
Eaglearn Application Verification
Comprehensive end-to-end verification script
"""

import sys
import time
import json
import logging
import subprocess
import requests
from pathlib import Path
from threading import Thread

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AppVerifier:
    """Verify Eaglearn application functionality"""

    def __init__(self):
        self.app_process = None
        self.app_ready = False
        self.base_url = 'http://localhost:5000'

    def start_app(self, timeout=30):
        """Start the Flask application"""
        logger.info("Starting Eaglearn Flask application...")
        try:
            self.app_process = subprocess.Popen(
                [sys.executable, 'run.py'],
                cwd='D:\\Eaglearn-Project',
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Wait for app to be ready
            start_time = time.time()
            while time.time() - start_time < timeout:
                try:
                    response = requests.get(f'{self.base_url}/', timeout=2)
                    if response.status_code == 200:
                        self.app_ready = True
                        logger.info("✓ Application ready")
                        return True
                except:
                    time.sleep(0.5)

            logger.error("✗ Application failed to start within timeout")
            return False

        except Exception as e:
            logger.error(f"✗ Failed to start application: {e}")
            return False

    def stop_app(self):
        """Stop the Flask application"""
        if self.app_process:
            logger.info("Stopping application...")
            self.app_process.terminate()
            try:
                self.app_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.app_process.kill()
            logger.info("✓ Application stopped")

    def test_root_endpoint(self):
        """Test root endpoint"""
        logger.info("Testing root endpoint...")
        try:
            response = requests.get(f'{self.base_url}/')
            assert response.status_code == 200
            assert 'html' in response.text.lower()
            logger.info("✓ Root endpoint working")
            return True
        except Exception as e:
            logger.error(f"✗ Root endpoint failed: {e}")
            return False

    def test_api_state(self):
        """Test /api/state endpoint"""
        logger.info("Testing /api/state endpoint...")
        try:
            response = requests.get(f'{self.base_url}/api/state')
            assert response.status_code == 200

            data = response.json()
            required_keys = [
                'session_id', 'is_running', 'focus_percentage',
                'head_pose', 'facial_metrics', 'body_pose',
                'webcam', 'time_tracking'
            ]

            for key in required_keys:
                assert key in data, f"Missing key: {key}"

            logger.info(f"✓ /api/state endpoint working")
            logger.info(f"  Focus: {data['focus_percentage']}%")
            logger.info(f"  Running: {data['is_running']}")
            return True

        except Exception as e:
            logger.error(f"✗ /api/state endpoint failed: {e}")
            return False

    def test_api_metrics(self):
        """Test /api/metrics endpoint"""
        logger.info("Testing /api/metrics endpoint...")
        try:
            response = requests.get(f'{self.base_url}/api/metrics')
            assert response.status_code == 200

            data = response.json()
            assert 'head_pose' in data
            assert 'facial_metrics' in data
            assert 'body_pose' in data

            logger.info("✓ /api/metrics endpoint working")
            return True

        except Exception as e:
            logger.error(f"✗ /api/metrics endpoint failed: {e}")
            return False

    def test_session_endpoints(self):
        """Test session control endpoints"""
        logger.info("Testing session endpoints...")
        try:
            # Start session
            logger.info("  Starting session...")
            response = requests.post(f'{self.base_url}/api/session/start')
            if response.status_code != 200:
                logger.error(f"  ✗ Start session failed: {response.status_code}")
                return False

            data = response.json()
            assert 'session_id' in data
            logger.info(f"  ✓ Session started: {data['session_id']}")

            time.sleep(1)

            # Check state
            response = requests.get(f'{self.base_url}/api/state')
            state = response.json()
            assert state['is_running'] == True
            logger.info("  ✓ Session state confirmed running")

            # Stop session
            logger.info("  Stopping session...")
            response = requests.post(f'{self.base_url}/api/session/stop')
            if response.status_code != 200:
                logger.error(f"  ✗ Stop session failed: {response.status_code}")
                return False

            logger.info("  ✓ Session stopped")

            # Verify state
            response = requests.get(f'{self.base_url}/api/state')
            state = response.json()
            assert state['is_running'] == False
            logger.info("  ✓ Session state confirmed stopped")

            logger.info("✓ Session endpoints working")
            return True

        except Exception as e:
            logger.error(f"✗ Session endpoints failed: {e}")
            return False

    def test_error_handling(self):
        """Test error handling"""
        logger.info("Testing error handling...")
        try:
            # Test 404
            response = requests.get(f'{self.base_url}/nonexistent')
            assert response.status_code == 404

            logger.info("✓ Error handling working (404 handled)")
            return True

        except Exception as e:
            logger.error(f"✗ Error handling test failed: {e}")
            return False

    def run_verification(self):
        """Run all verification tests"""
        logger.info("=" * 60)
        logger.info("Eaglearn Application Verification")
        logger.info("=" * 60)

        tests = [
            self.test_root_endpoint,
            self.test_api_state,
            self.test_api_metrics,
            self.test_session_endpoints,
            self.test_error_handling,
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
        logger.info("Verification Summary")
        logger.info("=" * 60)

        passed = sum(1 for _, r in results if r)
        total = len(results)

        for name, result in results:
            status = "✓ PASS" if result else "✗ FAIL"
            test_name = name.replace('test_', '')
            logger.info(f"{status} - {test_name}")

        logger.info("=" * 60)
        logger.info(f"Results: {passed}/{total} tests passed")
        logger.info("=" * 60)

        return passed == total

def main():
    """Main entry point"""
    verifier = AppVerifier()

    try:
        # Start application
        if not verifier.start_app(timeout=30):
            logger.error("Failed to start application")
            return False

        # Run verification
        success = verifier.run_verification()

        return success

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return False

    except Exception as e:
        logger.error(f"Verification failed: {e}")
        return False

    finally:
        # Stop application
        verifier.stop_app()

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
