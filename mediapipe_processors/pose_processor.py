"""
Pose Detection Processor
Handles body pose detection using MediaPipe Pose
"""

import logging
import numpy as np
import mediapipe as mp

logger = logging.getLogger(__name__)


class PoseProcessor:
    """Processes body pose detection"""

    def __init__(self, config):
        """
        Initialize pose processor

        Args:
            config: Config object from config_loader
        """
        self.config = config
        self.mp_pose = mp.solutions.pose

        # Initialize pose detector with config settings
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=config.pose_model_complexity,
            smooth_landmarks=False,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )

        self.last_pose_landmarks = None
        
        # Track consecutive errors to trigger reinitialization
        self.consecutive_errors = 0
        self.max_consecutive_errors = 5
        
        logger.info("✅ PoseProcessor initialized")

    def process(self, rgb_frame):
        """
        Process frame for pose detection

        Args:
            rgb_frame: RGB image frame

        Returns:
            dict: Pose metrics including posture_score, body_detected, etc.
        """
        # Validate input frame
        if rgb_frame is None or not isinstance(rgb_frame, np.ndarray):
            logger.warning(f"Invalid frame type for pose processing: {type(rgb_frame)}")
            return {'body_detected': False, 'posture_score': 0.0, 'pose_confidence': 0.0}

        # Check frame dimensions
        if len(rgb_frame.shape) != 3 or rgb_frame.shape[2] != 3:
            logger.warning(f"Invalid frame dimensions for pose: {rgb_frame.shape}")
            return {'body_detected': False, 'posture_score': 0.0, 'pose_confidence': 0.0}

        try:
            # Check if we need to reinitialize due to too many errors
            if self.consecutive_errors >= self.max_consecutive_errors:
                logger.warning("Too many consecutive pose errors, reinitializing MediaPipe graph")
                self._reinitialize_graph()
                self.consecutive_errors = 0

            results = self.pose.process(rgb_frame)
            
            # Reset error counter on successful processing
            self.consecutive_errors = 0

            if results.pose_landmarks:
                # Cache landmarks
                self.last_pose_landmarks = results.pose_landmarks

                # Calculate pose metrics
                metrics = self._calculate_pose_metrics(results.pose_landmarks)
                metrics['body_detected'] = True
                return metrics
            else:
                return {
                    'body_detected': False,
                    'posture_score': 0.0,
                    'pose_confidence': 0.0
                }

        except Exception as e:
            logger.warning(f"Pose processing error (non-critical): {e}")
            self.consecutive_errors += 1
            return {
                'body_detected': False,
                'posture_score': 0.0,
                'pose_confidence': 0.0
            }

    def _calculate_pose_metrics(self, landmarks):
        """
        Calculate pose metrics from landmarks

        Args:
            landmarks: MediaPipe pose landmarks

        Returns:
            dict: Pose metrics
        """
        # Get key landmarks
        head = landmarks.landmark[0]
        left_shoulder = landmarks.landmark[11]
        right_shoulder = landmarks.landmark[12]

        # Calculate posture score based on head and shoulder positions
        shoulder_center_x = (left_shoulder.x + right_shoulder.x) / 2
        posture_deviation = abs(head.x - shoulder_center_x)
        posture_score = max(0, 100 - (posture_deviation * 200))

        # Get pose confidence
        pose_confidence = landmarks.landmark[0].visibility if landmarks else 0

        return {
            'posture_score': posture_score,
            'pose_confidence': pose_confidence,
            'head_x': head.x,
            'head_y': head.y,
            'left_shoulder_x': left_shoulder.x,
            'right_shoulder_x': right_shoulder.x
        }

    def _reinitialize_graph(self):
        """Reinitialize MediaPipe pose graph when it becomes corrupted"""
        try:
            # Close existing graph
            if hasattr(self, 'pose') and self.pose:
                try:
                    self.pose.close()
                except:
                    pass
            
            # Recreate graph with config settings
            self.pose = self.mp_pose.Pose(
                static_image_mode=False,
                model_complexity=self.config.pose_model_complexity,
                smooth_landmarks=False,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5
            )
            
            logger.info("✅ Pose MediaPipe graph reinitialized")
            
        except Exception as e:
            logger.error(f"Failed to reinitialize pose graph: {e}")

    def cleanup(self):
        """Release MediaPipe resources safely"""
        try:
            # Check if pose exists and is not None
            pose_obj = getattr(self, 'pose', None)
            if pose_obj is not None:
                try:
                    pose_obj.close()
                    logger.debug("Pose graph closed successfully")
                except Exception as close_error:
                    logger.debug(f"Error closing pose graph: {close_error}")
                finally:
                    self.pose = None
            else:
                logger.debug("Pose object is None, skipping close operation")
        except Exception as e:
            logger.warning(f"⚠️ Pose cleanup error: {e}")
        
        # Reset error tracking
        self.consecutive_errors = 0
        
        logger.info("✅ PoseProcessor cleaned up")
