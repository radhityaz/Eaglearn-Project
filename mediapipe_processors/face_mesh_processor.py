"""
Face Mesh Processor
Handles facial landmark detection and analysis
"""

import logging
import numpy as np
import mediapipe as mp
from collections import deque
from typing import TypedDict

logger = logging.getLogger(__name__)


class _OverlayPoint(TypedDict):
    id: str
    x: int
    y: int
    group: str


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
            min_detection_confidence=0.3,
        )

        # Initialize face mesh with iris refinement
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            refine_landmarks=True,  # Enable iris tracking
            min_detection_confidence=0.3,
            min_tracking_confidence=0.3,
        )

        self.last_face_landmarks = None
        self.last_face_landmarks_time = 0.0

        # Face stability tracking for selective processing
        self.face_stability_history = deque(maxlen=5)

        # Track last successful processing to avoid timestamp conflicts
        self.last_frame_timestamp = None

        # Track consecutive errors to trigger reinitialization
        self.consecutive_errors = 0
        self.max_consecutive_errors = 5

        logger.info("[OK] FaceMeshProcessor initialized")

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
            return {"face_detected": False, "face_count": 0}

        # Check frame dimensions
        if len(rgb_frame.shape) != 3 or rgb_frame.shape[2] != 3:
            logger.warning(f"Invalid frame dimensions: {rgb_frame.shape}")
            return {"face_detected": False, "face_count": 0}

        try:
            # Check if we need to reinitialize due to too many errors
            if self.consecutive_errors >= self.max_consecutive_errors:
                logger.warning(
                    "Too many consecutive errors, reinitializing MediaPipe graphs"
                )
                self._reinitialize_graphs()
                self.consecutive_errors = 0

            # First, detect faces
            detection_results = self.face_detection.process(rgb_frame)

            # Reset error counter on successful processing
            self.consecutive_errors = 0

            if detection_results.detections:
                metrics = {
                    "face_detected": True,
                    "face_count": len(detection_results.detections),
                    "face_mesh_processed": False,
                }

                # Selective processing: only process face mesh if face is stable
                if self._should_process_face_mesh(state):
                    try:
                        import time

                        face_results = self.face_mesh.process(rgb_frame)
                        if face_results.multi_face_landmarks:
                            # Cache landmarks
                            self.last_face_landmarks = (
                                face_results.multi_face_landmarks[0]
                            )
                            self.last_face_landmarks_time = time.time()

                            # Extract detailed metrics
                            landmarks = face_results.multi_face_landmarks[0]
                            metrics.update(self._extract_face_metrics(landmarks, state))
                            try:
                                h, w = rgb_frame.shape[:2]
                                mode = str(
                                    getattr(state, "face_mesh_overlay_mode", None)
                                    or "full"
                                ).strip()
                                stride = int(
                                    getattr(state, "face_mesh_overlay_stride", 0) or 0
                                )
                                metrics["_overlay"] = self._extract_overlay_points(
                                    landmarks, w, h, mode=mode, stride=stride
                                )
                            except Exception:
                                metrics["_overlay"] = None
                            metrics["face_mesh_processed"] = True

                            # Update stability tracking
                            self._update_stability_tracking(
                                0.9
                            )  # High confidence if processed
                    except Exception as e:
                        logger.warning(
                            f"Face mesh processing error (non-critical): {e}"
                        )
                        # Continue with basic face detection only
                        self._update_stability_tracking(0.5)  # Medium confidence
                elif (
                    bool(getattr(state, "force_face_mesh", False))
                    and self.last_face_landmarks
                ):
                    try:
                        import time

                        now = time.time()
                        if (now - float(self.last_face_landmarks_time or 0.0)) <= 0.6:
                            h, w = rgb_frame.shape[:2]
                            mode = str(
                                getattr(state, "face_mesh_overlay_mode", None) or "full"
                            ).strip()
                            stride = int(
                                getattr(state, "face_mesh_overlay_stride", 0) or 0
                            )
                            metrics["_overlay"] = self._extract_overlay_points(
                                self.last_face_landmarks, w, h, mode=mode, stride=stride
                            )
                            metrics["face_mesh_processed"] = True
                            self._update_stability_tracking(0.6)
                    except Exception:
                        pass
                else:
                    # Skip processing, return minimal metrics
                    metrics.update(
                        {
                            "eye_aspect_ratio": state.eye_aspect_ratio
                            if hasattr(state, "eye_aspect_ratio")
                            else 0.0,
                            "mouth_aspect_ratio": state.mouth_aspect_ratio
                            if hasattr(state, "mouth_aspect_ratio")
                            else 0.0,
                            "_overlay": None,
                        }
                    )
                    # Update stability tracking
                    self._update_stability_tracking(0.3)  # Low confidence if skipped

                return metrics
            else:
                self._update_stability_tracking(0.0)  # No face detected
                return {
                    "face_detected": False,
                    "face_count": 0,
                    "face_mesh_processed": False,
                }

        except Exception as e:
            logger.error(f"Face processing error: {e}")
            self.consecutive_errors += 1

            # Return safe fallback values
            return {
                "face_detected": False,
                "face_count": 0,
                "eye_aspect_ratio": 0.0,
                "mouth_aspect_ratio": 0.0,
                "face_mesh_processed": False,
            }

    def _should_process_face_mesh(self, state=None):
        """
        Determine if face mesh should be processed based on stability

        Returns:
            bool: True if face is stable enough for processing
        """
        if bool(getattr(state, "force_face_mesh", False)):
            return True

        if not self.config.selective_face_mesh_enabled:
            return True  # Always process if disabled

        frame_count = getattr(state, "frame_count", 0) if state is not None else 0
        if frame_count % 2 == 0:
            return True

        if len(self.face_stability_history) < 3:
            return True  # Need more data points

        avg_stability = sum(self.face_stability_history) / len(
            self.face_stability_history
        )
        return avg_stability >= self.config.face_stability_threshold

    def _extract_overlay_points(
        self, landmarks, frame_w: int, frame_h: int, *, mode: str, stride: int
    ):
        groups = {
            "left_eye": [33, 159, 145, 133],
            "right_eye": [362, 386, 374, 263],
            "left_iris": [468, 469, 470, 471, 472],
            "right_iris": [473, 474, 475, 476, 477],
            "nose": [1],
            "mouth": [13, 14, 61, 291],
        }

        points: list[_OverlayPoint] = []
        mode = (mode or "").strip().lower()
        if mode in ("full", "mesh", "facemesh", "triangles", "triangle"):
            s = int(stride) if int(stride) > 0 else 2
            count = len(landmarks.landmark)
            for idx in range(0, count, s):
                lm = landmarks.landmark[idx]
                x = int(float(lm.x) * frame_w)
                y = int(float(lm.y) * frame_h)
                points.append({"id": f"mesh:{idx}", "x": x, "y": y, "group": "mesh"})

        for group, idxs in groups.items():
            for idx in idxs:
                lm = landmarks.landmark[idx]
                x = int(float(lm.x) * frame_w)
                y = int(float(lm.y) * frame_h)
                points.append({"id": f"{group}:{idx}", "x": x, "y": y, "group": group})

        if not points:
            return {"points": [], "bbox": None}

        xs: list[int] = [p["x"] for p in points]
        ys: list[int] = [p["y"] for p in points]
        x1, y1, x2, y2 = min(xs), min(ys), max(xs), max(ys)
        x1 = max(0, min(frame_w - 1, x1))
        y1 = max(0, min(frame_h - 1, y1))
        x2 = max(0, min(frame_w - 1, x2))
        y2 = max(0, min(frame_h - 1, y2))
        return {"points": points, "bbox": [x1, y1, x2, y2]}

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
        eye_gaze_x = 0.0
        eye_gaze_y = 0.0
        raw_gaze_x = 0.0
        raw_gaze_y = 0.0

        # Ensure state attributes are properly initialized with numeric types
        if not hasattr(state, "blink_count"):
            state.blink_count = 0
        if not hasattr(state, "last_blink_time"):
            state.last_blink_time = None
        if not hasattr(state, "session_start_time"):
            state.session_start_time = None
        if not hasattr(state, "blink_rate"):
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
            metrics["eye_aspect_ratio"] = min(ear, 1.0)
        except (AttributeError, TypeError, ZeroDivisionError) as e:
            logger.warning(f"Error calculating EAR: {e}")
            metrics["eye_aspect_ratio"] = 0.0
            ear = 0.0

        # ===== BLINK DETECTION =====
        blink_ear_threshold = self.config.get(
            "emotion", "blink_ear_threshold", default=0.21
        )
        blink_debounce = self.config.get("emotion", "blink_debounce_time", default=0.20)

        current_time = time.time()
        is_blinking = ear < blink_ear_threshold

        if is_blinking:
            # Check debounce time to prevent double-counting
            if hasattr(state, "last_blink_time") and state.last_blink_time is not None:
                try:
                    # Ensure last_blink_time is numeric
                    last_blink_time = float(state.last_blink_time)
                    if (current_time - last_blink_time) > blink_debounce:
                        state.blink_count += 1
                        state.last_blink_time = current_time

                        # Calculate blink rate
                        if (
                            hasattr(state, "session_start_time")
                            and state.session_start_time
                        ):
                            try:
                                session_start_time = float(state.session_start_time)
                                session_duration = current_time - session_start_time
                                if session_duration > 0:
                                    state.blink_rate = int(
                                        (state.blink_count / session_duration) * 60
                                    )
                            except (ValueError, TypeError):
                                logger.warning(
                                    f"Invalid session_start_time type: {type(state.session_start_time)}"
                                )
                except (ValueError, TypeError):
                    logger.warning(
                        f"Invalid last_blink_time type: {type(state.last_blink_time)}"
                    )
                    state.last_blink_time = current_time  # Reset to valid value

        metrics["is_blinking"] = is_blinking

        # ===== MOUTH ASPECT RATIO (MAR) =====
        upper_lip = landmarks.landmark[13].y
        lower_lip = landmarks.landmark[14].y
        mouth_left = landmarks.landmark[61].x
        mouth_right = landmarks.landmark[291].x

        mouth_vertical = abs(upper_lip - lower_lip)
        mouth_horizontal = abs(mouth_left - mouth_right)

        mar = mouth_vertical / mouth_horizontal if mouth_horizontal > 0 else 0
        metrics["mouth_aspect_ratio"] = min(mar, 1.0)

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
        metrics["eyebrow_raise"] = float(np.clip(eyebrow_raise * 10, 0, 1))

        left_inner_brow = landmarks.landmark[107].x
        right_inner_brow = landmarks.landmark[336].x
        eyebrow_furrow = abs(left_inner_brow - right_inner_brow)
        metrics["eyebrow_furrow"] = float(np.clip(eyebrow_furrow * 5, 0, 1))

        # ===== LIP TENSION & FROWN =====
        lip_left_corner = landmarks.landmark[61]
        lip_right_corner = landmarks.landmark[291]
        upper_lip_center = landmarks.landmark[13]

        lip_width = abs(lip_right_corner.x - lip_left_corner.x)
        metrics["lip_tension"] = float(min(lip_width * 2, 1.0))

        lip_corners_avg_y = (lip_left_corner.y + lip_right_corner.y) / 2
        mouth_center_y = upper_lip_center.y
        frown_degree = (lip_corners_avg_y - mouth_center_y) * 100
        metrics["frown_degree"] = float(np.clip(frown_degree, -1, 1))

        nose_tip = landmarks.landmark[1]
        chin = landmarks.landmark[152]
        left_eye = landmarks.landmark[33]
        right_eye = landmarks.landmark[263]

        eye_center_x = (left_eye.x + right_eye.x) / 2
        yaw = (nose_tip.x - eye_center_x) * 90
        pitch = (nose_tip.y - chin.y) * 60
        eye_diff_y = left_eye.y - right_eye.y
        roll = np.arctan2(eye_diff_y, right_eye.x - left_eye.x) * 180 / np.pi

        head_yaw = float(np.clip(yaw, -90, 90))
        head_pitch = float(np.clip(pitch, -90, 90))
        head_roll = float(np.clip(roll, -90, 90))

        metrics["head_yaw"] = head_yaw
        metrics["head_pitch"] = head_pitch
        metrics["head_roll"] = head_roll

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
            metrics["face_scale"] = float(max(0.0, min(1.0, float(avg_eye_width))))

            left_eye_top_v = landmarks.landmark[159].y
            left_eye_bottom_v = landmarks.landmark[145].y
            right_eye_top_v = landmarks.landmark[386].y
            right_eye_bottom_v = landmarks.landmark[374].y

            avg_eye_top = (left_eye_top_v + right_eye_top_v) / 2
            avg_eye_bottom = (left_eye_bottom_v + right_eye_bottom_v) / 2
            avg_eye_height = avg_eye_bottom - avg_eye_top

            face_center_x = (left_eye_outer + right_eye_outer) / 2

            # Calculate raw gaze (before calibration)
            raw_gaze_x = (
                (avg_iris_x - face_center_x) / (avg_eye_width * 2.5)
                if avg_eye_width > 0
                else 0.0
            )
            raw_gaze_y = (
                (avg_iris_y - avg_eye_top) / avg_eye_height - 0.5
                if avg_eye_height > 0
                else 0.0
            )

            if bool(self.config.get("eye_tracking", "invert_y", default=False)):
                raw_gaze_y = -raw_gaze_y

            if hasattr(state, "calibration_face_scale") and state.calibration_face_scale:
                if bool(
                    self.config.get(
                        "eye_tracking", "distance_compensation_enabled", default=True
                    )
                ):
                    try:
                        baseline = float(state.calibration_face_scale)
                        current = float(metrics.get("face_scale", 0.0) or 0.0)
                        if baseline > 1e-6 and current > 1e-6:
                            ratio = baseline / current
                            ratio_min = float(
                                self.config.get(
                                    "eye_tracking",
                                    "distance_compensation_ratio_min",
                                    default=0.75,
                                )
                            )
                            ratio_max = float(
                                self.config.get(
                                    "eye_tracking",
                                    "distance_compensation_ratio_max",
                                    default=1.35,
                                )
                            )
                            ratio = max(ratio_min, min(ratio_max, ratio))
                            raw_gaze_x *= ratio
                            raw_gaze_y *= ratio
                    except Exception:
                        pass

            if hasattr(state, "calibration_applied") and state.calibration_applied:
                try:
                    base_yaw = float(getattr(state, "calibration_head_yaw", 0.0) or 0.0)
                    base_pitch = float(
                        getattr(state, "calibration_head_pitch", 0.0) or 0.0
                    )
                    yaw_gain = getattr(state, "calibration_head_compensation_yaw_gain", None)
                    if yaw_gain is None:
                        yaw_gain = self.config.get(
                            "eye_tracking", "head_compensation_yaw", default=0.004
                        )
                    pitch_gain = getattr(
                        state, "calibration_head_compensation_pitch_gain", None
                    )
                    if pitch_gain is None:
                        pitch_gain = self.config.get(
                            "eye_tracking", "head_compensation_pitch", default=0.003
                        )
                    yaw_gain = float(yaw_gain)
                    pitch_gain = float(pitch_gain)
                    raw_gaze_x -= (head_yaw - base_yaw) * yaw_gain
                    raw_gaze_y -= (head_pitch - base_pitch) * pitch_gain
                except Exception:
                    pass

            # Apply calibration if available (from self.calibration if passed)
            # Check if state has calibration data
            if hasattr(state, "calibration_applied") and state.calibration_applied:
                # Use calibrated values with type validation
                try:
                    gaze_offset_x = (
                        float(state.calibration_gaze_offset_x)
                        if hasattr(state, "calibration_gaze_offset_x")
                        else 0.0
                    )
                    gaze_offset_y = (
                        float(state.calibration_gaze_offset_y)
                        if hasattr(state, "calibration_gaze_offset_y")
                        else 0.0
                    )
                    scale_factor = (
                        float(state.calibration_scale_factor)
                        if hasattr(state, "calibration_scale_factor")
                        else 1.0
                    )

                    eye_gaze_x = raw_gaze_x - gaze_offset_x
                    eye_gaze_y = raw_gaze_y - gaze_offset_y
                    eye_gaze_x *= scale_factor
                    eye_gaze_y *= scale_factor
                except (ValueError, TypeError) as e:
                    logger.warning(
                        f"Calibration data type error: {e}, using raw gaze values"
                    )
                    eye_gaze_x = raw_gaze_x
                    eye_gaze_y = raw_gaze_y
            else:
                # Use raw values (no calibration)
                eye_gaze_x = raw_gaze_x
                eye_gaze_y = raw_gaze_y

            metrics["eye_gaze_x"] = float(np.clip(eye_gaze_x, -1, 1))
            metrics["eye_gaze_y"] = float(np.clip(eye_gaze_y, -1, 1))
            metrics["raw_gaze_x"] = float(raw_gaze_x)  # Store raw for calibration
            metrics["raw_gaze_y"] = float(raw_gaze_y)

            # Calculate screen coordinates (with better calibration support)
            if hasattr(state, "calibration_screen_width"):
                try:
                    screen_width = int(float(state.calibration_screen_width))
                    screen_height = int(float(state.calibration_screen_height))
                except (ValueError, TypeError):
                    screen_width = self.config.get(
                        "eye_tracking", "screen_width", default=1920
                    )
                    screen_height = self.config.get(
                        "eye_tracking", "screen_height", default=1080
                    )
            else:
                screen_width = self.config.get(
                    "eye_tracking", "screen_width", default=1920
                )
                screen_height = self.config.get(
                    "eye_tracking", "screen_height", default=1080
                )

            mapping_x = getattr(state, "calibration_screen_mapping_x", None)
            mapping_y = getattr(state, "calibration_screen_mapping_y", None)

            if mapping_x is not None and mapping_y is not None:
                try:
                    ax, bx, cx = [float(v) for v in mapping_x]
                    ay, by, cy = [float(v) for v in mapping_y]

                    screen_x = int(
                        (ax * float(metrics["eye_gaze_x"]))
                        + (bx * float(metrics["eye_gaze_y"]))
                        + cx
                    )
                    screen_y = int(
                        (ay * float(metrics["eye_gaze_x"]))
                        + (by * float(metrics["eye_gaze_y"]))
                        + cy
                    )

                    metrics["screen_x"] = max(0, min(screen_width, screen_x))
                    metrics["screen_y"] = max(0, min(screen_height, screen_y))
                except Exception as e:
                    logger.warning(
                        f"Invalid screen mapping calibration data: {e}, falling back to scale"
                    )
                    mapping_x = None

            if "screen_x" not in metrics or "screen_y" not in metrics:
                scale_x = self.config.get("eye_tracking", "gaze_scale_x", default=800)
                scale_y = self.config.get("eye_tracking", "gaze_scale_y", default=450)

                center_x = screen_width / 2
                center_y = screen_height / 2

                screen_x = int(center_x + (eye_gaze_x * scale_x))
                screen_y = int(center_y + (eye_gaze_y * scale_y))

                metrics["screen_x"] = max(0, min(screen_width, screen_x))
                metrics["screen_y"] = max(0, min(screen_height, screen_y))

            # Determine looking direction
            threshold = self.config.get(
                "eye_tracking", "sensitivity_threshold", default=0.18
            )

            if abs(eye_gaze_x) < threshold and abs(eye_gaze_y) < threshold:
                metrics["looking_at"] = "center"
                metrics["attention_score"] = 100
            elif eye_gaze_y < -threshold and eye_gaze_x < -threshold:
                metrics["looking_at"] = "top-left"
                metrics["attention_score"] = 40
            elif eye_gaze_y < -threshold and eye_gaze_x > threshold:
                metrics["looking_at"] = "top-right"
                metrics["attention_score"] = 40
            elif eye_gaze_y > threshold and eye_gaze_x < -threshold:
                metrics["looking_at"] = "bottom-left"
                metrics["attention_score"] = 30
            elif eye_gaze_y > threshold and eye_gaze_x > threshold:
                metrics["looking_at"] = "bottom-right"
                metrics["attention_score"] = 30
            elif eye_gaze_y < -threshold:
                metrics["looking_at"] = "top"
                metrics["attention_score"] = 60
            elif eye_gaze_y > threshold:
                metrics["looking_at"] = "bottom"
                metrics["attention_score"] = 50
            elif eye_gaze_x < -threshold:
                metrics["looking_at"] = "left"
                metrics["attention_score"] = 70
            elif eye_gaze_x > threshold:
                metrics["looking_at"] = "right"
                metrics["attention_score"] = 70
        else:
            metrics["eye_gaze_x"] = 0.0
            metrics["eye_gaze_y"] = 0.0
            metrics["raw_gaze_x"] = 0.0
            metrics["raw_gaze_y"] = 0.0
            metrics["looking_at"] = "center"
            metrics["attention_score"] = 100

        # ===== DERIVED METRICS =====
        confusion_level = (eyebrow_raise * 2 + (ear - 0.25) * 2) if ear > 0.25 else 0
        metrics["confusion_level"] = float(np.clip(confusion_level, 0, 1))

        # NEW: Mental effort estimation from multiple cues
        # High mental effort: slight eyebrow tension + stable gaze + normal EAR
        mental_effort = 0

        # Eyebrow tension indicates concentration
        if eyebrow_raise > 0.3 and eyebrow_raise < 0.7:
            mental_effort += 0.3

        # Stable gaze indicates focus
        if hasattr(state, "last_gaze_x") and hasattr(state, "last_gaze_y"):
            if state.last_gaze_x is not None and state.last_gaze_y is not None:
                gaze_stability = 1.0 - (
                    abs(float(eye_gaze_x) - float(state.last_gaze_x))
                    + abs(float(eye_gaze_y) - float(state.last_gaze_y))
                )
                mental_effort += gaze_stability * 0.4

        # Normal EAR (not too wide open, not too closed) indicates alertness
        if 0.2 <= ear <= 0.3:
            mental_effort += 0.3

        metrics["mental_effort"] = float(np.clip(mental_effort, 0, 1))

        # Store current gaze for next frame's stability calculation
        state.last_gaze_x = eye_gaze_x
        state.last_gaze_y = eye_gaze_y

        # NEW: Blink rate calculation
        current_time = time.time()
        if hasattr(state, "last_blink_time") and state.last_blink_time is not None:
            if ear < 0.15:  # Blink detected
                time_since_blink = current_time - float(state.last_blink_time)
                if time_since_blink > 0.1:  # Debounce
                    # Calculate blink rate (blinks per minute)
                    if hasattr(state, "blink_times"):
                        state.blink_times.append(current_time)
                        # Keep only last 60 seconds of blinks
                        state.blink_times = [
                            t for t in state.blink_times if current_time - t < 60
                        ]
                        blink_rate = len(state.blink_times)
                    else:
                        state.blink_times = [current_time]
                        blink_rate = 15  # Default assumption

                    metrics["blink_rate"] = blink_rate
                    state.last_blink_time = current_time
        else:
            state.last_blink_time = current_time
            if not hasattr(state, "blink_times"):
                state.blink_times = []

        # NEW: Focus stability calculation
        if hasattr(state, "focus_history"):
            if isinstance(state.focus_history, deque):
                state.focus_history.append(float(metrics["mental_effort"]))
                if len(state.focus_history) >= 10:
                    stability = 1.0 - float(np.std(list(state.focus_history)))
                    metrics["focus_stability"] = float(np.clip(stability, 0, 1))
                else:
                    metrics["focus_stability"] = 0.5
            else:
                state.focus_history.append(float(metrics["mental_effort"]))
                if len(state.focus_history) > 30:
                    state.focus_history = state.focus_history[-30:]
                if len(state.focus_history) >= 10:
                    stability = 1.0 - float(np.std(state.focus_history))
                    metrics["focus_stability"] = float(np.clip(stability, 0, 1))
                else:
                    metrics["focus_stability"] = 0.5
        else:
            state.focus_history = deque([float(metrics["mental_effort"])], maxlen=30)
            metrics["focus_stability"] = 0.5

        # NEW: Recent focus average for dynamic thresholds
        current_focus_score = 0
        if ear > 0.2:
            current_focus_score += 20
        if abs(yaw) < 15 and abs(pitch) < 12:
            current_focus_score += 25

        if (
            not hasattr(state, "recent_focus_scores")
            or state.recent_focus_scores is None
        ):
            state.recent_focus_scores = deque(maxlen=60)

        state.recent_focus_scores.append(current_focus_score)

        if isinstance(state.recent_focus_scores, deque):
            metrics["recent_focus_avg"] = (
                float(np.mean(list(state.recent_focus_scores)))
                if len(state.recent_focus_scores) > 0
                else 70.0
            )
        else:
            if len(state.recent_focus_scores) > 60:
                state.recent_focus_scores = state.recent_focus_scores[-60:]
            metrics["recent_focus_avg"] = (
                float(np.mean(state.recent_focus_scores))
                if len(state.recent_focus_scores) > 0
                else 70.0
            )

        blink_stress = 0
        if hasattr(state, "blink_rate") and state.blink_rate is not None:
            try:
                blink_rate = float(state.blink_rate)
                if blink_rate < 10 or blink_rate > 30:
                    blink_stress = 0.3
            except (ValueError, TypeError):
                logger.warning(f"Invalid blink_rate type: {type(state.blink_rate)}")
        metrics["stress_level"] = float(
            np.clip(float(metrics["lip_tension"]) * 0.7 + blink_stress, 0, 1)
        )

        # ===== YAWNING DETECTION =====
        is_yawning = mar > 0.6
        current_time = time.time()

        if is_yawning:
            if hasattr(state, "last_yawn_time") and state.last_yawn_time is not None:
                try:
                    last_yawn_time = float(state.last_yawn_time)
                    if (current_time - last_yawn_time) < 5:
                        metrics["yawning_duration"] = current_time - last_yawn_time
                    else:
                        metrics["last_yawn_time"] = current_time
                        metrics["yawning_duration"] = 0
                except (ValueError, TypeError):
                    logger.warning(
                        f"Invalid last_yawn_time type: {type(state.last_yawn_time)}"
                    )
                    metrics["last_yawn_time"] = current_time
                    metrics["yawning_duration"] = 0
            else:
                metrics["last_yawn_time"] = current_time
                metrics["yawning_duration"] = 0
        else:
            metrics["yawning_duration"] = 0

        return metrics

    def _reinitialize_graphs(self):
        """Reinitialize MediaPipe graphs when they become corrupted"""
        try:
            # Close existing graphs
            if hasattr(self, "face_detection") and self.face_detection:
                try:
                    self.face_detection.close()
                except Exception:
                    pass
            if hasattr(self, "face_mesh") and self.face_mesh:
                try:
                    self.face_mesh.close()
                except Exception:
                    pass

            # Recreate graphs
            self.face_detection = self.mp_face_detection.FaceDetection(
                model_selection=self.config.face_detection_selection,
                min_detection_confidence=0.3,
            )

            self.face_mesh = self.mp_face_mesh.FaceMesh(
                static_image_mode=False,
                max_num_faces=1,
                refine_landmarks=True,
                min_detection_confidence=0.3,
                min_tracking_confidence=0.3,
            )

            logger.info("[OK] MediaPipe graphs reinitialized")

        except Exception as e:
            logger.error(f"Failed to reinitialize MediaPipe graphs: {e}")

    def cleanup(self):
        """Release MediaPipe resources safely"""
        try:
            # Check if face_detection exists and is not None
            face_detection_obj = getattr(self, "face_detection", None)
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
            logger.warning(f"Face detection cleanup error: {e}")

        try:
            # Check if face_mesh exists and is not None
            face_mesh_obj = getattr(self, "face_mesh", None)
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
            logger.warning(f"Face mesh cleanup error: {e}")

        # Reset error tracking
        self.consecutive_errors = 0

        logger.info("[OK] FaceMeshProcessor cleaned up")
