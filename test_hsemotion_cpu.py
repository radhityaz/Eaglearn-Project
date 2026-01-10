"""
Test HSEmotion with CPU
Quick performance benchmark
"""

import time
import numpy as np

print("=" * 60)
print("HSEmotion CPU Performance Test")
print("=" * 60)

# Import HSEmotion
try:
    from hsemotion.facial_emotions import HSEmotionRecognizer

    print("\n✅ HSEmotion imported successfully!")
except ImportError as e:
    print(f"\n❌ Failed to import HSEmotion: {e}")
    exit(1)

# Initialize model (CPU mode)
print("\n🔧 Initializing HSEmotion on CPU...")
try:
    model = HSEmotionRecognizer(model_name="enet_b0_8_best_vgaf", device="cpu")
    print("✅ Model loaded successfully!")
except Exception as e:
    print(f"❌ Failed to load model: {e}")
    exit(1)

# Create test image
print("\n📸 Creating test image...")
test_image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
print(f"   Image shape: {test_image.shape}")

# Warm up (first few iterations are slow)
print("\n🔥 Warming up model (5 iterations)...")
for i in range(5):
    _ = model.predict_emotions(test_image, logits=False)
    print(f"   Warmup {i + 1}/5 done")

# Benchmark
print("\n⏱️ Running benchmark (50 iterations)...")
iterations = 50
times = []

for i in range(iterations):
    start = time.time()
    emotion, scores = model.predict_emotions(test_image, logits=False)
    elapsed = (time.time() - start) * 1000
    times.append(elapsed)

    if (i + 1) % 10 == 0:
        print(f"   Completed {i + 1}/{iterations} iterations")

# Results
avg_time = sum(times) / len(times)
fps = 1000 / avg_time

print("\n" + "=" * 60)
print("RESULTS")
print("=" * 60)
print("\n📊 Performance:")
print(f"   Average time: {avg_time:.2f} ms/frame")
print(f"   FPS: {fps:.1f}")
print(f"   Min time: {min(times):.2f} ms")
print(f"   Max time: {max(times):.2f} ms")

print("\n🎭 Emotion Detection:")
print(f"   Detected emotion: {emotion}")
print(f"   Scores: {scores}")

print("\n💡 Comparison:")
print("   DeepFace CPU: ~10-15 FPS")
print(f"   HSEmotion CPU: ~{fps:.1f} FPS")

if fps > 15:
    print("\n✅ HSEmotion CPU is FASTER than DeepFace CPU!")
    print(f"   Improvement: {(fps / 12.5 - 1) * 100:.1f}% faster")
else:
    print("\n⚠️ Similar performance to DeepFace")

print("\n" + "=" * 60)
print("✅ Test Complete!")
print("=" * 60)

print("\n🚀 Next Step:")
if fps > 20:
    print("   → CPU performance is good enough!")
    print("   → Can use HSEmotion CPU for production")
else:
    print("   → Consider installing PyTorch GPU for better performance")
    print("   → Expected with GPU: 50-100 FPS")
