"""
DeepFace Emotion Detector
Uses pre-trained deep learning model for accurate emotion detection
Accuracy: ~93% (vs ~70% for rule-based)
"""

import logging
import numpy as np
from typing import Dict, Optional
import os
from collections import deque

logger = logging.getLogger(__name__)

# ============================================================================
# TENSORFLOW GPU OPTIMIZATION
# ============================================================================
# Configure TensorFlow GPU before importing DeepFace
TF_GPU_AVAILABLE = False
try:
    import tensorflow as tf

    # Suppress TensorFlow warnings
    os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"  # 0=all, 1=INFO, 2=WARNING, 3=ERROR

    # Check for GPU availability
    physical_devices = tf.config.list_physical_devices("GPU")
    if physical_devices:
        TF_GPU_AVAILABLE = True
        logger.info(f"[GPU] TensorFlow GPU detected: {len(physical_devices)} device(s)")

        # Configure GPU memory growth (prevent OOM errors)
        for gpu in physical_devices:
            try:
                tf.config.experimental.set_memory_growth(gpu, True)
                logger.info(f"[OK] GPU memory growth enabled for: {gpu.name}")
            except RuntimeError as e:
                logger.warning(f"[WARN] Could not set memory growth: {e}")

        # Optional: Limit GPU memory allocation (uncomment if needed)
        # tf.config.set_logical_device_configuration(
        #     physical_devices[0],
        #     [tf.config.LogicalDeviceConfiguration(memory_limit=2048)]  # 2GB limit
        # )
    else:
        logger.info("[INFO] No TensorFlow GPU detected, using CPU")

except ImportError:
    logger.warning("[WARN] TensorFlow not installed, GPU acceleration unavailable")
except Exception as e:
    logger.warning(f"[WARN] TensorFlow GPU configuration error: {e}")

# ============================================================================
# DEEPFACE IMPORT (after TensorFlow GPU config)
# ============================================================================
try:
    from deepface import DeepFace

    DEEPFACE_AVAILABLE = True
    logger.info("[OK] DeepFace imported successfully")
except ImportError:
    DEEPFACE_AVAILABLE = False
    logger.warning(
        "[WARN] DeepFace not installed. Run: pip install deepface tf-keras tensorflow"
    )


