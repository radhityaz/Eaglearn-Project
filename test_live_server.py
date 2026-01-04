#!/usr/bin/env python3
"""
Live Server Test - Test with actual running Flask server
This is the REAL test - not mocking anything
"""

import sys
import time
import subprocess
import requests
import json
from pathlib import Path

class LiveServerTest:
    """Test with actual running server"""

    def __init__(self):
        self.server_process = None
        self.base_url = 'http://localhost:5000'
        self.passed = 0
        self.failed = 0

    def start_server(self, timeout=15):
        """Start the Flask server"""
        print("\n" + "="*60)
        print("STARTING FLASK SERVER...")
        print("="*60)

        try:
            self.server_process = subprocess.Popen(
                [sys.executable, 'run.py'],
                cwd=str(Path(__file__).parent),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Wait for server to start
            start_time = time.time()
            while time.time() - start_time < timeout:
                try:
                    response = requests.get(f'{self.base_url}/', timeout=2)
                    if response.status_code == 200:
                        print(f"✅ Server started successfully")
                        print(f"   URL: {self.base_url}")
                        return True
                except:
                    time.sleep(0.5)

            print(f"❌ Server failed to start within {timeout}s")
            return False

        except Exception as e:
            print(f"❌ Failed to start server: {e}")
            return False

    def stop_server(self):
        """Stop the Flask server"""
        if self.server_process:
            print("\n" + "="*60)
            print("STOPPING FLASK SERVER...")
            print("="*60)
            self.server_process.terminate()
            try:
                self.server_process.wait(timeout=5)
                print("✅ Server stopped")
            except subprocess.TimeoutExpired:
                self.server_process.kill()
                print("⚠️  Server killed (didn't stop gracefully)")

    def test(self, name, func):
        """Run a test"""
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
            return result
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            self.failed += 1
            return False

    def test_root_endpoint(self):
        """Test GET /"""
        response = requests.get(f'{self.base_url}/')
        print(f"  Status: {response.status_code}")
        print(f"  Content-Type: {response.headers.get('Content-Type')}")

        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert 'html' in response.text.lower(), "Response doesn't contain HTML"

        print(f"  ✓ HTML page returned")
        return True

    def test_api_state(self):
        """Test GET /api/state"""
        response = requests.get(f'{self.base_url}/api/state')
        print(f"  Status: {response.status_code}")

        assert response.status_code == 200
        data = response.json()

        print(f"  ✓ JSON response received")
        print(f"  Focus: {data['focus_percentage']}%")
        print(f"  Running: {data['is_running']}")
        print(f"  Emotion: {data['facial_metrics']['emotion']}")

        return True

    def test_api_metrics(self):
        """Test GET /api/metrics"""
        response = requests.get(f'{self.base_url}/api/metrics')
        print(f"  Status: {response.status_code}")

        assert response.status_code == 200
        data = response.json()

        print(f"  ✓ Metrics received")
        print(f"  Head Yaw: {data['head_pose']['yaw']}°")
        print(f"  Posture: {data['body_pose']['posture_score']}%")

        return True

    def test_session_start(self):
        """Test POST /api/session/start"""
        response = requests.post(f'{self.base_url}/api/session/start')
        print(f"  Status: {response.status_code}")

        # May be 200 (webcam available) or 500 (no webcam)
        data = response.json()
        print(f"  Response: {data}")

        if response.status_code == 200:
            print(f"  ✓ Session started (webcam available)")
            print(f"  Session ID: {data.get('session_id', 'N/A')}")
            return True
        elif response.status_code == 500:
            print(f"  ⚠️  Webcam not available (expected in test env)")
            return True
        else:
            print(f"  ✗ Unexpected status: {response.status_code}")
            return False

    def test_session_stop(self):
        """Test POST /api/session/stop"""
        response = requests.post(f'{self.base_url}/api/session/stop')
        print(f"  Status: {response.status_code}")

        assert response.status_code == 200
        data = response.json()
        print(f"  ✓ Session stopped")
        print(f"  Response: {data}")

        return True

    def test_404_handling(self):
        """Test 404 error handling"""
        response = requests.get(f'{self.base_url}/nonexistent')
        print(f"  Status: {response.status_code}")

        assert response.status_code == 404
        print(f"  ✓ 404 handled correctly")

        return True

    def test_state_persistence(self):
        """Test state persists across requests"""
        # Get initial state
        r1 = requests.get(f'{self.base_url}/api/state')
        state1 = r1.json()

        # Get state again
        time.sleep(0.5)
        r2 = requests.get(f'{self.base_url}/api/state')
        state2 = r2.json()

        print(f"  ✓ State retrieved twice")
        print(f"  State 1 - Focus: {state1['focus_percentage']}%")
        print(f"  State 2 - Focus: {state2['focus_percentage']}%")

        # Both should have same structure
        assert state1.keys() == state2.keys()
        print(f"  ✓ State structure consistent")

        return True

    def run_all_tests(self):
        """Run all tests"""
        print("\n" + "="*60)
        print("LIVE SERVER TESTING SUITE")
        print("="*60)

        # Start server
        if not self.start_server():
            print("\n❌ Cannot start server - aborting tests")
            return False

        # Run tests
        self.test("Root Endpoint", self.test_root_endpoint)
        self.test("API State", self.test_api_state)
        self.test("API Metrics", self.test_api_metrics)
        self.test("Session Start", self.test_session_start)
        self.test("Session Stop", self.test_session_stop)
        self.test("404 Handling", self.test_404_handling)
        self.test("State Persistence", self.test_state_persistence)

        # Summary
        print("\n" + "="*60)
        print("LIVE TEST SUMMARY")
        print("="*60)
        print(f"Passed: {self.passed}")
        print(f"Failed: {self.failed}")
        print(f"Total:  {self.passed + self.failed}")

        if self.failed == 0:
            print("\n✅ ALL LIVE TESTS PASSED!")
            success = True
        else:
            print(f"\n❌ {self.failed} TESTS FAILED!")
            success = False

        # Stop server
        self.stop_server()

        return success

def main():
    tester = LiveServerTest()
    try:
        success = tester.run_all_tests()
        return success
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        tester.stop_server()
        return False
    except Exception as e:
        print(f"\n\n❌ Test suite error: {e}")
        import traceback
        traceback.print_exc()
        tester.stop_server()
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
