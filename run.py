#!/usr/bin/env python3
"""
Eaglearn Application Runner
Simplified Flask application for focus monitoring
"""

import os
import sys
import logging
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def main():
    """Main entry point for Eaglearn application"""

    # Set up logging
    log_dir = os.path.join(os.path.dirname(__file__), "logs")
    os.makedirs(log_dir, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(
                os.path.join(
                    log_dir, f"eaglearn_{datetime.now().strftime('%Y%m%d')}.log"
                ),
                mode="a",
            ),
        ],
    )

    logger = logging.getLogger(__name__)

    logger.info("===========================================================")
    logger.info("Eaglearn - Focus Monitoring Application")
    logger.info("===========================================================")

    try:
        # Import and run the Flask app
        from app import app, socketio

        # Start the server
        port = int(os.getenv("PORT", 8080))
        logger.info(f"[WEB] Starting Eaglearn Application on http://localhost:{port}")

        socketio.run(
            app, host="0.0.0.0", port=port, debug=False, allow_unsafe_werkzeug=True
        )

    except ImportError as e:
        logger.error(f"[ERROR] Failed to import application modules: {e}")
        logger.error("Please ensure all dependencies are installed:")
        logger.error("  pip install -r requirements.txt")
        logger.error("  python -m venv\\Scripts\\activate")
        logger.error("  python run.py")
        sys.exit(1)
    except Exception as e:
        logger.error(f"[ERROR] Failed to start application: {e}")
        logger.error(
            "Please check the error above and ensure all dependencies are installed"
        )
        logger.error("Common issues:")
        logger.error("  - Missing dependencies: pip install -r requirements.txt")
        logger.error("  - Python environment: python -m venv\\Scripts\\activate")
        logger.error("  - Configuration: Check config.yaml syntax")
        logger.error("  - GPU drivers: Ensure CUDA drivers are up to date")
        logger.error("  - Permissions: Run as administrator if needed")
        logger.error(f"Error details: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
