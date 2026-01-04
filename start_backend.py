"""
Startup script for Eaglearn Backend.
Ensures all dependencies are ready before starting the server.
"""

import os
import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_environment():
    """Check environment variables required for startup."""
    required_vars = ["EAGLEARN_ENCRYPTION_KEY"]
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)

    if missing_vars:
        logger.warning(f"Missing environment variables: {', '.join(missing_vars)}")
        logger.warning("Using default values (NOT SECURE for production)")

        if "EAGLEARN_ENCRYPTION_KEY" in missing_vars:
            os.environ["EAGLEARN_ENCRYPTION_KEY"] = "default-insecure-key-change-in-production"

    return True


def main():
    """Main startup function."""
    logger.info("=" * 60)
    logger.info("Eaglearn Backend - Starting...")
    logger.info("=" * 60)

    if not check_environment():
        logger.error("Environment check failed")
        sys.exit(1)

    try:
        import uvicorn
        from backend.main import app

        host = os.getenv("API_HOST", "0.0.0.0")
        port = int(os.getenv("API_PORT", "8000"))
        reload = os.getenv("DEBUG", "false").lower() == "true"

        logger.info(f"Server configuration:")
        logger.info(f"  Host: {host}")
        logger.info(f"  Port: {port}")
        logger.info(f"  Reload: {reload}")

        uvicorn.run(app, host=host, port=port, reload=reload, log_level="info")

    except Exception as e:
        logger.error(f"Failed to start server: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()