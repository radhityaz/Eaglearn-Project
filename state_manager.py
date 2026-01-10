"""
State Manager
Centralized state management to ensure singleton behavior
"""

import logging
from threading import Lock
from collections import deque

logger = logging.getLogger(__name__)


class SessionState:
    """Main state container for the application"""

    def __init__(self):
        self.lock = Lock()

        # Session info
        self.session_id = None
        self.session_start_time = None
        self.is_running = False

        # Focus metrics (0-100%)
        self.focus_percentage = 0.0
        self.focus_status = "distracted"  # "focused" | "distracted" | "drowsy"
        self.focus_history = deque(maxlen=30)  # Last 30 seconds
        self.current_distractions = []  # List of current distraction strings
        self.mental_effort = (
            0.0  # 0-100, indicates cognitive load and concentration intensity
        )

        # Head pose metrics
        self.head_yaw = 0.0  # Horizontal rotation (-90 to 90)
        self.head_pitch = 0.0  # Vertical rotation (-90 to 90)
        self.head_roll = 0.0  # Tilt (-90 to 90)

        # Facial metrics
        self.eye_aspect_ratio = 0.0  # 0-1, lower = eyes closed
        self.mouth_aspect_ratio = 0.0  # 0-1
        self.emotion = "neutral"  # happy, sad, angry, surprised, neutral
        self.emotion_confidence = 0.0  # 0-1
        self.emotion_scores = {}  # All emotion scores from DeepFace

        # Micro-expressions (NEW)
        self.eyebrow_raise = 0.0  # 0-1, higher = raised eyebrows
        self.eyebrow_furrow = 0.0  # 0-1, higher = furrowed (concentrating)
        self.blink_rate = 0  # Blinks per minute
        self.last_blink_time = 0
        self.blink_count = 0
        self.lip_tension = 0.0  # 0-1, higher = tense/stressed
        self.frown_degree = 0.0  # Negative to positive, positive = sad
        self.eye_gaze_x = 0.0  # -1 to 1, left to right
        self.eye_gaze_y = 0.0  # -1 to 1, up to down
        self.face_scale = 0.0
        self.confusion_level = 0.0  # 0-1, derived from micro-expressions
        self.stress_level = 0.0  # 0-1, derived from micro-expressions
        self.yawning_duration = 0  # Seconds of continuous yawning
        self.last_yawn_time = 0
        self.is_blinking = False
        self.face_mesh_processed = False
        self.last_face_mesh_time = 0.0
        self.sleepiness_score = 0.0

        # Eye Tracking (NEW)
        self.looking_at = "center"  # center, left, right, top, bottom, top-left, top-right, bottom-left, bottom-right
        self.attention_score = 100  # 0-100, based on how centered gaze is
        self.gaze_history = []  # Last 10 gaze positions
        self.off_screen_time = 0  # Seconds looking away
        self.screen_x = 0  # Estimated screen X coordinate (0-1920 or user's resolution)
        self.screen_y = 0  # Estimated screen Y coordinate (0-1080 or user's resolution)

        # Body pose metrics
        self.pose_confidence = 0.0  # 0-1
        self.posture_score = 0.0  # 0-100, higher = better
        self.body_detected = False

        # Webcam metrics
        self.face_detected = False
        self.face_count = 0
        self.frame_count = 0
        self.fps = 0.0
        self.smartphone_detected = False
        self.smartphone_confidence = 0.0
        self.night_mode = False
        self.frame_brightness = 0.0
        self.vlm_status = "disabled"
        self.vlm_ready = False
        self.vlm_last_error = None
        self.quality_preset = "balanced"

        # Time tracking
        self.focused_time_seconds = 0
        self.unfocused_time_seconds = 0
        self.distracted_events = 0

        # ENHANCED: Unfocus analytics (GazeRecorder-style)
        self.unfocus_intervals = []  # List of {'start': float, 'end': float, 'duration': float, 'reason': str}
        self.unfocus_count = 0  # Total number of unfocus events
        self.first_unfocus_time = None  # Timestamp of first unfocus event
        self.last_unfocus_time = None  # Timestamp of last unfocus event
        self.current_unfocus_start = (
            None  # Start time of current unfocus event (if active)
        )
        self.current_focus_start = (
            None  # Start time of current focus period (for tracking focus duration)
        )

        # Calibration state
        self.calibration_applied = False
        self.calibration_in_progress = False
        self.calibration_gaze_offset_x = 0.0
        self.calibration_gaze_offset_y = 0.0
        self.calibration_scale_factor = 1.0
        self.calibration_head_yaw = 0.0
        self.calibration_head_pitch = 0.0
        self.calibration_head_compensation_yaw_gain = None
        self.calibration_head_compensation_pitch_gain = None
        self.calibration_face_scale = None
        self.calibration_screen_width = None
        self.calibration_screen_height = None
        self.calibration_screen_mapping_x = None
        self.calibration_screen_mapping_y = None

        # Last update timestamp for time tracking
        self.last_tracking_update = None
        self.last_focus_status = None
        self.rule_metrics = {}

    def _format_time(self, seconds):
        """Format seconds to HH:MM:SS"""
        seconds = int(seconds)
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def to_dict(self):
        """Convert state to dictionary for transmission"""

        def to_builtin(value):
            try:
                if hasattr(value, "item") and callable(value.item):
                    return value.item()
            except Exception:
                pass
            return value

        def safe_scores(scores):
            if not isinstance(scores, dict):
                return {}
            out = {}
            for k, v in scores.items():
                v = to_builtin(v)
                if isinstance(v, (int, float)):
                    out[str(k)] = float(v)
                else:
                    try:
                        out[str(k)] = float(v)
                    except Exception:
                        continue
            return out

        with self.lock:
            # Debug log for zero stats issue
            if self.frame_count % 100 == 0 and self.frame_count > 0:
                logger.info(
                    f"State dump - Frame: {self.frame_count}, Focus: {self.focus_percentage}%, FPS: {self.fps}"
                )

            return {
                "session_id": self.session_id,
                "session_start_time": self.session_start_time,
                "is_running": self.is_running,
                "focus_percentage": round(self.focus_percentage, 2),
                "focus_status": self.focus_status,
                "current_distractions": self.current_distractions,
                "mental_effort": round(self.mental_effort, 2),
                "head_pose": {
                    "yaw": round(self.head_yaw, 2),
                    "pitch": round(self.head_pitch, 2),
                    "roll": round(self.head_roll, 2),
                },
                "facial_metrics": {
                    "eye_aspect_ratio": round(self.eye_aspect_ratio, 3),
                    "mouth_aspect_ratio": round(self.mouth_aspect_ratio, 3),
                    "emotion": self.emotion,
                    "emotion_confidence": round(self.emotion_confidence, 3),
                    "emotion_scores": safe_scores(self.emotion_scores),
                    "micro_expressions": {
                        "eyebrow_raise": round(self.eyebrow_raise, 3),
                        "eyebrow_furrow": round(self.eyebrow_furrow, 3),
                        "blink_rate": self.blink_rate,
                        "lip_tension": round(self.lip_tension, 3),
                        "frown_degree": round(self.frown_degree, 3),
                        "eye_gaze_x": round(self.eye_gaze_x, 3),
                        "eye_gaze_y": round(self.eye_gaze_y, 3),
                        "face_scale": round(float(self.face_scale), 5),
                        "confusion_level": round(self.confusion_level, 3),
                        "stress_level": round(self.stress_level, 3),
                        "sleepiness_score": round(float(self.sleepiness_score), 2),
                    },
                },
                "body_pose": {
                    "confidence": round(float(self.pose_confidence), 3),
                    "posture_score": round(float(self.posture_score), 2),
                    "body_detected": self.body_detected,
                },
                "webcam": {
                    "face_detected": self.face_detected,
                    "face_count": self.face_count,
                    "frame_count": self.frame_count,
                    "fps": round(self.fps, 2),
                    "quality_preset": self.quality_preset,
                },
                "vision": {
                    "smartphone_detected": bool(self.smartphone_detected),
                    "smartphone_confidence": round(
                        float(self.smartphone_confidence), 3
                    ),
                    "night_mode": bool(self.night_mode),
                    "frame_brightness": round(float(self.frame_brightness), 3),
                },
                "vlm": {
                    "status": self.vlm_status,
                    "ready": bool(self.vlm_ready),
                    "last_error": self.vlm_last_error,
                    "user_enabled": bool(getattr(self, "vlm_user_enabled", False)),
                },
                "eye_tracking": {
                    "looking_at": self.looking_at,
                    "attention_score": round(self.attention_score, 2),
                    "off_screen_time": round(self.off_screen_time, 2),
                    "screen_x": self.screen_x,
                    "screen_y": self.screen_y,
                },
                "time_tracking": {
                    "focused_seconds": int(self.focused_time_seconds),
                    "unfocused_seconds": int(self.unfocused_time_seconds),
                    "focused_time_formatted": self._format_time(
                        self.focused_time_seconds
                    ),
                    "unfocused_time_formatted": self._format_time(
                        self.unfocused_time_seconds
                    ),
                    "total_time_formatted": self._format_time(
                        self.focused_time_seconds + self.unfocused_time_seconds
                    ),
                    "distracted_events": self.distracted_events,
                    "focus_ratio": round(
                        self.focused_time_seconds
                        / (self.focused_time_seconds + self.unfocused_time_seconds + 1),
                        3,
                    ),
                },
                # ENHANCED: Unfocus analytics (GazeRecorder-style)
                "unfocus_analytics": {
                    "unfocus_count": self.unfocus_count,
                    "first_unfocus_time": self.first_unfocus_time,
                    "last_unfocus_time": self.last_unfocus_time,
                    "intervals_count": len(self.unfocus_intervals),
                    "recent_intervals": self.unfocus_intervals[-5:]
                    if len(self.unfocus_intervals) > 5
                    else self.unfocus_intervals,
                },
                "rule_metrics": self.rule_metrics
                if isinstance(self.rule_metrics, dict)
                else {},
            }


# Create a global singleton instance
state = SessionState()
