"""
Eaglearn - Simplified Flask Application
Focus monitoring with clear state management
"""

import os
import logging
import time
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import cv2
import sys
import re
import math
from logging.handlers import RotatingFileHandler

# Import singleton state from state manager
from state_manager import state

# Import improved components
from config_loader import config
from improved_webcam_processor import ImprovedWebcamProcessor

# Configure logging
base_dir = os.path.dirname(os.path.abspath(__file__))
log_dir = os.path.join(base_dir, "logs")
if not os.path.exists(log_dir):
    os.makedirs(log_dir)


class RedactFilter(logging.Filter):
    def __init__(self):
        super().__init__()
        self.patterns = [
            re.compile(r"(SECRET_KEY=)[^\\s]+", re.IGNORECASE),
            re.compile(r"(EAGLEARN_ENCRYPTION_KEY=)[^\\s]+", re.IGNORECASE),
            re.compile(
                r"(api[_-]?key['\"]?\\s*[:=]\\s*['\"]?)[^'\"\\s]+", re.IGNORECASE
            ),
            re.compile(r"(token['\"]?\\s*[:=]\\s*['\"]?)[^'\"\\s]+", re.IGNORECASE),
            re.compile(r"(password['\"]?\\s*[:=]\\s*['\"]?)[^'\"\\s]+", re.IGNORECASE),
            re.compile(r"(Bearer\\s+)[A-Za-z0-9\\-\\._~\\+/]+=*", re.IGNORECASE),
        ]

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            msg = record.getMessage()
            for p in self.patterns:
                msg = p.sub(r"\\1[REDACTED]", msg)
            record.msg = msg
            record.args = ()
        except Exception:
            pass
        return True


log_file = os.path.join(log_dir, f"app_{datetime.now().strftime('%Y%m%d')}.log")
file_handler = RotatingFileHandler(
    log_file, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
)
stream_handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
file_handler.setFormatter(formatter)
stream_handler.setFormatter(formatter)

redact_filter = RedactFilter()
file_handler.addFilter(redact_filter)
stream_handler.addFilter(redact_filter)

root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.handlers = [file_handler, stream_handler]
logger = logging.getLogger(__name__)


def api_error(error_code, message, status=500, extra=None):
    payload = {"status": "error", "error_code": error_code, "message": message}
    if isinstance(extra, dict):
        payload.update(extra)
    return jsonify(payload), status


# Initialize Flask app
app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv(
    "SECRET_KEY", "dev-secret-key-change-in-production"
)
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0
CORS(app)
# IMPORTANT: Use threading mode explicitly to handle background threads properly
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode="threading",
    logger=False,
    engineio_logger=False,
)

# ============================================================================
# STATE MANAGEMENT - Clear, quantifiable metrics
# ============================================================================

# State is managed via singleton in state_manager.py
# Use 'state' variable imported from state_manager

# ============================================================================
# WEBCAM & COMPUTER VISION
# ============================================================================

# Import improved modular webcam processor

# Global webcam processor instance with socketio reference
webcam = ImprovedWebcamProcessor(state, socketio=socketio)

# ============================================================================
# FLASK ROUTES
# ============================================================================


@app.route("/")
def index():
    """Main page"""
    return render_template("index.html")


@app.route("/api/state", methods=["GET"])
def get_state():
    """Get current application state"""
    return jsonify(state.to_dict())


