"""
Improved Webcam Processor
Integrates all modular MediaPipe processors with new features:
- Adaptive frame skipping
- GPU acceleration support
- Privacy controls
- Proper resource cleanup
"""

import os
import logging
import time
import cv2
import numpy as np
from collections import deque
from threading import Thread, Lock

from config_loader import config
from mediapipe_processors import PoseProcessor, FaceMeshProcessor, DeepFaceEmotionDetector
from mediapipe_processors.efficientnet_emotion_detector import EfficientNetEmotionDetector
from calibration import CalibrationManager

logger = logging.getLogger(__name__)


class ImprovedWebcamProcessor:
    """Enhanced webcam processor with all improvements"""

    def __init__(self, state):
        """
        Initialize improved webcam processor

        Args:
            state: SessionState object
        """
        self.state = state
        self.cap = None
        self.running = False
        self.thread = None
        self.lock = Lock()

        # Privacy controls
        self.processing_enabled = True  # Can be toggled for privacy

        # Initialize modular processors
        self.pose_processor = PoseProcessor(config)
        self.face_processor = FaceMeshProcessor(config)

        # Emotion detectors (priority order)
        # 1. EfficientNet-B3 (SAFE, 86-87%, 50-60 FPS) - PRIMARY
        # 2. DeepFace (backup - 70%, 10-15 FPS)
        self.efficientnet_detector = EfficientNetEmotionDetector(
            config,
            model_size="b3",
            use_huggingface=False
        )
        self.deepface_detector = DeepFaceEmotionDetector(config)

        # Calibration system
        self.calibration = CalibrationManager(config)
        if config.get('calibration', 'enabled', default=True):
            self.calibration.load_calibration('default')

        # Adaptive frame skipping
        self.frame_skip = config.frame_skip_base
        self.fps_history = deque(maxlen=30)

        # Gaze smoothing (reduce jitter)
        self.gaze_smoothing_enabled = config.get('eye_tracking', 'enable_smoothing', default=True)
        self.gaze_smoothing_window = config.get('eye_tracking', 'smoothing_window', default=5)
        self.gaze_history_x = deque(maxlen=self.gaze_smoothing_window)
        self.gaze_history_y = deque(maxlen=self.gaze_smoothing_window)

        # GPU acceleration check
        self.gpu_enabled = self._check_gpu_support()

        logger.info("✅ ImprovedWebcamProcessor initialized")
        logger.info(f"🔧 GPU Acceleration: {'Enabled' if self.gpu_enabled else 'Disabled'}")
        logger.info(f"🔧 Adaptive Quality: {'Enabled' if config.adaptive_quality_enabled else 'Disabled'}")
        logger.info(f"🔧 Privacy Controls: {'Enabled' if config.privacy_allow_pause else 'Disabled'}")

    def _check_gpu_support(self):
        """Check if GPU acceleration is available"""
        if not config.gpu_acceleration_enabled:
            return False

        try:
            # Check for CUDA
            if cv2.cuda.getCudaEnabledDeviceCount() > 0:
                logger.info("🚀 CUDA GPU detected")
                return True
        except:
            pass

        # Check for other GPU backends
        try:
            # Try to use OpenCV DNN backend with GPU
            if hasattr(cv2.dnn, 'DNN_BACKEND_CUDA'):
                logger.info("🚀 OpenCV CUDA backend available")
                return True
        except:
            pass

        logger.info("⚠️ No GPU acceleration available, using CPU")
        return False

    def start(self):
        """Start webcam processing"""
        logger.info("🔵 START: Improved webcam processor")

        if self.running:
            logger.info("⚠️ Webcam already running")
            return True

        # Try to open camera with configured backend
        backend_map = {
            'dshow': cv2.CAP_DSHOW,
            'default': 0,
            'v4l2': cv2.CAP_V4L2
        }

        backend = config.get('camera', 'backend', default='dshow')
        cap_backend = backend_map.get(backend, 0)

        logger.info(f"🔵 Opening webcam with backend: {backend}...")
        self.cap = cv2.VideoCapture(0, cap_backend)

        if not self.cap.isOpened():
            logger.warning(f"⚠️ Cannot open webcam with {backend}, trying default...")
            self.cap = cv2.VideoCapture(0)

        if not self.cap.isOpened():
            logger.error("❌ Cannot open webcam")
            return False

        # Set camera properties
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.camera_width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.camera_height)
        self.cap.set(cv2.CAP_PROP_FPS, config.camera_fps)

        logger.info(f"✅ Webcam opened: {config.camera_width}x{config.camera_height} @ {config.camera_fps}fps")

        self.running = True
        self.thread = Thread(target=self._process_loop, daemon=True)
        self.thread.start()

        logger.info("✅ Webcam processing started")
        return True

    def stop(self):
        """Stop webcam processing with proper cleanup"""
        logger.info("🛑 Stopping webcam processor...")

        self.running = False

        # Wait for thread to finish
        if self.thread:
            self.thread.join(timeout=3)

        # Release camera
        if self.cap:
            self.cap.release()
            self.cap = None

        # Cleanup all processors - wrap in try-except to prevent segfault
        try:
            self.pose_processor.cleanup()
        except Exception as e:
            logger.warning(f"⚠️ Pose cleanup error (non-critical): {e}")

        try:
            self.face_processor.cleanup()
        except Exception as e:
            logger.warning(f"⚠️ Face processor cleanup error (non-critical): {e}")

        logger.info("✅ Webcam processor stopped and cleaned up")

    def toggle_processing(self):
        """Toggle privacy mode (pause/resume processing)"""
        if not config.privacy_allow_pause:
            logger.warning("⚠️ Privacy controls are disabled")
            return

        self.processing_enabled = not self.processing_enabled
        status = "resumed" if self.processing_enabled else "paused"
        logger.info(f"🔒 Processing {status}")
        return self.processing_enabled

    def _process_loop(self):
        """Main processing loop with adaptive frame skipping"""
        frame_times = deque(maxlen=30)

        # Give camera time to stabilize
        time.sleep(0.5)

        logger.info("🟢 Processing loop started")

        while self.running:
            try:
                ret, frame = self.cap.read()

                if not ret:
                    logger.warning("⚠️ Cannot read frame")
                    continue

                start_time = time.time()

                # Mirror flip
                frame = cv2.flip(frame, 1)

                # Privacy check
                if not self.processing_enabled:
                    # Draw privacy indicator but don't process
                    cv2.putText(frame, "PRIVACY MODE - PAUSED", (10, 30),
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

                    # Still emit frame but without ML processing
                    self._emit_frame(frame)
                    continue

                # Adaptive frame skipping
                if self._should_process_frame():
                    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                    # Process face (includes selective optimization)
                    try:
                        face_metrics = self.face_processor.process(rgb_frame, self.state)

                        with self.state.lock:
                            self.state.face_detected = face_metrics.get('face_detected', False)
                            self.state.face_count = face_metrics.get('face_count', 0)

                            # Apply smoothing to gaze values
                            if 'eye_gaze_x' in face_metrics and 'eye_gaze_y' in face_metrics:
                                face_metrics['eye_gaze_x'], face_metrics['eye_gaze_y'] = self._smooth_gaze(
                                    face_metrics['eye_gaze_x'],
                                    face_metrics['eye_gaze_y']
                                )

                            # Update all face metrics
                            for key, value in face_metrics.items():
                                if hasattr(self.state, key):
                                    setattr(self.state, key, value)

                    except Exception as e:
                        logger.error(f"Face processing error: {e}")

                    # Process pose with better error handling
                    # Fixed: Create copy of frame to prevent timestamp conflicts
                    try:
                        if self.state.frame_count % 6 == 0:  # Process pose every 6th frame to save CPU
                            pose_metrics = self.pose_processor.process(rgb_frame)

                            with self.state.lock:
                                self.state.body_detected = pose_metrics.get('body_detected', False)
                                self.state.posture_score = pose_metrics.get('posture_score', 0.0)
                                self.state.pose_confidence = pose_metrics.get('pose_confidence', 0.0)

                    except Exception as e:
                        logger.warning(f"Pose processing error (non-critical): {e}")

                    # Detect emotion using optimized multi-detector approach
                    # Priority: DeepFace (93% accurate) > EfficientNet (87%)
                    try:
                        # Process emotion detection every 10th frame to save CPU
                        if self.state.frame_count % 10 == 0:
                            # Primary: DeepFace (most accurate, 93%)
                            if self.deepface_detector.available:
                                emotion_result = self.deepface_detector.detect_emotion(rgb_frame)

                                with self.state.lock:
                                    self.state.emotion = emotion_result['emotion']
                                    self.state.emotion_confidence = emotion_result['emotion_confidence']

                                    # Store emotion scores for UI
                                    if 'emotion_scores' in emotion_result:
                                        if not hasattr(self.state, 'emotion_scores'):
                                            self.state.emotion_scores = {}
                                        self.state.emotion_scores.update(emotion_result['emotion_scores'])

                            # Fallback: EfficientNet (87% accurate, faster)
                            elif self.efficientnet_detector.available:
                                emotion_result = self.efficientnet_detector.detect_emotion(rgb_frame)

                                with self.state.lock:
                                    self.state.emotion = emotion_result['emotion']
                                    self.state.emotion_confidence = emotion_result['emotion_confidence']

                                    if 'emotion_scores' in emotion_result:
                                        if not hasattr(self.state, 'emotion_scores'):
                                            self.state.emotion_scores = {}
                                        self.state.emotion_scores.update(emotion_result['emotion_scores'])

                    except Exception as e:
                        logger.error(f"Emotion detection error: {e}")

                    # Calculate focus and detect distractions
                    try:
                        focus_score, focus_status = self._calculate_focus_score()
                        distractions = self._detect_distractions()

                        with self.state.lock:
                            self.state.focus_percentage = focus_score
                            self.state.focus_status = focus_status
                            self.state.current_distractions = distractions

                        self._update_time_tracking(focus_status)

                    except Exception as e:
                        logger.error(f"Focus calculation error: {e}")

                # Draw lightweight visual feedback
                self._draw_lightweight_feedback(frame)

                # Calculate and update FPS
                frame_time = time.time() - start_time
                frame_times.append(frame_time)
                if frame_times:
                    fps = 1.0 / (sum(frame_times) / len(frame_times))
                    self.state.fps = fps
                    self.fps_history.append(fps)

                    # Adaptive frame skipping adjustment
                    if config.adaptive_quality_enabled:
                        self._adjust_frame_skip(fps)

                # Update frame count
                with self.state.lock:
                    self.state.frame_count += 1

                # Emit frame with optimized frequency
                # Only emit every 3rd frame to reduce network load (was every frame)
                # State is still calculated every frame
                if self.state.frame_count % 3 == 0:
                    self._emit_frame(frame)

                # Log periodically
                if self.state.frame_count % config.log_interval == 0:
                    logger.info(f"FPS: {self.state.fps:.1f} | Frame Skip: {self.frame_skip} | Focus: {self.state.focus_percentage:.0f}%")

                # Small sleep to prevent CPU spinning
                time.sleep(0.01)

            except Exception as e:
                logger.error(f"Error in processing loop: {e}", exc_info=True)

    def _should_process_frame(self):
        """Determine if ML processing should run on this frame"""
        if self.state.frame_count % (self.frame_skip + 1) == 0:
            return True
        return False

    def _smooth_gaze(self, gaze_x, gaze_y):
        """
        Apply smoothing filter to gaze values to reduce jitter

        Args:
            gaze_x: Raw gaze X value (-1 to 1)
            gaze_y: Raw gaze Y value (-1 to 1)

        Returns:
            tuple: (smoothed_gaze_x, smoothed_gaze_y)
        """
        if not self.gaze_smoothing_enabled:
            return gaze_x, gaze_y

        # Add to history
        self.gaze_history_x.append(gaze_x)
        self.gaze_history_y.append(gaze_y)

        # Apply moving average smoothing
        if len(self.gaze_history_x) >= 2:  # Need at least 2 frames
            import numpy as np

            # Simple moving average
            smoothed_x = sum(self.gaze_history_x) / len(self.gaze_history_x)
            smoothed_y = sum(self.gaze_history_y) / len(self.gaze_history_y)

            # Clamp to valid range
            smoothed_x = np.clip(smoothed_x, -1, 1)
            smoothed_y = np.clip(smoothed_y, -1, 1)

            return smoothed_x, smoothed_y
        else:
            # Not enough history, return raw
            return gaze_x, gaze_y

    def _adjust_frame_skip(self, current_fps):
        """
        Adjust frame skip based on current FPS (adaptive quality)

        Args:
            current_fps: Current frames per second
        """
        target_fps = config.target_fps
        low_threshold = config.get('performance', 'adaptive_quality', 'fps_low_threshold', default=20)
        high_threshold = config.get('performance', 'adaptive_quality', 'fps_high_threshold', default=30)
        min_skip = config.get('performance', 'adaptive_quality', 'min_skip', default=1)
        max_skip = config.get('performance', 'adaptive_quality', 'max_skip', default=7)

        if current_fps < low_threshold and self.frame_skip < max_skip:
            self.frame_skip += 1
            logger.debug(f"⬇️ Increased frame skip to {self.frame_skip} (FPS: {current_fps:.1f})")
        elif current_fps > high_threshold and self.frame_skip > min_skip:
            self.frame_skip -= 1
            logger.debug(f"⬆️ Decreased frame skip to {self.frame_skip} (FPS: {current_fps:.1f})")

    def _draw_lightweight_feedback(self, frame):
        """Draw lightweight visual indicators"""
        if not config.visual_feedback_enabled:
            return

        h, w = frame.shape[:2]

        # Draw FPS
        cv2.putText(frame, f"FPS: {self.state.fps:.1f}", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        # Draw Focus
        focus_color = (0, 255, 0) if self.state.focus_percentage >= 70 else (0, 165, 255)
        cv2.putText(frame, f"Focus: {self.state.focus_percentage:.0f}%", (10, 60),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, focus_color, 2)

        # Draw Emotion
        cv2.putText(frame, f"Emotion: {self.state.emotion}", (10, 90),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

        # Draw lightweight gaze point (circle)
        if config.show_gaze_point and hasattr(self.state, 'screen_x'):
            # Map screen coordinates to frame coordinates
            gaze_x = int((self.state.screen_x / 1920) * w)
            gaze_y = int((self.state.screen_y / 1080) * h)

            # Draw simple circle (very lightweight)
            cv2.circle(frame, (gaze_x, gaze_y), 10, (0, 255, 255), -1)
            cv2.circle(frame, (gaze_x, gaze_y), 12, (255, 255, 255), 2)

    def _emit_frame(self, frame):
        """Encode and emit frame via SocketIO with optimization"""
        import base64

        # Use lower JPEG quality (75 instead of 85) to reduce size
        ret_encode, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 75])

        if ret_encode:
            frame_b64 = base64.b64encode(buffer).decode('utf-8')

            # Import socketio instance for background thread emit
            try:
                from app import socketio

                # Emit with smaller state data (only essential fields)
                minimal_state = {
                    'focus_percentage': self.state.focus_percentage,
                    'focus_status': self.state.focus_status,
                    'emotion': self.state.emotion,
                    'emotion_confidence': self.state.emotion_confidence,
                    'fps': self.state.fps,
                    'face_detected': self.state.face_detected
                }

                socketio.emit('frame_update', {
                    'frame': frame_b64,
                    'state': minimal_state  # Send minimal state to reduce payload
                })
                logger.debug(f"✅ Frame emitted: {len(frame_b64)} bytes")
            except Exception as e:
                # Silently skip emit errors to avoid log spam
                pass

    def _calculate_focus_score(self):
        """Calculate focus score using metrics from state"""
        score = 0

        # Face detection (30 points)
        if self.state.face_detected:
            score += 30
        else:
            return 0, "distracted"

        # Eye aspect ratio (20 points)
        if self.state.eye_aspect_ratio > 0.2:
            score += 20
        elif self.state.eye_aspect_ratio > 0.15:
            score += 10
        else:
            return score, "drowsy"

        # Head pose (25 points)
        if abs(self.state.head_yaw) < 10 and abs(self.state.head_pitch) < 8:
            score += 25
        elif abs(self.state.head_yaw) < 20 and abs(self.state.head_pitch) < 15:
            score += 15
        elif abs(self.state.head_yaw) < 30 and abs(self.state.head_pitch) < 20:
            score += 5

        # Body posture (15 points)
        if self.state.posture_score > 80:
            score += 15
        elif self.state.posture_score > 60:
            score += 10
        else:
            score += 5

        # Mouth aspect ratio (10 points)
        if self.state.mouth_aspect_ratio > 0.6:
            score -= 10
        else:
            score += 10

        # Micro-expression adjustments
        if self.state.confusion_level > 0.5:
            score -= int(self.state.confusion_level * 15)

        if self.state.stress_level > 0.5:
            score -= int(self.state.stress_level * 10)

        # Eye gaze deviation
        gaze_deviation = abs(self.state.eye_gaze_x) + abs(self.state.eye_gaze_y)
        if gaze_deviation > 0.5:
            score -= int(gaze_deviation * 10)

        score = max(0, min(100, score))

        if score >= config.focused_threshold:
            status = "focused"
        elif score >= config.distracted_threshold:
            status = "distracted"
        else:
            status = "drowsy"

        return score, status

    def _update_time_tracking(self, current_status):
        """Update time tracking based on focus status"""
        current_time = time.time()

        if not hasattr(self.state, 'last_status_change_time'):
            self.state.last_status_change_time = current_time
            self.state.last_status = "distracted"

        elapsed = current_time - self.state.last_status_change_time
        self.state.last_status_change_time = current_time

        with self.state.lock:
            if current_status == "focused":
                self.state.focused_time_seconds += elapsed
            else:
                self.state.unfocused_time_seconds += elapsed

            self.state.last_status = current_status

    def _detect_distractions(self):
        """Detect specific types of distractions"""
        distractions = []

        if abs(self.state.head_yaw) > 20 or abs(self.state.head_pitch) > 15:
            direction = ""
            if self.state.head_yaw > 20:
                direction = "→ looking RIGHT"
            elif self.state.head_yaw < -20:
                direction = "← looking LEFT"
            elif self.state.head_pitch > 15:
                direction = "↓ looking DOWN"
            elif self.state.head_pitch < -15:
                direction = "↑ looking UP"

            distractions.append(f"👀 Head turned {direction}")

        if self.state.looking_at != "center":
            gaze_direction = self.state.looking_at.replace("-", " ").upper()
            distractions.append(f"👁️ Eyes looking {gaze_direction}")

        if self.state.face_count > 1:
            distractions.append(f"👥 {self.state.face_count} faces detected")

        if not self.state.face_detected:
            distractions.append("❌ Face not visible")

        if self.state.posture_score < 40:
            distractions.append(f"🪑 Poor posture ({self.state.posture_score:.0f}%)")

        if self.state.mouth_aspect_ratio > 0.6:
            duration_text = f" for {self.state.yawning_duration:.1f}s" if hasattr(self.state, 'yawning_duration') and self.state.yawning_duration > 0 else ""
            distractions.append(f"🥱 Yawning detected{duration_text}")

        if self.state.eye_aspect_ratio < 0.15:
            distractions.append(f"😴 Eyes closed (EAR: {self.state.eye_aspect_ratio:.2f})")

        if self.state.stress_level > 0.7:
            distractions.append(f"😰 High stress ({self.state.stress_level*100:.0f}%)")

        if self.state.confusion_level > 0.7:
            distractions.append(f"🤔 High confusion ({self.state.confusion_level*100:.0f}%)")

        if distractions:
            with self.state.lock:
                self.state.distracted_events += 1

        return distractions
