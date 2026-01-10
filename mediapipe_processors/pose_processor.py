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
            min_tracking_confidence=0.5,
        )

        self.last_pose_landmarks = None

        # Track consecutive errors to trigger reinitialization
        self.consecutive_errors = 0
        self.max_consecutive_errors = 5

        logger.info("[OK] PoseProcessor initialized")

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
            return {
                "body_detected": False,
                "posture_score": 0.0,
                "pose_confidence": 0.0,
            }

        # Check frame dimensions
        if len(rgb_frame.shape) != 3 or rgb_frame.shape[2] != 3:
            logger.warning(f"Invalid frame dimensions for pose: {rgb_frame.shape}")
            return {
                "body_detected": False,
                "posture_score": 0.0,
                "pose_confidence": 0.0,
            }

        try:
            # Check if we need to reinitialize due to too many errors
            if self.consecutive_errors >= self.max_consecutive_errors:
                logger.warning(
                    "Too many consecutive pose errors, reinitializing MediaPipe graph"
                )
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
                metrics["body_detected"] = True
                return metrics
            else:
                return {
                    "body_detected": False,
                    "posture_score": 0.0,
                    "pose_confidence": 0.0,
                }

        except Exception as e:
            logger.warning(f"Pose processing error (non-critical): {e}")
            self.consecutive_errors += 1
            return {
                "body_detected": False,
                "posture_score": 0.0,
                "pose_confidence": 0.0,
            }

    def _calculate_pose_metrics(self, landmarks):
        """
        Calculate pose metrics from landmarks including activity detection

        Args:
            landmarks: MediaPipe pose landmarks

        Returns:
            dict: Pose metrics with activity detection
        """
        # Get key landmarks
        head = landmarks.landmark[0]
        left_shoulder = landmarks.landmark[11]
        right_shoulder = landmarks.landmark[12]
        left_elbow = landmarks.landmark[13]
        right_elbow = landmarks.landmark[14]
        left_wrist = landmarks.landmark[15]
        right_wrist = landmarks.landmark[16]

        # Store previous positions for movement detection
        if hasattr(self, "prev_landmarks"):
            prev_head = self.prev_landmarks.landmark[0]
            prev_left_wrist = self.prev_landmarks.landmark[15]
            prev_right_wrist = self.prev_landmarks.landmark[16]
        else:
            prev_head = head
            prev_left_wrist = left_wrist
            prev_right_wrist = right_wrist

        # Calculate posture score based on head and shoulder positions
        shoulder_center_x = (left_shoulder.x + right_shoulder.x) / 2
        posture_deviation = abs(head.x - shoulder_center_x)
        posture_score = max(0, 100 - (posture_deviation * 200))

        # Get pose confidence
        pose_confidence = landmarks.landmark[0].visibility if landmarks else 0

        # NEW: Activity detection
        activity_metrics = self._detect_activity(
            head,
            left_shoulder,
            right_shoulder,
            left_elbow,
            right_elbow,
            left_wrist,
            right_wrist,
            prev_head,
            prev_left_wrist,
            prev_right_wrist,
        )

        # Store current landmarks for next frame
        self.prev_landmarks = landmarks

        metrics = {
            "posture_score": posture_score,
            "pose_confidence": pose_confidence,
            "head_x": head.x,
            "head_y": head.y,
            "left_shoulder_x": left_shoulder.x,
            "right_shoulder_x": right_shoulder.x,
            **activity_metrics,
        }

        return metrics

    def _detect_activity(
        self,
        head,
        left_shoulder,
        right_shoulder,
        left_elbow,
        right_elbow,
        left_wrist,
        right_wrist,
        prev_head,
        prev_left_wrist,
        prev_right_wrist,
    ):
        """
        Detect user activity: typing, thinking, resting, etc.

        Returns:
            dict: Activity metrics
        """
        metrics = {}

        # Calculate movement vectors
        head_movement = abs(head.x - prev_head.x) + abs(head.y - prev_head.y)
        left_wrist_movement = abs(left_wrist.x - prev_left_wrist.x) + abs(
            left_wrist.y - prev_left_wrist.y
        )
        right_wrist_movement = abs(right_wrist.x - prev_right_wrist.x) + abs(
            right_wrist.y - prev_right_wrist.y
        )
        total_wrist_movement = left_wrist_movement + right_wrist_movement

        # NEW: Chin resting pose detection (thinking/resting)
        chin_resting = self._detect_chin_resting(head, left_shoulder, right_shoulder)
        metrics["chin_resting"] = chin_resting

        # NEW: Typing detection
        typing_confidence = self._detect_typing(
            left_wrist, right_wrist, left_elbow, right_elbow, total_wrist_movement
        )
        metrics["typing"] = typing_confidence > 0.6
        metrics["typing_confidence"] = typing_confidence

        # NEW: Hand position analysis
        hand_position = self._analyze_hand_position(
            left_wrist, right_wrist, left_shoulder, right_shoulder
        )
        metrics["hand_position"] = hand_position

        # NEW: Activity level
        if total_wrist_movement > 0.15:
            activity = "active"
            activity_level = min(1.0, total_wrist_movement * 3)
        elif head_movement > 0.05:
            activity = "head_movement"
            activity_level = min(1.0, head_movement * 5)
        else:
            activity = "resting"
            activity_level = max(0.0, 1.0 - total_wrist_movement * 2)

        metrics["activity"] = activity
        metrics["activity_level"] = activity_level

        # NEW: Posture context
        if chin_resting and typing_confidence < 0.3:
            metrics["posture_context"] = "thinking"
        elif typing_confidence > 0.6:
            metrics["posture_context"] = "typing"
        elif activity_level > 0.7:
            metrics["posture_context"] = "active"
        else:
            metrics["posture_context"] = "neutral"

        return metrics

    def _detect_chin_resting(self, head, left_shoulder, right_shoulder):
        """
        Detect if user is resting chin on hand (thinking pose)

        Returns:
            float: Confidence of chin resting (0-1)
        """
        # Calculate head position relative to shoulders
        shoulder_center_y = (left_shoulder.y + right_shoulder.y) / 2
        head_to_shoulder_ratio = head.y / shoulder_center_y

        # Chin resting typically indicated by:
        # 1. Head lower than usual (head_y > shoulder_center_y)
        # 2. Slight forward tilt
        chin_resting_confidence = 0.0

        if head_to_shoulder_ratio > 1.05:  # Head lower than shoulders
            chin_resting_confidence += 0.4

        # Add confidence based on head stability (less movement = more likely resting)
        if hasattr(self, "head_movement_history"):
            if len(self.head_movement_history) > 10:
                avg_movement = sum(self.head_movement_history[-10:]) / 10
                if avg_movement < 0.02:  # Very stable head
                    chin_resting_confidence += 0.3
        else:
            self.head_movement_history = []

        # Track head movement
        if hasattr(self, "prev_head_pos"):
            movement = abs(head.x - self.prev_head_pos.x) + abs(
                head.y - self.prev_head_pos.y
            )
            self.head_movement_history.append(movement)
            self.head_movement_history = self.head_movement_history[
                -30:
            ]  # Keep last 30 frames
        self.prev_head_pos = head

        return min(1.0, chin_resting_confidence)

    def _detect_typing(
        self, left_wrist, right_wrist, left_elbow, right_elbow, wrist_movement
    ):
        """
        Detect typing activity based on hand positions and movements

        Returns:
            float: Typing confidence (0-1)
        """
        typing_confidence = 0.0

        # Typing indicators:
        # 1. Wrists near keyboard level (below shoulders)
        # 2. Elbows bent (~90 degrees)
        # 3. Small, rapid wrist movements

        # Check wrist position relative to shoulders
        if left_wrist.y > left_elbow.y and right_wrist.y > right_elbow.y:
            typing_confidence += 0.3

        # Check for rapid, small movements (typing motion)
        if 0.02 < wrist_movement < 0.1:
            typing_confidence += 0.4

        # Check hand proximity (both hands in similar horizontal plane)
        hand_proximity = abs(left_wrist.y - right_wrist.y)
        if hand_proximity < 0.1:
            typing_confidence += 0.3

        return min(1.0, typing_confidence)

    def _analyze_hand_position(
        self, left_wrist, right_wrist, left_shoulder, right_shoulder
    ):
        """
        Analyze hand position for context

        Returns:
            str: Hand position description
        """
        # Calculate average wrist height
        avg_wrist_y = (left_wrist.y + right_wrist.y) / 2
        avg_shoulder_y = (left_shoulder.y + right_shoulder.y) / 2

        # Determine hand position
        if avg_wrist_y < avg_shoulder_y - 0.15:
            return "raised"
        elif avg_wrist_y > avg_shoulder_y + 0.1:
            return "lap_desk"
        else:
            return "neutral"

    def _reinitialize_graph(self):
        """Reinitialize MediaPipe pose graph when it becomes corrupted"""
        try:
            # Close existing graph
            if hasattr(self, "pose") and self.pose:
                try:
                    self.pose.close()
                except Exception:
                    pass

            # Recreate graph with config settings
            self.pose = self.mp_pose.Pose(
                static_image_mode=False,
                model_complexity=self.config.pose_model_complexity,
                smooth_landmarks=False,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5,
            )

            logger.info("[OK] Pose MediaPipe graph reinitialized")

        except Exception as e:
            logger.error(f"Failed to reinitialize pose graph: {e}")

    def cleanup(self):
        """Release MediaPipe resources safely"""
        try:
            # Check if pose exists and is not None
            pose_obj = getattr(self, "pose", None)
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

        logger.info("[OK] PoseProcessor cleaned up")
