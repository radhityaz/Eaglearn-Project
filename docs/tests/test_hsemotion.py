"""
Quick test for HSEmotion detector
"""
import logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

print("=" * 60)
print("Testing HSEmotion Detector")
print("=" * 60)

# Test 1: Import
print("\n[Test 1] Importing HSEmotion...")
try:
    from mediapipe_processors.hsemotion_emotion_detector import HSEmotionDetector
    print("✅ Import successful")
except Exception as e:
    print(f"❌ Import failed: {e}")
    exit(1)

# Test 2: Initialize detector
print("\n[Test 2] Initializing detector...")
try:
    from config_loader import config
    detector = HSEmotionDetector(config)
    print(f"✅ Detector initialized")
    print(f"   - Available: {detector.available}")
    print(f"   - Model: {detector.model_name}")
    print(f"   - Device: {detector.device}")
except Exception as e:
    print(f"❌ Initialization failed: {e}")
    exit(1)

# Test 3: Load model
print("\n[Test 3] Loading model (may take 10-30 seconds)...")
try:
    detector._load_model()
    print(f"✅ Model loaded: {detector.model}")
except Exception as e:
    print(f"❌ Model loading failed: {e}")
    exit(1)

# Test 4: Test with dummy image
print("\n[Test 4] Testing emotion detection...")
try:
    import numpy as np
    # Create dummy RGB image (face-like)
    dummy_face = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)

    result = detector.detect_emotion(dummy_face)

    print(f"✅ Detection successful")
    print(f"   - Emotion: {result['emotion']}")
    print(f"   - Confidence: {result['emotion_confidence']:.1%}")
    print(f"   - Method: {result['method']}")
    if 'emotion_scores' in result:
        print(f"   - Top 3 emotions:")
        for emo, score in sorted(result['emotion_scores'].items(),
                                key=lambda x: x[1], reverse=True)[:3]:
            print(f"     • {emo}: {score:.1%}")
except Exception as e:
    print(f"❌ Detection failed: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

print("\n" + "=" * 60)
print("✅ All tests passed!")
print("=" * 60)