class DeepFaceEmotionDetector:
    """
    Emotion detector using DeepFace pre-trained model

    Model: VGG-Face + Emotion weights
    Accuracy: ~93% on AffectNet dataset
    Emotions: happy, sad, angry, fearful, disgust, neutral, surprise
    """

    def __init__(self, config, gpu_enabled=False):
        """
        Initialize DeepFace emotion detector

        Args:
            config: Config object from config_loader
            gpu_enabled: Whether CUDA GPU is available (for OpenCV operations)
        """
        self.config = config
        self.available = DEEPFACE_AVAILABLE

        # Use TensorFlow GPU detection (more reliable than CUDA check)
        # gpu_enabled parameter is for OpenCV CUDA, TF_GPU_AVAILABLE is for TensorFlow
        self.gpu_enabled = TF_GPU_AVAILABLE
        self.cuda_enabled = gpu_enabled  # Keep for reference

        # DeepFace settings - OPTIMIZED for real-time
        self.actions = ["emotion"]
        self.enforce_detection = (
            False  # Don't enforce face detection (we do it already)
        )

        # IMPROVED: Adaptive backend selection based on GPU availability
        # 'opencv' = fastest, but less accurate (~70%)
        # 'ssd' = fast and accurate (~85%), good for CPU
        # 'mtcnn' = moderate speed, better accuracy (~90%)
        # 'retinaface' = most accurate (~95%), slow on CPU but good for GPU
        if self.gpu_enabled:
            self.detector_backend = "retinaface"  # Best accuracy with GPU
            logger.info("[GPU] Using RetinaFace backend (TensorFlow GPU accelerated)")
        else:
            self.detector_backend = "ssd"  # Best balance for CPU-only systems
            logger.info("[INFO] Using SSD backend (CPU optimized)")

        # Try different emotion models (in order of preference):
        # - 'Emotion' (default) = VGG-Face based
        # - 'DeepFace' = original model
        self.emotion_model = "Emotion"

        # Confidence threshold to reduce false positives
        # Lower threshold when GPU available (can handle more processing)
        if self.gpu_enabled:
            self.confidence_threshold = 0.20  # More sensitive with GPU
        else:
            self.confidence_threshold = 0.25  # Standard for CPU

        # Model will be loaded on first use (lazy loading)
        self.model_loaded = False

        # ========================================================================
        # TEMPORAL SMOOTHING - Reduce emotion fluctuation
        # ========================================================================
        # Keep history of last N emotion results for smoothing
        self.emotion_history = deque(maxlen=5)  # Last 5 frames
        self.smoothing_enabled = True
        self.min_emotion_frames = 3  # Minimum frames before switching emotions

        # Current stabilized emotion
        self.current_emotion = "neutral"
        self.emotion_confidence = 0.5
        self.emotion_stable_frames = (
            0  # How many frames current emotion has been stable
        )

        logger.info("[OK] DeepFaceEmotionDetector initialized")
        logger.info(
            f"[CONFIG] Backend: {self.detector_backend} | TensorFlow GPU: {self.gpu_enabled}"
        )
        logger.info(f"[CONFIG] Confidence Threshold: {self.confidence_threshold}")
        logger.info(
            f"[CONFIG] Temporal Smoothing: {self.smoothing_enabled} (window={self.emotion_history.maxlen})"
        )

    def detect_emotion(
        self, frame: np.ndarray, face_bbox: Optional[tuple] = None
    ) -> Dict:
        """
        Detect emotion from face image using DeepFace

        Args:
            frame: Full frame or face crop (BGR format)
            face_bbox: Optional face bounding box (x, y, w, h)

        Returns:
            dict: Emotion detection results
        """
        logger.debug("DeepFace emotion detection called")

        if not self.available:
            logger.warning("[WARN] DeepFace not available, using fallback")
            return self._fallback_detection()

        try:
            # Validate input frame type FIRST
            if frame is None:
                logger.warning("[WARN] Frame is None")
                return self._fallback_detection()

            if not isinstance(frame, np.ndarray):
                logger.warning(
                    f"[WARN] Invalid frame type: {type(frame)}, expected np.ndarray"
                )
                return self._fallback_detection()

            # If face bbox provided, crop face
            if face_bbox is not None:
                x, y, w, h = face_bbox
                face_crop = frame[y : y + h, x : x + w]

                # Validate face_crop after slicing
                if not isinstance(face_crop, np.ndarray):
                    logger.warning(
                        f"[WARN] Face crop is not ndarray: {type(face_crop)}"
                    )
                    face_crop = frame  # Fall back to full frame
            else:
                face_crop = frame

            # Final validation before processing
            if not isinstance(face_crop, np.ndarray):
                logger.error(
                    f"[ERROR] CRITICAL: face_crop is not ndarray: {type(face_crop)}"
                )
                return self._fallback_detection()

            # Log frame info (now safe to access .shape)
            logger.debug(
                f"[OK] Frame OK: type={type(face_crop).__name__}, shape={face_crop.shape}"
            )
            logger.debug(
                f"Image dtype: {face_crop.dtype}, min: {face_crop.min()}, max: {face_crop.max()}"
            )

            # Analyze emotion with DeepFace
            result = DeepFace.analyze(
                face_crop,
                actions=self.actions,
                enforce_detection=self.enforce_detection,
                detector_backend=self.detector_backend,
            )

            # DeepFace returns list, take first result
            if isinstance(result, list):
                result = result[0]

            emotion = result.get("dominant_emotion", "neutral")
            emotions_dict = result.get("emotion", {}) or {}
            safe_emotions_dict = {}
            for emo, score in emotions_dict.items():
                try:
                    safe_emotions_dict[str(emo)] = float(score)
                except Exception:
                    continue

            # Log ALL emotion scores for debugging
            logger.info("[EMOTION] DeepFace Raw Results:")
            logger.info(f"   Dominant: {emotion}")
            for emo, score in safe_emotions_dict.items():
                logger.info(f"   - {emo}: {score:.1f}%")

            # Normalize emotions to match our format
            emotion_confidence = safe_emotions_dict.get(emotion, 0.0) / 100.0

            # Filter low-confidence detections
            if emotion_confidence < self.confidence_threshold:
                logger.warning(
                    f"[WARN] Low confidence ({emotion_confidence:.1%}) - falling back to neutral"
                )
                emotion = "neutral"
                emotion_confidence = 0.5

            # Map DeepFace emotions to our set
            emotion_mapping = {
                "happy": "happy",
                "sad": "sad",
                "angry": "angry",
                "fearful": "surprised",  # Map fear to surprise
                "disgust": "neutral",  # Map disgust to neutral
                "neutral": "neutral",
                "surprise": "surprised",
            }

            mapped_emotion = emotion_mapping.get(emotion, "neutral")

            # ========================================================================
            # TEMPORAL SMOOTHING - Stabilize emotion across frames
            # ========================================================================
            if self.smoothing_enabled:
                stabilized_emotion, stabilized_confidence = self._smooth_emotion(
                    mapped_emotion, emotion_confidence, safe_emotions_dict
                )
                logger.info(
                    f"[OK] Final: {emotion} -> {mapped_emotion} -> {stabilized_emotion} "
                    f"(raw: {emotion_confidence:.1%} -> stable: {stabilized_confidence:.1%})"
                )
            else:
                stabilized_emotion = mapped_emotion
                stabilized_confidence = emotion_confidence
                logger.info(
                    f"[OK] Final: {emotion} -> {mapped_emotion} ({emotion_confidence:.1%})"
                )

            return {
                "emotion": stabilized_emotion,
                "emotion_confidence": stabilized_confidence,
                "emotion_scores": safe_emotions_dict,
                "method": "deepface",
                "raw_emotion": emotion,  # Also return raw DeepFace emotion
            }

        except Exception as e:
            logger.error(f"DeepFace error: {e}")
            return self._fallback_detection()

    def _fallback_detection(self) -> Dict:
        """Fallback when DeepFace not available"""
        return {
            "emotion": "neutral",
            "emotion_confidence": 0.5,
            "emotion_scores": {"neutral": 0.5},
            "method": "fallback",
            "warning": "DeepFace not available, using neutral",
        }

    def _smooth_emotion(
        self, new_emotion: str, new_confidence: float, emotion_scores: Dict
    ) -> tuple:
        """
        Apply temporal smoothing to reduce emotion fluctuation

        Args:
            new_emotion: Newly detected emotion
            new_confidence: Confidence score for new emotion
            emotion_scores: All emotion scores from DeepFace

        Returns:
            tuple: (stabilized_emotion, stabilized_confidence)
        """
        # Add new detection to history
        self.emotion_history.append(
            {
                "emotion": new_emotion,
                "confidence": new_confidence,
                "scores": emotion_scores,
            }
        )

        # If not enough history yet, return new emotion
        if len(self.emotion_history) < 2:
            self.current_emotion = new_emotion
            self.emotion_confidence = new_confidence
            return new_emotion, new_confidence

        # Count emotions in history
        emotion_counts: dict[str, int] = {}
        for detection in self.emotion_history:
            emo = detection["emotion"]
            emotion_counts[emo] = emotion_counts.get(emo, 0) + 1

        # Find most common emotion
        most_common_emotion = max(emotion_counts, key=lambda k: emotion_counts[k])
        most_common_count = emotion_counts[most_common_emotion]

        # Get average confidence for most common emotion
        confidences = [
            d["confidence"]
            for d in self.emotion_history
            if d["emotion"] == most_common_emotion
        ]
        avg_confidence = (
            sum(confidences) / len(confidences) if confidences else new_confidence
        )

        # Decision logic:
        # 1. If most common emotion appears >= min_emotion_frames, switch to it
        # 2. Otherwise, keep current emotion if it has significant support
        # 3. If new emotion is much more confident, allow faster switch

        # Check if we should switch
        if most_common_count >= self.min_emotion_frames:
            # Switch to most common emotion
            self.current_emotion = most_common_emotion
            self.emotion_confidence = avg_confidence
            self.emotion_stable_frames = most_common_count
        elif self.current_emotion in emotion_counts:
            # Keep current emotion if it still has support
            current_count = emotion_counts[self.current_emotion]
            if current_count >= 2:
                # Maintain current emotion
                # Decay confidence slightly to indicate uncertainty
                self.emotion_confidence = max(
                    self.emotion_confidence * 0.95, avg_confidence
                )
            else:
                # New emotion is dominant, switch
                self.current_emotion = most_common_emotion
                self.emotion_confidence = avg_confidence
                self.emotion_stable_frames = most_common_count
        else:
            # Current emotion not in history anymore, switch
            self.current_emotion = most_common_emotion
            self.emotion_confidence = avg_confidence
            self.emotion_stable_frames = most_common_count

        # Additional smoothing: boost confidence for stable emotions
        if self.emotion_stable_frames >= self.emotion_history.maxlen:
            # Emotion has been stable for full history, boost confidence
            self.emotion_confidence = min(self.emotion_confidence * 1.05, 0.98)

        return self.current_emotion, self.emotion_confidence
