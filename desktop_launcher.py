#!/usr/bin/env python3
"""
Eaglearn Desktop Application Launcher
Wraps Flask app in WebView2 for native desktop experience
"""

import os
import sys
import logging
import time
import threading
import webview
from pathlib import Path
import re
from logging.handlers import RotatingFileHandler

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set up logging
log_dir = project_root / "logs"
log_dir.mkdir(parents=True, exist_ok=True)


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


log_file = str(log_dir / "eaglearn_desktop.log")
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


class EaglearnDesktopApp:
    """Desktop wrapper for Eaglearn application"""

    def __init__(self):
        self.flask_app = None
        self.socketio = None
        self.server_thread = None
        self.server_running = False
        self.port = int(os.getenv("PORT", 8080))
        self.host = "127.0.0.1"

    def start_flask_server(self):
        """Start Flask server in background thread"""
        try:
            logger.info("=" * 60)
            logger.info("Eaglearn Desktop - Focus Monitoring Application")
            logger.info("=" * 60)

            # Import Flask app
            from app import app, socketio

            self.flask_app = app
            self.socketio = socketio

            logger.info(f"[WEB] Starting Flask server on {self.host}:{self.port}")

            # Run Flask server
            self.server_running = True
            self.socketio.run(
                self.flask_app,
                host=self.host,
                port=self.port,
                debug=False,
                allow_unsafe_werkzeug=True,
                use_reloader=False,  # Important: disable reloader in desktop mode
            )

        except Exception as e:
            logger.error(f"[ERROR] Failed to start Flask server: {e}")
            self.server_running = False

    def wait_for_server(self):
        """Wait for Flask server to be ready"""
        import urllib.request
        import urllib.error
        import socket

        max_attempts = int(os.getenv("EAGLEARN_SERVER_WAIT_ATTEMPTS", "90"))
        per_request_timeout = float(os.getenv("EAGLEARN_SERVER_WAIT_TIMEOUT", "2.0"))
        for attempt in range(max_attempts):
            try:
                url = f"http://{self.host}:{self.port}/api/health"
                with urllib.request.urlopen(url, timeout=per_request_timeout) as resp:
                    resp.read(64)
                logger.info("[OK] Flask server is ready")
                return True
            except (
                urllib.error.URLError,
                urllib.error.HTTPError,
                ConnectionRefusedError,
                TimeoutError,
                socket.timeout,
                OSError,
            ):
                if self.server_thread and not self.server_thread.is_alive():
                    logger.error("[ERROR] Flask server thread exited early")
                    return False
                if attempt < max_attempts - 1:
                    time.sleep(0.5)
                else:
                    logger.error("[ERROR] Flask server failed to start")
                    return False
        return False

    def on_closing(self):
        """Handle window closing event"""
        logger.info("[STOP] Desktop window closing...")
        self.server_running = False
        # Give Flask time to shut down gracefully
        time.sleep(1)
        logger.info("[OK] Desktop application closed")

    def run(self):
        """Start desktop application"""
        try:
            # Start Flask server in background thread
            self.server_thread = threading.Thread(
                target=self.start_flask_server, daemon=True
            )
            self.server_thread.start()

            # Wait for server to be ready
            if not self.wait_for_server():
                logger.error("[ERROR] Cannot start application - server not responding")
                return

            # Create WebView window
            logger.info("[START] Creating desktop window...")

            window = webview.create_window(
                title="Eaglearn - Focus Monitoring",
                url=f"http://{self.host}:{self.port}",
                width=1280,
                height=800,
                resizable=True,
                fullscreen=False,
                min_size=(800, 600),
                background_color="#1a1a1a",
                text_select=False,  # Disable text selection for app-like feel
            )

            # Set window event handlers
            window.events.closing += self.on_closing

            logger.info("[OK] Desktop window created")
            logger.info("[RUNNING] Application is running - Close window to exit")

            # Start WebView (blocking call)
            webview.start(debug=False)

        except ImportError as e:
            logger.error(f"[ERROR] Failed to import required modules: {e}")
            logger.error("Please ensure all dependencies are installed:")
            logger.error("  pip install -r requirements.txt")
            logger.error("  pip install pywebview pywin32")
            sys.exit(1)

        except Exception as e:
            logger.error(f"[ERROR] Desktop application error: {e}")
            import traceback

            logger.error(traceback.format_exc())
            sys.exit(1)

        finally:
            logger.info("[STOP] Desktop application shutdown complete")


def main():
    """Main entry point"""
    app = EaglearnDesktopApp()
    app.run()


if __name__ == "__main__":
    main()
