"""
Calibration service for gaze estimation.
Implements 4-point calibration to create transformation matrix.
"""

import numpy as np
import cv2
from typing import List, Tuple, Optional
import logging
import json

logger = logging.getLogger(__name__)


class CalibrationService:
    """
    Manages calibration process for gaze estimation.
    Uses 4-point calibration to create homography transformation matrix.
    """
    
    def __init__(self):
        """Initialize calibration service."""
        self.calibration_points = 4
        logger.info("Calibration service initialized")
    
    def calculate_transformation_matrix(
        self,
        screen_points: List[Tuple[float, float]],
        gaze_points: List[Tuple[float, float]]
    ) -> Tuple[np.ndarray, float]:
        """
        Calculate transformation matrix from calibration points.
        
        Args:
            screen_points: List of 4 screen coordinates (x, y) where user looked
            gaze_points: List of 4 corresponding gaze coordinates from estimator
            
        Returns:
            Tuple of (transformation_matrix, accuracy_score)
            - transformation_matrix: 3x3 homography matrix
            - accuracy_score: Calibration accuracy (0.0 to 1.0)
        """
        try:
            if len(screen_points) != 4 or len(gaze_points) != 4:
                raise ValueError("Exactly 4 calibration points required")
            
            # Convert to numpy arrays
            src_points = np.array(gaze_points, dtype=np.float32)
            dst_points = np.array(screen_points, dtype=np.float32)
            
            # Calculate homography matrix
            matrix, mask = cv2.findHomography(src_points, dst_points, cv2.RANSAC, 5.0)
            
            if matrix is None:
                raise ValueError("Failed to calculate homography matrix")
            
            # Calculate accuracy score (reprojection error)
            accuracy_score = self._calculate_accuracy(
                src_points,
                dst_points,
                matrix
            )
            
            logger.info(f"Calibration matrix calculated (accuracy={accuracy_score:.3f})")
            
            return matrix, accuracy_score
            
        except Exception as e:
            logger.error(f"Calibration error: {str(e)}")
            raise
    
    def _calculate_accuracy(
        self,
        src_points: np.ndarray,
        dst_points: np.ndarray,
        matrix: np.ndarray
    ) -> float:
        """
        Calculate calibration accuracy using reprojection error.
        
        Args:
            src_points: Source points (gaze coordinates)
            dst_points: Destination points (screen coordinates)
            matrix: Transformation matrix
            
        Returns:
            Accuracy score (0.0 to 1.0, higher is better)
        """
        # Transform source points using matrix
        src_homogeneous = np.hstack([src_points, np.ones((len(src_points), 1))])
        transformed = (matrix @ src_homogeneous.T).T
        transformed_points = transformed[:, :2] / transformed[:, 2:]
        
        # Calculate mean squared error
        mse = np.mean(np.sum((transformed_points - dst_points) ** 2, axis=1))
        
        # Convert to accuracy score (inverse of error, normalized)
        # Assuming max acceptable error is 100 pixels
        max_error = 100.0
        accuracy = max(0.0, 1.0 - (np.sqrt(mse) / max_error))
        
        return float(accuracy)
    
    def matrix_to_json(self, matrix: np.ndarray) -> str:
        """
        Convert transformation matrix to JSON string for database storage.
        
        Args:
            matrix: 3x3 transformation matrix
            
        Returns:
            JSON string representation
        """
        return json.dumps(matrix.tolist())
    
    def json_to_matrix(self, json_str: str) -> np.ndarray:
        """
        Convert JSON string back to transformation matrix.
        
        Args:
            json_str: JSON string representation
            
        Returns:
            3x3 transformation matrix
        """
        matrix_list = json.loads(json_str)
        return np.array(matrix_list, dtype=np.float64)


# Global calibration service instance
_calibration_service: Optional[CalibrationService] = None


def get_calibration_service() -> CalibrationService:
    """Get or create global calibration service instance."""
    global _calibration_service
    if _calibration_service is None:
        _calibration_service = CalibrationService()
    return _calibration_service