@app.route("/api/environment", methods=["GET"])
def get_environment():
    try:
        env = {
            "python_executable": sys.executable,
            "gpu_enabled": bool(getattr(webcam, "gpu_enabled", False)),
            "vlm_import_available": bool(
                getattr(webcam, "vlm_service", None) is not None
            ),
        }

        try:
            import torch

            env["torch_version"] = getattr(torch, "__version__", None)
            env["torch_cuda_available"] = bool(torch.cuda.is_available())
            env["torch_cuda_device_count"] = (
                int(torch.cuda.device_count()) if torch.cuda.is_available() else 0
            )
        except Exception as e:
            env["torch_error"] = str(e)

        try:
            import tensorflow as tf

            gpus = tf.config.list_physical_devices("GPU")
            env["tf_version"] = getattr(tf, "__version__", None)
            env["tf_gpu_count"] = len(gpus)
        except Exception as e:
            env["tf_error"] = str(e)

        try:
            env["opencv_version"] = cv2.__version__
            env["opencv_cuda_device_count"] = (
                int(cv2.cuda.getCudaEnabledDeviceCount()) if hasattr(cv2, "cuda") else 0
            )
        except Exception as e:
            env["opencv_error"] = str(e)

        try:
            from improved_webcam_processor import VLM_AVAILABLE, VLM_IMPORT_ERROR

            env["vlm_available_flag"] = bool(VLM_AVAILABLE)
            env["vlm_import_error"] = VLM_IMPORT_ERROR
            vlm_service = getattr(webcam, "vlm_service", None)
            env["vlm_ready"] = bool(getattr(vlm_service, "is_ready", lambda: False)())
            env["vlm_status"] = (
                vlm_service.get_status()
                if vlm_service and hasattr(vlm_service, "get_status")
                else {"status": "disabled", "ready": False}
            )
        except Exception as e:
            env["vlm_flag_error"] = str(e)

        return jsonify(env), 200
    except Exception as e:
        logger.error(f"Error getting environment: {e}")
        return api_error("ENVIRONMENT_ERROR", str(e), 500)


@app.route("/api/session/start", methods=["POST"])
def start_session():
    """Start a monitoring session"""
    try:
        with state.lock:
            if state.is_running:
                return jsonify(
                    {
                        "status": "success",
                        "session_id": state.session_id,
                        "message": "Session already running",
                    }
                ), 200

            state.session_id = datetime.now().isoformat()
            state.session_start_time = time.time()
            state.is_running = True
            state.focus_percentage = 50.0
            state.focused_time_seconds = 0
            state.unfocused_time_seconds = 0
            state.distracted_events = 0

            state.unfocus_intervals = []
            state.unfocus_count = 0
            state.first_unfocus_time = None
            state.last_unfocus_time = None
            state.current_unfocus_start = None
            state.current_focus_start = time.time()

            if hasattr(state, "last_status"):
                state.last_status = "distracted"
            if hasattr(state, "last_update_time"):
                state.last_update_time = time.time()

        if webcam.start():
            return jsonify(
                {
                    "status": "success",
                    "session_id": state.session_id,
                    "message": "Session started",
                }
            ), 200
        else:
            with state.lock:
                state.is_running = False
            return api_error("WEBCAM_START_FAILED", "Failed to start webcam", 500)
    except Exception as e:
        logger.error(f"Error starting session: {e}")
        return api_error("SESSION_START_ERROR", str(e), 500)


@app.route("/api/session/stop", methods=["POST"])
def stop_session():
    """Stop monitoring session"""
    try:
        webcam.stop()
        with state.lock:
            state.is_running = False
            state.calibration_in_progress = False

        return jsonify({"status": "success", "message": "Session stopped"}), 200
    except Exception as e:
        logger.error(f"Error stopping session: {e}")
        return api_error("SESSION_STOP_ERROR", str(e), 500)


@app.route("/api/metrics", methods=["GET"])
def get_metrics():
    """Get current metrics"""
    return jsonify(state.to_dict())


@app.route("/api/quality", methods=["POST"])
def set_quality():
    try:
        data = request.get_json(silent=True) or {}
        preset = (data.get("preset") or "").strip().lower()
        if preset not in ("low", "balanced", "high"):
            return api_error(
                "BAD_REQUEST", "Invalid preset. Use low|balanced|high", 400
            )
        webcam.set_quality_preset(preset)
        return jsonify({"status": "success", "preset": preset}), 200
    except Exception as e:
        logger.error(f"Error setting quality: {e}")
        return api_error("QUALITY_SET_ERROR", str(e), 500)


