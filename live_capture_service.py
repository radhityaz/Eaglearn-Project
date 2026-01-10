"""
Live Capture Service for streaming applications
Supports RTMP, WebRTC, and other streaming protocols
"""

import logging
import cv2
import threading
import time
from queue import Queue, Empty

logger = logging.getLogger(__name__)


class LiveCaptureService:
    """Service for live streaming capture with multiple backend support"""

    def __init__(self):
        self.cap = None
        self.streaming = False
        self.frame_queue = Queue(maxsize=30)  # Buffer 30 frames
        self.clients = []  # Connected streaming clients
        self.stream_thread = None
        self.current_backend = None

    def start_capture(self, backend="auto"):
        """
        Start capture with optimal backend for streaming

        Args:
            backend: 'auto', 'rtmp', 'webrtc', 'directshow'
        """
        if self.streaming:
            logger.warning("Capture already streaming")
            return False

        # Backend priority for streaming
        backend_priority = [
            "rtmp",  # Best for streaming servers
            "webrtc",  # Best for web browsers
            "directshow",  # DirectShow for Windows
            "v4l2",  # Linux camera
            "dshow",  # Windows fallback
        ]

        if backend != "auto":
            backend_priority = [backend]

        for try_backend in backend_priority:
            if self._try_backend(try_backend):
                self.current_backend = try_backend
                self.streaming = True
                logger.info(f"🎥 Live capture started with {try_backend} backend")
                return True

        logger.error("Failed to start capture with any backend")
        return False

    def _try_backend(self, backend):
        """Try specific backend"""
        try:
            if backend == "rtmp":
                return self._start_rtmp_capture()
            elif backend == "webrtc":
                return self._start_webrtc_capture()
            else:
                return self._start_opencv_backend(backend)
        except Exception as e:
            logger.error(f"Backend {backend} failed: {e}")
            return False

    def _start_opencv_backend(self, backend):
        """Start OpenCV with specified backend"""
        backend_map = {
            "directshow": cv2.CAP_DIRECTSHOW,
            "dshow": cv2.CAP_DSHOW,
            "v4l2": cv2.CAP_V4L2,
        }

        cap_backend = backend_map.get(backend, cv2.CAP_ANY)

        self.cap = cv2.VideoCapture(0, cap_backend)

        if not self.cap.isOpened():
            return False

        # Configure for streaming
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimize latency

        # Start capture thread
        self.stream_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.stream_thread.start()

        return True

    def _start_rtmp_capture(self):
        """Start RTMP streaming (requires FFmpeg)"""
        try:
            import subprocess

            # FFmpeg command for RTMP streaming
            cmd = [
                "ffmpeg",
                "-f",
                "dshow",
                "-i",
                "0",
                "-f",
                "flv",
                "-r",
                "30",
                "-s",
                "1920x1080",
                "-c:v",
                "libx264",
                "-preset",
                "ultrafast",
                "-tune",
                "zerolatency",
                "-f",
                "flv",
                "rtmp://your-streaming-server/live/stream-key",
            ]

            self.cap = subprocess.Popen(cmd, stdin=subprocess.PIPE)
            self.streaming = True

            logger.info("🎥 RTMP streaming started with FFmpeg")
            return True

        except ImportError:
            logger.error("FFmpeg not available for RTMP streaming")
            return False
        except Exception as e:
            logger.error(f"RTMP setup failed: {e}")
            return False

    def _start_webrtc_capture(self):
        """Start WebRTC capture (requires aiortc)"""
        try:
            from aiortc import MediaStreamTrack

            class VideoTrack(MediaStreamTrack):
                def __init__(self):
                    super().__init__()
                    self.cap = cv2.VideoCapture(0)

                async def recv(self):
                    ret, frame = self.cap.read()
                    if ret:
                        # Convert to WebRTC format
                        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        return frame_rgb
                    return None

            self.streaming = True
            logger.info("WebRTC capture ready")
            return True

        except ImportError:
            logger.error("aiortc not available for WebRTC")
            return False
        except Exception as e:
            logger.error(f"WebRTC setup failed: {e}")
            return False

    def _capture_loop(self):
        """Capture loop for streaming"""
        while self.streaming:
            ret, frame = self.cap.read()
            if ret:
                # Add frame to queue
                if not self.frame_queue.full():
                    self.frame_queue.put(frame)
            else:
                logger.warning("Frame capture failed")
                time.sleep(0.01)

    def get_frame(self):
        """Get latest frame for processing"""
        try:
            return self.frame_queue.get_nowait()
        except Empty:
            return None

    def add_client(self, client_id):
        """Add streaming client"""
        self.clients.append(client_id)
        logger.info(f"Client connected: {client_id}")

    def remove_client(self, client_id):
        """Remove streaming client"""
        if client_id in self.clients:
            self.clients.remove(client_id)
            logger.info(f"Client disconnected: {client_id}")

    def get_stream_info(self):
        """Get current streaming information"""
        if not self.streaming:
            return {"streaming": False}

        return {
            "streaming": True,
            "backend": self.current_backend,
            "resolution": f"{self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)}x{self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)}",
            "fps": self.cap.get(cv2.CAP_PROP_FPS),
            "clients": len(self.clients),
        }

    def stop_capture(self):
        """Stop live capture"""
        self.streaming = False

        if self.stream_thread:
            self.stream_thread.join(timeout=2)

        if self.cap:
            self.cap.release()
            self.cap = None

        logger.info("🛑 Live capture stopped")

    def get_supported_backends(self):
        """Get list of supported backends"""
        return {
            "opencv": ["directshow", "dshow", "v4l2"],
            "rtmp": "Requires FFmpeg",
            "webrtc": "Requires aiortc",
            "recommended": "rtmp for servers, webrtc for web",
        }
