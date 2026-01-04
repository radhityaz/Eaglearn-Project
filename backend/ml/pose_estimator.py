"""
Head Pose Estimation Engine using MediaPipe Face Mesh.
Estimates head orientation (yaw, pitch, roll) and classifies posture.
"""

import cv2
import numpy as np
import mediapipe as mp
from typing import Dict, Tuple
import logging

logger = logging.getLogger(__name__)


class HeadPoseEstimator:
    """
    Head pose estimation using MediaPipe face landmarks.
    Calculates yaw, pitch, roll angles and classifies posture.
    """
    
    def __init__(self):
        """Initialize head pose estimator."""
        # Initialize MediaPipe Face Mesh
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        # 3D model points for head pose estimation (canonical face model)
        self.model_points = np.array([
            (0.0, 0.0, 0.0),             # Nose tip
            (0.0, -330.0, -65.0),        # Chin
            (-225.0, 170.0, -135.0),     # Left eye left corner
            (225.0, 170.0, -135.0),      # Right eye right corner
            (-150.0, -150.0, -125.0),    # Left mouth corner
            (150.0, -150.0, -125.0)      # Right mouth corner
        ], dtype=np.float64)
        
        # Landmark indices for 2D points (MediaPipe face mesh)
        self.landmark_indices = [1, 152, 33, 263, 61, 291]  # Nose, chin, eyes, mouth
        
        logger.info("Head pose estimator initialized")
    
    def estimate(self, frame: np.ndarray) -> Dict:
        """
        Estimate head pose from a single frame.
        
        Args:
            frame: Input frame (BGR format from OpenCV)
            
        Returns:
            Dictionary with pose estimation results:
            {
                'yaw': float,  # Yaw angle in degrees (-90 to 90)
                'pitch': float,  # Pitch angle in degrees (-90 to 90)
                'roll': float,  # Roll angle in degrees (-90 to 90)
                'posture': str,  # Posture classification
                'confidence': float,  # Confidence score (0.0 to 1.0)
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
                    'yaw': 0.0,
                    'pitch': 0.0,
                    'roll': 0.0,
                    'posture': 'unknown',
                    'confidence': 0.0,
                    'landmarks_detected': False
                }
            
            # Get face landmarks
            face_landmarks = results.multi_face_landmarks[0]
            
            # Extract 2D points from landmarks
            image_points = self._extract_2d_points(face_landmarks, frame.shape)
            
            # Calculate pose angles
            yaw, pitch, roll = self._calculate_pose_angles(image_points, frame.shape)
            
            # Classify posture
            posture = self._classify_posture(yaw, pitch, roll)
            
            # Calculate confidence
            confidence = self._calculate_confidence(face_landmarks)
            
            return {
                'yaw': float(yaw),
                'pitch': float(pitch),
                'roll': float(roll),
                'posture': posture,
                'confidence': float(confidence),
                'landmarks_detected': True
            }
            
        except Exception as e:
            logger.error(f"Head pose estimation error: {str(e)}")
            return {
                'yaw': 0.0,
                'pitch': 0.0,
                'roll': 0.0,
                'posture': 'unknown',
                'confidence': 0.0,
                'landmarks_detected': False
            }
    
    def _extract_2d_points(self, face_landmarks, frame_shape: Tuple[int, int, int]) -> np.ndarray:
        """
        Extract 2D points from face landmarks.
        
        Args:
            face_landmarks: MediaPipe face landmarks
            frame_shape: Frame shape (height, width, channels)
            
        Returns:
            2D points array (6 points x 2 coordinates)
        """
        height, width, _ = frame_shape
        
        image_points = []
        for idx in self.landmark_indices:
            landmark = face_landmarks.landmark[idx]
            x = landmark.x * width
            y = landmark.y * height
            image_points.append([x, y])
        
        return np.array(image_points, dtype=np.float64)
    
    def _calculate_pose_angles(
        self,
        image_points: np.ndarray,
        frame_shape: Tuple[int, int, int]
    ) -> Tuple[float, float, float]:
        """
        Calculate yaw, pitch, roll angles using PnP (Perspective-n-Point).
        
        Args:
            image_points: 2D facial landmarks
            frame_shape: Frame shape
            
        Returns:
            (yaw, pitch, roll) in degrees
        """
        height, width, _ = frame_shape
        
        # Camera matrix (assuming standard webcam)
        focal_length = width
        center = (width / 2, height / 2)
        camera_matrix = np.array([
            [focal_length, 0, center[0]],
            [0, focal_length, center[1]],
            [0, 0, 1]
        ], dtype=np.float64)
        
        # Assuming no lens distortion
        dist_coeffs = np.zeros((4, 1))
        
        # Solve PnP
        success, rotation_vector, translation_vector = cv2.solvePnP(
            self.model_points,
            image_points,
            camera_matrix,
            dist_coeffs,
            flags=cv2.SOLVEPNP_ITERATIVE
        )
        
        if not success:
            return 0.0, 0.0, 0.0
        
        # Convert rotation vector to rotation matrix
        rotation_matrix, _ = cv2.Rodrigues(rotation_vector)
        
        # Calculate Euler angles from rotation matrix
        yaw, pitch, roll = self._rotation_matrix_to_euler_angles(rotation_matrix)
        
        return yaw, pitch, roll
    
    def _rotation_matrix_to_euler_angles(self, R: np.ndarray) -> Tuple[float, float, float]:
        """
        Convert rotation matrix to Euler angles (yaw, pitch, roll).
        
        Args:
            R: 3x3 rotation matrix
            
        Returns:
            (yaw, pitch, roll) in degrees
        """
        sy = np.sqrt(R[0, 0] * R[0, 0] + R[1, 0] * R[1, 0])
        
        singular = sy < 1e-6
        
        if not singular:
            pitch = np.arctan2(R[2, 1], R[2, 2])
            yaw = np.arctan2(-R[2, 0], sy)
            roll = np.arctan2(R[1, 0], R[0, 0])
        else:
            pitch = np.arctan2(-R[1, 2], R[1, 1])
            yaw = np.arctan2(-R[2, 0], sy)
            roll = 0
        
        # Convert to degrees
        pitch = np.degrees(pitch)
        yaw = np.degrees(yaw)
        roll = np.degrees(roll)
        
        return float(yaw), float(pitch), float(roll)
    
    def _classify_posture(self, yaw: float, pitch: float, roll: float) -> str:
        """
        Classify posture based on head angles.
        
        Args:
            yaw: Yaw angle in degrees
            pitch: Pitch angle in degrees
            roll: Roll angle in degrees
            
        Returns:
            Posture classification: "good", "forward", "tilted", "slouched"
        """
        # Good posture: head relatively straight
        if abs(yaw) < 15 and abs(pitch) < 15 and abs(roll) < 10:
            return "good"
        
        # Forward lean: pitch > 15 degrees
        if pitch > 15:
            return "forward"
        
        # Tilted: roll > 10 degrees
        if abs(roll) > 10:
            return "tilted"
        
        # Slouched: pitch < -15 degrees
        if pitch < -15:
            return "slouched"
        
        # Default
        return "good"
    
    def _calculate_confidence(self, face_landmarks) -> float:
        """
        Calculate confidence score based on landmark detection quality.
        
        Args:
            face_landmarks: MediaPipe face landmarks
            
        Returns:
            Confidence score (0.0 to 1.0)
        """
        num_landmarks = len(face_landmarks.landmark)
        expected_landmarks = 478
        confidence = min(num_landmarks / expected_landmarks, 1.0)
        return float(confidence)
    
    def __del__(self):
        """Cleanup MediaPipe resources."""
        if hasattr(self, 'face_mesh'):
            self.face_mesh.close()


# Global pose estimator instance
_pose_estimator = None


def get_pose_estimator() -> HeadPoseEstimator:
    """Get or create global pose estimator instance."""
    global _pose_estimator
    if _pose_estimator is None:
        _pose_estimator = HeadPoseEstimator()
    return _pose_estimator