@app.route("/api/ui/overlay", methods=["GET"])
def get_overlay_settings():
    try:
        overlay = (
            webcam.get_overlay_settings()
            if hasattr(webcam, "get_overlay_settings")
            else {}
        )
        return jsonify({"status": "success", "overlay": overlay}), 200
    except Exception as e:
        logger.error(f"Error getting overlay settings: {e}")
        return api_error("OVERLAY_GET_ERROR", str(e), 500)


@app.route("/api/ui/overlay", methods=["POST"])
def set_overlay_settings():
    try:
        data = request.get_json(silent=True) or {}
        show_face_mesh = data.get("show_face_mesh", None)
        face_mesh_alpha = data.get("face_mesh_alpha", None)
        face_mesh_smoothing = data.get("face_mesh_smoothing", None)
        face_mesh_mode = data.get("face_mesh_mode", None)
        face_mesh_stride = data.get("face_mesh_stride", None)

        if (
            show_face_mesh is None
            and isinstance(data.get("toggle"), bool)
            and data.get("toggle")
        ):
            current = (
                webcam.get_overlay_settings()
                if hasattr(webcam, "get_overlay_settings")
                else {}
            )
            show_face_mesh = not bool(current.get("show_face_mesh"))

        if hasattr(webcam, "set_overlay_settings"):
            webcam.set_overlay_settings(
                show_face_mesh=show_face_mesh,
                face_mesh_alpha=face_mesh_alpha,
                face_mesh_smoothing=face_mesh_smoothing,
                face_mesh_mode=face_mesh_mode,
                face_mesh_stride=face_mesh_stride,
            )

        overlay = (
            webcam.get_overlay_settings()
            if hasattr(webcam, "get_overlay_settings")
            else {}
        )
        return jsonify({"status": "success", "overlay": overlay}), 200
    except Exception as e:
        logger.error(f"Error setting overlay settings: {e}")
        return api_error("OVERLAY_SET_ERROR", str(e), 500)


@app.route("/api/vlm/settings", methods=["GET"])
def get_vlm_settings():
    try:
        if hasattr(webcam, "get_vlm_settings"):
            vlm = webcam.get_vlm_settings()
        else:
            vlm = {
                "user_enabled": False,
                "status": getattr(state, "vlm_status", "disabled"),
                "ready": bool(getattr(state, "vlm_ready", False)),
                "last_error": getattr(state, "vlm_last_error", None),
            }
        return jsonify({"status": "success", "vlm": vlm}), 200
    except Exception as e:
        logger.error(f"Error getting VLM settings: {e}")
        return api_error("VLM_GET_ERROR", str(e), 500)


@app.route("/api/vlm/settings", methods=["POST"])
def set_vlm_settings():
    try:
        data = request.get_json(silent=True) or {}
        enabled = data.get("enabled", None)
        toggle = bool(data.get("toggle", False))
        if toggle:
            current = (
                webcam.get_vlm_settings() if hasattr(webcam, "get_vlm_settings") else {}
            )
            enabled = not bool(current.get("user_enabled", False))
        if enabled is None:
            return api_error("BAD_REQUEST", "Missing enabled or toggle", 400)
        vlm = (
            webcam.set_vlm_enabled(bool(enabled))
            if hasattr(webcam, "set_vlm_enabled")
            else None
        )
        if not vlm:
            vlm = {
                "user_enabled": bool(enabled),
                "status": getattr(state, "vlm_status", "disabled"),
                "ready": bool(getattr(state, "vlm_ready", False)),
                "last_error": getattr(state, "vlm_last_error", None),
            }
        return jsonify({"status": "success", "vlm": vlm}), 200
    except Exception as e:
        logger.error(f"Error setting VLM settings: {e}")
        return api_error("VLM_SET_ERROR", str(e), 500)


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


@app.route("/api/logs/metrics/download", methods=["GET"])
def download_metrics_log():
    try:
        path = webcam.get_metrics_log_path()
        if not path or not os.path.exists(path):
            return api_error(
                "METRICS_LOG_NOT_AVAILABLE",
                "Metrics log belum tersedia. Mulai sesi dulu.",
                404,
            )

        filename = os.path.basename(path)
        return send_file(
            path,
            as_attachment=True,
            download_name=filename,
            mimetype="application/jsonl",
        )
    except Exception as e:
        logger.error(f"Error downloading metrics log: {e}")
        return api_error("METRICS_LOG_DOWNLOAD_ERROR", str(e), 500)


