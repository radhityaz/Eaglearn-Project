#!/usr/bin/env python3
"""
Test script specifically for MediaPipe timestamp and error handling fixes
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
from mediapipe_processors import FaceMeshProcessor, PoseProcessor, DeepFaceEmotionDetector

# Configure logging to see debug messages
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

class MockState:
    """Mock state object for testing"""
    def __init__(self):
        self.frame_count = 0
        self.emotion = 'neutral'
        self.emotion_confidence = 0.5

def test_mediapipe_timestamp_handling():
    """Test MediaPipe timestamp error handling"""
    logger.info("=== Testing MediaPipe timestamp handling ===")
    
    try:
        face_processor = FaceMeshProcessor(config)
        pose_processor = PoseProcessor(config)
        
        # Create test frames with different "timestamps"
        test_frames = []
        for i in range(10):
            # Create frames with different content to simulate real camera feed
            frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
            # Add some structure to make it more realistic
            cv2.rectangle(frame, (100+i*10, 100+i*10), (200+i*10, 200+i*10), (255, 255, 255), -1)
            test_frames.append(frame)
        
        mock_state = MockState()
        
        # Test rapid processing that might cause timestamp conflicts
        logger.info("Testing rapid frame processing...")
        for i, frame in enumerate(test_frames):
            mock_state.frame_count = i
            
            # Test face processing
            try:
                face_result = face_processor.process(frame, mock_state)
                logger.debug(f"Frame {i}: face_detected={face_result.get('face_detected', False)}")
            except Exception as e:
                logger.error(f"Face processing failed on frame {i}: {e}")
                return False
            
            # Test pose processing
            try:
                pose_result = pose_processor.process(frame)
                logger.debug(f"Frame {i}: body_detected={pose_result.get('body_detected', False)}")
            except Exception as e:
                logger.error(f"Pose processing failed on frame {i}: {e}")
                return False
            
            # Small delay to simulate real processing
            time.sleep(0.01)
        
        logger.info("✅ MediaPipe timestamp handling test passed")
        return True
        
    except Exception as e:
        logger.error(f"MediaPipe test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_error_recovery():
    """Test error recovery and reinitialization"""
    logger.info("=== Testing error recovery ===")
    
    try:
        face_processor = FaceMeshProcessor(config)
        
        # Test with invalid frames that should trigger errors
        invalid_frames = [
            None,
            "string_frame",
            np.array([1, 2, 3]),  # Wrong dimensions
            np.zeros((100, 100)),  # Missing color channel
        ]
        
        mock_state = MockState()
        
        for i, invalid_frame in enumerate(invalid_frames):
            logger.info(f"Testing invalid frame type {i+1}: {type(invalid_frame)}")
            try:
                result = face_processor.process(invalid_frame, mock_state)
                logger.debug(f"Result for invalid frame {i+1}: {result}")
            except Exception as e:
                logger.error(f"Unexpected exception for invalid frame {i+1}: {e}")
                return False
        
        # Test recovery with valid frame
        logger.info("Testing recovery with valid frame...")
        valid_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        result = face_processor.process(valid_frame, mock_state)
        logger.debug(f"Recovery result: {result}")
        
        logger.info("✅ Error recovery test passed")
        return True
        
    except Exception as e:
        logger.error(f"Error recovery test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_consecutive_error_handling():
    """Test consecutive error handling and graph reinitialization"""
    logger.info("=== Testing consecutive error handling ===")
    
    try:
        face_processor = FaceMeshProcessor(config)
        
        # Force multiple errors to trigger reinitialization
        mock_state = MockState()
        
        # Send multiple invalid frames
        for i in range(10):
            invalid_frame = None
            result = face_processor.process(invalid_frame, mock_state)
            logger.debug(f"Error frame {i+1}: consecutive_errors={getattr(face_processor, 'consecutive_errors', 'N/A')}")
        
        # Now send a valid frame to test recovery
        valid_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        result = face_processor.process(valid_frame, mock_state)
        logger.debug(f"Recovery after errors: {result}")
        
        logger.info("✅ Consecutive error handling test passed")
        return True
        
    except Exception as e:
        logger.error(f"Consecutive error test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_deepface_tuple_prevention():
    """Test that DeepFace tuple errors are prevented"""
    logger.info("=== Testing DeepFace tuple error prevention ===")
    
    try:
        detector = DeepFaceEmotionDetector(config)
        
        # Test various problematic inputs
        problematic_inputs = [
            None,
            (np.zeros((100, 100, 3), dtype=np.uint8), "extra_data"),
            [np.zeros((100, 100, 3), dtype=np.uint8)],
            "string_frame",
            123,
        ]
        
        for i, problematic_input in enumerate(problematic_inputs):
            logger.info(f"Testing problematic input {i+1}: {type(problematic_input)}")
            result = detector.detect_emotion(problematic_input)
            
            # Should always return a valid result with fallback method
            assert result['method'] == 'fallback', f"Should fallback for input {i+1}"
            assert result['emotion'] == 'neutral', f"Should return neutral for input {i+1}"
            
            logger.debug(f"Result for input {i+1}: method={result['method']}")
        
        logger.info("✅ DeepFace tuple prevention test passed")
        return True
        
    except Exception as e:
        logger.error(f"DeepFace prevention test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_cleanup_safety():
    """Test cleanup safety with None objects"""
    logger.info("=== Testing cleanup safety ===")
    
    try:
        # Test cleanup on fresh processors
        face_processor = FaceMeshProcessor(config)
        pose_processor = PoseProcessor(config)
        
        # Test cleanup without any processing
        try:
            face_processor.cleanup()
            pose_processor.cleanup()
            logger.debug("Cleanup without processing: successful")
        except Exception as e:
            logger.error(f"Cleanup without processing failed: {e}")
            return False
        
        # Test cleanup after processing
        face_processor2 = FaceMeshProcessor(config)
        pose_processor2 = PoseProcessor(config)
        
        mock_state = MockState()
        valid_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        face_processor2.process(valid_frame, mock_state)
        pose_processor2.process(valid_frame)
        
        try:
            face_processor2.cleanup()
            pose_processor2.cleanup()
            logger.debug("Cleanup after processing: successful")
        except Exception as e:
            logger.error(f"Cleanup after processing failed: {e}")
            return False
        
        logger.info("✅ Cleanup safety test passed")
        return True
        
    except Exception as e:
        logger.error(f"Cleanup safety test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all MediaPipe tests"""
    logger.info("Starting MediaPipe fixes verification tests")
    
    tests = [
        ("MediaPipe Timestamp Handling", test_mediapipe_timestamp_handling),
        ("Error Recovery", test_error_recovery),
        ("Consecutive Error Handling", test_consecutive_error_handling),
        ("DeepFace Tuple Prevention", test_deepface_tuple_prevention),
        ("Cleanup Safety", test_cleanup_safety),
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
        logger.info("🎉 All MediaPipe fixes are working correctly!")
        return 0
    else:
        logger.error("⚠️ Some tests failed - review the fixes")
        return 1

if __name__ == "__main__":
    sys.exit(main())