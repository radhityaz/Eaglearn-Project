"""
Eaglearn - Simplified Flask Application
Focus monitoring with clear state management
"""

import os
import json
import logging
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room
import numpy as np
import cv2
import mediapipe as mp
from threading import Thread, Lock
import base64
from collections import deque

# Import improved components
from config_loader import config
from improved_webcam_processor import ImprovedWebcamProcessor
from mediapipe_processors.deepface_emotion_detector import DeepFaceEmotionDetector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
CORS(app)
# IMPORTANT: Use threading mode explicitly to handle background threads properly
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading', logger=False, engineio_logger=False)

# ============================================================================
# STATE MANAGEMENT - Clear, quantifiable metrics
# ============================================================================

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

        # Head pose metrics
        self.head_yaw = 0.0      # Horizontal rotation (-90 to 90)
        self.head_pitch = 0.0    # Vertical rotation (-90 to 90)
        self.head_roll = 0.0     # Tilt (-90 to 90)

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
        self.confusion_level = 0.0  # 0-1, derived from micro-expressions
        self.stress_level = 0.0  # 0-1, derived from micro-expressions
        self.yawning_duration = 0  # Seconds of continuous yawning
        self.last_yawn_time = 0

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

        # Time tracking
        self.focused_time_seconds = 0
        self.unfocused_time_seconds = 0
        self.distracted_events = 0

        # ENHANCED: Unfocus analytics (GazeRecorder-style)
        self.unfocus_intervals = []  # List of {'start': float, 'end': float, 'duration': float, 'reason': str}
        self.unfocus_count = 0  # Total number of unfocus events
        self.first_unfocus_time = None  # Timestamp of first unfocus event
        self.last_unfocus_time = None  # Timestamp of last unfocus event
        self.current_unfocus_start = None  # Start time of current unfocus event (if active)
        self.current_focus_start = None  # Start time of current focus period (for tracking focus duration)

    def _format_time(self, seconds):
        """Format seconds to HH:MM:SS"""
        seconds = int(seconds)
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def to_dict(self):
        """Convert state to dictionary for transmission"""
        with self.lock:
            return {
                'session_id': self.session_id,
                'session_start_time': self.session_start_time,
                'is_running': self.is_running,
                'focus_percentage': round(self.focus_percentage, 2),
                'focus_status': self.focus_status,
                'current_distractions': self.current_distractions,
                'head_pose': {
                    'yaw': round(self.head_yaw, 2),
                    'pitch': round(self.head_pitch, 2),
                    'roll': round(self.head_roll, 2),
                },
                'facial_metrics': {
                    'eye_aspect_ratio': round(self.eye_aspect_ratio, 3),
                    'mouth_aspect_ratio': round(self.mouth_aspect_ratio, 3),
                    'emotion': self.emotion,
                    'emotion_confidence': round(self.emotion_confidence, 3),
                    'emotion_scores': self.emotion_scores,  # All DeepFace scores
                    'micro_expressions': {
                        'eyebrow_raise': round(self.eyebrow_raise, 3),
                        'eyebrow_furrow': round(self.eyebrow_furrow, 3),
                        'blink_rate': self.blink_rate,
                        'lip_tension': round(self.lip_tension, 3),
                        'frown_degree': round(self.frown_degree, 3),
                        'eye_gaze_x': round(self.eye_gaze_x, 3),
                        'eye_gaze_y': round(self.eye_gaze_y, 3),
                        'confusion_level': round(self.confusion_level, 3),
                        'stress_level': round(self.stress_level, 3),
                    },
                },
                'body_pose': {
                    'confidence': round(self.pose_confidence, 3),
                    'posture_score': round(self.posture_score, 2),
                    'body_detected': self.body_detected,
                },
                'webcam': {
                    'face_detected': self.face_detected,
                    'face_count': self.face_count,
                    'frame_count': self.frame_count,
                    'fps': round(self.fps, 2),
                },
                'eye_tracking': {
                    'looking_at': self.looking_at,
                    'attention_score': round(self.attention_score, 2),
                    'off_screen_time': round(self.off_screen_time, 2),
                    'screen_x': self.screen_x,
                    'screen_y': self.screen_y,
                },
                'time_tracking': {
                    'focused_seconds': int(self.focused_time_seconds),
                    'unfocused_seconds': int(self.unfocused_time_seconds),
                    'focused_time_formatted': self._format_time(self.focused_time_seconds),
                    'unfocused_time_formatted': self._format_time(self.unfocused_time_seconds),
                    'total_time_formatted': self._format_time(self.focused_time_seconds + self.unfocused_time_seconds),
                    'distracted_events': self.distracted_events,
                    'focus_ratio': round(
                        self.focused_time_seconds / (self.focused_time_seconds + self.unfocused_time_seconds + 1),
                        3
                    ),
                },
                # ENHANCED: Unfocus analytics (GazeRecorder-style)
                'unfocus_analytics': {
                    'unfocus_count': self.unfocus_count,
                    'first_unfocus_time': self.first_unfocus_time,
                    'last_unfocus_time': self.last_unfocus_time,
                    'intervals_count': len(self.unfocus_intervals),
                    'recent_intervals': self.unfocus_intervals[-5:] if len(self.unfocus_intervals) > 5 else self.unfocus_intervals,
                },
            }