@app.route("/api/analytics/unfocus", methods=["GET"])
def get_unfocus_analytics():
    """
    ENHANCED: Get detailed unfocus analytics (GazeRecorder-style)

    Returns comprehensive unfocus statistics including:
    - Unfocus count, durations, rates
    - Time to first unfocus
    - Common unfocus reasons
    - Recent unfocus intervals
    """
    try:
        analytics = webcam.calculate_unfocus_analytics()

        # Format times for display
        def format_duration(seconds):
            if seconds is None:
                return "N/A"
            mins = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{mins}m {secs}s"

        return jsonify(
            {
                "status": "success",
                "analytics": {
                    "unfocus_count": analytics["unfocus_count"],
                    "total_unfocus_time": analytics["total_duration"],
                    "total_unfocus_time_formatted": format_duration(
                        analytics["total_duration"]
                    ),
                    "avg_duration": round(analytics["avg_duration"], 1),
                    "avg_duration_formatted": format_duration(
                        analytics["avg_duration"]
                    ),
                    "min_duration": round(analytics["min_duration"], 1),
                    "max_duration": round(analytics["max_duration"], 1),
                    "time_to_first_unfocus": round(
                        analytics["time_to_first_unfocus"], 1
                    )
                    if analytics["time_to_first_unfocus"]
                    else None,
                    "time_to_first_unfocus_formatted": format_duration(
                        analytics["time_to_first_unfocus"]
                    ),
                    "unfocus_rate_per_hour": analytics["unfocus_rate"],
                    "common_reasons": analytics["common_reasons"],
                    "recent_intervals": [
                        {
                            "start": interval["start"],
                            "end": interval["end"],
                            "duration": round(interval["duration"], 1),
                            "reason": interval["reason"],
                        }
                        for interval in analytics["recent_intervals"]
                    ],
                },
            }
        ), 200
    except Exception as e:
        logger.error(f"Error calculating unfocus analytics: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/calibration/start", methods=["POST"])
def start_calibration():
    """Start calibration session"""
    try:
        data = request.get_json() or {}
        user_id = data.get("user_id", "default")

        webcam.calibration.start_calibration(user_id)

        return jsonify(
            {"status": "success", "message": f"Calibration started for user: {user_id}"}
        ), 200
    except Exception as e:
        logger.error(f"Error starting calibration: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/calibration/add-point", methods=["POST"])
