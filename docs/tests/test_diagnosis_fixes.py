"""
Quick Verification Test for Diagnosis Fixes
Tests:
1. Module imports
2. GPU detection
3. Adaptive DeepFace backend selection
4. FaceMeshProcessor (no duplicate code)
"""

import sys
import os

def test_imports():
    """Test all critical modules can be imported"""
    print("=" * 60)
    print("TEST 1: Module Imports")
    print("=" * 60)

    try:
        from config_loader import config
        print("✅ config_loader imported")
    except Exception as e:
        print(f"❌ config_loader failed: {e}")
        return False

    try:
        from mediapipe_processors.face_mesh_processor import FaceMeshProcessor
        print("✅ FaceMeshProcessor imported")
    except Exception as e:
        print(f"❌ FaceMeshProcessor failed: {e}")
        return False

    try:
        from mediapipe_processors.deepface_emotion_detector import DeepFaceEmotionDetector
        print("✅ DeepFaceEmotionDetector imported")
    except Exception as e:
        print(f"❌ DeepFaceEmotionDetector failed: {e}")
        return False

    try:
        from improved_webcam_processor import ImprovedWebcamProcessor
        print("✅ ImprovedWebcamProcessor imported")
    except Exception as e:
        print(f"❌ ImprovedWebcamProcessor failed: {e}")
        return False

    print()
    return True

def test_gpu_detection():
    """Test GPU detection logic"""
    print("=" * 60)
    print("TEST 2: GPU Detection")
    print("=" * 60)

    try:
        import cv2
        import numpy as np

        # Check for CUDA
        cuda_available = False
        try:
            if cv2.cuda.getCudaEnabledDeviceCount() > 0:
                cuda_available = True
                print(f"🚀 CUDA devices: {cv2.cuda.getCudaEnabledDeviceCount()}")
        except:
            print("⚠️ CUDA not available")

        # Check for OpenCV DNN CUDA backend
        dnn_cuda = hasattr(cv2.dnn, 'DNN_BACKEND_CUDA')
        if dnn_cuda:
            print("🚀 OpenCV DNN CUDA backend available")

        # Check config setting
        from config_loader import config
        config_gpu = config.gpu_acceleration_enabled
        print(f"🔧 Config GPU acceleration: {config_gpu}")

        gpu_enabled = cuda_available and config_gpu
        print(f"\n📊 Final GPU Status: {'ENABLED' if gpu_enabled else 'DISABLED'}")

        print()
        return True
    except Exception as e:
        print(f"❌ GPU detection failed: {e}")
        return False

def test_adaptive_backend():
    """Test adaptive backend selection"""
    print("=" * 60)
    print("TEST 3: Adaptive DeepFace Backend")
    print("=" * 60)

    try:
        from config_loader import config
        from mediapipe_processors.deepface_emotion_detector import DeepFaceEmotionDetector

        # Test with GPU enabled
        print("\n🔧 Testing with GPU=True:")
        detector_gpu = DeepFaceEmotionDetector(config, gpu_enabled=True)
        print(f"   Backend: {detector_gpu.detector_backend}")
        print(f"   Expected: retinaface")
        if detector_gpu.detector_backend == 'retinaface':
            print("   ✅ PASS")
        else:
            print("   ❌ FAIL")
            return False

        # Test with GPU disabled
        print("\n🔧 Testing with GPU=False:")
        detector_cpu = DeepFaceEmotionDetector(config, gpu_enabled=False)
        print(f"   Backend: {detector_cpu.detector_backend}")
        print(f"   Expected: ssd")
        if detector_cpu.detector_backend == 'ssd':
            print("   ✅ PASS")
        else:
            print("   ❌ FAIL")
            return False

        print()
        return True
    except Exception as e:
        print(f"❌ Adaptive backend test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_no_duplicate_code():
    """Verify no duplicate code in FaceMeshProcessor"""
    print("=" * 60)
    print("TEST 4: No Duplicate Code Check")
    print("=" * 60)

    try:
        from mediapipe_processors.face_mesh_processor import FaceMeshProcessor

        # Check for unique method definitions
        import inspect

        # Get source code
        source = inspect.getsource(FaceMeshProcessor)

        # Count method definitions
        init_count = source.count('def __init__')
        process_count = source.count('def process(')
        extract_count = source.count('def _extract_face_metrics(')
        cleanup_count = source.count('def cleanup(')

        print(f"   __init__ definitions: {init_count} (expected: 1)")
        print(f"   process definitions: {process_count} (expected: 1)")
        print(f"   _extract_face_metrics definitions: {extract_count} (expected: 1)")
        print(f"   cleanup definitions: {cleanup_count} (expected: 1)")

        if init_count == 1 and process_count == 1 and extract_count == 1 and cleanup_count == 1:
            print("\n   ✅ PASS - No duplicate methods found")
            print()
            return True
        else:
            print("\n   ❌ FAIL - Duplicate methods detected!")
            print()
            return False

    except Exception as e:
        print(f"❌ Duplicate code check failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 15 + "DIAGNOSIS FIXES VERIFICATION" + " " * 16 + "║")
    print("╚" + "=" * 58 + "╝")
    print()

    results = {
        "Module Imports": test_imports(),
        "GPU Detection": test_gpu_detection(),
        "Adaptive Backend": test_adaptive_backend(),
        "No Duplicate Code": test_no_duplicate_code()
    }

    # Summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)

    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name:.<40} {status}")

    all_passed = all(results.values())
    print()
    if all_passed:
        print("🎉 ALL TESTS PASSED! Fixes are working correctly.")
        return 0
    else:
        print("⚠️ SOME TESTS FAILED. Please review the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
