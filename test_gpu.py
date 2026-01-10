"""
GPU Detection Test for Eaglearn
Tests if TensorFlow can detect and use NVIDIA GPU
"""

import os

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"  # Suppress warnings

import time
import tensorflow as tf

print("=" * 60)
print("TensorFlow GPU Detection Test")
print("=" * 60)

# TensorFlow version
print(f"\n📦 TensorFlow Version: {tf.__version__}")

# Check GPU devices
print("\n🔍 Searching for GPU devices...")
gpus = tf.config.list_physical_devices("GPU")

if gpus:
    print(f"✅ GPU DETECTED: {len(gpus)} device(s) found!\n")

    for i, gpu in enumerate(gpus):
        print(f"GPU {i}:")
        print(f"  Name: {gpu.name}")
        print(f"  Type: {gpu.device_type}")

        # Get GPU details
        try:
            gpu_details = tf.config.experimental.get_device_details(gpu)
            print(f"  Details: {gpu_details}")
        except Exception:
            print("  Details: Not available")

    # Test GPU memory growth
    print("\n🔧 Testing GPU memory configuration...")
    try:
        for gpu in gpus:
            tf.config.experimental.set_memory_growth(gpu, True)
        print("✅ GPU memory growth enabled successfully!")
    except Exception as e:
        print(f"⚠️ Could not enable memory growth: {e}")

    # Test GPU computation
    print("\n🧪 Testing GPU computation...")
    try:
        with tf.device("/GPU:0"):
            # Create tensors
            a = tf.constant([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])
            b = tf.constant([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]])
            c = tf.matmul(a, b)

            print("✅ GPU computation successful!")
            print(f"   Matrix multiplication result shape: {c.shape}")
            print(f"   Result:\n{c.numpy()}")
    except Exception as e:
        print(f"❌ GPU computation failed: {e}")

    # CUDA and cuDNN versions
    print("\n📚 Library Versions:")
    print(f"  CUDA: {tf.sysconfig.get_build_info().get('cuda_version', 'Unknown')}")
    print(f"  cuDNN: {tf.sysconfig.get_build_info().get('cudnn_version', 'Unknown')}")

    print("\n" + "=" * 60)
    print("✅ GPU IS READY FOR EAGLEARN!")
    print("   You should see:")
    print("   - 🚀 Using RetinaFace backend (TensorFlow GPU accelerated)")
    print("   - 🔧 Confidence Threshold: 0.20")
    print("   - Expected FPS: 20-25")
    print("=" * 60)

else:
    print("❌ NO GPU DETECTED\n")
    print("Possible reasons:")
    print("  1. CUDA Toolkit not installed")
    print("  2. cuDNN not installed")
    print("  3. CUDA version mismatch (need CUDA 11.8 for TF 2.15)")
    print("  4. Environment variables not set")
    print("\nCurrent system info:")
    print("  Build configuration:")
    for key, value in tf.sysconfig.get_build_info().items():
        print(f"    {key}: {value}")

    print("\n" + "=" * 60)
    print("⚠️ RUNNING IN CPU MODE")
    print("   Current backend: SSD (CPU optimized)")
    print("   Expected FPS: 10-15")
    print("\n📖 To enable GPU:")
    print("   See: docs/CUDA_INSTALLATION_GUIDE.md")
    print("=" * 60)

# Test inference speed
print("\n⏱️ Testing inference speed...")

# Warm up
for _ in range(5):
    tf.random.normal([100, 100])

# Benchmark
device = "/GPU:0" if gpus else "/CPU:0"
iterations = 100

start = time.time()
with tf.device(device):
    for _ in range(iterations):
        a = tf.random.normal([100, 100])
        b = tf.matmul(a, a)
end = time.time()

elapsed = (end - start) * 1000 / iterations
device_name = "GPU" if gpus else "CPU"
print(f"  {device_name} average time: {elapsed:.2f} ms per iteration")

print("\n✅ Test complete!")
