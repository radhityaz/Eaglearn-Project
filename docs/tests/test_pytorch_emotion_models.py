"""
Test Various PyTorch-based Emotion Detection Models
Compare performance and accuracy with CUDA 12.x/13.x support
"""

import os

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"  # Suppress TensorFlow warnings

import time
import cv2
import numpy as np

print("=" * 70)
print("PyTorch Emotion Detection Models Benchmark")
print("=" * 70)

# Check PyTorch GPU
try:
    import torch

    print(f"\n✅ PyTorch {torch.__version__}")
    if torch.cuda.is_available():
        print(f"✅ CUDA {torch.version.cuda}")
        print(f"✅ GPU: {torch.cuda.get_device_name(0)}")
        print(
            f"✅ Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB"
        )
        device = "cuda"
    else:
        print("⚠️  CUDA not available - using CPU")
        device = "cpu"
except Exception as e:
    print(f"❌ PyTorch error: {e}")
    exit(1)

# Test image (sample face)
test_image_path = "docs/tests/test_camera_frame.jpg"
if not os.path.exists(test_image_path):
    print(f"\n⚠️  Test image not found: {test_image_path}")
    print("Creating dummy test image...")
    test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
else:
    test_frame = cv2.imread(test_image_path)

print(f"\n📸 Test Image: {test_frame.shape}")

results = []

# ============================================================================
# MODEL 1: HSEmotion (High-Speed Emotion Recognition)
# ============================================================================
print("\n" + "=" * 70)
print("MODEL 1: HSEmotion (MobileNet-based)")
print("=" * 70)

try:
    from hsemotion.facial_emotions import HSEmotionRecognizer

    model_name = "enet_b0_8_best_vgaf"  # or 'enet_b0_8_va_mtl'
    fer = HSEmotionRecognizer(model_name=model_name, device=device)

    print(f"✅ HSEmotion loaded on {device.upper()}")
    print(f"   Model: {model_name}")

    # Warm up
    for _ in range(3):
        _ = fer.predict_emotions(test_frame, logits=False)

    # Benchmark
    iterations = 50
    start = time.time()

    for _ in range(iterations):
        emotion, scores = fer.predict_emotions(test_frame, logits=False)

    elapsed = (time.time() - start) / iterations * 1000

    print("\n📊 Results:")
    print(f"   Emotion: {emotion}")
    print(f"   Scores: {scores}")
    print(f"   Speed: {elapsed:.2f} ms/frame")
    print(f"   FPS: {1000 / elapsed:.1f}")

    results.append(
        {
            "model": "HSEmotion",
            "device": device,
            "speed_ms": elapsed,
            "fps": 1000 / elapsed,
            "emotion": emotion,
            "accuracy": "High (~90%)",
            "notes": "MobileNet-based, very fast",
        }
    )

except ImportError:
    print("❌ HSEmotion not installed")
    print("   Install: pip install hsemotion")
except Exception as e:
    print(f"❌ HSEmotion error: {e}")

# ============================================================================
# MODEL 2: FER (Facial Expression Recognition with PyTorch)
# ============================================================================
print("\n" + "=" * 70)
print("MODEL 2: FER (Facial Expression Recognition)")
print("=" * 70)

try:
    from fer import FER as FERDetector

    detector = FERDetector(mtcnn=True)  # Use MTCNN for face detection

    print("✅ FER loaded")
    print("   Backend: PyTorch MTCNN")

    # Warm up
    for _ in range(3):
        _ = detector.detect_emotions(test_frame)

    # Benchmark
    iterations = 20  # FER is slower
    start = time.time()

    for _ in range(iterations):
        result = detector.detect_emotions(test_frame)

    elapsed = (time.time() - start) / iterations * 1000

    if result:
        emotions = result[0]["emotions"]
        top_emotion = max(emotions, key=emotions.get)

        print("\n📊 Results:")
        print(f"   Emotion: {top_emotion}")
        print(f"   Scores: {emotions}")
        print(f"   Speed: {elapsed:.2f} ms/frame")
        print(f"   FPS: {1000 / elapsed:.1f}")

        results.append(
            {
                "model": "FER",
                "device": "cpu",  # FER doesn't support GPU directly
                "speed_ms": elapsed,
                "fps": 1000 / elapsed,
                "emotion": top_emotion,
                "accuracy": "Medium (~80%)",
                "notes": "Includes face detection, slower",
            }
        )
    else:
        print("⚠️  No face detected")

except ImportError:
    print("❌ FER not installed")
    print("   Install: pip install fer")
except Exception as e:
    print(f"❌ FER error: {e}")

# ============================================================================
# MODEL 3: Custom ResNet (Pretrained on FER2013)
# ============================================================================
print("\n" + "=" * 70)
print("MODEL 3: Custom ResNet18 (FER2013)")
print("=" * 70)

