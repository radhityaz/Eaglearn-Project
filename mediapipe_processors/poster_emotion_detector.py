"""
POSTER++ Emotion Detector (SOTA 2024)
State-of-the-art facial expression recognition model
Accuracy: ~90% on AffectNet, ~88% on RAF-DB
Architecture: Hybrid MobileFaceNet + IR50 + Pyramid Vision Transformer

Hardware Requirements:
- GPU: Recommended (RTX 3050 or better)
- VRAM: ~2.5GB for inference
- RAM: ~4GB
"""

import os
import sys
import logging
import numpy as np
import cv2
import torch
import torch.nn.functional as F
from torchvision import transforms
from typing import Dict, Optional

# Add POSTER++ to path
FER_POSTER_PATH = os.path.join(os.path.dirname(__file__), '..', 'FER_POSTER')
if FER_POSTER_PATH not in sys.path:
    sys.path.insert(0, FER_POSTER_PATH)

logger = logging.getLogger(__name__)

try:
    from FER_POSTER.models.emotion_hyp import pyramid_trans_expr, load_pretrained_weights
    POSTER_AVAILABLE = True
    logger.info("✅ POSTER++ imported successfully")
except ImportError as e:
    POSTER_AVAILABLE = False
    logger.warning(f"⚠️ POSTER++ not available: {e}")


