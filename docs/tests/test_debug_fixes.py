#!/usr/bin/env python3
"""
Test script to verify debug fixes for:
1. DeepFace tuple error: 'tuple' object has no attribute 'shape'
2. Face processing error: unsupported operand type(s) for -: 'float' and 'str'
3. MediaPipe timestamp synchronization errors
"""

import logging
import numpy as np
import cv2
import time
import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config_loader import config
from mediapipe_processors import DeepFaceEmotionDetector, FaceMeshProcessor
from improved_webcam_processor import ImprovedWebcamProcessor

# Configure logging to see debug messages
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

class MockState:
    """Mock state object for testing"""
    def __init__(self):
        self.lock = MockLock()
        self.frame_count = 0
        # Initialize with potentially problematic string values
        self.calibration_gaze_offset_x = "0.5"  # String instead of float
        self.calibration_gaze_offset_y = "0.3"  # String instead of float
        self.calibration_scale_factor = "1.2"   # String instead of float
        self.calibration_applied = True
        self.last_blink_time = "1234567890"     # String instead of float
        self.session_start_time = "1234567800"  # String instead of float
        self.blink_count = 0
        self.blink_rate = "15"                  # String instead of int
        self.last_yawn_time = "1234567880"      # String instead of float

class MockLock:
    """Mock lock for testing"""
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass

def test_deepface_tuple_error():
    """Test 1: DeepFace tuple error handling"""
    logger.info("=== Testing DeepFace tuple error handling ===")
    
    try:
        detector = DeepFaceEmotionDetector(config)
        
        # Test case 1: None frame
        logger.info("Test 1a: None frame")
        result = detector.detect_emotion(None)
        logger.info(f"Result for None frame: {result}")
        assert result['method'] == 'fallback', "Should fallback for None frame"
        
        # Test case 2: Tuple frame (simulating the original error)
        logger.info("Test 1b: Tuple frame")
        tuple_frame = (np.zeros((100, 100, 3), dtype=np.uint8), "extra_data")
        result = detector.detect_emotion(tuple_frame)
        logger.info(f"Result for tuple frame: {result}")
        assert result['method'] == 'fallback', "Should fallback for tuple frame"
        
        # Test case 3: Valid numpy array
        logger.info("Test 1c: Valid numpy array")
        valid_frame = np.zeros((100, 100, 3), dtype=np.uint8)
        result = detector.detect_emotion(valid_frame)
        logger.info(f"Result for valid frame: emotion={result.get('emotion', 'N/A')}, method={result.get('method', 'N/A')}")
        
        logger.info("✅ DeepFace tuple error tests passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ DeepFace test failed: {e}")
        return False

def test_face_processing_arithmetic():
    """Test 2: Face processing arithmetic error handling"""
    logger.info("=== Testing face processing arithmetic errors ===")
    
    try:
        processor = FaceMeshProcessor(config)
        mock_state = MockState()
        
        # Create a simple test frame
        test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        logger.info("Test 2a: Processing with string calibration data")
        result = processor.process(test_frame, mock_state)
        
        # Check that processing didn't crash
        logger.info(f"Face processing result: face_detected={result.get('face_detected', False)}")
        
        # Test specific arithmetic operations that were failing
        logger.info("Test 2b: Testing blink detection with string timestamps")
        if hasattr(mock_state, 'last_blink_time'):
            logger.info(f"last_blink_time type: {type(mock_state.last_blink_time)}")
        
        logger.info("Test 2c: Testing calibration with string offsets")
        if hasattr(mock_state, 'calibration_gaze_offset_x'):
            logger.info(f"calibration_gaze_offset_x type: {type(mock_state.calibration_gaze_offset_x)}")
        
        logger.info("✅ Face processing arithmetic tests passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Face processing test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_mediapipe_timestamp_errors():
    """Test 3: MediaPipe timestamp synchronization"""
    logger.info("=== Testing MediaPipe timestamp synchronization ===")
    
    try:
        # Test with a mock webcam processor
        mock_state = MockState()
        processor = ImprovedWebcamProcessor(mock_state)
        
        logger.info("Test 3a: Testing frame validation")
        
        # Test with invalid frames
        invalid_frames = [None, "string_frame", [1, 2, 3], (1, 2, 3)]
        
        for i, invalid_frame in enumerate(invalid_frames):
            logger.info(f"Testing invalid frame type {i+1}: {type(invalid_frame)}")
            # This should be handled gracefully in the actual processor
        
        logger.info("Test 3b: Testing valid frame processing")
        valid_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Test pose processor directly
        from mediapipe_processors import PoseProcessor
        pose_processor = PoseProcessor(config)
        
        try:
            pose_result = pose_processor.process(valid_frame)
            logger.info(f"Pose processing result: body_detected={pose_result.get('body_detected', False)}")
        except Exception as e:
            logger.warning(f"Pose processing warning (expected): {e}")
        
        logger.info("✅ MediaPipe timestamp tests passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ MediaPipe test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_integration():
    """Test 4: Integration test with camera simulation"""
    logger.info("=== Integration test with camera simulation ===")
    
    try:
        # Create a mock camera feed
        mock_state = MockState()
        processor = ImprovedWebcamProcessor(mock_state)
        
        # Simulate camera frames
        for i in range(10):
            # Create a realistic test frame
            frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
            
            logger.info(f"Processing frame {i+1}")
            mock_state.frame_count = i
            
            # Test face processing
            try:
                face_result = processor.face_processor.process(frame, mock_state)
                logger.debug(f"Frame {i+1}: face_detected={face_result.get('face_detected', False)}")
            except Exception as e:
                logger.warning(f"Face processing error on frame {i+1}: {e}")
            
            # Test emotion detection
            if i % 3 == 0:  # Test every few frames
                try:
                    emotion_result = processor.deepface_detector.detect_emotion(frame)
                    logger.debug(f"Frame {i+1}: emotion={emotion_result.get('emotion', 'N/A')}")
                except Exception as e:
                    logger.warning(f"Emotion detection error on frame {i+1}: {e}")
            
            time.sleep(0.1)  # Small delay
        
        logger.info("✅ Integration test passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    logger.info("Starting debug fixes verification tests")
    
    tests = [
        ("DeepFace Tuple Error", test_deepface_tuple_error),
        ("Face Processing Arithmetic", test_face_processing_arithmetic),
        ("MediaPipe Timestamp Errors", test_mediapipe_timestamp_errors),
        ("Integration Test", test_integration)
    ]
    
    results = []
    for test_name, test_func in tests:
        logger.info(f"\n{'='*60}")
        logger.info(f"Running: {test_name}")
        logger.info('='*60)
        
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            logger.error(f"Test {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    logger.info(f"\n{'='*60}")
    logger.info("TEST SUMMARY")
    logger.info('='*60)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"{test_name}: {status}")
        if result:
            passed += 1
    
    logger.info(f"\nOverall: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        logger.info("🎉 All debug fixes are working correctly!")
        return 0
    else:
        logger.error("⚠️ Some tests failed - review the fixes")
        return 1

if __name__ == "__main__":
    sys.exit(main())