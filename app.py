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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

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
        self.focus_history = deque(maxlen=30)  # Last 30 seconds

        # Head pose metrics
        self.head_yaw = 0.0      # Horizontal rotation (-90 to 90)
        self.head_pitch = 0.0    # Vertical rotation (-90 to 90)
        self.head_roll = 0.0     # Tilt (-90 to 90)

        # Facial metrics
        self.eye_aspect_ratio = 0.0  # 0-1, lower = eyes closed
        self.mouth_aspect_ratio = 0.0  # 0-1
        self.emotion = "neutral"  # happy, sad, angry, surprised, neutral
        self.emotion_confidence = 0.0  # 0-1

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

    def to_dict(self):
        """Convert state to dictionary for transmission"""
        with self.lock:
            return {
                'session_id': self.session_id,
                'session_start_time': self.session_start_time,
                'is_running': self.is_running,
                'focus_percentage': round(self.focus_percentage, 2),
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
                'time_tracking': {
                    'focused_seconds': self.focused_time_seconds,
                    'unfocused_seconds': self.unfocused_time_seconds,
                    'distracted_events': self.distracted_events,
                    'focus_ratio': round(
                        self.focused_time_seconds / (self.focused_time_seconds + self.unfocused_time_seconds + 1),
                        3
                    ),
                },
            }

# Global state
state = SessionState()

# ============================================================================
# WEBCAM & COMPUTER VISION
# ============================================================================

