"""
Face Mesh Processor
Handles facial landmark detection and analysis
"""

import logging
import numpy as np
import mediapipe as mp
from collections import deque

logger = logging.getLogger(__name__)


class FaceMeshProcessor:
    """Processes facial landmarks and micro-expressions"""

    def __init__(self, config):
        """
        Initialize face mesh processor

        Args:
            config: Config object from config_loader
        """
        self.config = config
        self.mp_face_detection = mp.solutions.face_detection
        self.mp_face_mesh = mp.solutions.face_mesh

        # Initialize face detection
        self.face_detection = self.mp_face_detection.FaceDetection(
            model_selection=config.face_detection_selection,
            min_detection_confidence=0.3
        )

        # Initialize face mesh with iris refinement
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            refine_landmarks=True,  # Enable iris tracking
            min_detection_confidence=0.3,
            min_tracking_confidence=0.3
        )

        self.last_face_landmarks = None

        # Face stability tracking for selective processing
        self.face_stability_history = deque(maxlen=5)

        # Track last successful processing to avoid timestamp conflicts
        self.last_frame_timestamp = None

        # Track consecutive errors to trigger reinitialization
        self.consecutive_errors = 0
        self.max_consecutive_errors = 5

        logger.info("✅ FaceMeshProcessor initialized")

    def process(self, rgb_frame, state):
        """
        Process frame for face detection and landmark extraction

        Args:
            rgb_frame: RGB image frame
            state: SessionState object to update

        Returns:
            dict: Face metrics including EAR, MAR, head pose, eye gaze, etc.
        """
        # Validate input frame
        if rgb_frame is None or not isinstance(rgb_frame, np.ndarray):
            logger.warning(f"Invalid frame type for face processing: {type(rgb_frame)}")
            return {'face_detected': False, 'face_count': 0}

        # Check frame dimensions
        if len(rgb_frame.shape) != 3 or rgb_frame.shape[2] != 3:
            logger.warning(f"Invalid frame dimensions: {rgb_frame.shape}")
            return {'face_detected': False, 'face_count': 0}

        try:
            # Check if we need to reinitialize due to too many errors
            if self.consecutive_errors >= self.max_consecutive_errors:
                logger.warning("Too many consecutive errors, reinitializing MediaPipe graphs")
                self._reinitialize_graphs()
                self.consecutive_errors = 0

            # First, detect faces
            detection_results = self.face_detection.process(rgb_frame)
            
            # Reset error counter on successful processing
            self.consecutive_errors = 0

            if detection_results.detections:
                metrics = {
                    'face_detected': True,
                    'face_count': len(detection_results.detections)
                }

                # Selective processing: only process face mesh if face is stable
                if self._should_process_face_mesh():
                    try:
                        face_results = self.face_mesh.process(rgb_frame)
                        if face_results.multi_face_landmarks:
                            # Cache landmarks
                            self.last_face_landmarks = face_results.multi_face_landmarks[0]

                            # Extract detailed metrics
                            landmarks = face_results.multi_face_landmarks[0]
                            metrics.update(self._extract_face_metrics(landmarks, state))

                            # Update stability tracking
                            self._update_stability_tracking(0.9)  # High confidence if processed
                    except Exception as e:
                        logger.warning(f"Face mesh processing error (non-critical): {e}")
                        # Continue with basic face detection only
                        self._update_stability_tracking(0.5)  # Medium confidence
                else:
                    # Skip processing, return minimal metrics
                    metrics.update({
                        'eye_aspect_ratio': state.eye_aspect_ratio if hasattr(state, 'eye_aspect_ratio') else 0.0,
                        'mouth_aspect_ratio': state.mouth_aspect_ratio if hasattr(state, 'mouth_aspect_ratio') else 0.0,
                    })
                    # Update stability tracking
                    self._update_stability_tracking(0.3)  # Low confidence if skipped

                return metrics
            else:
                self._update_stability_tracking(0.0)  # No face detected
                return {
                    'face_detected': False,
                    'face_count': 0
                }

        except Exception as e:
            logger.error(f"Face processing error: {e}")
            self.consecutive_errors += 1
            
            # Return safe fallback values
            return {
                'face_detected': False,
                'face_count': 0,
                'eye_aspect_ratio': 0.0,
                'mouth_aspect_ratio': 0.0
            }

    def _should_process_face_mesh(self):
        """
        Determine if face mesh should be processed based on stability

        Returns:
            bool: True if face is stable enough for processing
        """
        if not self.config.selective_face_mesh_enabled:
            return True  # Always process if disabled

        if len(self.face_stability_history) < 3:
            return True  # Need more data points

        avg_stability = sum(self.face_stability_history) / len(self.face_stability_history)
        return avg_stability >= self.config.face_stability_threshold

    def _update_stability_tracking(self, confidence):
        """Update face stability history"""
        self.face_stability_history.append(confidence)

    def _extract_face_metrics(self, landmarks, state):
        """
        Extract comprehensive facial metrics from landmarks

        Args:
            landmarks: MediaPipe face mesh landmarks
            state: SessionState object

        Returns:
            dict: Facial metrics
        """
        import time

        metrics = {}

        # Ensure state attributes are properly initialized with numeric types
        if not hasattr(state, 'blink_count'):
            state.blink_count = 0
        if not hasattr(state, 'last_blink_time'):
            state.last_blink_time = None
        if not hasattr(state, 'session_start_time'):
            state.session_start_time = None
        if not hasattr(state, 'blink_rate'):
            state.blink_rate = 0

        # ===== EYE ASPECT RATIO (EAR) =====
        try:
            left_eye_top = float(landmarks.landmark[159].y)
            left_eye_bottom = float(landmarks.landmark[145].y)
            left_eye_left = float(landmarks.landmark[33].x)
            left_eye_right = float(landmarks.landmark[133].x)

            eye_vertical = abs(left_eye_top - left_eye_bottom)
            eye_horizontal = abs(left_eye_left - left_eye_right)

            ear = eye_vertical / eye_horizontal if eye_horizontal > 0 else 0
            metrics['eye_aspect_ratio'] = min(ear, 1.0)
        except (AttributeError, TypeError, ZeroDivisionError) as e:
            logger.warning(f"Error calculating EAR: {e}")
            metrics['eye_aspect_ratio'] = 0.0
            ear = 0.0

        # ===== BLINK DETECTION =====
        blink_ear_threshold = self.config.get('emotion', 'blink_ear_threshold', default=0.21)
        blink_debounce = self.config.get('emotion', 'blink_debounce_time', default=0.20)

        current_time = time.time()
        is_blinking = ear < blink_ear_threshold

        if is_blinking:
            # Check debounce time to prevent double-counting
            if hasattr(state, 'last_blink_time') and state.last_blink_time is not None:
                try:
                    # Ensure last_blink_time is numeric
                    last_blink_time = float(state.last_blink_time)
                    if (current_time - last_blink_time) > blink_debounce:
                        state.blink_count += 1
                        state.last_blink_time = current_time

                        # Calculate blink rate
                        if hasattr(state, 'session_start_time') and state.session_start_time:
                            try:
                                session_start_time = float(state.session_start_time)
                                session_duration = current_time - session_start_time
                                if session_duration > 0:
                                    state.blink_rate = int((state.blink_count / session_duration) * 60)
                            except (ValueError, TypeError):
                                logger.warning(f"Invalid session_start_time type: {type(state.session_start_time)}")
                except (ValueError, TypeError):
                    logger.warning(f"Invalid last_blink_time type: {type(state.last_blink_time)}")
                    state.last_blink_time = current_time  # Reset to valid value

        metrics['is_blinking'] = is_blinking

        # ===== MOUTH ASPECT RATIO (MAR) =====
        upper_lip = landmarks.landmark[13].y
        lower_lip = landmarks.landmark[14].y
        mouth_left = landmarks.landmark[61].x
        mouth_right = landmarks.landmark[291].x

        mouth_vertical = abs(upper_lip - lower_lip)
        mouth_horizontal = abs(mouth_left - mouth_right)

        mar = mouth_vertical / mouth_horizontal if mouth_horizontal > 0 else 0
        metrics['mouth_aspect_ratio'] = min(mar, 1.0)

        # ===== EYEBROW ANALYSIS =====
        left_eyebrow_top = landmarks.landmark[66].y
        left_eye_center = (left_eye_top + left_eye_bottom) / 2
        right_eyebrow_top = landmarks.landmark[296].y
        right_eye_top = landmarks.landmark[386].y
        right_eye_bottom = landmarks.landmark[374].y
        right_eye_center = (right_eye_top + right_eye_bottom) / 2

        left_eyebrow_dist = abs(left_eyebrow_top - left_eye_center)
        right_eyebrow_dist = abs(right_eyebrow_top - right_eye_center)
        eyebrow_raise = (left_eyebrow_dist + right_eyebrow_dist) / 2
        metrics['eyebrow_raise'] = np.clip(eyebrow_raise * 10, 0, 1)

        left_inner_brow = landmarks.landmark[107].x
        right_inner_brow = landmarks.landmark[336].x
        eyebrow_furrow = abs(left_inner_brow - right_inner_brow)
        metrics['eyebrow_furrow'] = np.clip(eyebrow_furrow * 5, 0, 1)

        # ===== LIP TENSION & FROWN =====
        lip_left_corner = landmarks.landmark[61]
        lip_right_corner = landmarks.landmark[291]
        upper_lip_center = landmarks.landmark[13]

        lip_width = abs(lip_right_corner.x - lip_left_corner.x)
        metrics['lip_tension'] = min(lip_width * 2, 1.0)

        lip_corners_avg_y = (lip_left_corner.y + lip_right_corner.y) / 2
        mouth_center_y = upper_lip_center.y
        frown_degree = (lip_corners_avg_y - mouth_center_y) * 100
        metrics['frown_degree'] = np.clip(frown_degree, -1, 1)

        # ===== EYE GAZE DIRECTION =====
        if len(landmarks.landmark) > 475:
            # Use iris landmarks for accurate gaze tracking
            left_iris_center = landmarks.landmark[468]
            right_iris_center = landmarks.landmark[473]

            avg_iris_x = (left_iris_center.x + right_iris_center.x) / 2
            avg_iris_y = (left_iris_center.y + right_iris_center.y) / 2

            left_eye_outer = landmarks.landmark[33].x
            left_eye_inner = landmarks.landmark[133].x
            right_eye_inner = landmarks.landmark[362].x
            right_eye_outer = landmarks.landmark[263].x

            left_eye_width = left_eye_inner - left_eye_outer
            right_eye_width = right_eye_outer - right_eye_inner
            avg_eye_width = (left_eye_width + right_eye_width) / 2

            left_eye_top_v = landmarks.landmark[159].y
            left_eye_bottom_v = landmarks.landmark[145].y
            right_eye_top_v = landmarks.landmark[386].y
            right_eye_bottom_v = landmarks.landmark[374].y

            avg_eye_top = (left_eye_top_v + right_eye_top_v) / 2
            avg_eye_bottom = (left_eye_bottom_v + right_eye_bottom_v) / 2
            avg_eye_height = avg_eye_bottom - avg_eye_top

            face_center_x = (left_eye_outer + right_eye_outer) / 2

            # Calculate raw gaze (before calibration)
            raw_gaze_x = (avg_iris_x - face_center_x) / (avg_eye_width * 2.5) if avg_eye_width > 0 else 0
            raw_gaze_y = (avg_iris_y - avg_eye_top) / avg_eye_height - 0.5 if avg_eye_height > 0 else 0

            # Apply calibration if available (from self.calibration if passed)
            # Check if state has calibration data
            if hasattr(state, 'calibration_applied') and state.calibration_applied:
                # Use calibrated values with type validation
                try:
                    gaze_offset_x = float(state.calibration_gaze_offset_x) if hasattr(state, 'calibration_gaze_offset_x') else 0.0
                    gaze_offset_y = float(state.calibration_gaze_offset_y) if hasattr(state, 'calibration_gaze_offset_y') else 0.0
                    scale_factor = float(state.calibration_scale_factor) if hasattr(state, 'calibration_scale_factor') else 1.0
                    
                    eye_gaze_x = raw_gaze_x - gaze_offset_x
                    eye_gaze_y = raw_gaze_y - gaze_offset_y
                    eye_gaze_x *= scale_factor
                    eye_gaze_y *= scale_factor
                except (ValueError, TypeError) as e:
                    logger.warning(f"Calibration data type error: {e}, using raw gaze values")
                    eye_gaze_x = raw_gaze_x
                    eye_gaze_y = raw_gaze_y
            else:
                # Use raw values (no calibration)
                eye_gaze_x = raw_gaze_x
                eye_gaze_y = raw_gaze_y

            metrics['eye_gaze_x'] = np.clip(eye_gaze_x, -1, 1)
            metrics['eye_gaze_y'] = np.clip(eye_gaze_y, -1, 1)
            metrics['raw_gaze_x'] = raw_gaze_x  # Store raw for calibration
            metrics['raw_gaze_y'] = raw_gaze_y

            # Calculate screen coordinates (with better calibration support)
            screen_width = self.config.get('eye_tracking', 'screen_width', default=1920)
            screen_height = self.config.get('eye_tracking', 'screen_height', default=1080)

            # Get calibration data if available
            if hasattr(state, 'calibration_scale_x'):
                try:
                    scale_x = float(state.calibration_scale_x)
                    scale_y = float(state.calibration_scale_y)
                except (ValueError, TypeError):
                    logger.warning(f"Invalid calibration scale types, using defaults")
                    scale_x = self.config.get('eye_tracking', 'gaze_scale_x', default=800)
                    scale_y = self.config.get('eye_tracking', 'gaze_scale_y', default=450)
            else:
                scale_x = self.config.get('eye_tracking', 'gaze_scale_x', default=800)
                scale_y = self.config.get('eye_tracking', 'gaze_scale_y', default=450)

            center_x = screen_width / 2
            center_y = screen_height / 2

            screen_x = int(center_x + (eye_gaze_x * scale_x))
            screen_y = int(center_y + (eye_gaze_y * scale_y))

            metrics['screen_x'] = max(0, min(screen_width, screen_x))
            metrics['screen_y'] = max(0, min(screen_height, screen_y))

            # Determine looking direction
            threshold = self.config.get('eye_tracking', 'sensitivity_threshold', default=0.18)

            if abs(eye_gaze_x) < threshold and abs(eye_gaze_y) < threshold:
                metrics['looking_at'] = "center"
                metrics['attention_score'] = 100
            elif eye_gaze_y < -threshold and eye_gaze_x < -threshold:
                metrics['looking_at'] = "top-left"
                metrics['attention_score'] = 40
            elif eye_gaze_y < -threshold and eye_gaze_x > threshold:
                metrics['looking_at'] = "top-right"
                metrics['attention_score'] = 40
            elif eye_gaze_y > threshold and eye_gaze_x < -threshold:
                metrics['looking_at'] = "bottom-left"
                metrics['attention_score'] = 30
            elif eye_gaze_y > threshold and eye_gaze_x > threshold:
                metrics['looking_at'] = "bottom-right"
                metrics['attention_score'] = 30
            elif eye_gaze_y < -threshold:
                metrics['looking_at'] = "top"
                metrics['attention_score'] = 60
            elif eye_gaze_y > threshold:
                metrics['looking_at'] = "bottom"
                metrics['attention_score'] = 50
            elif eye_gaze_x < -threshold:
                metrics['looking_at'] = "left"
                metrics['attention_score'] = 70
            elif eye_gaze_x > threshold:
                metrics['looking_at'] = "right"
                metrics['attention_score'] = 70

        # ===== HEAD POSE =====
        nose_tip = landmarks.landmark[1]
        chin = landmarks.landmark[152]
        left_eye = landmarks.landmark[33]
        right_eye = landmarks.landmark[263]

        eye_center_x = (left_eye.x + right_eye.x) / 2
        yaw = (nose_tip.x - eye_center_x) * 90
        pitch = (nose_tip.y - chin.y) * 60
        eye_diff_y = left_eye.y - right_eye.y
        roll = np.arctan2(eye_diff_y, right_eye.x - left_eye.x) * 180 / np.pi

        metrics['head_yaw'] = np.clip(yaw, -90, 90)
        metrics['head_pitch'] = np.clip(pitch, -90, 90)
        metrics['head_roll'] = np.clip(roll, -90, 90)

        # ===== DERIVED METRICS =====
        confusion_level = (eyebrow_raise * 2 + (ear - 0.25) * 2) if ear > 0.25 else 0
        metrics['confusion_level'] = np.clip(confusion_level, 0, 1)

        blink_stress = 0
        if hasattr(state, 'blink_rate') and state.blink_rate is not None:
            try:
                blink_rate = float(state.blink_rate)
                if blink_rate < 10 or blink_rate > 30:
                    blink_stress = 0.3
            except (ValueError, TypeError):
                logger.warning(f"Invalid blink_rate type: {type(state.blink_rate)}")
        metrics['stress_level'] = np.clip(metrics['lip_tension'] * 0.7 + blink_stress, 0, 1)

        # ===== YAWNING DETECTION =====
        is_yawning = mar > 0.6
        current_time = time.time()

        if is_yawning:
            if hasattr(state, 'last_yawn_time') and state.last_yawn_time is not None:
                try:
                    last_yawn_time = float(state.last_yawn_time)
                    if (current_time - last_yawn_time) < 5:
                        metrics['yawning_duration'] = current_time - last_yawn_time
                    else:
                        metrics['last_yawn_time'] = current_time
                        metrics['yawning_duration'] = 0
                except (ValueError, TypeError):
                    logger.warning(f"Invalid last_yawn_time type: {type(state.last_yawn_time)}")
                    metrics['last_yawn_time'] = current_time
                    metrics['yawning_duration'] = 0
            else:
                metrics['last_yawn_time'] = current_time
                metrics['yawning_duration'] = 0
        else:
            metrics['yawning_duration'] = 0

        return metrics

    def _reinitialize_graphs(self):
        """Reinitialize MediaPipe graphs when they become corrupted"""
        try:
            # Close existing graphs
            if hasattr(self, 'face_detection') and self.face_detection:
                try:
                    self.face_detection.close()
                except:
                    pass
            if hasattr(self, 'face_mesh') and self.face_mesh:
                try:
                    self.face_mesh.close()
                except:
                    pass
            
            # Recreate graphs
            self.face_detection = self.mp_face_detection.FaceDetection(
                model_selection=self.config.face_detection_selection,
                min_detection_confidence=0.3
            )
            
            self.face_mesh = self.mp_face_mesh.FaceMesh(
                static_image_mode=False,
                max_num_faces=1,
                refine_landmarks=True,
                min_detection_confidence=0.3,
                min_tracking_confidence=0.3
            )
            
            logger.info("✅ MediaPipe graphs reinitialized")
            
        except Exception as e:
            logger.error(f"Failed to reinitialize MediaPipe graphs: {e}")

    def cleanup(self):
        """Release MediaPipe resources safely"""
        try:
            # Check if face_detection exists and is not None
            face_detection_obj = getattr(self, 'face_detection', None)
            if face_detection_obj is not None:
                try:
                    face_detection_obj.close()
                    logger.debug("Face detection graph closed successfully")
                except Exception as close_error:
                    logger.debug(f"Error closing face detection graph: {close_error}")
                finally:
                    self.face_detection = None
            else:
                logger.debug("Face detection object is None, skipping close operation")
        except Exception as e:
            logger.warning(f"⚠️ Face detection cleanup error: {e}")

        try:
            # Check if face_mesh exists and is not None
            face_mesh_obj = getattr(self, 'face_mesh', None)
            if face_mesh_obj is not None:
                try:
                    face_mesh_obj.close()
                    logger.debug("Face mesh graph closed successfully")
                except Exception as close_error:
                    logger.debug(f"Error closing face mesh graph: {close_error}")
                finally:
                    self.face_mesh = None
            else:
                logger.debug("Face mesh object is None, skipping close operation")
        except Exception as e:
            logger.warning(f"⚠️ Face mesh cleanup error: {e}")

        # Reset error tracking
        self.consecutive_errors = 0

        logger.info("✅ FaceMeshProcessor cleaned up")