# Global state
state = SessionState()

# ============================================================================
# WEBCAM & COMPUTER VISION
# ============================================================================

# Import improved modular webcam processor
from improved_webcam_processor import ImprovedWebcamProcessor

# Global webcam processor instance with socketio reference
webcam = ImprovedWebcamProcessor(state, socketio=socketio)

# ============================================================================
# FLASK ROUTES
# ============================================================================

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')

@app.route('/api/state', methods=['GET'])
def get_state():
    """Get current application state"""
    return jsonify(state.to_dict())

@app.route('/api/session/start', methods=['POST'])
def start_session():
    """Start a monitoring session"""
    try:
        with state.lock:
            state.session_id = datetime.now().isoformat()
            state.session_start_time = state.session_id
            state.is_running = True
            state.focus_percentage = 50.0
            state.focused_time_seconds = 0
            state.unfocused_time_seconds = 0
            state.distracted_events = 0

        if webcam.start():
            return jsonify({
                'status': 'success',
                'session_id': state.session_id,
                'message': 'Session started'
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'message': 'Failed to start webcam'
            }), 500
    except Exception as e:
        logger.error(f"Error starting session: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/session/stop', methods=['POST'])
def stop_session():
    """Stop monitoring session"""
    try:
        webcam.stop()
        with state.lock:
            state.is_running = False

        return jsonify({
            'status': 'success',
            'message': 'Session stopped'
        }), 200
    except Exception as e:
        logger.error(f"Error stopping session: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/metrics', methods=['GET'])
def get_metrics():
    """Get current metrics"""
    return jsonify(state.to_dict())

@app.route('/api/analytics/unfocus', methods=['GET'])
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

        return jsonify({
            'status': 'success',
            'analytics': {
                'unfocus_count': analytics['unfocus_count'],
                'total_unfocus_time': analytics['total_duration'],
                'total_unfocus_time_formatted': format_duration(analytics['total_duration']),
                'avg_duration': round(analytics['avg_duration'], 1),
                'avg_duration_formatted': format_duration(analytics['avg_duration']),
                'min_duration': round(analytics['min_duration'], 1),
                'max_duration': round(analytics['max_duration'], 1),
                'time_to_first_unfocus': round(analytics['time_to_first_unfocus'], 1) if analytics['time_to_first_unfocus'] else None,
                'time_to_first_unfocus_formatted': format_duration(analytics['time_to_first_unfocus']),
                'unfocus_rate_per_hour': analytics['unfocus_rate'],
                'common_reasons': analytics['common_reasons'],
                'recent_intervals': [
                    {
                        'start': interval['start'],
                        'end': interval['end'],
                        'duration': round(interval['duration'], 1),
                        'reason': interval['reason']
                    }
                    for interval in analytics['recent_intervals']
                ]
            }
        }), 200
    except Exception as e:
        logger.error(f"Error calculating unfocus analytics: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/calibration/start', methods=['POST'])
def start_calibration():
    """Start calibration session"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default')

        webcam.calibration.start_calibration(user_id)

        return jsonify({
            'status': 'success',
            'message': f'Calibration started for user: {user_id}'
        }), 200
    except Exception as e:
        logger.error(f"Error starting calibration: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/calibration/add-point', methods=['POST'])
def add_calibration_point():
    """Add a calibration point"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'status': 'error', 'message': 'No data provided'}), 400

        webcam.calibration.add_calibration_point(
            screen_x=data.get('screen_x', 0),
            screen_y=data.get('screen_y', 0),
            gaze_x=data.get('gaze_x', 0),
            gaze_y=data.get('gaze_y', 0)
        )

        return jsonify({'status': 'success'}), 200
    except Exception as e:
        logger.error(f"Error adding calibration point: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/calibration/calculate', methods=['POST'])
def calculate_calibration():
    """Calculate and save calibration"""
    try:
        calibration_data = webcam.calibration.calculate_calibration()

        return jsonify({
            'status': 'success',
            'calibration': calibration_data
        }), 200
    except Exception as e:
        logger.error(f"Error calculating calibration: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/calibration/status', methods=['GET'])
def get_calibration_status():
    """Get calibration status"""
    try:
        status = webcam.calibration.get_calibration_status()
        return jsonify(status), 200
    except Exception as e:
        logger.error(f"Error getting calibration status: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/privacy/toggle', methods=['POST'])
def toggle_privacy():
    """Toggle privacy mode (pause/resume processing)"""
    try:
        is_enabled = webcam.toggle_processing()

        return jsonify({
            'status': 'success',
            'processing_enabled': is_enabled,
            'message': 'Processing resumed' if is_enabled else 'Processing paused'
        }), 200
    except Exception as e:
        logger.error(f"Error toggling privacy: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/config/reload', methods=['POST'])
def reload_config():
    """Reload configuration from file"""
    try:
        config.reload()

        return jsonify({
            'status': 'success',
            'message': 'Configuration reloaded'
        }), 200
    except Exception as e:
        logger.error(f"Error reloading config: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/config', methods=['GET'])
def get_config():
    """Get current configuration"""
    try:
        return jsonify(config.config), 200
    except Exception as e:
        logger.error(f"Error getting config: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ============================================================================
# WEBSOCKET EVENTS
# ============================================================================

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    logger.info(f"Client connected: {request.sid}")
    emit('connection_response', {'status': 'connected'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    logger.info(f"Client disconnected: {request.sid}")

@socketio.on('request_state')
def handle_state_request():
    """Handle state request"""
    emit('state_update', state.to_dict())

# ============================================================================
# CALIBRATION SOCKETIO HANDLERS
# ============================================================================

@socketio.on('calibration_start')
def handle_calibration_start():
    """Handle calibration start"""
    logger.info("🎯 Calibration started")
    emit('calibration_started', {'status': 'ok'})

@socketio.on('calibration_complete')
def handle_calibration_complete(data):
    """Handle calibration complete - save calibration data"""
    try:
        gaze_data = data.get('data', [])

        if not gaze_data or len(gaze_data) < 9:
            logger.warning("⚠️ Insufficient calibration data")
            emit('calibration_error', {'error': 'Insufficient data'})
            return

        # Calculate calibration offsets from collected data
        all_gaze_x = []
        all_gaze_y = []

        for point_data in gaze_data:
            samples = point_data.get('samples', [])
            if samples:
                avg_x = sum(s['x'] for s in samples) / len(samples)
                avg_y = sum(s['y'] for s in samples) / len(samples)
                all_gaze_x.append(avg_x)
                all_gaze_y.append(avg_y)

        if len(all_gaze_x) == 0:
            logger.warning("⚠️ No valid gaze samples in calibration data")
            emit('calibration_error', {'error': 'No valid samples'})
            return

        # Calculate calibration values
        gaze_offset_x = sum(all_gaze_x) / len(all_gaze_x)
        gaze_offset_y = sum(all_gaze_y) / len(all_gaze_y)

        # Calculate scale factor (how much gaze varies vs expected)
        gaze_variance = sum((x - gaze_offset_x)**2 for x in all_gaze_x) / len(all_gaze_x)
        scale_factor = max(0.5, min(2.0, 1.0 / (gaze_variance + 0.1)))

        calibration_data = {
            'user_id': 'default',
            'gaze_offset_x': gaze_offset_x,
            'gaze_offset_y': gaze_offset_y,
            'scale_factor': scale_factor,
            'timestamp': datetime.now().isoformat(),
            'sample_count': len(gaze_data)
        }

        # Save to file
        import json
        os.makedirs('calibration_data', exist_ok=True)
        with open('calibration_data/default.json', 'w') as f:
            json.dump(calibration_data, f, indent=2)

        # Load into calibration manager
        from calibration import calibration_manager
        calibration_manager.current_calibration = calibration_data

        logger.info(f"✅ Calibration saved: offset=({gaze_offset_x:.3f}, {gaze_offset_y:.3f}), scale={scale_factor:.3f}")
        emit('calibration_saved', {
            'status': 'success',
            'offset_x': gaze_offset_x,
            'offset_y': gaze_offset_y,
            'scale_factor': scale_factor
        })

    except Exception as e:
        logger.error(f"Calibration save error: {e}")
        emit('calibration_error', {'error': str(e)})

@socketio.on('calibration_cancel')
def handle_calibration_cancel():
    """Handle calibration cancel"""
    logger.info("❌ Calibration cancelled")
    emit('calibration_cancelled', {'status': 'cancelled'})

# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors"""
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors"""
    logger.error(f"Server error: {e}")
    return jsonify({'error': 'Internal server error'}), 500

# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    logger.info("Starting Eaglearn Flask Application...")
    logger.info(f"📊 Configuration loaded: GPU={config.gpu_acceleration_enabled}, Adaptive={config.adaptive_quality_enabled}")

    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)

    # Run with SocketIO
    socketio.run(
        app,
        host='0.0.0.0',
        port=int(os.getenv('PORT', 8080)),
        debug=os.getenv('DEBUG', 'False').lower() == 'true'
    )