class WebcamProcessor:
    """Handles webcam capture and ML inference"""

    def __init__(self, state):
        self.state = state
        self.cap = None
        self.running = False
        self.thread = None

        # MediaPipe
        self.mp_pose = mp.solutions.pose
        self.mp_face_detection = mp.solutions.face_detection
        self.mp_face_mesh = mp.solutions.face_mesh

        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=1,
            smooth_landmarks=True
        )
        self.face_detection = self.mp_face_detection.FaceDetection(
            model_selection=0,
            min_detection_confidence=0.5
        )
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            min_detection_confidence=0.5
        )

    def start(self):
        """Start webcam processing"""
        if self.running:
            return

        # Try DirectShow backend first (more reliable on Windows)
        self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not self.cap.isOpened():
            logger.warning("Cannot open webcam with DirectShow, trying default...")
            self.cap = cv2.VideoCapture(0)

        if not self.cap.isOpened():
            logger.error("Cannot open webcam")
            return False

        # Set camera properties for better performance
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.cap.set(cv2.CAP_PROP_FPS, 30)

        # Test if we can actually read a frame
        ret, test_frame = self.cap.read()
        if not ret or test_frame is None:
            logger.error("Webcam opened but cannot read frames")
            self.cap.release()
            return False

        logger.info(f"Webcam opened: {test_frame.shape}")

        self.running = True
        self.thread = Thread(target=self._process_loop, daemon=True)
        self.thread.start()
        logger.info("Webcam processing started")
        return True

    def stop(self):
        """Stop webcam processing"""
        self.running = False
        if self.cap:
            self.cap.release()
        if self.thread:
            self.thread.join(timeout=2)
        logger.info("Webcam processing stopped")

    def _process_loop(self):
        """Main processing loop"""
        import time
        frame_times = deque(maxlen=30)

        while self.running:
            try:
                ret, frame = self.cap.read()
                if not ret:
                    continue

                start_time = time.time()

                # Flip and resize
                frame = cv2.flip(frame, 1)
                h, w, c = frame.shape

                # Convert to RGB
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                # Process face detection and landmarks
                self._process_face(rgb_frame, frame)

                # Process body pose
                self._process_pose(rgb_frame, frame)

                # Draw overlays
                self._draw_overlays(frame)

                # Calculate FPS
                frame_time = time.time() - start_time
                frame_times.append(frame_time)
                if frame_times:
                    self.state.fps = 1.0 / (sum(frame_times) / len(frame_times))

                # Update frame counter
                with self.state.lock:
                    self.state.frame_count += 1

                # Encode and emit frame
                _, buffer = cv2.imencode('.jpg', frame)
                frame_b64 = base64.b64encode(buffer).decode('utf-8')
                socketio.emit('frame_update', {
                    'frame': frame_b64,
                    'state': self.state.to_dict()
                }, broadcast=True)

                # Small sleep to prevent CPU spinning
                time.sleep(0.01)

            except Exception as e:
                logger.error(f"Error in processing loop: {e}", exc_info=True)

    def _process_face(self, rgb_frame, bgr_frame):
        """Process face detection and emotion"""
        results = self.face_detection.process(rgb_frame)

        if results.detections:
            with self.state.lock:
                self.state.face_detected = True
                self.state.face_count = len(results.detections)

                # Process face mesh for emotions
                face_results = self.face_mesh.process(rgb_frame)
                if face_results.multi_face_landmarks:
                    # Draw face mesh
                    mp_drawing = mp.solutions.drawing_utils
                    mp_drawing_styles = mp.solutions.drawing_styles
                    for face_landmarks in face_results.multi_face_landmarks:
                        mp_drawing.draw_landmarks(
                            image=bgr_frame,
                            landmark_list=face_landmarks,
                            connections=self.mp_face_mesh.FACEMESH_TESSELATION,
                            landmark_drawing_spec=None,
                            connection_drawing_spec=mp_drawing_styles.get_default_face_mesh_tesselation_style()
                        )
                        mp_drawing.draw_landmarks(
                            image=bgr_frame,
                            landmark_list=face_landmarks,
                            connections=self.mp_face_mesh.FACEMESH_CONTOURS,
                            landmark_drawing_spec=None,
                            connection_drawing_spec=mp_drawing_styles.get_default_face_mesh_contours_style()
                        )

                    self._process_face_landmarks(face_results.multi_face_landmarks[0])
        else:
            with self.state.lock:
                self.state.face_detected = False

    def _process_face_landmarks(self, landmarks):
        """Extract facial landmarks for emotion detection"""
        # Simple eye aspect ratio calculation
        # Using landmarks indices for left and right eyes
        left_eye_top = landmarks.landmark[159].y
        left_eye_bottom = landmarks.landmark[145].y
        left_eye_left = landmarks.landmark[33].x
        left_eye_right = landmarks.landmark[133].x

        eye_vertical = abs(left_eye_top - left_eye_bottom)
        eye_horizontal = abs(left_eye_left - left_eye_right)

        if eye_horizontal > 0:
            ear = eye_vertical / eye_horizontal
        else:
            ear = 0

        with self.state.lock:
            self.state.eye_aspect_ratio = min(ear, 1.0)

            # Simple emotion estimation based on eye and mouth
            if self.state.eye_aspect_ratio < 0.2:
                self.state.emotion = "sleepy"
                self.state.emotion_confidence = 0.8
                self.state.focus_percentage = max(0, self.state.focus_percentage - 30)
            else:
                self.state.emotion = "neutral"
                self.state.emotion_confidence = 0.5

    def _process_pose(self, rgb_frame, bgr_frame):
        """Process body pose"""
        results = self.pose.process(rgb_frame)

        # Draw pose landmarks on frame
        if results.pose_landmarks:
            mp_drawing = mp.solutions.drawing_utils
            mp_drawing_styles = mp.solutions.drawing_styles
            mp_drawing.draw_landmarks(
                bgr_frame,
                results.pose_landmarks,
                self.mp_pose.POSE_CONNECTIONS,
                landmark_drawing_spec=mp_drawing_styles.get_default_pose_landmarks_style()
            )

        if results.pose_landmarks:
            with self.state.lock:
                self.state.body_detected = True
                self.state.pose_confidence = results.pose_landmarks.landmark[0].visibility if results.pose_landmarks else 0

                # Calculate posture score based on head and shoulder positions
                # This is simplified - in production you'd use more sophisticated metrics
                head = results.pose_landmarks.landmark[0]
                left_shoulder = results.pose_landmarks.landmark[11]
                right_shoulder = results.pose_landmarks.landmark[12]

                # If head is centered between shoulders, good posture
                shoulder_center_x = (left_shoulder.x + right_shoulder.x) / 2
                posture_deviation = abs(head.x - shoulder_center_x)
                self.state.posture_score = max(0, 100 - (posture_deviation * 200))
        else:
            with self.state.lock:
                self.state.body_detected = False

    def _draw_overlays(self, frame):
        """Draw skeleton and metrics overlays"""
        h, w, c = frame.shape

        # Draw FPS
        cv2.putText(frame, f"FPS: {self.state.fps:.1f}", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        # Draw focus percentage
        cv2.putText(frame, f"Focus: {self.state.focus_percentage:.1f}%", (10, 70),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        # Draw emotion
        cv2.putText(frame, f"Emotion: {self.state.emotion}", (10, 110),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        # Draw posture
        cv2.putText(frame, f"Posture: {self.state.posture_score:.1f}%", (10, 150),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

# Global webcam processor
webcam = WebcamProcessor(state)

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

    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)

    # Run with SocketIO
    socketio.run(
        app,
        host='0.0.0.0',
        port=int(os.getenv('PORT', 5000)),
        debug=os.getenv('DEBUG', 'False').lower() == 'true'
    )