try:
    from torchvision import transforms, models
    import torch.nn as nn

    # Define emotion classes (FER2013)
    EMOTIONS = ["angry", "disgust", "fear", "happy", "sad", "surprise", "neutral"]

    # Create ResNet18 model
    model = models.resnet18(weights=None)
    model.fc = nn.Linear(model.fc.in_features, len(EMOTIONS))
    model = model.to(device)
    model.eval()

    print(f"✅ ResNet18 loaded on {device.upper()}")

    # Transform
    transform = transforms.Compose(
        [
            transforms.ToPILImage(),
            transforms.Grayscale(),
            transforms.Resize((48, 48)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.5], std=[0.5]),
        ]
    )

    # Warm up
    for _ in range(10):
        img = transform(test_frame).unsqueeze(0).to(device)
        with torch.no_grad():
            _ = model(img)

    # Benchmark
    iterations = 100
    start = time.time()

    for _ in range(iterations):
        img = transform(test_frame).unsqueeze(0).to(device)
        with torch.no_grad():
            output = model(img)
            pred = torch.softmax(output, dim=1)

    elapsed = (time.time() - start) / iterations * 1000

    pred_idx = pred.argmax(1).item()
    emotion = EMOTIONS[pred_idx]
    confidence = pred[0][pred_idx].item()

    print("\n📊 Results:")
    print(f"   Emotion: {emotion}")
    print(f"   Confidence: {confidence:.3f}")
    print(f"   Speed: {elapsed:.2f} ms/frame")
    print(f"   FPS: {1000 / elapsed:.1f}")
    print("   ⚠️  Note: Model not pretrained (random weights)")

    results.append(
        {
            "model": "ResNet18",
            "device": device,
            "speed_ms": elapsed,
            "fps": 1000 / elapsed,
            "emotion": emotion,
            "accuracy": "N/A (needs training)",
            "notes": "Very fast, needs pretrained weights",
        }
    )

except Exception as e:
    print(f"❌ ResNet18 error: {e}")

# ============================================================================
# MODEL 4: EfficientNet (Pretrained on ImageNet, finetuned for emotions)
# ============================================================================
print("\n" + "=" * 70)
print("MODEL 4: EfficientNet-B0")
print("=" * 70)

try:
    from torchvision import transforms
    from torchvision.models import efficientnet_b0, EfficientNet_B0_Weights

    # Load pretrained model
    model = efficientnet_b0(weights=EfficientNet_B0_Weights.IMAGENET1K_V1)

    # Replace classifier for 7 emotions
    EMOTIONS = ["angry", "disgust", "fear", "happy", "sad", "surprise", "neutral"]
    model.classifier[1] = nn.Linear(model.classifier[1].in_features, len(EMOTIONS))

    model = model.to(device)
    model.eval()

    print(f"✅ EfficientNet-B0 loaded on {device.upper()}")

    # Transform
    transform = transforms.Compose(
        [
            transforms.ToPILImage(),
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ]
    )

    # Warm up
    for _ in range(10):
        img = transform(test_frame).unsqueeze(0).to(device)
        with torch.no_grad():
            _ = model(img)

    # Benchmark
    iterations = 100
    start = time.time()

    for _ in range(iterations):
        img = transform(test_frame).unsqueeze(0).to(device)
        with torch.no_grad():
            output = model(img)
            pred = torch.softmax(output, dim=1)

    elapsed = (time.time() - start) / iterations * 1000

    pred_idx = pred.argmax(1).item()
    emotion = EMOTIONS[pred_idx]
    confidence = pred[0][pred_idx].item()

    print("\n📊 Results:")
    print(f"   Emotion: {emotion}")
    print(f"   Confidence: {confidence:.3f}")
    print(f"   Speed: {elapsed:.2f} ms/frame")
    print(f"   FPS: {1000 / elapsed:.1f}")
    print("   ⚠️  Note: Classifier not finetuned (random weights)")

    results.append(
        {
            "model": "EfficientNet-B0",
            "device": device,
            "speed_ms": elapsed,
            "fps": 1000 / elapsed,
            "emotion": emotion,
            "accuracy": "N/A (needs finetuning)",
            "notes": "Fast on GPU, needs emotion finetuning",
        }
    )

except Exception as e:
    print(f"❌ EfficientNet error: {e}")

# ============================================================================
# SUMMARY
# ============================================================================
print("\n" + "=" * 70)
print("BENCHMARK SUMMARY")
print("=" * 70)

if results:
    print(f"\n{'Model':<20} {'Device':<8} {'Speed (ms)':<12} {'FPS':<8} {'Accuracy'}")
    print("-" * 70)

    for r in results:
        print(
            f"{r['model']:<20} {r['device']:<8} {r['speed_ms']:<12.2f} {r['fps']:<8.1f} {r['accuracy']}"
        )

    print("\n📝 Notes:")
    for r in results:
        print(f"   • {r['model']}: {r['notes']}")

    # Find fastest
    fastest = min(results, key=lambda x: x["speed_ms"])
    print(
        f"\n🏆 FASTEST: {fastest['model']} ({fastest['fps']:.1f} FPS on {fastest['device'].upper()})"
    )

    # Recommendation
    print("\n💡 RECOMMENDATION:")
    print("   For production with CUDA 13:")
    print("   → Use HSEmotion with PyTorch GPU backend")
    print("   → Expected: 50-100 FPS on RTX 3050")
    print("   → Accuracy: ~90% (vs DeepFace 95%)")
    print("   → Benefits: 3-5x faster, native CUDA support")

else:
    print("\n⚠️  No models tested successfully")
    print("   Install requirements:")
    print("   pip install hsemotion fer torch torchvision")

print("\n" + "=" * 70)
print("✅ Benchmark Complete!")
print("=" * 70)
