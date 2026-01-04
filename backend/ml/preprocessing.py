"""
Preprocessing utilities for frame and audio data.
Handles normalization, resizing, and format conversion.
"""

import cv2
import numpy as np
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class FramePreprocessor:
    """Preprocesses video frames for ML engines."""
    
    def __init__(self, target_size: Tuple[int, int] = (640, 480)):
        """
        Initialize frame preprocessor.
        
        Args:
            target_size: Target frame size (width, height)
        """
        self.target_size = target_size
        logger.info(f"Frame preprocessor initialized (target_size={target_size})")
    
    def preprocess(self, frame: np.ndarray) -> np.ndarray:
        """
        Preprocess frame for ML inference.
        
        Args:
            frame: Input frame (BGR format)
            
        Returns:
            Preprocessed frame
        """
        try:
            # Resize to target size
            if frame.shape[:2][::-1] != self.target_size:
                frame = cv2.resize(frame, self.target_size)
            
            # Normalize pixel values to 0-1 range
            frame = frame.astype(np.float32) / 255.0
            
            return frame
            
        except Exception as e:
            logger.error(f"Frame preprocessing error: {str(e)}")
            raise
    
    def denormalize(self, frame: np.ndarray) -> np.ndarray:
        """
        Convert normalized frame back to 0-255 range.
        
        Args:
            frame: Normalized frame (0-1 range)
            
        Returns:
            Denormalized frame (0-255 range)
        """
        return (frame * 255.0).astype(np.uint8)


class AudioPreprocessor:
    """Preprocesses audio data for stress analysis."""
    
    def __init__(self, target_sample_rate: int = 16000):
        """
        Initialize audio preprocessor.
        
        Args:
            target_sample_rate: Target sample rate in Hz
        """
        self.target_sample_rate = target_sample_rate
        logger.info(f"Audio preprocessor initialized (sample_rate={target_sample_rate})")
    
    def preprocess(
        self,
        audio_data: np.ndarray,
        original_sample_rate: int
    ) -> np.ndarray:
        """
        Preprocess audio for stress analysis.
        
        Args:
            audio_data: Input audio samples
            original_sample_rate: Original sample rate
            
        Returns:
            Preprocessed audio
        """
        try:
            # Resample if needed
            if original_sample_rate != self.target_sample_rate:
                import librosa
                audio_data = librosa.resample(
                    audio_data,
                    orig_sr=original_sample_rate,
                    target_sr=self.target_sample_rate
                )
            
            # Normalize amplitude to -1 to 1 range
            max_val = np.abs(audio_data).max()
            if max_val > 0:
                audio_data = audio_data / max_val
            
            # Remove DC offset
            audio_data = audio_data - np.mean(audio_data)
            
            return audio_data.astype(np.float32)
            
        except Exception as e:
            logger.error(f"Audio preprocessing error: {str(e)}")
            raise


# Global preprocessor instances
_frame_preprocessor: Optional[FramePreprocessor] = None
_audio_preprocessor: Optional[AudioPreprocessor] = None


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