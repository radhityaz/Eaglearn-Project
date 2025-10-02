#!/usr/bin/env python3
"""
Eaglearn Backend - Main Entry Point
Resource-conscious AI processing for learning monitoring
"""

import argparse
import asyncio
import os
import signal
import sys
from pathlib import Path
from typing import Optional

from loguru import logger
from fastapi import FastAPI
from uvicorn import Config, Server
import psutil

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import Settings
from utils.resource_governor import ResourceGovernor
from api.server import create_app


class EaglearnBackend:
    """Main backend orchestrator"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.app: Optional[FastAPI] = None
        self.server: Optional[Server] = None
        self.resource_governor: Optional[ResourceGovernor] = None
        self.shutdown_event = asyncio.Event()
        
        # Configure logging
        self._setup_logging()
        
        # Set process priority
        self._set_process_priority()
    
    def _setup_logging(self):
        """Configure structured logging"""
        logger.remove()  # Remove default handler
        
        # Console logging
        logger.add(
            sys.stdout,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{line} - {message}",
            level=self.settings.log_level,
            colorize=True
        )
        
        # File logging (rotating)
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        logger.add(
            log_dir / "backend_{time}.log",
            rotation="100 MB",
            retention="7 days",
            level="DEBUG",
            format="{time} | {level} | {name}:{line} | {message}"
        )
        
        logger.info("Eaglearn Backend Starting...")
        logger.info(f"Python {sys.version}")
        logger.info(f"Process PID: {os.getpid()}")
    
    def _set_process_priority(self):
        """Set process priority to below normal"""
        try:
            p = psutil.Process(os.getpid())
            
            if sys.platform == "win32":
                p.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
                logger.info("Process priority set to BELOW_NORMAL")
            else:
                p.nice(10)  # Nice value for Unix
                logger.info("Process nice value set to 10")
                
        except Exception as e:
            logger.warning(f"Could not set process priority: {e}")
    
    async def start(self):
        """Start the backend services"""
        logger.info("Starting Eaglearn Backend Services")
        
        # Initialize resource governor
        self.resource_governor = ResourceGovernor(
            max_cpu_percent=self.settings.max_cpu_percent,
            max_gpu_percent=self.settings.max_gpu_percent,
            max_memory_mb=self.settings.max_memory_mb
        )
        await self.resource_governor.start()
        
        # Create FastAPI app
        self.app = create_app(self.settings, self.resource_governor)
        
        # Configure Uvicorn server
        config = Config(
            app=self.app,
            host=self.settings.api_host,
            port=self.settings.api_port,
            log_level="info",
            access_log=False,  # We use our own logging
            workers=1,  # Single worker for resource control
            limit_concurrency=10,  # Limit concurrent connections
            limit_max_requests=1000,  # Restart worker after N requests
            timeout_keep_alive=5
        )
        
        self.server = Server(config)
        
        # Start server
        logger.info(f"API Server starting on {self.settings.api_host}:{self.settings.api_port}")
        
        try:
            await self.server.serve()
        except Exception as e:
            logger.error(f"Server error: {e}")
            raise
    
    async def shutdown(self):
        """Graceful shutdown"""
        logger.info("Initiating graceful shutdown...")
        
        if self.server:
            await self.server.shutdown()
        
        if self.resource_governor:
            await self.resource_governor.stop()
        
        self.shutdown_event.set()
        logger.info("Shutdown complete")
    
    def handle_signal(self, sig, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {sig}")
        asyncio.create_task(self.shutdown())


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Eaglearn Backend Server")
    
    parser.add_argument(
        "--max-cpu",
        type=int,
        default=40,
        help="Maximum CPU usage percentage (default: 40)"
    )
    
    parser.add_argument(
        "--max-gpu", 
        type=int,
        default=50,
        help="Maximum GPU usage percentage (default: 50)"
    )
    
    parser.add_argument(
        "--max-memory",
        type=int,
        default=2048,
        help="Maximum memory usage in MB (default: 2048)"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="API server port (default: 8000)"
    )
    
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="API server host (default: 127.0.0.1)"
    )
    
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO)"
    )
    
    parser.add_argument(
        "--dev",
        action="store_true",
        help="Run in development mode"
    )
    
    return parser.parse_args()


async def main():
    """Main entry point"""
    args = parse_arguments()
    
    # Create settings from arguments
    settings = Settings(
        max_cpu_percent=args.max_cpu,
        max_gpu_percent=args.max_gpu,
        max_memory_mb=args.max_memory,
        api_host=args.host,
        api_port=args.port,
        log_level=args.log_level,
        dev_mode=args.dev
    )
    
    # Create and start backend
    backend = EaglearnBackend(settings)
    
    # Register signal handlers
    signal.signal(signal.SIGINT, backend.handle_signal)
    signal.signal(signal.SIGTERM, backend.handle_signal)
    
    try:
        await backend.start()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
    finally:
        await backend.shutdown()


if __name__ == "__main__":
    # Set environment variables for optimization
    os.environ["OMP_NUM_THREADS"] = "2"
    os.environ["MKL_NUM_THREADS"] = "2"
    os.environ["NUMEXPR_NUM_THREADS"] = "2"
    os.environ["OPENCV_VIDEOIO_PRIORITY_MSMF"] = "0"  # Use DirectShow on Windows
    
    # Run the backend
    asyncio.run(main())