class POSTEREmotionDetector:
    """
    POSTER++ Emotion Detector - SOTA 2024

    Model: pyramid_trans_expr (Hybrid MobileFaceNet + IR50 + Vision Transformer)
    Accuracy: ~90% on AffectNet (7-class)
    Speed: ~20-30 FPS on RTX 3050
    VRAM: ~2.5GB
    """

    # Emotion labels for AffectNet 7-class
    EMOTIONS_7 = ['neutral', 'happy', 'sad', 'surprise', 'fear', 'disgust', 'angry']
    # Emotion labels for RAF-DB
    EMOTIONS_RAF = ['surprise', 'fear', 'disgust', 'happy', 'sad', 'angry', 'neutral']

    def __init__(self, config, model_type: str = "large"):
        """
        Initialize POSTER++ emotion detector

        Args:
            config: Config object from config_loader
            model_type: "small", "base", or "large" (default: "large")
                - small: depth=4, fastest but less accurate
                - base: depth=6, balanced
                - large: depth=8, most accurate (recommended)
        """
        self.config = config
        self.available = POSTER_AVAILABLE

        if not self.available:
            logger.error("❌ POSTER++ not available!")
            return

        # Model configuration
        self.model_type = model_type
        self.num_classes = 7  # AffectNet 7-class
        self.img_size = 224

        # Device configuration
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        logger.info(f"🔧 Using device: {self.device}")

        # Image preprocessing (same as POSTER++ training)
        self.transform = transforms.Compose([
            transforms.ToPILImage(),
            transforms.Resize((self.img_size, self.img_size)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406],
                               std=[0.229, 0.224, 0.225])
        ])

        # Model will be loaded on first use (lazy loading)
        self.model = None
        self.model_loaded = False

        logger.info(f"✅ POSTER++ Emotion Detector initialized")
        logger.info(f"🔧 Model type: {model_type}")
        logger.info(f"🔧 Num classes: {self.num_classes}")

    def _load_model(self):
        """Load POSTER++ model and weights"""
        if self.model_loaded:
            return

        try:
            logger.info("🔵 Loading POSTER++ model...")

            # Initialize model architecture
            self.model = pyramid_trans_expr(
                img_size=self.img_size,
                num_classes=self.num_classes,
                type=self.model_type
            )

            # Load checkpoint
            checkpoint_path = self._get_checkpoint_path()

            if not os.path.exists(checkpoint_path):
                logger.error(f"❌ Checkpoint not found: {checkpoint_path}")
                logger.error("⚠️ Please download POSTER++ checkpoint from:")
                logger.error("⚠️ https://drive.google.com/drive/folders/1jeCPTGjBL8YgKKB9YrI9TYZywme8gymv")
                logger.error("⚠️ And save to: checkpoint/rafdb_best.pth")
                raise FileNotFoundError("POSTER++ checkpoint not found")

            logger.info(f"🔵 Loading checkpoint: {checkpoint_path}")
            checkpoint = torch.load(checkpoint_path, map_location=self.device)

            # Load weights
            if 'model_state_dict' in checkpoint:
                state_dict = checkpoint['model_state_dict']
            else:
                state_dict = checkpoint

            self.model = load_pretrained_weights(self.model, state_dict)

            # Move to device
            self.model.to(self.device)
            self.model.eval()

            self.model_loaded = True
            logger.info("✅ POSTER++ model loaded successfully")

            # Log model info
            total_params = sum(p.numel() for p in self.model.parameters())
            trainable_params = sum(p.numel() for p in self.model.parameters() if p.requires_grad)
            logger.info(f"🔧 Total parameters: {total_params:,}")
            logger.info(f"🔧 Trainable parameters: {trainable_params:,}")

        except Exception as e:
            logger.error(f"❌ Error loading POSTER++ model: {e}")
            self.available = False
            raise

    def _get_checkpoint_path(self) -> str:
        """Get path to POSTER++ checkpoint file"""
        # Check multiple possible locations
        possible_paths = [
            os.path.join(FER_POSTER_PATH, 'checkpoint', 'rafdb_best.pth'),
            os.path.join(FER_POSTER_PATH, 'checkpoint', 'affectnet_best.pth'),
            'FER_POSTER/checkpoint/rafdb_best.pth',
            'checkpoint/rafdb_best.pth',
        ]

        for path in possible_paths:
            if os.path.exists(path):
                return path

        # Return default path (even if doesn't exist)
        return os.path.join(FER_POSTER_PATH, 'checkpoint', 'rafdb_best.pth')

    def detect_emotion(self, frame: np.ndarray, face_bbox: Optional[tuple] = None) -> Dict:
        """
        Detect emotion from face image using POSTER++

        Args:
            frame: Full frame or face crop (BGR format)
            face_bbox: Optional face bounding box (x, y, w, h)

        Returns:
            dict: Emotion detection results
        """
        if not self.available:
            logger.warning("⚠️ POSTER++ not available, using fallback")
            return self._fallback_detection()

        # Load model on first use
        if not self.model_loaded:
            self._load_model()

        try:
            # If face bbox provided, crop face
            if face_bbox is not None:
                x, y, w, h = face_bbox
                face_crop = frame[y:y+h, x:x+w]
            else:
                face_crop = frame

            # Preprocess
            face_rgb = cv2.cvtColor(face_crop, cv2.COLOR_BGR2RGB)
            face_tensor = self.transform(face_rgb).unsqueeze(0).to(self.device)

            # Predict
            with torch.no_grad():
                outputs, features = self.model(face_tensor)
                probs = F.softmax(outputs[0], dim=0)

            # Get results
            confidence, predicted = torch.max(probs, 0)
            emotion_idx = predicted.item()
            emotion_confidence = confidence.item()

            # Map to emotion name
            emotion = self.EMOTIONS_7[emotion_idx]

            # Get all emotion scores
            all_scores = {
                self.EMOTIONS_7[i]: prob.item()
                for i, prob in enumerate(probs)
            }

            # Log results
            logger.info(f"🎭 POSTER++ Results:")
            logger.info(f"   Dominant: {emotion} ({emotion_confidence:.1%})")
            for emo, score in sorted(all_scores.items(), key=lambda x: x[1], reverse=True):
                logger.info(f"   - {emo}: {score:.1%}")

            return {
                'emotion': emotion,
                'emotion_confidence': emotion_confidence,
                'emotion_scores': all_scores,
                'method': 'poster++',
                'model_type': self.model_type
            }

        except Exception as e:
            logger.error(f"POSTER++ detection error: {e}")
            return self._fallback_detection()

    def _fallback_detection(self) -> Dict:
        """Fallback when POSTER++ not available"""
        return {
            'emotion': 'neutral',
            'emotion_confidence': 0.5,
            'emotion_scores': {'neutral': 0.5},
            'method': 'fallback',
            'warning': 'POSTER++ not available, using neutral'
        }

    def benchmark(self, num_iterations: int = 100):
        """
        Benchmark POSTER++ inference speed

        Args:
            num_iterations: Number of iterations for benchmarking

        Returns:
            dict: Benchmark results
        """
        if not self.available or not self.model_loaded:
            logger.error("❌ Model not loaded, cannot benchmark")
            return {}

        logger.info(f"🔵 Benchmarking POSTER++ ({num_iterations} iterations)...")

        # Create dummy input
        dummy_input = torch.randn(1, 3, self.img_size, self.img_size).to(self.device)

        # Warmup
        with torch.no_grad():
            for _ in range(10):
                _ = self.model(dummy_input)

        # Benchmark
        if self.device.type == 'cuda':
            torch.cuda.synchronize()

        import time
        start_time = time.time()

        with torch.no_grad():
            for _ in range(num_iterations):
                _ = self.model(dummy_input)

        if self.device.type == 'cuda':
            torch.cuda.synchronize()

        end_time = time.time()
        total_time = end_time - start_time
        avg_time = total_time / num_iterations
        fps = 1.0 / avg_time

        # Get memory usage
        if self.device.type == 'cuda':
            memory_allocated = torch.cuda.memory_allocated(self.device) / 1024**3
            memory_reserved = torch.cuda.memory_reserved(self.device) / 1024**3
        else:
            memory_allocated = 0
            memory_reserved = 0

        results = {
            'avg_inference_time_ms': avg_time * 1000,
            'fps': fps,
            'total_time_sec': total_time,
            'iterations': num_iterations,
            'memory_allocated_gb': memory_allocated,
            'memory_reserved_gb': memory_reserved,
            'device': str(self.device)
        }

        logger.info(f"📊 Benchmark Results:")
        logger.info(f"   Avg Inference Time: {results['avg_inference_time_ms']:.2f} ms")
        logger.info(f"   FPS: {results['fps']:.1f}")
        logger.info(f"   Memory Allocated: {results['memory_allocated_gb']:.2f} GB")
        logger.info(f"   Memory Reserved: {results['memory_reserved_gb']:.2f} GB")

        return results
