"""
Eaglearn Backend - Main FastAPI Application
Integrates Database, WebSocket, REST API, and Scheduler
"""

import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Import core components
from backend.db.database import init_db, get_db_context
from backend.db.encryption import get_encryption_manager
from backend.scheduler import get_scheduler
from backend.api.endpoints import api_router, router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting Eaglearn Backend...")
    scheduler = None
    try:
        # 1. Verify encryption key
        encryption_key = os.getenv("EAGLEARN_ENCRYPTION_KEY")
        if not encryption_key:
            logger.warning("EAGLEARN_ENCRYPTION_KEY not set! Using default (INSECURE for production)")
            os.environ["EAGLEARN_ENCRYPTION_KEY"] = "default-insecure-key-change-in-production"
        # Initialize encryption manager
        get_encryption_manager()
        logger.info("Encryption manager initialized")

        # 2. Initialize database
        init_db()
        logger.info("Database initialized")

        # 3. Start scheduler for retention policy
        scheduler = get_scheduler()
        # Pass a DB session provider to scheduler
        def get_db_for_scheduler():
            with get_db_context() as db:
                return db
        scheduler.setup_jobs(get_db_for_scheduler)
        scheduler.start()
        logger.info("Scheduler started")

        yield

    except Exception as e:
        logger.error(f"Failed to start application: {str(e)}")
        raise
    finally:
        if scheduler:
            try:
                scheduler.shutdown()
                logger.info("Scheduler stopped")
            except Exception as e:
                logger.error(f"Error during shutdown: {str(e)}")


# Create FastAPI application
app = FastAPI(
    title="Eaglearn API",
    description="AI/ML Focus Monitoring Application - Backend API",
    version="0.1.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(router)
app.include_router(api_router)


# Root endpoint
@app.get("/", tags=["root"])
async def root():
    """Root endpoint - API health check."""
    return {
        "status": "online",
        "service": "Eaglearn Backend API",
        "version": "0.1.0",
        "endpoints": {
            "docs": "/docs",
            "openapi": "/openapi.json",
            "health": "/health"
        }
    }


# Health check endpoint
@app.get("/health", tags=["root"])
async def health_check():
    """Health check endpoint."""
    try:
        # Check database connection
        with get_db_context() as db:
            db.execute("SELECT 1")
        
        # Check scheduler
        scheduler = get_scheduler()
        scheduler_running = scheduler.scheduler.running
        
        return {
            "status": "healthy",
            "database": "connected",
            "scheduler": "running" if scheduler_running else "stopped",
            "encryption": "enabled"
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e)
            }
        )


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if os.getenv("DEBUG") else "An error occurred"
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    # Get configuration from environment
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    reload = os.getenv("DEBUG", "false").lower() == "true"
    
    logger.info(f"Starting server on {host}:{port}")
    
    uvicorn.run(
        "backend.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )
