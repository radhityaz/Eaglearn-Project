"""
Eaglearn ML C++ Extension Wrapper
Provides drop-in replacement for Python modules using C++ backend when available.

Usage:
    from backend.ml import preprocessing, pose_estimator, gaze_estimator, calibration, kpi_calculator, stress_analyzer
    from backend.db import encryption
    
This module automatically uses C++ implementations when available, falling back to Python.
"""

import numpy as np
from typing import Optional, Dict, List, Tuple, Any
import logging

logger = logging.getLogger(__name__)

# Try to import C++ extension
try:
    import eaglearn_ml as _cpp_module
    CPP_AVAILABLE = True
    logger.info("C++ ML extension loaded successfully")
except ImportError as e:
    CPP_AVAILABLE = False
    logger.warning(f"C++ ML extension not available, using Python fallback: {e}")


# ============================================================================
# FramePreprocessor
# ============================================================================
class FramePreprocessor:
    """Preprocesses video frames for ML engines."""
    
    def __init__(self, target_size: Tuple[int, int] = (640, 480)):
        self.target_size = target_size
        if CPP_AVAILABLE:
            self._cpp = _cpp_module.FramePreprocessor(target_size[0], target_size[1])
        else:
            # Python fallback
            self._python = None  # Will use original Python implementation
            
    def preprocess(self, frame: np.ndarray) -> np.ndarray:
        """Preprocess frame for ML inference."""
        if CPP_AVAILABLE:
            return self._cpp.preprocess(frame)
        else:
            # Python fallback - use original implementation
            import cv2
            h, w = frame.shape[:2]
            if (w, h) != self.target_size:
                resized = cv2.resize(frame, self.target_size)
            else:
                resized = frame
            return resized.astype(np.float32) / 255.0
    
    def denormalize(self, frame: np.ndarray) -> np.ndarray:
        """Convert normalized frame back to 0-255 range."""
        if CPP_AVAILABLE:
            return self._cpp.denormalize(frame)
        else:
            return (frame * 255.0).astype(np.uint8)


# ============================================================================
# AudioPreprocessor
# ============================================================================
class AudioPreprocessor:
    """Preprocesses audio data for stress analysis."""
    
    def __init__(self, target_sample_rate: int = 16000):
        self.target_sample_rate = target_sample_rate
        if CPP_AVAILABLE:
            self._cpp = _cpp_module.AudioPreprocessor(target_sample_rate)
        else:
            self._python = None
            
    def preprocess(self, audio_data: np.ndarray, original_sample_rate: int) -> np.ndarray:
        """Preprocess audio for stress analysis."""
        if CPP_AVAILABLE:
            return self._cpp.preprocess(audio_data, original_sample_rate)
        else:
            # Python fallback
            if original_sample_rate != self.target_sample_rate:
                import librosa
                audio_data = librosa.resample(
                    audio_data,
                    orig_sr=original_sample_rate,
                    target_sr=self.target_sample_rate
                )
            max_val = np.abs(audio_data).max()
            if max_val > 0:
                audio_data = audio_data / max_val
            audio_data = audio_data - np.mean(audio_data)
            return audio_data.astype(np.float32)


# ============================================================================
# CalibrationService
# ============================================================================
class CalibrationService:
    """Manages calibration process for gaze estimation."""
    
    def __init__(self):
        if CPP_AVAILABLE:
            self._cpp = _cpp_module.CalibrationService()
        else:
            self._python = None
            
    def calculate_transformation_matrix(
        self,
        screen_points: List[Tuple[float, float]],
        gaze_points: List[Tuple[float, float]]
    ) -> Tuple[np.ndarray, float]:
        """Calculate transformation matrix from calibration points."""
        if CPP_AVAILABLE:
            matrix, accuracy = self._cpp.calculate_transformation_matrix(screen_points, gaze_points)
            return np.array(matrix), accuracy
        else:
            # Python fallback
            import cv2
            src_points = np.array(gaze_points, dtype=np.float32)
            dst_points = np.array(screen_points, dtype=np.float32)
            matrix, mask = cv2.findHomography(src_points, dst_points, cv2.RANSAC, 5.0)
            return matrix, 0.9  # Simplified


# ============================================================================
# HeadPoseEstimator
# ============================================================================
class HeadPoseEstimator:
    """Head pose estimation using MediaPipe face landmarks."""
    
    def __init__(self):
        if CPP_AVAILABLE:
            self._cpp = _cpp_module.HeadPoseEstimator()
        else:
            # Import original Python implementation
            from .pose_estimator import HeadPoseEstimator as PyHeadPoseEstimator
            self._python = PyHeadPoseEstimator()
    
    def estimate(self, frame: np.ndarray) -> Dict:
        """Estimate head pose from a single frame."""
        if CPP_AVAILABLE:
            return self._cpp.estimate(frame)
        else:
            return self._python.estimate(frame)


# ============================================================================
# GazeEstimator
# ============================================================================
class GazeEstimator:
    """Gaze estimation using MediaPipe face landmarks."""
    
    def __init__(self, smoothing_window: int = 5):
        if CPP_AVAILABLE:
            self._cpp = _cpp_module.GazeEstimator(smoothing_window)
        else:
            from .gaze_estimator import GazeEstimator as PyGazeEstimator
            self._python = PyGazeEstimator(smoothing_window)
    
    def estimate(self, frame: np.ndarray, calibration_matrix: Optional[np.ndarray] = None) -> Dict:
        """Estimate gaze from a single frame."""
        if CPP_AVAILABLE:
            return self._cpp.estimate(frame, calibration_matrix)
        else:
            return self._python.estimate(frame, calibration_matrix)
    
    def reset_smoothing(self):
        """Reset smoothing buffer."""
        if CPP_AVAILABLE:
            self._cpp.reset_smoothing()
        else:
            self._python.reset_smoothing()


# ============================================================================
# KPICalculator
# ============================================================================
class KPICalculator:
    """Calculates productivity KPIs from ML engine outputs."""
    
    def __init__(self):
        if CPP_AVAILABLE:
            self._cpp = _cpp_module.KPICalculator()
        else:
            from .kpi_calculator import KPICalculator as PyKPICalculator
            self._python = PyKPICalculator()
    
    def calculate_productivity_metrics(
        self,
        gaze_data: List[Dict],
        pose_data: List[Dict],
        stress_data: List[Dict],
        window_start: str,
        window_end: str
    ) -> Dict:
        """Calculate productivity metrics for a time window."""
        if CPP_AVAILABLE:
            return self._cpp.calculate_productivity_metrics(gaze_data, pose_data, stress_data, window_start, window_end)
        else:
            return self._python.calculate_productivity_metrics(gaze_data, pose_data, stress_data, window_start, window_end)


# ============================================================================
# StressAnalyzer
# ============================================================================
class StressAnalyzer:
    """Audio stress analysis using voice features."""
    
    def __init__(self, sample_rate: int = 16000):
        if CPP_AVAILABLE:
            self._cpp = _cpp_module.StressAnalyzer(sample_rate)
        else:
            from .stress_analyzer import StressAnalyzer as PyStressAnalyzer
            self._python = PyStressAnalyzer(sample_rate)
    
    def analyze(self, audio_data: np.ndarray) -> Dict:
        """Analyze audio data for stress indicators."""
        if CPP_AVAILABLE:
            return self._cpp.analyze(audio_data)
        else:
            return self._python.analyze(audio_data)


# ============================================================================
# EncryptionManager
# ============================================================================
class EncryptionManager:
    """Manages encryption/decryption operations for database fields."""
    
    def __init__(self, master_key: Optional[str] = None):
        if CPP_AVAILABLE:
            self._cpp = _cpp_module.EncryptionManager(master_key or "")
        else:
            from ..db.encryption import EncryptionManager as PyEncryptionManager
            self._python = PyEncryptionManager(master_key)
    
    def encrypt(self, plaintext: str) -> str:
        """Encrypt plaintext using AES-256-GCM."""
        if CPP_AVAILABLE:
            return self._cpp.encrypt(plaintext)
        else:
            return self._python.encrypt(plaintext)
    
    def decrypt(self, encrypted: str) -> str:
        """Decrypt ciphertext using AES-256-GCM."""
        if CPP_AVAILABLE:
            return self._cpp.decrypt(encrypted)
        else:
            return self._python.decrypt(encrypted)


# ============================================================================
# Factory functions to maintain API compatibility
# ============================================================================
_frame_preprocessor = None
_audio_preprocessor = None
_calibration_service = None
_pose_estimator = None
_gaze_estimator = None
_kpi_calculator = None
_stress_analyzer = None
_encryption_manager = None

def get_frame_preprocessor() -> FramePreprocessor:
    """Get or create global frame preprocessor instance."""
    global _frame_preprocessor
    if _frame_preprocessor is None:
        _frame_preprocessor = FramePreprocessor()
    return _frame_preprocessor

def get_audio_preprocessor() -> AudioPreprocessor:
    """Get or create global audio preprocessor instance."""
    global _audio_preprocessor
    if _audio_preprocessor is None:
        _audio_preprocessor = AudioPreprocessor()
    return _audio_preprocessor

def get_calibration_service() -> CalibrationService:
    """Get or create global calibration service instance."""
    global _calibration_service
    if _calibration_service is None:
        _calibration_service = CalibrationService()
    return _calibration_service

def get_pose_estimator() -> HeadPoseEstimator:
    """Get or create global pose estimator instance."""
    global _pose_estimator
    if _pose_estimator is None:
        _pose_estimator = HeadPoseEstimator()
    return _pose_estimator

def get_gaze_estimator() -> GazeEstimator:
    """Get or create global gaze estimator instance."""
    global _gaze_estimator
    if _gaze_estimator is None:
        _gaze_estimator = GazeEstimator()
    return _gaze_estimator

def get_kpi_calculator() -> KPICalculator:
    """Get or create global KPI calculator instance."""
    global _kpi_calculator
    if _kpi_calculator is None:
        _kpi_calculator = KPICalculator()
    return _kpi_calculator

def get_stress_analyzer() -> StressAnalyzer:
    """Get or create global stress analyzer instance."""
    global _stress_analyzer
    if _stress_analyzer is None:
        _stress_analyzer = StressAnalyzer()
    return _stress_analyzer

def get_encryption_manager() -> EncryptionManager:
    """Get or create global encryption manager instance."""
    global _encryption_manager
    if _encryption_manager is None:
        _encryption_manager = EncryptionManager()
    return _encryption_manager


# ============================================================================
# Helper: Check C++ availability
# ============================================================================
def is_cpp_available() -> bool:
    """Check if C++ extension is available."""
    return CPP_AVAILABLE

def get_backend_info() -> Dict[str, Any]:
    """Get information about which backend is being used."""
    info = {
        "cpp_available": CPP_AVAILABLE,
        "backend": "C++" if CPP_AVAILABLE else "Python"
    }
    return info