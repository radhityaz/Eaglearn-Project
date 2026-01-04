#!/usr/bin/env python3
"""
Eaglearn Application Runner
Simplified Flask application for focus monitoring
"""

import os
import sys
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def main():
    """Main entry point"""
    logger.info("=" * 60)
    logger.info("Eaglearn - Focus Monitoring Application")
    logger.info("=" * 60)

    # Set environment variables
    os.environ.setdefault('FLASK_APP', 'app.py')
    os.environ.setdefault('FLASK_ENV', 'development')
    os.environ.setdefault('DEBUG', 'False')

    # Import and run app
    try:
        from app import app, socketio

        logger.info("Starting application...")
        logger.info("Web interface: http://localhost:5000")
        logger.info("Press Ctrl+C to stop")
        logger.info("=" * 60)

        # Run with SocketIO
        socketio.run(
            app,
            host='0.0.0.0',
            port=5000,
            debug=False,
            allow_unsafe_werkzeug=True
        )

    except Exception as e:
        logger.error(f"Failed to start application: {e}", exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    main()
