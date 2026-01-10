"""
Improved Webcam Processor
Clean working version with all features
"""

import os
import json
import logging
import time
import base64
import cv2
import numpy as np
from collections import deque
from threading import Thread, Lock
from typing import Any

from config_loader import config
from mediapipe_processors.face_mesh_processor import FaceMeshProcessor
from mediapipe_processors.pose_processor import PoseProcessor
from mediapipe_processors.deepface_emotion_detector import DeepFaceEmotionDetector
from calibration import CalibrationManager
from cv_modules.smartphone_detector import SmartphoneDetector

# Optional VLM service (requires additional dependencies)
VLM_IMPORT_ERROR = None
LocalVLMService: Any = None
try:
    from vlm_service import LocalVLMService as _LocalVLMService

    LocalVLMService = _LocalVLMService
    VLM_AVAILABLE = True
except Exception as e:
    VLM_IMPORT_ERROR = str(e)
    logging.getLogger(__name__).warning(f"[WARN] VLM import failed (optional): {e}")
    VLM_AVAILABLE = False

logger = logging.getLogger(__name__)


class ImprovedWebcamProcessor:
    """Enhanced webcam processor with all improvements"""

    def __init__(self, state, socketio=None):
        """Initialize improved webcam processor"""
        self.state = state
        self.socketio = socketio
        self.cap = None
        self.running = False
        self.starting = False
        self.thread = None
        self.lock = Lock()
        self.processing_enabled = True
        self.metrics_log_fp = None
        self.metrics_log_path = None
        self.last_metrics_log_time = 0.0
        self.last_state_emit_time = 0.0
        self.jpeg_quality = int(config.get("ui", "jpeg_quality", default=75))
        self.quality_preset = str(
            config.get("ui", "quality_preset", default="balanced")
        )

        # GPU acceleration check
        self.gpu_enabled = self._check_gpu_support()

        # Initialize processors
        self.pose_processor = PoseProcessor(config)
        self.face_processor = FaceMeshProcessor(config)
        self.deepface_detector = DeepFaceEmotionDetector(
            config, gpu_enabled=self.gpu_enabled
        )
        self.calibration = CalibrationManager(config)
        try:
            existing_calibration = self.calibration.load_calibration("default")
            if isinstance(existing_calibration, dict):
                invert_y = bool(config.get("eye_tracking", "invert_y", default=False))
                calibration_invert_y = bool(existing_calibration.get("invert_y", False))
                with self.state.lock:
                    self.state.calibration_applied = True
                    self.state.calibration_gaze_offset_x = float(
                        existing_calibration.get("gaze_offset_x", 0.0) or 0.0
                    )
                    offset_y = float(
                        existing_calibration.get("gaze_offset_y", 0.0) or 0.0
                    )
                    if invert_y and (not calibration_invert_y):
                        offset_y = -offset_y
                    self.state.calibration_gaze_offset_y = offset_y
                    self.state.calibration_scale_factor = float(
                        existing_calibration.get("scale_factor", 1.0) or 1.0
                    )
                    self.state.calibration_screen_width = int(
                        float(existing_calibration.get("screen_width", 1920) or 1920)
                    )
                    self.state.calibration_screen_height = int(
                        float(existing_calibration.get("screen_height", 1080) or 1080)
                    )
                    self.state.calibration_head_yaw = float(
                        existing_calibration.get("head_baseline_yaw", 0.0) or 0.0
                    )
                    self.state.calibration_head_pitch = float(
                        existing_calibration.get("head_baseline_pitch", 0.0) or 0.0
                    )
                    self.state.calibration_head_compensation_yaw_gain = (
                        existing_calibration.get("head_compensation_yaw_gain", None)
                    )
                    pitch_gain = existing_calibration.get("head_compensation_pitch_gain", None)
                    if invert_y and (not calibration_invert_y) and pitch_gain is not None:
                        try:
                            pitch_gain = -float(pitch_gain)
                        except Exception:
                            pass
                    self.state.calibration_head_compensation_pitch_gain = pitch_gain
                    mapping = existing_calibration.get("screen_mapping") or {}
                    if isinstance(mapping, dict) and "x" in mapping and "y" in mapping:
                        self.state.calibration_screen_mapping_x = mapping.get("x")
                        mapping_y = mapping.get("y")
                        if (
                            invert_y
                            and (not calibration_invert_y)
                            and isinstance(mapping_y, list)
                            and len(mapping_y) >= 3
                        ):
                            try:
                                ay = float(mapping_y[0])
                                by = float(mapping_y[1])
                                cy = float(mapping_y[2])
                                mapping_y = [ay, -by, cy]
                            except Exception:
                                pass
                        self.state.calibration_screen_mapping_y = mapping_y
        except Exception:
            pass

        # VLM service (optional)
        self.last_vlm_status = None
        self.last_vlm_status_time = 0.0
        self.vlm_user_enabled = bool(config.get("vlm", "enabled", default=False))
        self.vlm_service = None
        self._vlm_init_lock = Lock()
        self._vlm_init_in_progress = False
        self._vlm_init_thread = None
        with self.state.lock:
            self.state.vlm_user_enabled = bool(self.vlm_user_enabled)
        if self.vlm_user_enabled:
            self._schedule_vlm_init()
        self.last_vlm_analysis = None
        self.vlm_analysis_cooldown = 5.0

        # Live capture
        self.live_capture = None
        self.use_live_capture = config.get("camera", "use_live_capture", default=False)

        self.smartphone_detector = None
        self.smartphone_detection_enabled = bool(
            config.get("smartphone_detection", "enabled", default=False)
        )
        if self.smartphone_detection_enabled:
            model_path = config.get(
                "smartphone_detection",
                "model_path",
                default=os.path.join(
                    os.path.dirname(__file__), "models", "smartphone_detector.onnx"
                ),
            )
            threshold = float(
                config.get("smartphone_detection", "threshold", default=0.5)
            )
            self.smartphone_detector = SmartphoneDetector(
                model_path=model_path, score_threshold=threshold
            )
            if not getattr(self.smartphone_detector, "ready", False):
                self.smartphone_detector = None
                self.smartphone_detection_enabled = False

        # Frame processing
        self.frame_skip = config.frame_skip_base
        self.fps_history = deque(maxlen=30)
        self.frame_timestamp = 0
        self.timestamp_increment = 33333

        # Gaze smoothing
        self.gaze_smoothing_enabled = config.get(
            "eye_tracking", "enable_smoothing", default=True
        )
        self.gaze_smoothing_window = config.get(
            "eye_tracking", "smoothing_window", default=5
        )
        self.gaze_history_x = deque(maxlen=self.gaze_smoothing_window)
        self.gaze_history_y = deque(maxlen=self.gaze_smoothing_window)

        self.visual_feedback_enabled = bool(
            config.get("ui", "visual_feedback", "enabled", default=True)
        )
        self.face_mesh_overlay_enabled = bool(
            config.get("ui", "visual_feedback", "show_face_mesh", default=False)
        )
        self.face_mesh_overlay_alpha = float(
            config.get("ui", "visual_feedback", "face_mesh_alpha", default=0.5)
        )
        self.face_mesh_overlay_smoothing = float(
            config.get("ui", "visual_feedback", "face_mesh_smoothing", default=0.35)
        )
        self.face_mesh_overlay_mode = str(
            config.get("ui", "visual_feedback", "face_mesh_mode", default="full")
        ).strip()
        self.face_mesh_overlay_stride = int(
            config.get("ui", "visual_feedback", "face_mesh_stride", default=4)
        )
        self.face_mesh_triangles_every_n_frames = int(
            config.get(
                "ui",
                "visual_feedback",
                "face_mesh_triangles_every_n_frames",
                default=3,
            )
        )
        self.face_mesh_triangles_max_points = int(
            config.get(
                "ui", "visual_feedback", "face_mesh_triangles_max_points", default=140
            )
        )
        self._last_face_overlay = None
        self._overlay_smoothed_points = {}

        # Focus status
        self.focus_status_debounce_seconds = config.get(
            "focus", "status_debounce_seconds", default=0.7
        )
        self.focus_status_last_emitted = None
        self.focus_status_candidate = None
        self.focus_status_candidate_since = None
        self.focus_score_ema = None
        self.focus_score_smoothing_alpha = float(
            config.get("focus", "score_smoothing_alpha", default=0.22)
        )
        self.focus_status_hysteresis = float(
            config.get("focus", "status_hysteresis", default=6.0)
        )
        self.focus_distracted_hysteresis = float(
            config.get("focus", "distracted_hysteresis", default=4.0)
        )
        self.forced_unfocused_score = float(
            config.get("focus", "forced_unfocused_score", default=30.0)
        )
        self.metric_smoothing_alpha = float(
            config.get("focus", "metric_smoothing_alpha", default=0.25)
        )
        self._metric_ema = {}
        self._last_distraction_active = {}

        self._distraction_states = {}
        self._last_distraction_event_time = 0.0

        logger.info("[OK] ImprovedWebcamProcessor initialized")
        logger.info(
            f"[CONFIG] GPU Acceleration: {'Enabled' if self.gpu_enabled else 'Disabled'}"
        )
        logger.info(
            f"[CONFIG] Adaptive Quality: {'Enabled' if config.adaptive_quality_enabled else 'Disabled'}"
        )
        logger.info(
            f"[CONFIG] Privacy Controls: {'Enabled' if config.privacy_allow_pause else 'Disabled'}"
        )

    def set_quality_preset(self, preset: str):
        preset = (preset or "").strip().lower()
        if preset not in ("low", "balanced", "high"):
            preset = "balanced"

        if preset == "low":
            width, height, fps = 640, 480, 24
            frame_skip = 5
            jpeg_quality = 60
        elif preset == "high":
            width, height, fps = 1280, 720, 30
            frame_skip = 2
            jpeg_quality = 80
        else:
            width, height, fps = 1280, 720, 30
            frame_skip = 3
            jpeg_quality = 75

        with self.lock:
            self.quality_preset = preset
            self.jpeg_quality = int(jpeg_quality)
            self.frame_skip = int(frame_skip)
            if self.cap:
                try:
                    self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, int(width))
                    self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, int(height))
                    self.cap.set(cv2.CAP_PROP_FPS, int(fps))
                except Exception:
                    pass

        with self.state.lock:
            self.state.quality_preset = preset

    def _schedule_vlm_init(self) -> bool:
        if not bool(getattr(self, "vlm_user_enabled", False)):
            return False

        with self._vlm_init_lock:
            if self.vlm_service is not None:
                return True
            if bool(self._vlm_init_in_progress):
                return True
            self._vlm_init_in_progress = True

        with self.state.lock:
            if getattr(self.state, "vlm_status", None) in (
                None,
                "disabled",
                "unavailable",
            ):
                self.state.vlm_status = "loading"
            self.state.vlm_ready = False
            self.state.vlm_last_error = None

        def worker():
            try:
                if not bool(getattr(self, "vlm_user_enabled", False)):
                    return
                self._ensure_vlm_service()
            finally:
                with self._vlm_init_lock:
                    self._vlm_init_in_progress = False

        self._vlm_init_thread = Thread(target=worker, daemon=True)
        self._vlm_init_thread.start()
        return True

    def _ensure_vlm_service(self) -> bool:
        if not self.vlm_user_enabled:
            with self.state.lock:
                self.state.vlm_status = "disabled"
                self.state.vlm_ready = False
                self.state.vlm_last_error = None
            return False

        if not VLM_AVAILABLE or LocalVLMService is None:
            with self.state.lock:
                self.state.vlm_status = "unavailable"
                self.state.vlm_ready = False
                self.state.vlm_last_error = "vlm_not_installed"
            self.vlm_service = None
            return False

        if self.vlm_service is not None:
            return True

        try:
            self.vlm_service = LocalVLMService(
                model_name=config.get(
                    "vlm", "model_name", default="HuggingFaceTB/SmolVLM-500M-Instruct"
                ),
                async_load=bool(config.get("vlm", "async_load", default=True)),
                warmup=bool(config.get("vlm", "warmup", default=True)),
                status_callback=self._on_vlm_status_update,
            )
            logger.info("[OK] VLM service created")
            return True
        except Exception as e:
            self.vlm_service = None
            with self.state.lock:
                self.state.vlm_status = "error"
                self.state.vlm_ready = False
                self.state.vlm_last_error = str(e)
            logger.warning(f"[WARN] VLM initialization failed: {e}")
            return False

    def get_vlm_settings(self):
        with self.state.lock:
            out = {
                "user_enabled": bool(getattr(self, "vlm_user_enabled", False)),
                "status": getattr(self.state, "vlm_status", "disabled"),
                "ready": bool(getattr(self.state, "vlm_ready", False)),
                "last_error": getattr(self.state, "vlm_last_error", None),
            }
        try:
            svc = getattr(self, "vlm_service", None)
            if svc and hasattr(svc, "get_status"):
                out["service_status"] = svc.get_status()
        except Exception:
            pass
        return out

    def set_vlm_enabled(self, enabled: bool):
        enabled = bool(enabled)
        self.vlm_user_enabled = enabled
        with self.state.lock:
            self.state.vlm_user_enabled = bool(enabled)
        if enabled:
            with self.state.lock:
                self.state.vlm_status = "loading"
                self.state.vlm_ready = False
                self.state.vlm_last_error = None
            self._schedule_vlm_init()
        else:
            with self.state.lock:
                self.state.vlm_status = "disabled"
                self.state.vlm_ready = False
                self.state.vlm_last_error = None
        return self.get_vlm_settings()

    def _check_gpu_support(self):
        """Check if GPU acceleration is available"""
        if not config.gpu_acceleration_enabled:
            logger.info("[WARN] GPU acceleration disabled in config")
            return False

        try:
            device_count = cv2.cuda.getCudaEnabledDeviceCount()
            if device_count > 0:
                logger.info(f"[GPU] CUDA GPU detected: {device_count} device(s)")
                return True
        except Exception:
            pass

        try:
            import tensorflow as tf

            gpus = tf.config.list_physical_devices("GPU")
            if gpus:
                logger.info(f"[GPU] TensorFlow GPU detected: {len(gpus)} device(s)")
                return True
        except Exception:
            pass

        try:
            import torch

            if torch.cuda.is_available():
                device_count = torch.cuda.device_count()
                logger.info(f"[CUDA] PyTorch CUDA available: {device_count} device(s)")
                return True
        except Exception:
            pass

        logger.info(
            "[WARN] No GPU acceleration available, using CPU-optimized processing"
        )
        return False

    def start(self):
        """Start webcam processing"""
        with self.lock:
            if self.running or self.starting:
                logger.info("[WARN] Webcam already running")
                return True

            logger.info("[START] START: Enhanced webcam processor")
            self.starting = True

        # Try to open camera
        backend_map = {"dshow": cv2.CAP_DSHOW, "default": 0, "v4l2": cv2.CAP_V4L2}

        backend = config.get("camera", "backend", default="dshow")
        cap_backend = backend_map.get(backend, 0)

        logger.info(f"[START] Opening webcam with backend: {backend}...")
        self.cap = cv2.VideoCapture(0, cap_backend)

        if not self.cap.isOpened():
            logger.warning(
                f"[WARN] Cannot open webcam with {backend}, trying default..."
            )
            self.cap = cv2.VideoCapture(0)

        if not self.cap.isOpened():
            logger.error("[ERROR] Cannot open webcam with any backend")
            with self.lock:
                self.starting = False
            return False

        # Set camera properties
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.camera_width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.camera_height)
        self.cap.set(cv2.CAP_PROP_FPS, config.camera_fps)

        logger.info(
            f"[OK] Webcam opened: {config.camera_width}x{config.camera_height} @ {config.camera_fps}fps"
        )

        with self.lock:
            self.running = True
            self.starting = False
            self.thread = Thread(target=self._process_loop, daemon=True)
            self.thread.start()

        try:
            self.set_quality_preset(self.quality_preset)
        except Exception:
            pass

        self._open_metrics_log()
        logger.info("[OK] Webcam processing started")
        return True

    def stop(self):
        """Stop webcam processing"""
        logger.info("[STOP] Stopping webcam processor...")

        with self.lock:
            self.running = False
            self.starting = False

        if self.thread:
            self.thread.join(timeout=3)

        if self.cap:
            self.cap.release()
            self.cap = None

        self._close_metrics_log()

        try:
            if hasattr(self, "pose_processor") and self.pose_processor:
                self.pose_processor.cleanup()
        except Exception as e:
            logger.warning(f"[WARN] Pose cleanup error (non-critical): {e}")

        try:
            if hasattr(self, "face_processor") and self.face_processor:
                self.face_processor.cleanup()
        except Exception as e:
            logger.warning(f"[WARN] Face processor cleanup error (non-critical): {e}")

        logger.info("[OK] Webcam processor stopped and cleaned up")

    def _sanitize_filename_part(self, value: str) -> str:
        if not value:
            return ""
        out = []
        for ch in str(value):
            if ch.isalnum() or ch in ("-", "_", "."):
                out.append(ch)
            else:
                out.append("_")
        return "".join(out).strip("_")

    def _metrics_log_dir(self) -> str:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base_dir, "logs")

    def get_metrics_log_path(self):
        with self.lock:
            return self.metrics_log_path

    def _open_metrics_log(self):
        try:
            logs_dir = self._metrics_log_dir()
            os.makedirs(logs_dir, exist_ok=True)
            session_id = (
                getattr(self.state, "session_id", None) or f"session_{int(time.time())}"
            )
            safe_session = self._sanitize_filename_part(session_id)
            if not safe_session:
                safe_session = f"session_{int(time.time())}"
            self.metrics_log_path = os.path.join(
                logs_dir, f"metrics_{safe_session}.jsonl"
            )
            self.metrics_log_fp = open(self.metrics_log_path, "a", encoding="utf-8")
            self.last_metrics_log_time = 0.0
            logger.info(f"[OK] Metrics log started: {self.metrics_log_path}")
        except Exception as e:
            self.metrics_log_fp = None
            self.metrics_log_path = None
            logger.error(f"[ERROR] Failed to open metrics log: {e}")

    def _close_metrics_log(self):
        try:
            if self.metrics_log_fp:
                self.metrics_log_fp.flush()
                self.metrics_log_fp.close()
        except Exception as e:
            logger.error(f"[ERROR] Failed to close metrics log: {e}")
        finally:
            self.metrics_log_fp = None
            self.metrics_log_path = None

    def _write_metrics_log(self):
        if not self.metrics_log_fp:
            return
        if bool(getattr(self.state, "calibration_in_progress", False)):
            return
        now = time.time()
        if (now - self.last_metrics_log_time) < 1.0:
            return
        self.last_metrics_log_time = now
        try:
            state_dict = self.state.to_dict()
            snapshot = {
                "ts": now,
                "session_id": state_dict.get("session_id"),
                "focus_percentage": state_dict.get("focus_percentage"),
                "focus_status": state_dict.get("focus_status"),
                "mental_effort": state_dict.get("mental_effort"),
                "head_pose": state_dict.get("head_pose"),
                "facial_metrics": {
                    "eye_aspect_ratio": state_dict.get("facial_metrics", {}).get(
                        "eye_aspect_ratio"
                    ),
                    "mouth_aspect_ratio": state_dict.get("facial_metrics", {}).get(
                        "mouth_aspect_ratio"
                    ),
                    "emotion": state_dict.get("facial_metrics", {}).get("emotion"),
                    "emotion_confidence": state_dict.get("facial_metrics", {}).get(
                        "emotion_confidence"
                    ),
                    "micro_expressions": state_dict.get("facial_metrics", {}).get(
                        "micro_expressions"
                    ),
                },
                "body_pose": state_dict.get("body_pose"),
                "webcam": state_dict.get("webcam"),
                "rule_metrics": state_dict.get("rule_metrics", {}),
            }
            self.metrics_log_fp.write(json.dumps(snapshot, ensure_ascii=False) + "\n")
            self.metrics_log_fp.flush()
        except Exception as e:
            logger.error(f"[ERROR] Failed to write metrics log: {e}")

    def _process_loop(self):
        """Main processing loop"""
        frame_times = deque(maxlen=30)
        time.sleep(0.5)  # Give camera time to stabilize

        logger.info("[RUNNING] Processing loop started")

        consecutive_read_failures = 0

        while self.running:
            try:
                frame_start_time = time.time()  # Start timing for FPS calculation
                ret, frame = self.cap.read()
                if not ret:
                    consecutive_read_failures += 1
                    if consecutive_read_failures % 10 == 0:
                        logger.warning(
                            f"[WARN] Failed to read frame from camera ({consecutive_read_failures})"
                        )

                    if consecutive_read_failures > 50:
                        logger.error(
                            "[ERROR] Camera failed too many times, attempting to restart..."
                        )
                        self.cap.release()
                        time.sleep(1)
                        self.cap = cv2.VideoCapture(0)
                        consecutive_read_failures = 0

                    time.sleep(0.1)
                    continue

                consecutive_read_failures = 0

                # Process frame
                frame = self._apply_lighting_adaptation(frame)
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                # Process face
                try:
                    self.frame_timestamp += self.timestamp_increment
                    frame_copy = rgb_frame.copy()

                    with self.state.lock:
                        self.state.force_face_mesh = bool(
                            self.face_mesh_overlay_enabled
                        )
                        self.state.face_mesh_overlay_mode = (
                            self.face_mesh_overlay_mode
                            if self.face_mesh_overlay_enabled
                            else "subset"
                        )
                        self.state.face_mesh_overlay_stride = int(
                            self.face_mesh_overlay_stride
                        )

                    face_metrics = self.face_processor.process(frame_copy, self.state)
                    with self.lock:
                        self._last_face_overlay = face_metrics.get("_overlay")

                    with self.state.lock:
                        self.state.face_detected = face_metrics.get(
                            "face_detected", False
                        )
                        self.state.face_count = face_metrics.get("face_count", 0)

                        # Apply smoothing to gaze values
                        if (
                            "eye_gaze_x" in face_metrics
                            and "eye_gaze_y" in face_metrics
                        ):
                            face_metrics["eye_gaze_x"], face_metrics["eye_gaze_y"] = (
                                self._smooth_gaze(
                                    face_metrics["eye_gaze_x"],
                                    face_metrics["eye_gaze_y"],
                                )
                            )

                        # Update all face metrics
                        for key, value in face_metrics.items():
                            if hasattr(self.state, key):
                                if key in (
                                    "head_yaw",
                                    "head_pitch",
                                    "head_roll",
                                    "attention_score",
                                    "eye_aspect_ratio",
                                    "mouth_aspect_ratio",
                                ):
                                    try:
                                        v = float(value)
                                        prev = self._metric_ema.get(key)
                                        a = float(self.metric_smoothing_alpha)
                                        a = max(0.05, min(0.9, a))
                                        if prev is None:
                                            self._metric_ema[key] = v
                                        else:
                                            self._metric_ema[key] = (a * v) + (
                                                (1.0 - a) * float(prev)
                                            )
                                        value = self._metric_ema[key]
                                    except Exception:
                                        pass
                                setattr(self.state, key, value)
                        if bool(getattr(self.state, "face_mesh_processed", False)):
                            self.state.last_face_mesh_time = time.time()

                    self._update_rule_based_metrics()

                    # Calculate focus and detect distractions
                    distractions = self._detect_distractions()
                    with self.state.lock:
                        self.state.current_distractions = distractions

                    raw_focus_score, raw_focus_status = self._calculate_focus_score()
                    focus_score, focus_status = self._stabilize_focus(
                        raw_focus_score, raw_focus_status
                    )
                    mental_effort = self._calculate_mental_effort()

                    with self.state.lock:
                        self.state.focus_percentage = focus_score
                        self.state.focus_status = focus_status
                        self.state.mental_effort = mental_effort

                    self._update_time_tracking(focus_status)
                    self._emit_state_update()
                    self._write_metrics_log()

                    # Log focus changes
                    if (
                        not bool(getattr(self.state, "calibration_in_progress", False))
                    ) and self.state.frame_count % 30 == 0:
                        logger.info(
                            f"Focus: {focus_score:.0f}% ({focus_status}) | "
                            f"EAR: {self.state.eye_aspect_ratio:.2f} | "
                            f"Head: ({self.state.head_yaw:.1f}, {self.state.head_pitch:.1f})"
                        )

                    # Request VLM analysis periodically
                    if (
                        bool(getattr(self, "vlm_user_enabled", False))
                        and VLM_AVAILABLE
                        and not bool(
                            getattr(self.state, "calibration_in_progress", False)
                        )
                        and self.state.frame_count % 150 == 0
                    ):
                        self._request_vlm_analysis()

                    # Process pose
                    try:
                        if self.state.frame_count % 3 == 0:
                            if rgb_frame is not None and isinstance(
                                rgb_frame, np.ndarray
                            ):
                                frame_copy = rgb_frame.copy()
                                pose_metrics = self.pose_processor.process(frame_copy)

                                with self.state.lock:
                                    self.state.body_detected = pose_metrics.get(
                                        "body_detected", False
                                    )
                                    self.state.posture_score = pose_metrics.get(
                                        "posture_score", 0.0
                                    )
                                    self.state.pose_confidence = pose_metrics.get(
                                        "pose_confidence", 0.0
                                    )

                    except Exception as e:
                        logger.warning(f"Pose processing error (non-critical): {e}")

                    # Detect emotion
                    try:
                        if self.state.frame_count % 5 == 0:
                            if self.deepface_detector.available:
                                if rgb_frame is not None and isinstance(
                                    rgb_frame, np.ndarray
                                ):
                                    try:
                                        emotion_frame = rgb_frame.copy()
                                        emotion_result = (
                                            self.deepface_detector.detect_emotion(
                                                emotion_frame
                                            )
                                        )

                                        with self.state.lock:
                                            self.state.emotion = emotion_result[
                                                "emotion"
                                            ]
                                            self.state.emotion_confidence = (
                                                emotion_result["emotion_confidence"]
                                            )

                                        if "emotion_scores" in emotion_result:
                                            if not hasattr(
                                                self.state, "emotion_scores"
                                            ):
                                                self.state.emotion_scores = {}
                                            self.state.emotion_scores.update(
                                                emotion_result["emotion_scores"]
                                            )

                                    except Exception as e:
                                        if VLM_AVAILABLE:
                                            logger.error(
                                                f"[ERROR] Emotion detection error: {e}"
                                            )
                                        if (
                                            not hasattr(self.state, "emotion")
                                            or self.state.emotion is None
                                        ):
                                            with self.state.lock:
                                                self.state.emotion = "neutral"
                                                self.state.emotion_confidence = 0.5
                            else:
                                emotion, confidence, scores = (
                                    self._estimate_rule_based_emotion()
                                )
                                with self.state.lock:
                                    self.state.emotion = emotion
                                    self.state.emotion_confidence = confidence
                                    if not hasattr(self.state, "emotion_scores"):
                                        self.state.emotion_scores = {}
                                    self.state.emotion_scores.update(scores)

                    except Exception as e:
                        if VLM_AVAILABLE:
                            logger.error(f"[ERROR] Emotion detection outer error: {e}")

                except Exception as e:
                    logger.error(f"[ERROR] Face processing error: {e}")

                # Draw feedback
                self._draw_lightweight_feedback(frame)

                # Calculate FPS
                frame_time = time.time() - frame_start_time
                frame_times.append(frame_time)
                if frame_times:
                    fps = 1.0 / (sum(frame_times) / len(frame_times))
                    self.state.fps = fps
                    self.fps_history.append(fps)

                # Update frame count
                with self.state.lock:
                    self.state.frame_count += 1

                self._run_smartphone_detection(frame)
                self._draw_smartphone_feedback(frame)
                self._maybe_update_vlm_status()

                # Emit frame
                if self.state.frame_count % 2 == 0:
                    self._emit_frame(frame)

                # Log periodically
                if self.state.frame_count % config.log_interval == 0:
                    logger.info(
                        f"FPS: {self.state.fps:.1f} | Focus: {self.state.focus_percentage:.0f}%"
                    )

                time.sleep(0.01)

            except Exception as e:
                logger.error(f"Error in processing loop: {e}", exc_info=True)

    def _smooth_gaze(self, gaze_x, gaze_y):
        """Apply smoothing to gaze coordinates"""
        if not self.gaze_smoothing_enabled:
            return gaze_x, gaze_y

        self.gaze_history_x.append(gaze_x)
        self.gaze_history_y.append(gaze_y)

        smoothed_x = sum(self.gaze_history_x) / len(self.gaze_history_x)
        smoothed_y = sum(self.gaze_history_y) / len(self.gaze_history_y)

        return smoothed_x, smoothed_y

    def _update_rule_based_metrics(self):
        face_detected = bool(getattr(self.state, "face_detected", False))
        if not face_detected:
            with self.state.lock:
                self.state.stress_level = 0.0
                self.state.confusion_level = 0.0
                self.state.yawning_duration = 0
            return

        with self.state.lock:
            ear = float(getattr(self.state, "eye_aspect_ratio", 0.0) or 0.0)
            mar = float(getattr(self.state, "mouth_aspect_ratio", 0.0) or 0.0)
            eyebrow_raise = float(getattr(self.state, "eyebrow_raise", 0.0) or 0.0)
            eyebrow_furrow = float(getattr(self.state, "eyebrow_furrow", 0.0) or 0.0)
            lip_tension = float(getattr(self.state, "lip_tension", 0.0) or 0.0)
            frown_degree = float(getattr(self.state, "frown_degree", 0.0) or 0.0)
            head_yaw = abs(float(getattr(self.state, "head_yaw", 0.0) or 0.0))
            head_pitch = abs(float(getattr(self.state, "head_pitch", 0.0) or 0.0))
            blink_rate = float(getattr(self.state, "blink_rate", 0) or 0)
            last_yawn_time = getattr(self.state, "last_yawn_time", None)

        confusion = 0.0
        eyebrow_raise_threshold = float(
            config.get("emotion", "eyebrow_raise_threshold", default=0.08)
        )
        head_tilt_threshold = float(
            config.get("emotion", "head_tilt_threshold", default=8)
        )
        if eyebrow_raise > eyebrow_raise_threshold:
            confusion += 0.6
        if head_yaw > head_tilt_threshold:
            confusion += 0.3
        if ear < float(config.get("focus", "eye_aspect_ratio_threshold", default=0.2)):
            confusion += 0.2
        confusion = float(np.clip(confusion, 0.0, 1.0))

        stress = 0.0
        stress += float(np.clip(lip_tension, 0.0, 1.0)) * 0.5
        stress += float(np.clip(eyebrow_furrow, 0.0, 1.0)) * 0.3
        stress += float(np.clip(max(0.0, frown_degree), 0.0, 1.0)) * 0.3
        if blink_rate < 10 or blink_rate > 30:
            stress += 0.2
        if head_yaw > float(
            config.get("distractions", "head_turn_threshold", default=20)
        ):
            stress += 0.2
        if head_pitch > float(
            config.get("distractions", "head_pitch_threshold", default=15)
        ):
            stress += 0.2
        stress = float(np.clip(stress, 0.0, 1.0))

        yawning_mar_threshold = float(
            config.get("emotion", "yawning_mar_threshold", default=0.6)
        )
        now = time.time()
        if mar > yawning_mar_threshold:
            if isinstance(last_yawn_time, (int, float)):
                yawning_duration = now - float(last_yawn_time)
            else:
                yawning_duration = 0.0
                last_yawn_time = now
        else:
            yawning_duration = 0.0
            last_yawn_time = (
                now if not isinstance(last_yawn_time, (int, float)) else last_yawn_time
            )

        with self.state.lock:
            self.state.confusion_level = confusion
            self.state.stress_level = stress
            self.state.yawning_duration = yawning_duration
            self.state.last_yawn_time = last_yawn_time
            ear_risk = float(np.clip((0.22 - ear) * 5.0, 0.0, 1.0))
            mar_risk = float(np.clip((mar - yawning_mar_threshold) * 2.5, 0.0, 1.0))
            head_away = (
                1.0
                if (
                    head_yaw
                    > float(
                        config.get("distractions", "head_turn_threshold", default=20)
                    )
                    or head_pitch
                    > float(
                        config.get("distractions", "head_pitch_threshold", default=15)
                    )
                )
                else 0.0
            )
            blink_risk = 0.0
            if blink_rate < 10:
                blink_risk = 0.2
            elif blink_rate > 30:
                blink_risk = 0.1
            sleepiness = float(
                np.clip(ear_risk * 0.55 + mar_risk * 0.35 + blink_risk * 0.10, 0.0, 1.0)
            )
            self.state.sleepiness_score = float(round(sleepiness * 100.0, 2))
            self.state.rule_metrics = {
                "confusion_level_rule": confusion,
                "stress_level_rule": stress,
                "drowsiness_risk": float(
                    np.clip(ear_risk * 0.7 + mar_risk * 0.3, 0.0, 1.0)
                ),
                "sleepiness_score": float(round(sleepiness * 100.0, 2)),
                "head_away": float(head_away),
                "yawning_duration": float(yawning_duration),
            }

    def _estimate_rule_based_emotion(self):
        with self.state.lock:
            stress = float(getattr(self.state, "stress_level", 0.0) or 0.0)
            confusion = float(getattr(self.state, "confusion_level", 0.0) or 0.0)
            mar = float(getattr(self.state, "mouth_aspect_ratio", 0.0) or 0.0)
            frown_degree = float(getattr(self.state, "frown_degree", 0.0) or 0.0)

        yawning_mar_threshold = float(
            config.get("emotion", "yawning_mar_threshold", default=0.6)
        )
        if mar > yawning_mar_threshold:
            emotion = "neutral"
            confidence = 0.55
        elif stress > 0.75 and frown_degree > 0.2:
            emotion = "angry"
            confidence = 0.6
        elif confusion > 0.7:
            emotion = "surprised"
            confidence = 0.55
        elif frown_degree > 0.35:
            emotion = "sad"
            confidence = 0.55
        else:
            emotion = "neutral"
            confidence = 0.5

        scores = {
            "happy": 0.0,
            "sad": 0.0,
            "angry": 0.0,
            "surprised": 0.0,
            "neutral": 0.0,
        }
        scores[emotion] = confidence
        return emotion, confidence, scores

    def _calculate_focus_score(self):
        """Calculate focus score based on metrics"""

        def clamp01(x):
            return 0.0 if x <= 0.0 else (1.0 if x >= 1.0 else float(x))

        with self.state.lock:
            face_detected = bool(getattr(self.state, "face_detected", False))
            ear = float(getattr(self.state, "eye_aspect_ratio", 0.0) or 0.0)
            mar = float(getattr(self.state, "mouth_aspect_ratio", 0.0) or 0.0)
            head_yaw = abs(float(getattr(self.state, "head_yaw", 0.0) or 0.0))
            head_pitch = abs(float(getattr(self.state, "head_pitch", 0.0) or 0.0))
            attention_score = float(getattr(self.state, "attention_score", 0.0) or 0.0)
            looking_at = str(getattr(self.state, "looking_at", "center") or "center")
            body_detected = bool(getattr(self.state, "body_detected", False))
            posture_score = float(getattr(self.state, "posture_score", 0.0) or 0.0)
            distractions = list(getattr(self.state, "current_distractions", []) or [])
            calibration_applied = bool(
                getattr(self.state, "calibration_applied", False)
            )
            frame_brightness = float(
                getattr(self.state, "frame_brightness", 0.0) or 0.0
            )
            night_mode = bool(getattr(self.state, "night_mode", False))
            face_mesh_processed = bool(
                getattr(self.state, "face_mesh_processed", False)
            )
            last_face_mesh_time = float(
                getattr(self.state, "last_face_mesh_time", 0.0) or 0.0
            )

        if not face_detected:
            with self.state.lock:
                existing = (
                    self.state.rule_metrics
                    if isinstance(self.state.rule_metrics, dict)
                    else {}
                )
                self.state.rule_metrics = {
                    **existing,
                    "focus_face_detected": False,
                    "focus_score_components": {
                        "ear": ear,
                        "head_yaw": head_yaw,
                        "head_pitch": head_pitch,
                        "attention_score": attention_score,
                    },
                }
            return 0.0, "unfocused"

        now = time.time()
        mesh_age = (now - last_face_mesh_time) if last_face_mesh_time > 0 else 1e9
        mesh_recent = bool(face_mesh_processed) and mesh_age <= float(
            config.get("focus", "face_mesh_max_age_seconds", default=0.8)
        )
        if not mesh_recent and mesh_age >= float(
            config.get("focus", "face_mesh_hard_fail_seconds", default=2.5)
        ):
            with self.state.lock:
                existing = (
                    self.state.rule_metrics
                    if isinstance(self.state.rule_metrics, dict)
                    else {}
                )
                self.state.rule_metrics = {
                    **existing,
                    "focus_face_detected": True,
                    "focus_face_mesh_recent": False,
                    "focus_face_mesh_age_seconds": float(mesh_age),
                }
            return 0.0, "unfocused"

        ear_threshold = float(
            config.get("focus", "eye_aspect_ratio_threshold", default=0.2)
        )
        ear_soft = float(
            config.get("focus", "eye_aspect_ratio_soft_delta", default=0.05)
        )
        yaw_threshold = float(config.get("focus", "head_yaw_threshold", default=10))
        pitch_threshold = float(config.get("focus", "head_pitch_threshold", default=8))
        posture_good = float(config.get("focus", "posture_good_threshold", default=80))
        posture_ok = float(
            config.get("focus", "posture_acceptable_threshold", default=60)
        )
        yawning_mar = float(config.get("emotion", "yawning_mar_threshold", default=0.6))

        weights = config.get("focus", "weights", default=None)
        if not isinstance(weights, dict):
            weights = {
                "face_detection": 30,
                "eye_aspect_ratio": 20,
                "head_pose": 25,
                "body_posture": 15,
                "mouth_aspect_ratio": 10,
            }

        w_face = float(weights.get("face_detection", 30) or 0)
        w_ear = float(weights.get("eye_aspect_ratio", 20) or 0)
        w_head = float(weights.get("head_pose", 25) or 0)
        w_body = float(weights.get("body_posture", 15) or 0)
        w_mouth = float(weights.get("mouth_aspect_ratio", 10) or 0)
        w_total = max(1.0, w_face + w_ear + w_head + w_body + w_mouth)

        ear_score = clamp01((ear - ear_threshold) / max(ear_soft, 1e-3))

        yaw_score = clamp01(1.0 - (head_yaw / max(yaw_threshold * 2.0, 1e-3)))
        pitch_score = clamp01(1.0 - (head_pitch / max(pitch_threshold * 2.0, 1e-3)))
        head_score = min(yaw_score, pitch_score)

        if attention_score > 0:
            head_score *= clamp01(0.5 + 0.5 * (attention_score / 100.0))

        if body_detected:
            if posture_score >= posture_good:
                posture_comp = 1.0
            elif posture_score >= posture_ok:
                posture_comp = 0.7
            else:
                posture_comp = 0.3
        else:
            posture_comp = 0.7

        mouth_comp = 0.0 if mar >= yawning_mar else 1.0

        base_score = (
            (w_face * 1.0)
            + (w_ear * ear_score)
            + (w_head * head_score)
            + (w_body * posture_comp)
            + (w_mouth * mouth_comp)
        ) / w_total

        penalty = 0.0
        if distractions:
            penalty += min(
                float(config.get("focus", "max_distraction_penalty", default=0.45)),
                float(config.get("focus", "distraction_penalty_per_event", default=0.14))
                * len(distractions),
            )
        if not calibration_applied:
            penalty += float(
                config.get("focus", "no_calibration_penalty", default=0.05)
            )
        if night_mode or frame_brightness < float(
            config.get("lighting", "night_mode_threshold", default=0.25)
        ):
            penalty += float(config.get("focus", "low_light_penalty", default=0.05))
        if not mesh_recent:
            penalty += float(config.get("focus", "no_face_mesh_penalty", default=0.2))

        head_pose_low_threshold = float(
            config.get("focus", "head_pose_low_threshold", default=0.45)
        )
        if head_score < head_pose_low_threshold:
            penalty += float(config.get("focus", "head_pose_low_penalty", default=0.2))

        if mesh_recent and looking_at != "center":
            penalty += float(config.get("focus", "gaze_offcenter_penalty", default=0.18))

        attention_low_threshold = float(
            config.get("focus", "attention_score_low_threshold", default=75)
        )
        if mesh_recent and attention_score < attention_low_threshold:
            penalty += float(config.get("focus", "attention_low_penalty", default=0.12))

        score = 100.0 * clamp01(base_score * (1.0 - penalty))

        focused_threshold = float(config.get("focus", "focused_threshold", default=80))
        distracted_threshold = float(
            config.get("focus", "distracted_threshold", default=50)
        )

        if score >= focused_threshold:
            status = "focused"
        elif score >= distracted_threshold:
            status = "distracted"
        else:
            status = "unfocused"

        with self.state.lock:
            existing = (
                self.state.rule_metrics
                if isinstance(self.state.rule_metrics, dict)
                else {}
            )
            self.state.rule_metrics = {
                **existing,
                "focus_face_detected": True,
                "focus_calibration_applied": bool(calibration_applied),
                "focus_looking_at": looking_at,
                "focus_attention_score": float(attention_score),
                "focus_face_mesh_recent": bool(mesh_recent),
                "focus_face_mesh_age_seconds": float(mesh_age),
                "focus_components": {
                    "ear_score": float(ear_score),
                    "head_score": float(head_score),
                    "posture_score": float(posture_comp),
                    "mouth_score": float(mouth_comp),
                    "penalty": float(penalty),
                },
                "focus_raw": {
                    "ear": float(ear),
                    "mar": float(mar),
                    "head_yaw": float(head_yaw),
                    "head_pitch": float(head_pitch),
                    "posture": float(posture_score),
                    "distractions": len(distractions),
                    "frame_brightness": float(frame_brightness),
                    "night_mode": bool(night_mode),
                },
            }

        return round(score, 2), status

    def _calculate_mental_effort(self):
        """
        Calculate mental effort score (0-100)
        Mental effort indicates cognitive load and concentration intensity
        """
        if not self.state.face_detected:
            return 0

        effort = 0

        # Eyebrow furrow (high = concentrating hard)
        if hasattr(self.state, "eyebrow_furrow"):
            effort += self.state.eyebrow_furrow * 30  # Max 30 points

        # Lip tension (high = stress/concentration)
        if hasattr(self.state, "lip_tension"):
            effort += self.state.lip_tension * 20  # Max 20 points

        # Reduced blink rate (indicates deep concentration)
        if hasattr(self.state, "blink_rate"):
            # Normal blink rate is 15-20/min
            # Lower = more concentrated
            blink_score = max(0, (20 - self.state.blink_rate) / 20.0)
            effort += blink_score * 15  # Max 15 points

        # Eye aspect ratio (slightly lower = focused, but not closed)
        ear = self.state.eye_aspect_ratio
        if 0.22 < ear < 0.28:  # Optimal focused range
            effort += 15
        elif 0.20 < ear < 0.30:
            effort += 10

        # Focus percentage contributes to mental effort
        # Higher focus often correlates with higher effort
        effort += (self.state.focus_percentage / 100.0) * 20  # Max 20 points

        # Clamp to 0-100
        effort = max(0, min(100, effort))

        return round(effort, 2)

    def _debounce_focus_status(self, raw_status):
        """Debounce focus status changes"""
        if raw_status != self.focus_status_candidate:
            self.focus_status_candidate = raw_status
            self.focus_status_candidate_since = time.time()
        else:
            if (
                time.time() - self.focus_status_candidate_since
                >= self.focus_status_debounce_seconds
                and raw_status != self.focus_status_last_emitted
            ):
                self.focus_status_last_emitted = raw_status
                return raw_status

        return self.focus_status_last_emitted or "unfocused"

    def _stabilize_focus(self, raw_score: float, raw_status: str):
        try:
            raw_score = float(raw_score)
        except Exception:
            raw_score = 0.0

        if raw_score <= 0.0 and (raw_status or "") == "unfocused":
            self.focus_score_ema = 0.0
            self.focus_status_last_emitted = "unfocused"
            return 0.0, "unfocused"

        active = self._last_distraction_active if isinstance(self._last_distraction_active, dict) else {}
        if (
            active.get("no_face")
            or active.get("eyes_closed")
            or active.get("head_turn")
            or active.get("gaze_away")
            or active.get("smartphone")
        ):
            self.focus_score_ema = min(
                float(self.focus_score_ema) if self.focus_score_ema is not None else raw_score,
                float(self.forced_unfocused_score),
            )
            self.focus_status_last_emitted = "unfocused"
            return round(float(self.focus_score_ema), 2), "unfocused"

        alpha = float(self.focus_score_smoothing_alpha)
        alpha = max(0.05, min(0.9, alpha))
        if self.focus_score_ema is None:
            self.focus_score_ema = raw_score
        else:
            self.focus_score_ema = (alpha * raw_score) + ((1.0 - alpha) * float(self.focus_score_ema))

        score = float(max(0.0, min(100.0, self.focus_score_ema)))

        focused_threshold = float(config.get("focus", "focused_threshold", default=80))
        distracted_threshold = float(config.get("focus", "distracted_threshold", default=50))
        hysteresis = float(self.focus_status_hysteresis)
        distracted_hysteresis = float(self.focus_distracted_hysteresis)

        stable = str(self.focus_status_last_emitted or raw_status or "unfocused")
        if stable not in ("focused", "distracted", "unfocused"):
            stable = "unfocused"

        if stable == "focused":
            if score < (focused_threshold - hysteresis):
                stable = "distracted" if score >= distracted_threshold else "unfocused"
        else:
            if score >= focused_threshold:
                stable = "focused"
            else:
                if stable == "distracted" and score < (distracted_threshold - distracted_hysteresis):
                    stable = "unfocused"
                elif stable == "unfocused" and score >= (distracted_threshold + distracted_hysteresis):
                    stable = "distracted"
                else:
                    stable = "distracted" if score >= distracted_threshold else "unfocused"

        self.focus_status_last_emitted = stable

        with self.state.lock:
            existing = self.state.rule_metrics if isinstance(self.state.rule_metrics, dict) else {}
            self.state.rule_metrics = {
                **existing,
                "focus_score_raw": float(raw_score),
                "focus_score_smoothed": float(score),
                "focus_thresholds": {
                    "focused": float(focused_threshold),
                    "distracted": float(distracted_threshold),
                    "hysteresis": float(hysteresis),
                    "distracted_hysteresis": float(distracted_hysteresis),
                },
            }

        return round(score, 2), stable

    def _detect_distractions(self):
        now = time.time()

        min_seconds = float(
            config.get("distractions", "validation_min_seconds", default=0.9)
        )
        grace_seconds = float(
            config.get("distractions", "clear_grace_seconds", default=1.2)
        )

        head_turn_threshold = float(
            config.get("distractions", "head_turn_threshold", default=20)
        )
        head_roll_threshold = float(
            config.get("distractions", "head_roll_threshold", default=18)
        )
        eye_closed_seconds = float(
            config.get("distractions", "eye_closed_seconds", default=0.6)
        )
        attention_score_threshold = float(
            config.get("distractions", "attention_score_threshold", default=55)
        )
        stress_high_threshold = float(
            config.get("distractions", "stress_high_threshold", default=0.7)
        )
        posture_poor_threshold = float(
            config.get("distractions", "posture_poor_threshold", default=40)
        )
        yawning_mar_threshold = float(
            config.get("emotion", "yawning_mar_threshold", default=0.6)
        )
        yawning_duration_threshold = float(
            config.get("emotion", "yawning_duration_threshold", default=0.5)
        )

        with self.state.lock:
            face_detected = bool(getattr(self.state, "face_detected", False))
            head_yaw = float(getattr(self.state, "head_yaw", 0.0) or 0.0)
            head_roll = float(getattr(self.state, "head_roll", 0.0) or 0.0)
            ear = float(getattr(self.state, "eye_aspect_ratio", 0.0) or 0.0)
            is_blinking = bool(getattr(self.state, "is_blinking", False))
            attention_score = float(getattr(self.state, "attention_score", 0.0) or 0.0)
            looking_at = str(getattr(self.state, "looking_at", "center") or "center")
            emotion = str(getattr(self.state, "emotion", "neutral") or "neutral")
            stress_level = float(getattr(self.state, "stress_level", 0.0) or 0.0)
            mar = float(getattr(self.state, "mouth_aspect_ratio", 0.0) or 0.0)
            yawning_duration = float(
                getattr(self.state, "yawning_duration", 0.0) or 0.0
            )
            body_detected = bool(getattr(self.state, "body_detected", False))
            posture_score = float(getattr(self.state, "posture_score", 0.0) or 0.0)
            smartphone_detected = bool(
                getattr(self.state, "smartphone_detected", False)
            )
            focus_pct = float(getattr(self.state, "focus_percentage", 0.0) or 0.0)
            face_mesh_processed = bool(
                getattr(self.state, "face_mesh_processed", False)
            )
            last_face_mesh_time = float(
                getattr(self.state, "last_face_mesh_time", 0.0) or 0.0
            )

        face_mesh_max_age = float(
            config.get("distractions", "face_mesh_max_age_seconds", default=0.8)
        )
        mesh_age = (now - last_face_mesh_time) if last_face_mesh_time > 0 else 1e9
        mesh_recent = bool(face_mesh_processed) and mesh_age <= face_mesh_max_age

        def update_gate(key: str, raw: bool, min_hold: float):
            st = self._distraction_states.get(key)
            if not isinstance(st, dict):
                st = {"candidate_since": None, "last_true": None, "active": False}

            if raw:
                st["last_true"] = now
                if st["candidate_since"] is None:
                    st["candidate_since"] = now
                if (
                    not st["active"]
                    and (now - float(st["candidate_since"])) >= min_hold
                ):
                    st["active"] = True
            else:
                st["candidate_since"] = None
                if st["active"]:
                    last_true = st["last_true"]
                    if last_true is None or (now - float(last_true)) >= grace_seconds:
                        st["active"] = False

            self._distraction_states[key] = st
            return bool(st["active"])

        distractions = []
        raw_signals = {}
        active_signals = {}

        if not face_detected:
            active = update_gate(
                "no_face",
                True,
                float(config.get("distractions", "no_face_min_seconds", default=0.6)),
            )
            raw_signals["no_face"] = True
            active_signals["no_face"] = active
            if active:
                distractions.append("No face detected")
        else:
            update_gate("no_face", False, 0.0)
            raw_signals["no_face"] = False
            active_signals["no_face"] = False

            yaw_abs = abs(head_yaw)
            raw_head_turn = yaw_abs > head_turn_threshold and attention_score < 85
            raw_signals["head_turn"] = bool(raw_head_turn)
            active = update_gate(
                "head_turn",
                bool(raw_head_turn),
                float(config.get("distractions", "head_turn_min_seconds", default=min_seconds)),
            )
            active_signals["head_turn"] = active
            if active:
                direction = "right" if head_yaw > 0 else "left"
                distractions.append(
                    f"Looking {direction} (head turned {yaw_abs:.0f} deg)"
                )

            roll_abs = abs(head_roll)
            raw_head_tilt = roll_abs > head_roll_threshold and focus_pct < 80
            raw_signals["head_tilt"] = bool(raw_head_tilt)
            active = update_gate("head_tilt", bool(raw_head_tilt), min_seconds)
            active_signals["head_tilt"] = active
            if active:
                distractions.append(
                    f"Head tilted {roll_abs:.0f} deg (possible fatigue)"
                )

            raw_eyes_closed = (
                mesh_recent
                and (
                    ear
                    < float(
                        config.get("focus", "eye_aspect_ratio_threshold", default=0.2)
                    )
                )
                and (not is_blinking)
            )
            raw_signals["eyes_closed"] = bool(raw_eyes_closed)
            active = update_gate(
                "eyes_closed",
                bool(raw_eyes_closed),
                max(min_seconds, eye_closed_seconds),
            )
            active_signals["eyes_closed"] = active
            if active:
                distractions.append("Eyes closed (drowsy)")

            raw_gaze_away = (
                mesh_recent
                and attention_score < attention_score_threshold
                and looking_at != "center"
            )
            raw_signals["gaze_away"] = bool(raw_gaze_away)
            active = update_gate(
                "gaze_away",
                bool(raw_gaze_away),
                float(config.get("distractions", "gaze_away_min_seconds", default=min_seconds)),
            )
            active_signals["gaze_away"] = active
            if active:
                distractions.append(
                    f"Gaze away from screen (attention: {attention_score:.0f}%)"
                )

            raw_yawning = (mar > yawning_mar_threshold) and (
                yawning_duration >= yawning_duration_threshold
            )
            raw_signals["yawning"] = bool(raw_yawning)
            active = update_gate("yawning", bool(raw_yawning), min_seconds)
            active_signals["yawning"] = active
            if active:
                distractions.append("Yawning (fatigued)")

            raw_poor_posture = body_detected and (
                posture_score < posture_poor_threshold
            )
            raw_signals["poor_posture"] = bool(raw_poor_posture)
            active = update_gate(
                "poor_posture",
                bool(raw_poor_posture),
                float(config.get("distractions", "posture_min_seconds", default=1.5)),
            )
            active_signals["poor_posture"] = active
            if active:
                distractions.append(f"Poor posture (score: {posture_score:.0f}%)")

            raw_smartphone = bool(smartphone_detected)
            raw_signals["smartphone"] = bool(raw_smartphone)
            active = update_gate(
                "smartphone",
                bool(raw_smartphone),
                float(
                    config.get("distractions", "smartphone_min_seconds", default=0.4)
                ),
            )
            active_signals["smartphone"] = active
            if active:
                distractions.append("Smartphone detected")

            include_affect = bool(
                config.get("distractions", "include_affect_signals", default=False)
            )
            if include_affect:
                raw_negative_emotion = (emotion in ["sad", "angry"]) and (
                    attention_score < 70
                )
                raw_signals["negative_emotion"] = bool(raw_negative_emotion)
                active = update_gate(
                    "negative_emotion",
                    bool(raw_negative_emotion),
                    float(
                        config.get("distractions", "affect_min_seconds", default=2.0)
                    ),
                )
                active_signals["negative_emotion"] = active
                if active:
                    distractions.append(f"Negative emotion: {emotion}")

                raw_high_stress = (stress_level > stress_high_threshold) and (
                    attention_score < 70
                )
                raw_signals["high_stress"] = bool(raw_high_stress)
                active = update_gate(
                    "high_stress",
                    bool(raw_high_stress),
                    float(
                        config.get("distractions", "affect_min_seconds", default=2.0)
                    ),
                )
                active_signals["high_stress"] = active
                if active:
                    distractions.append(
                        f"High stress detected ({stress_level * 100:.0f}%)"
                    )
            else:
                raw_signals["negative_emotion"] = False
                raw_signals["high_stress"] = False
                active_signals["negative_emotion"] = False
                active_signals["high_stress"] = False
                update_gate("negative_emotion", False, 0.0)
                update_gate("high_stress", False, 0.0)

        with self.state.lock:
            existing = (
                self.state.rule_metrics
                if isinstance(self.state.rule_metrics, dict)
                else {}
            )
            self.state.rule_metrics = {
                **existing,
                "distraction_raw": raw_signals,
                "distraction_active": active_signals,
            }

        self._last_distraction_active = active_signals

        if distractions and (now - self._last_distraction_event_time) >= float(
            config.get("distractions", "event_log_cooldown_seconds", default=1.0)
        ):
            self._last_distraction_event_time = now
            logger.info(f"[DISTRACTION] {', '.join(distractions)}")

        return distractions

    def _apply_lighting_adaptation(self, frame):
        try:
            if not bool(config.get("lighting", "enabled", default=False)):
                return frame

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            brightness = float(np.mean(gray) / 255.0)
            night_mode = brightness < float(
                config.get("lighting", "night_mode_threshold", default=0.25)
            )
            with self.state.lock:
                self.state.frame_brightness = brightness
                self.state.night_mode = bool(night_mode)

            out = frame
            if bool(config.get("lighting", "auto_brightness", default=True)):
                target = float(
                    config.get("lighting", "target_brightness", default=0.45)
                )
                gain = max(0.6, min(2.0, target / max(brightness, 1e-3)))
                out = cv2.convertScaleAbs(out, alpha=gain, beta=0)

            if bool(config.get("lighting", "dynamic_contrast", default=True)):
                ycrcb = cv2.cvtColor(out, cv2.COLOR_BGR2YCrCb)
                y, cr, cb = cv2.split(ycrcb)
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                y2 = clahe.apply(y)
                out = cv2.cvtColor(cv2.merge((y2, cr, cb)), cv2.COLOR_YCrCb2BGR)

            return out
        except Exception:
            return frame

    def _run_smartphone_detection(self, frame):
        if not self.smartphone_detection_enabled or self.smartphone_detector is None:
            return
        if bool(getattr(self.state, "calibration_in_progress", False)):
            return
        interval = int(
            config.get("smartphone_detection", "interval_frames", default=10)
        )
        if interval > 1 and (self.state.frame_count % interval) != 0:
            return
        detections = self.smartphone_detector.detect(frame)
        best = detections[0] if detections else None
        with self.state.lock:
            if best:
                self.state.smartphone_detected = True
                self.state.smartphone_confidence = float(best.get("score", 0.0))
                self.state.smartphone_bbox = best.get("bbox")
            else:
                self.state.smartphone_detected = False
                self.state.smartphone_confidence = 0.0
                self.state.smartphone_bbox = None

    def _draw_smartphone_feedback(self, frame):
        if not bool(
            config.get("smartphone_detection", "visual_feedback", default=False)
        ):
            return
        if not bool(getattr(self.state, "smartphone_detected", False)):
            return
        bbox = getattr(self.state, "smartphone_bbox", None)
        if not bbox:
            return
        x1, y1, x2, y2 = bbox
        cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 0, 255), 2)

    def _update_time_tracking(self, focus_status):
        """Update time tracking - FIXED to properly track focused and unfocused time"""
        current_time = time.time()

        if bool(getattr(self.state, "calibration_in_progress", False)):
            with self.state.lock:
                self.state.last_tracking_update = current_time
                self.state.last_focus_status = focus_status
            return

        # Initialize tracking variables
        if (
            not hasattr(self.state, "last_tracking_update")
            or self.state.last_tracking_update is None
        ):
            self.state.last_tracking_update = current_time
            self.state.last_focus_status = focus_status
            return

        time_elapsed = current_time - self.state.last_tracking_update

        with self.state.lock:
            previous_status = self.state.last_focus_status

            if focus_status == "focused":
                self.state.focused_time_seconds += time_elapsed
            else:
                self.state.unfocused_time_seconds += time_elapsed

            if previous_status == "focused" and focus_status != "focused":
                self.state.current_unfocus_start = self.state.last_tracking_update
                if self.state.first_unfocus_time is None:
                    self.state.first_unfocus_time = self.state.last_tracking_update

            if previous_status != "focused" and focus_status == "focused":
                if (
                    hasattr(self.state, "current_unfocus_start")
                    and self.state.current_unfocus_start is not None
                ):
                    unfocus_duration = current_time - self.state.current_unfocus_start
                    self.state.unfocus_intervals.append(
                        {
                            "start": self.state.current_unfocus_start,
                            "end": current_time,
                            "duration": unfocus_duration,
                            "reason": "distracted"
                            if self.state.current_distractions
                            else "unknown",
                        }
                    )
                    self.state.unfocus_count += 1
                    self.state.last_unfocus_time = current_time
                    self.state.current_unfocus_start = None

            self.state.last_tracking_update = current_time
            self.state.last_focus_status = focus_status

    def _request_vlm_analysis(self):
        """Request VLM analysis"""
        if not bool(getattr(self, "vlm_user_enabled", False)):
            return
        if self.vlm_service is None:
            self._schedule_vlm_init()
            return
        if self.vlm_service and bool(
            getattr(self.vlm_service, "is_ready", lambda: False)()
        ):
            try:
                # Get current frame
                if hasattr(self, "current_frame"):
                    skip_reason = self._get_vlm_skip_reason()
                    if skip_reason:
                        if hasattr(self.vlm_service, "suspend_inference"):
                            self.vlm_service.suspend_inference(
                                float(
                                    config.get(
                                        "vlm", "cooldown_on_skip_seconds", default=5.0
                                    )
                                ),
                                reason=skip_reason,
                            )
                        return
                    focus_metrics = {
                        "focus_percentage": self.state.focus_percentage,
                        "focus_status": self.state.focus_status,
                        "emotion": getattr(self.state, "emotion", "neutral"),
                        "typing": getattr(self.state, "typing", False),
                        "mental_effort": getattr(self.state, "mental_effort", 0),
                    }

                    pose_context = getattr(self.state, "posture_context", "unknown")

                    analysis = self.vlm_service.analyze_context(
                        self.current_frame, focus_metrics, pose_context
                    )

                    if analysis:
                        self.last_vlm_analysis = analysis
                        # Emit VLM insights to UI
                        if self.socketio:
                            self.socketio.emit("vlm_insights", analysis)

            except Exception as e:
                logger.error(f"[ERROR] VLM analysis error: {e}")
                try:
                    msg = str(e).lower()
                    if "out of memory" in msg or "cuda" in msg or "cublas" in msg:
                        if hasattr(self.vlm_service, "suspend_inference"):
                            self.vlm_service.suspend_inference(
                                60.0, reason="gpu_resource_conflict"
                            )
                except Exception:
                    pass

    def _on_vlm_status_update(self, status):
        try:
            if not bool(getattr(self, "vlm_user_enabled", False)):
                with self.state.lock:
                    self.state.vlm_status = "disabled"
                    self.state.vlm_ready = False
                    self.state.vlm_last_error = None
                return
            self.last_vlm_status = status
            if self.socketio:
                self.socketio.emit("vlm_status_update", status)
            if status and status.get("status") == "ready" and self.vlm_service:
                try:
                    self.vlm_service.analysis_cooldown = float(
                        config.get("vlm", "analysis_cooldown_seconds", default=5.0)
                    )
                except Exception:
                    pass
        except Exception:
            pass

    def _maybe_update_vlm_status(self):
        if not bool(getattr(self, "vlm_user_enabled", False)):
            return
        if self.vlm_service is None:
            self._schedule_vlm_init()
            return
        if not self.vlm_service:
            return
        now = time.time()
        if (now - self.last_vlm_status_time) < 1.0:
            return
        self.last_vlm_status_time = now
        try:
            status = (
                self.vlm_service.get_status()
                if hasattr(self.vlm_service, "get_status")
                else None
            )
            if not status:
                return
            if status != self.last_vlm_status:
                self.last_vlm_status = status
                if self.socketio:
                    self.socketio.emit("vlm_status_update", status)
            with self.state.lock:
                self.state.vlm_status = status.get("status")
                self.state.vlm_ready = bool(status.get("ready"))
                self.state.vlm_last_error = status.get("last_error")

            # Retry readiness when loaded/not ready and resources are OK
            if status.get("status") in ("loaded", "suspended", "error") and not bool(
                status.get("ready")
            ):
                reason = self._get_vlm_skip_reason()
                if not reason:
                    cfg = {
                        "enabled": bool(
                            config.get(
                                "vlm", "readiness_retry", "enabled", default=True
                            )
                        ),
                        "initial_seconds": float(
                            config.get(
                                "vlm", "readiness_retry", "initial_seconds", default=10
                            )
                        ),
                        "max_seconds": float(
                            config.get(
                                "vlm", "readiness_retry", "max_seconds", default=300
                            )
                        ),
                        "max_attempts_per_hour": int(
                            config.get(
                                "vlm",
                                "readiness_retry",
                                "max_attempts_per_hour",
                                default=12,
                            )
                        ),
                    }
                    if hasattr(self.vlm_service, "warmup_retry"):
                        self.vlm_service.warmup_retry(cfg=cfg)
        except Exception:
            pass

    def _get_vlm_skip_reason(self):
        try:
            if bool(getattr(self.state, "calibration_in_progress", False)):
                return "calibration_in_progress"
            if float(getattr(self.state, "fps", 0.0) or 0.0) < float(
                config.get("vlm", "min_fps_to_run", default=12.0)
            ):
                return "low_fps"
            min_free_mb = (
                float(config.get("vlm", "min_free_vram_mb", default=512))
                if self.gpu_enabled
                else 0.0
            )
            if min_free_mb <= 0:
                return None
            import torch

            if not torch.cuda.is_available():
                return None
            free_b, _total_b = torch.cuda.mem_get_info()
            free_mb = float(free_b) / (1024 * 1024)
            if free_mb < min_free_mb:
                return "low_free_vram"
            return None
        except Exception:
            return None

    def _draw_lightweight_feedback(self, frame):
        """Draw lightweight visual feedback"""
        if not bool(config.get("ui", "visual_feedback", "enabled", default=True)):
            return

        h, w = frame.shape[:2]

        # Draw FPS
        if config.get("ui", "show_fps", default=True):
            fps_text = f"FPS: {self.state.fps:.1f}"
            cv2.putText(
                frame, fps_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2
            )

        # Draw focus percentage
        if config.get("ui", "show_focus_percentage", default=True):
            focus_text = f"Focus: {self.state.focus_percentage:.0f}%"
            cv2.putText(
                frame,
                focus_text,
                (10, 60),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2,
            )

        # Draw emotion
        if config.get("ui", "show_emotion", default=True):
            emotion = getattr(self.state, "emotion", "neutral")
            emotion_text = f"Emotion: {emotion}"
            cv2.putText(
                frame,
                emotion_text,
                (10, 90),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2,
            )

        try:
            focus_pct = float(getattr(self.state, "focus_percentage", 0.0) or 0.0)
        except Exception:
            focus_pct = 0.0

        if focus_pct >= 70:
            focus_color = (0, 200, 0)
        elif focus_pct >= 40:
            focus_color = (0, 165, 255)
        else:
            focus_color = (0, 0, 255)

        cv2.circle(frame, (w - 24, 26), 10, focus_color, -1)
        cv2.circle(frame, (w - 24, 26), 10, (0, 0, 0), 2)

        if bool(self.face_mesh_overlay_enabled):
            with self.lock:
                overlay_payload = self._last_face_overlay

            if isinstance(overlay_payload, dict):
                points = overlay_payload.get("points") or []
                if points:
                    alpha = float(self.face_mesh_overlay_alpha)
                    alpha = max(0.0, min(1.0, alpha))
                    smoothing = float(self.face_mesh_overlay_smoothing)
                    smoothing = max(0.0, min(1.0, smoothing))

                    overlay = frame.copy()
                    next_smoothed = {}

                    bbox = overlay_payload.get("bbox")
                    if (
                        isinstance(bbox, list)
                        and len(bbox) == 4
                        and all(isinstance(v, (int, float)) for v in bbox)
                    ):
                        x1, y1, x2, y2 = [int(v) for v in bbox]
                        x1 = max(0, min(w - 1, x1))
                        x2 = max(0, min(w - 1, x2))
                        y1 = max(0, min(h - 1, y1))
                        y2 = max(0, min(h - 1, y2))
                        if x2 > x1 and y2 > y1:
                            cv2.rectangle(overlay, (x1, y1), (x2, y2), (0, 255, 0), 1)

                    groups_order = {
                        "left_eye": [33, 159, 145, 133],
                        "right_eye": [362, 386, 374, 263],
                        "left_iris": [468, 469, 470, 471, 472],
                        "right_iris": [473, 474, 475, 476, 477],
                        "mouth": [13, 14, 291, 61],
                    }

                    group_points = {}
                    for p in points:
                        pid = p.get("id")
                        if not pid:
                            continue
                        try:
                            x = int(p.get("x"))
                            y = int(p.get("y"))
                        except Exception:
                            continue

                        group = p.get("group") or ""
                        group = str(group)
                        if group != "mesh":
                            prev = self._overlay_smoothed_points.get(pid)
                            if prev:
                                sx = int(prev[0] * (1.0 - smoothing) + x * smoothing)
                                sy = int(prev[1] * (1.0 - smoothing) + y * smoothing)
                            else:
                                sx, sy = x, y
                            next_smoothed[pid] = (sx, sy)
                        else:
                            sx, sy = x, y
                        group_points.setdefault(str(group), []).append((pid, sx, sy))

                    self._overlay_smoothed_points = next_smoothed

                    if str(self.face_mesh_overlay_mode).strip().lower() in (
                        "triangles",
                        "triangle",
                    ):
                        if (
                            isinstance(bbox, list)
                            and len(bbox) == 4
                            and all(isinstance(v, (int, float)) for v in bbox)
                        ):
                            try:
                                every_n = int(self.face_mesh_triangles_every_n_frames)
                                if every_n <= 0:
                                    every_n = 3
                                if (
                                    int(getattr(self.state, "frame_count", 0) or 0)
                                    % every_n
                                ) != 0:
                                    raise RuntimeError("skip_triangles")

                                x1, y1, x2, y2 = [int(v) for v in bbox]
                                x1 = max(0, min(w - 1, x1))
                                x2 = max(0, min(w - 1, x2))
                                y1 = max(0, min(h - 1, y1))
                                y2 = max(0, min(h - 1, y2))
                                if x2 > x1 and y2 > y1:
                                    rect = (x1, y1, max(1, x2 - x1), max(1, y2 - y1))
                                    subdiv = cv2.Subdiv2D(rect)
                                    mesh_pts = []
                                    for _pid, px, py in group_points.get("mesh", []):
                                        if x1 <= px <= x2 and y1 <= py <= y2:
                                            mesh_pts.append((int(px), int(py)))
                                    max_pts = int(self.face_mesh_triangles_max_points)
                                    if max_pts > 0 and len(mesh_pts) > max_pts:
                                        step = max(1, len(mesh_pts) // max_pts)
                                        mesh_pts = mesh_pts[::step]
                                    for pt in mesh_pts:
                                        subdiv.insert(pt)
                                    tris = subdiv.getTriangleList()
                                    for t in tris:
                                        xA, yA, xB, yB, xC, yC = [int(v) for v in t]
                                        if (
                                            x1 <= xA <= x2
                                            and x1 <= xB <= x2
                                            and x1 <= xC <= x2
                                            and y1 <= yA <= y2
                                            and y1 <= yB <= y2
                                            and y1 <= yC <= y2
                                        ):
                                            cv2.line(
                                                overlay,
                                                (xA, yA),
                                                (xB, yB),
                                                (0, 255, 0),
                                                1,
                                            )
                                            cv2.line(
                                                overlay,
                                                (xB, yB),
                                                (xC, yC),
                                                (0, 255, 0),
                                                1,
                                            )
                                            cv2.line(
                                                overlay,
                                                (xC, yC),
                                                (xA, yA),
                                                (0, 255, 0),
                                                1,
                                            )
                            except Exception:
                                pass

                    group_colors = {
                        "mesh": (0, 255, 0),
                        "left_eye": (255, 255, 0),
                        "right_eye": (255, 255, 0),
                        "left_iris": (200, 200, 0),
                        "right_iris": (200, 200, 0),
                        "nose": (255, 255, 255),
                        "mouth": (255, 0, 255),
                    }

                    for group, pts in group_points.items():
                        color = group_colors.get(group, (255, 255, 255))
                        for _pid, x, y in pts:
                            if 0 <= x < w and 0 <= y < h:
                                r = 2 if group == "mesh" else 1
                                cv2.circle(overlay, (x, y), r, color, -1)

                        order = groups_order.get(group)
                        if order:
                            by_idx = {}
                            for pid, x, y in pts:
                                try:
                                    idx = int(str(pid).split(":")[-1])
                                except Exception:
                                    continue
                                by_idx[idx] = (x, y)
                            poly = [by_idx[i] for i in order if i in by_idx]
                            if len(poly) >= 2:
                                cv2.polylines(
                                    overlay,
                                    [np.array(poly, dtype=np.int32)],
                                    isClosed=True,
                                    color=color,
                                    thickness=1,
                                )

                    if alpha > 0:
                        cv2.addWeighted(overlay, alpha, frame, 1.0 - alpha, 0, frame)

        return

    def _emit_frame(self, frame):
        """Emit frame to UI"""
        if self.socketio:
            try:
                # Store current frame for VLM
                self.current_frame = frame.copy()

                # Use lower JPEG quality to reduce size
                ret_encode, buffer = cv2.imencode(
                    ".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, int(self.jpeg_quality)]
                )

                if ret_encode:
                    frame_b64 = base64.b64encode(buffer).decode("utf-8")

                    # Use stored socketio reference
                    try:
                        self.socketio.emit("frame_update", {"frame": frame_b64})
                    except TypeError as e:
                        logger.error(
                            f"[ERROR] SocketIO serialization error: {e} - check for numpy types in state"
                        )
                    except Exception as e:
                        logger.error(f"[ERROR] SocketIO emit error: {e}")

            except Exception as e:
                logger.error(f"[ERROR] Frame encoding error: {e}")

    def _emit_state_update(self):
        if not self.socketio:
            return
        now = time.time()
        if (now - self.last_state_emit_time) < 0.2:
            return
        self.last_state_emit_time = now
        try:
            self.socketio.emit(
                "state_update",
                {"state": self.state.to_dict(), "vlm_insights": self.last_vlm_analysis},
            )
        except Exception as e:
            logger.error(f"[ERROR] SocketIO state emit error: {e}")

    def toggle_processing(self):
        """Toggle privacy mode"""
        if not config.privacy_allow_pause:
            logger.warning("[WARN] Privacy controls are disabled")
            return

        self.processing_enabled = not self.processing_enabled
        status = "resumed" if self.processing_enabled else "paused"
        logger.info(f"[PRIVACY] Processing {status}")
        return self.processing_enabled

    def get_overlay_settings(self):
        with self.lock:
            return {
                "visual_feedback_enabled": bool(self.visual_feedback_enabled),
                "show_face_mesh": bool(self.face_mesh_overlay_enabled),
                "face_mesh_alpha": float(self.face_mesh_overlay_alpha),
                "face_mesh_smoothing": float(self.face_mesh_overlay_smoothing),
                "face_mesh_mode": str(self.face_mesh_overlay_mode),
                "face_mesh_stride": int(self.face_mesh_overlay_stride),
            }

    def set_overlay_settings(
        self,
        *,
        show_face_mesh=None,
        face_mesh_alpha=None,
        face_mesh_smoothing=None,
        face_mesh_mode=None,
        face_mesh_stride=None,
    ):
        with self.lock:
            if show_face_mesh is not None:
                self.face_mesh_overlay_enabled = bool(show_face_mesh)
                if not self.face_mesh_overlay_enabled:
                    self._last_face_overlay = None
                    self._overlay_smoothed_points = {}

            if face_mesh_alpha is not None:
                try:
                    self.face_mesh_overlay_alpha = float(face_mesh_alpha)
                except Exception:
                    pass

            if face_mesh_smoothing is not None:
                try:
                    self.face_mesh_overlay_smoothing = float(face_mesh_smoothing)
                except Exception:
                    pass

            if face_mesh_mode is not None:
                self.face_mesh_overlay_mode = str(face_mesh_mode).strip() or "full"

            if face_mesh_stride is not None:
                try:
                    self.face_mesh_overlay_stride = int(face_mesh_stride)
                except Exception:
                    pass