def add_calibration_point():
    """Add a calibration point"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "No data provided"}), 400

        webcam.calibration.add_calibration_point(
            screen_x=data.get("screen_x", 0),
            screen_y=data.get("screen_y", 0),
            gaze_x=data.get("gaze_x", 0),
            gaze_y=data.get("gaze_y", 0),
        )

        return jsonify({"status": "success"}), 200
    except Exception as e:
        logger.error(f"Error adding calibration point: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/calibration/calculate", methods=["POST"])
def calculate_calibration():
    """Calculate and save calibration"""
    try:
        calibration_data = webcam.calibration.calculate_calibration()

        return jsonify({"status": "success", "calibration": calibration_data}), 200
    except Exception as e:
        logger.error(f"Error calculating calibration: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/calibration/status", methods=["GET"])
def get_calibration_status():
    """Get calibration status"""
    try:
        status = webcam.calibration.get_calibration_status()
        return jsonify(status), 200
    except Exception as e:
        logger.error(f"Error getting calibration status: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/privacy/toggle", methods=["POST"])
def toggle_privacy():
    """Toggle privacy mode (pause/resume processing)"""
    try:
        is_enabled = webcam.toggle_processing()

        return jsonify(
            {
                "status": "success",
                "processing_enabled": is_enabled,
                "message": "Processing resumed" if is_enabled else "Processing paused",
            }
        ), 200
    except Exception as e:
        logger.error(f"Error toggling privacy: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/config/reload", methods=["POST"])
def reload_config():
    """Reload configuration from file"""
    try:
        config.reload()

        return jsonify({"status": "success", "message": "Configuration reloaded"}), 200
    except Exception as e:
        logger.error(f"Error reloading config: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/config", methods=["GET"])
def get_config():
    """Get current configuration"""
    try:
        return jsonify(config.config), 200
    except Exception as e:
        logger.error(f"Error getting config: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


# ============================================================================
# WEBSOCKET EVENTS
# ============================================================================


@socketio.on("connect")
def handle_connect():
    """Handle client connection"""
    logger.info(f"Client connected: {request.sid}")
    emit("connection_response", {"status": "connected"})


@socketio.on("disconnect")
def handle_disconnect():
    """Handle client disconnection"""
    logger.info(f"Client disconnected: {request.sid}")


@socketio.on("request_state")
def handle_state_request():
    """Handle state request"""
    emit("state_update", state.to_dict())


# ============================================================================
# CALIBRATION SOCKETIO HANDLERS
# ============================================================================


@socketio.on("calibration_start")
def handle_calibration_start():
    """Handle calibration start"""
    logger.info("Calibration started")

    # Ensure webcam is running
    if not webcam.start():
        logger.error("Failed to start webcam for calibration")
        emit("calibration_error", {"error": "Failed to start camera"})
        return

    with state.lock:
        state.calibration_applied = False
        state.calibration_in_progress = True
        state.calibration_gaze_offset_x = 0.0
        state.calibration_gaze_offset_y = 0.0
        state.calibration_scale_factor = 1.0
        state.calibration_head_yaw = 0.0
        state.calibration_head_pitch = 0.0
        state.calibration_screen_mapping_x = None
        state.calibration_screen_mapping_y = None
    emit("calibration_started", {"status": "ok"})


@socketio.on("calibration_complete")
def handle_calibration_complete(data):
    """Handle calibration complete - save calibration data"""
    try:
        gaze_data = data.get("data", [])
        head_samples = data.get("head_samples", []) or []

        if not gaze_data or len(gaze_data) < 9:
            logger.warning("[WARN] Insufficient calibration data")
            emit("calibration_error", {"error": "Insufficient data"})
            return

        user_id = "default"
        webcam.calibration.start_calibration(user_id)

        viewport = data.get("viewport", {})
        viewport_width = int(viewport.get("width", 1920) or 1920)
        viewport_height = int(viewport.get("height", 1080) or 1080)

        sample_count = 0
        for point_data in gaze_data:
            point = point_data.get("point", {})
            screen_x = point.get("screen_x")
            screen_y = point.get("screen_y")

            if screen_x is None or screen_y is None:
                x_pct = float(point.get("x", 50)) / 100.0
                y_pct = float(point.get("y", 50)) / 100.0
                screen_x = int(x_pct * viewport_width)
                screen_y = int(y_pct * viewport_height)

            samples = point_data.get("samples", [])
            for s in samples:
                gaze_x = s.get("x")
                gaze_y = s.get("y")
                if gaze_x is None or gaze_y is None:
                    continue
                webcam.calibration.add_calibration_point(
                    screen_x=int(screen_x),
                    screen_y=int(screen_y),
                    gaze_x=float(gaze_x),
                    gaze_y=float(gaze_y),
                )
                sample_count += 1

        if sample_count < 4:
            logger.warning(
                "[WARN] Calibration complete but insufficient gaze samples were captured"
            )
            emit(
                "calibration_error",
                {
                    "error": "Insufficient gaze samples captured. Ensure face is detected and keep eyes visible during calibration."
                },
            )
            return

        calibration_data = webcam.calibration.calculate_calibration()

        # Override screen size with actual viewport used for calibration
        calibration_data["screen_width"] = viewport_width
        calibration_data["screen_height"] = viewport_height

        def _safe_float(v):
            try:
                if v is None:
                    return None
                return float(v)
            except Exception:
                return None

        def _median(values):
            values = [v for v in values if isinstance(v, (int, float))]
            if not values:
                return None
            values = sorted(values)
            mid = len(values) // 2
            if len(values) % 2 == 1:
                return float(values[mid])
            return float((values[mid - 1] + values[mid]) / 2.0)

        def _linear_slope(x, y):
            if not x or not y or len(x) != len(y):
                return None, None
            if len(x) < 8:
                return None, None
            x_mean = sum(x) / len(x)
            y_mean = sum(y) / len(y)
            sxx = 0.0
            sxy = 0.0
            for xi, yi in zip(x, y):
                dx = xi - x_mean
                dy = yi - y_mean
                sxx += dx * dx
                sxy += dx * dy
            if sxx <= 1e-9:
                return None, None
            slope = sxy / sxx
            sse = 0.0
            sst = 0.0
            for xi, yi in zip(x, y):
                pred = y_mean + slope * (xi - x_mean)
                err = yi - pred
                sse += err * err
                dy = yi - y_mean
                sst += dy * dy
            r2 = None
            if sst > 1e-9:
                r2 = 1.0 - (sse / sst)
            return float(slope), (float(r2) if r2 is not None else None)

        baseline_yaw = None
        baseline_pitch = None
        baseline_face_scale = None
        if isinstance(head_samples, list) and head_samples:
            center = [s for s in head_samples if isinstance(s, dict) and s.get("step") == "center"]
            center_yaw_vals = []
            center_pitch_vals = []
            center_scale_vals = []
            for s in center:
                yv = _safe_float(s.get("head_yaw"))
                pv = _safe_float(s.get("head_pitch"))
                sv = _safe_float(s.get("face_scale"))
                if yv is not None:
                    center_yaw_vals.append(yv)
                if pv is not None:
                    center_pitch_vals.append(pv)
                if sv is not None:
                    center_scale_vals.append(sv)
            baseline_yaw = _median(center_yaw_vals)
            baseline_pitch = _median(center_pitch_vals)
            baseline_face_scale = _median(center_scale_vals)

        yaw_gain = None
        pitch_gain = None
        yaw_r2 = None
        pitch_r2 = None
        if baseline_yaw is not None and isinstance(head_samples, list) and head_samples:
            yaw_step = [s for s in head_samples if isinstance(s, dict) and s.get("step") == "yaw"]
            xs = []
            ys = []
            for s in yaw_step:
                hy = _safe_float(s.get("head_yaw"))
                gx = _safe_float(s.get("gaze_x"))
                if hy is None or gx is None:
                    continue
                xs.append(hy - baseline_yaw)
                ys.append(gx)
            slope, r2 = _linear_slope(xs, ys)
            if slope is not None:
                yaw_gain = float(max(-0.03, min(0.03, slope)))
                yaw_r2 = r2

        if baseline_pitch is not None and isinstance(head_samples, list) and head_samples:
            pitch_step = [s for s in head_samples if isinstance(s, dict) and s.get("step") == "pitch"]
            xs = []
            ys = []
            for s in pitch_step:
                hp = _safe_float(s.get("head_pitch"))
                gy = _safe_float(s.get("gaze_y"))
                if hp is None or gy is None:
                    continue
                xs.append(hp - baseline_pitch)
                ys.append(gy)
            slope, r2 = _linear_slope(xs, ys)
            if slope is not None:
                pitch_gain = float(max(-0.03, min(0.03, slope)))
                pitch_r2 = r2

        if baseline_yaw is not None:
            calibration_data["head_baseline_yaw"] = float(baseline_yaw)
        if baseline_pitch is not None:
            calibration_data["head_baseline_pitch"] = float(baseline_pitch)
        if yaw_gain is not None:
            calibration_data["head_compensation_yaw_gain"] = float(yaw_gain)
            if yaw_r2 is not None and not math.isnan(yaw_r2):
                calibration_data["head_compensation_yaw_r2"] = float(yaw_r2)
        if pitch_gain is not None:
            calibration_data["head_compensation_pitch_gain"] = float(pitch_gain)
            if pitch_r2 is not None and not math.isnan(pitch_r2):
                calibration_data["head_compensation_pitch_r2"] = float(pitch_r2)

        if baseline_face_scale is not None:
            calibration_data["face_scale_baseline"] = float(baseline_face_scale)

        # Ensure calibration is persisted even if auto_save is disabled
        webcam.calibration.save_calibration(user_id)

        with state.lock:
            state.calibration_applied = True
            state.calibration_in_progress = False
            state.calibration_gaze_offset_x = calibration_data.get("gaze_offset_x", 0.0)
            state.calibration_gaze_offset_y = calibration_data.get("gaze_offset_y", 0.0)
            state.calibration_scale_factor = calibration_data.get("scale_factor", 1.0)
            state.calibration_screen_width = calibration_data.get(
                "screen_width", viewport_width
            )
            state.calibration_screen_height = calibration_data.get(
                "screen_height", viewport_height
            )
            if baseline_yaw is not None:
                state.calibration_head_yaw = float(baseline_yaw)
            else:
                state.calibration_head_yaw = float(getattr(state, "head_yaw", 0.0) or 0.0)
            if baseline_pitch is not None:
                state.calibration_head_pitch = float(baseline_pitch)
            else:
                state.calibration_head_pitch = float(getattr(state, "head_pitch", 0.0) or 0.0)
            state.calibration_head_compensation_yaw_gain = calibration_data.get(
                "head_compensation_yaw_gain", None
            )
            state.calibration_head_compensation_pitch_gain = calibration_data.get(
                "head_compensation_pitch_gain", None
            )
            state.calibration_face_scale = calibration_data.get("face_scale_baseline", None)

            mapping = calibration_data.get("screen_mapping") or {}
            if "x" in mapping and "y" in mapping:
                state.calibration_screen_mapping_x = mapping.get("x")
                state.calibration_screen_mapping_y = mapping.get("y")

        logger.info(
            f"[OK] Calibration saved: offset=({calibration_data.get('gaze_offset_x', 0.0):.3f}, {calibration_data.get('gaze_offset_y', 0.0):.3f}), scale={calibration_data.get('scale_factor', 1.0):.3f}"
        )

        emit(
            "calibration_saved",
            {
                "status": "success",
                "offset_x": calibration_data.get("gaze_offset_x", 0.0),
                "offset_y": calibration_data.get("gaze_offset_y", 0.0),
                "scale_factor": calibration_data.get("scale_factor", 1.0),
                "head_yaw_gain": calibration_data.get("head_compensation_yaw_gain", None),
                "head_pitch_gain": calibration_data.get(
                    "head_compensation_pitch_gain", None
                ),
                "sample_count": sample_count,
            },
        )

    except Exception as e:
        logger.error(f"Calibration save error: {e}")
        emit("calibration_error", {"error": str(e)})


@socketio.on("calibration_cancel")
def handle_calibration_cancel():
    """Handle calibration cancel"""
    logger.info("[ERROR] Calibration cancelled")
    with state.lock:
        state.calibration_in_progress = False
    emit("calibration_cancelled", {"status": "cancelled"})


# ============================================================================
# ERROR HANDLERS
# ============================================================================


@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors"""
    return api_error("NOT_FOUND", "Not found", 404)


@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors"""
    logger.error(f"Server error: {e}")
    return api_error("INTERNAL_ERROR", "Internal server error", 500)


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    logger.info("Starting Eaglearn Flask Application...")
    logger.info(
        f"[CONFIG] Configuration loaded: GPU={config.gpu_acceleration_enabled}, Adaptive={config.adaptive_quality_enabled}"
    )

    # Create templates directory if it doesn't exist
    os.makedirs("templates", exist_ok=True)
    os.makedirs("static", exist_ok=True)

    # Run with SocketIO
    socketio.run(
        app,
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8080)),
        debug=os.getenv("DEBUG", "False").lower() == "true",
    )
