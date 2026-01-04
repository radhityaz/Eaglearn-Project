"""
APScheduler configuration for background jobs.
Handles retention policy and other scheduled tasks.
"""

import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session

from backend.db.retention import RetentionPolicy

logger = logging.getLogger(__name__)


class SchedulerService:
    """Manages scheduled background jobs."""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.retention_policy = RetentionPolicy(retention_days=30, hard_delete_days=60)
    
    def setup_jobs(self, get_db_session):
        """
        Setup all scheduled jobs.
        
        Args:
            get_db_session: Callable that returns database session
        """
        # Retention policy job - runs daily at 2 AM UTC
        self.scheduler.add_job(
            func=self._run_retention_job,
            trigger=CronTrigger(hour=2, minute=0),
            id='retention_policy',
            name='Data Retention Policy',
            replace_existing=True,
            args=[get_db_session]
        )
        
        logger.info("Scheduled jobs configured successfully")
    
    def _run_retention_job(self, get_db_session):
        """Execute retention policy job."""
        try:
            db = get_db_session()
            results = self.retention_policy.run_retention_job(db)
            logger.info(f"Retention job completed: {results}")
        except Exception as e:
            logger.error(f"Retention job failed: {str(e)}")
        finally:
            db.close()
    
    def start(self):
        """Start the scheduler."""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("Scheduler started")
    
    def shutdown(self):
        """Shutdown the scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Scheduler shutdown")


# Global scheduler instance
_scheduler_service = None


def get_scheduler() -> SchedulerService:
    """Get or create global scheduler instance."""
    global _scheduler_service
    if _scheduler_service is None:
        _scheduler_service = SchedulerService()
    return _scheduler_service