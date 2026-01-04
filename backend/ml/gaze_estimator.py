"""
Gaze Estimation Engine using MediaPipe Face Detection.
Estimates where the user is looking on the screen.
"""

import cv2
import numpy as np
import mediapipe as mp
from typing import Optional, Tuple, Dict
import logging
from collections import deque

logger = logging.getLogger(__name__)


class GazeEstimator:
    """
    Gaze estimation using MediaPipe face landmarks.
    Uses eye landmarks to calculate gaze direction.
    """
    
    def __init__(self, smoothing_window: int = 5):
        """
        Initialize gaze estimator.
        
        Args:
            smoothing_window: Number of frames for temporal smoothing
        """
        # Initialize MediaPipe Face Mesh
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        # Smoothing buffer
        self.smoothing_window = smoothing_window
        self.gaze_history = deque(maxlen=smoothing_window)
        
        # Eye landmark indices (MediaPipe face mesh)
        self.LEFT_EYE_INDICES = [33, 133, 160, 159, 158, 157, 173, 144]
        self.RIGHT_EYE_INDICES = [362, 263, 387, 386, 385, 384, 398, 373]
        self.LEFT_IRIS_INDICES = [468, 469, 470, 471, 472]
        self.RIGHT_IRIS_INDICES = [473, 474, 475, 476, 477]
        
        logger.info("Gaze estimator initialized")
    
    def estimate(self, frame: np.ndarray, calibration_matrix: Optional[np.ndarray] = None) -> Dict:
        """
        Estimate gaze from a single frame.
        
        Args:
            frame: Input frame (BGR format from OpenCV)
            calibration_matrix: Optional 3x3 transformation matrix from calibration
            
        Returns:
            Dictionary with gaze estimation results:
            {
                'gaze_x': float,  # Normalized gaze X (0.0 to 1.0)
                'gaze_y': float,  # Normalized gaze Y (0.0 to 1.0)
                'confidence': float,  # Confidence score (0.0 to 1.0)
                'raw_gaze_x': float,  # Raw gaze before calibration
                'raw_gaze_y': float,  # Raw gaze before calibration
                'landmarks_detected': bool
            }
        """
        try:
            # Convert normalized float32 frame back to uint8 for MediaPipe
            if frame.dtype == np.float32 and frame.max() <= 1.0:
                frame = (frame * 255.0).astype(np.uint8)
            
            # Convert BGR to RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Process frame with MediaPipe
            results = self.face_mesh.process(rgb_frame)
            
            if not results.multi_face_landmarks:
                return {
                    'gaze_x': 0.5,
                    'gaze_y': 0.5,
                    'confidence': 0.0,
                    'raw_gaze_x': 0.5,
                    'raw_gaze_y': 0.5,
                    'landmarks_detected': False
                }
            
            # Get face landmarks
            face_landmarks = results.multi_face_landmarks[0]
            
            # Calculate gaze from eye landmarks
            raw_gaze_x, raw_gaze_y = self._calculate_gaze_from_landmarks(
                face_landmarks,
                frame.shape
            )
            
            # Apply calibration if available
            if calibration_matrix is not None:
                gaze_x, gaze_y = self._apply_calibration(
                    raw_gaze_x,
                    raw_gaze_y,
                    calibration_matrix
                )
            else:
                gaze_x, gaze_y = raw_gaze_x, raw_gaze_y
            
            # Apply temporal smoothing
            smoothed_x, smoothed_y = self._apply_smoothing(gaze_x, gaze_y)
            
            # Calculate confidence based on landmark detection quality
            confidence = self._calculate_confidence(face_landmarks)
            
            return {
                'gaze_x': smoothed_x,
                'gaze_y': smoothed_y,
                'confidence': confidence,
                'raw_gaze_x': raw_gaze_x,
                'raw_gaze_y': raw_gaze_y,
                'landmarks_detected': True
            }
            
        except Exception as e:
            logger.error(f"Gaze estimation error: {str(e)}")
            return {
                'gaze_x': 0.5,
                'gaze_y': 0.5,
                'confidence': 0.0,
                'raw_gaze_x': 0.5,
                'raw_gaze_y': 0.5,
                'landmarks_detected': False
            }
    
    def _calculate_gaze_from_landmarks(
        self,
        face_landmarks,
        frame_shape: Tuple[int, int, int]
    ) -> Tuple[float, float]:
        """
        Calculate gaze direction from eye landmarks.
        Uses iris position relative to eye corners.
        """
        height, width, _ = frame_shape
        
        # Get left eye landmarks
        left_eye_points = []
        for idx in self.LEFT_EYE_INDICES:
            landmark = face_landmarks.landmark[idx]
            left_eye_points.append([landmark.x * width, landmark.y * height])
        left_eye_points = np.array(left_eye_points)
        
        # Get left iris center
        left_iris_points = []
        for idx in self.LEFT_IRIS_INDICES:
            landmark = face_landmarks.landmark[idx]
            left_iris_points.append([landmark.x * width, landmark.y * height])
        left_iris_center = np.mean(left_iris_points, axis=0)
        
        # Get right eye landmarks
        right_eye_points = []
        for idx in self.RIGHT_EYE_INDICES:
            landmark = face_landmarks.landmark[idx]
            right_eye_points.append([landmark.x * width, landmark.y * height])
        right_eye_points = np.array(right_eye_points)
        
        # Get right iris center
        right_iris_points = []
        for idx in self.RIGHT_IRIS_INDICES:
            landmark = face_landmarks.landmark[idx]
            right_iris_points.append([landmark.x * width, landmark.y * height])
        right_iris_center = np.mean(right_iris_points, axis=0)
        
        # Calculate eye centers
        left_eye_center = np.mean(left_eye_points, axis=0)
        right_eye_center = np.mean(right_eye_points, axis=0)
        
        # Calculate iris offset from eye center (normalized)
        left_offset_x = (left_iris_center[0] - left_eye_center[0]) / width
        left_offset_y = (left_iris_center[1] - left_eye_center[1]) / height
        
        right_offset_x = (right_iris_center[0] - right_eye_center[0]) / width
        right_offset_y = (right_iris_center[1] - right_eye_center[1]) / height
        
        # Average both eyes
        gaze_x = (left_offset_x + right_offset_x) / 2.0
        gaze_y = (left_offset_y + right_offset_y) / 2.0
        
        # Normalize to 0.0-1.0 range (center is 0.5)
        gaze_x = np.clip(gaze_x * 10 + 0.5, 0.0, 1.0)
        gaze_y = np.clip(gaze_y * 10 + 0.5, 0.0, 1.0)
        
        return float(gaze_x), float(gaze_y)
    
    def _apply_calibration(
        self,
        gaze_x: float,
        gaze_y: float,
        calibration_matrix: np.ndarray
    ) -> Tuple[float, float]:
        """
        Apply calibration transformation to raw gaze coordinates.
        
        Args:
            gaze_x: Raw gaze X coordinate
            gaze_y: Raw gaze Y coordinate
            calibration_matrix: 3x3 homography matrix
            
        Returns:
            Calibrated (gaze_x, gaze_y)
        """
        # Convert to homogeneous coordinates
        point = np.array([gaze_x, gaze_y, 1.0])
        
        # Apply transformation
        transformed = calibration_matrix @ point
        
        # Convert back to Cartesian coordinates
        calibrated_x = transformed[0] / transformed[2]
        calibrated_y = transformed[1] / transformed[2]
        
        # Clip to valid range
        calibrated_x = np.clip(calibrated_x, 0.0, 1.0)
        calibrated_y = np.clip(calibrated_y, 0.0, 1.0)
        
        return float(calibrated_x), float(calibrated_y)
    
    def _apply_smoothing(self, gaze_x: float, gaze_y: float) -> Tuple[float, float]:
        """
        Apply temporal smoothing using moving average.
        
        Args:
            gaze_x: Current gaze X
            gaze_y: Current gaze Y
            
        Returns:
            Smoothed (gaze_x, gaze_y)
        """
        # Add to history
        self.gaze_history.append((gaze_x, gaze_y))
        
        # Calculate moving average
        if len(self.gaze_history) > 0:
            smoothed_x = np.mean([g[0] for g in self.gaze_history])
            smoothed_y = np.mean([g[1] for g in self.gaze_history])
            return float(smoothed_x), float(smoothed_y)
        
        return gaze_x, gaze_y
    
    def _calculate_confidence(self, face_landmarks) -> float:
        """
        Calculate confidence score based on landmark detection quality.
        
        Args:
            face_landmarks: MediaPipe face landmarks
            
        Returns:
            Confidence score (0.0 to 1.0)
        """
        # Simple confidence based on number of landmarks detected
        num_landmarks = len(face_landmarks.landmark)
        expected_landmarks = 478  # MediaPipe face mesh has 478 landmarks
        
        confidence = min(num_landmarks / expected_landmarks, 1.0)
        return float(confidence)
    
    def reset_smoothing(self):
        """Reset smoothing buffer (e.g., when starting new session)."""
        self.gaze_history.clear()
    
    def __del__(self):
        """Cleanup MediaPipe resources."""
        if hasattr(self, 'face_mesh'):
            self.face_mesh.close()


# Global gaze estimator instance
_gaze_estimator: Optional[GazeEstimator] = None


def get_gaze_estimator() -> GazeEstimator:
    """Get or create global gaze estimator instance."""
    global _gaze_estimator
    if _gaze_estimator is None:
        _gaze_estimator = GazeEstimator(smoothing_window=5)
    return _gaze_estimator