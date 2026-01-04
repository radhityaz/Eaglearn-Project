"""
Data retention policy implementation.
Handles automatic purging of data older than 30 days using soft-delete strategy.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

from backend.db.models import (
    Session as SessionModel,
    FrameMetrics,
    GazeData,
    HeadPose,
    AudioStress,
    StressFeatures,
    ProductivityMetrics,
    UserCalibration
)

logger = logging.getLogger(__name__)


class RetentionPolicy:
    """Manages data retention and purging operations."""
    
    def __init__(self, retention_days: int = 30, hard_delete_days: int = 60):
        """
        Initialize retention policy.
        
        Args:
            retention_days: Days before soft-delete (default: 30)
            hard_delete_days: Days before hard-delete (default: 60)
        """
        self.retention_days = retention_days
        self.hard_delete_days = hard_delete_days
    
    def soft_delete_expired_data(
        self,
        db: Session,
        *,
        current_time: Optional[datetime] = None,
    ) -> dict:
        """
        Soft-delete data older than retention_days.
        Sets deleted_at timestamp instead of removing records.
        
        Args:
            db: SQLAlchemy database session
            
        Returns:
            Dictionary with counts of soft-deleted records per model
        """
        now = current_time or datetime.utcnow()
        cutoff_date = now - timedelta(days=self.retention_days)
        results = {}
        
        try:
            # Soft-delete Sessions
            sessions_count = db.query(SessionModel).filter(
                and_(
                    SessionModel.start_time < cutoff_date,
                    SessionModel.deleted_at.is_(None)
                )
            ).update(
                {SessionModel.deleted_at: now},
                synchronize_session=False
            )
            results['sessions'] = sessions_count
            
            # Soft-delete FrameMetrics
            frames_count = db.query(FrameMetrics).filter(
                and_(
                    FrameMetrics.timestamp < cutoff_date,
                    FrameMetrics.deleted_at.is_(None)
                )
            ).update(
                {FrameMetrics.deleted_at: now},
                synchronize_session=False
            )
            results['frame_metrics'] = frames_count
            
            # Soft-delete GazeData
            gaze_count = db.query(GazeData).filter(
                and_(
                    GazeData.timestamp < cutoff_date,
                    GazeData.deleted_at.is_(None)
                )
            ).update(
                {GazeData.deleted_at: now},
                synchronize_session=False
            )
            results['gaze_data'] = gaze_count
            
            # Soft-delete HeadPose
            pose_count = db.query(HeadPose).filter(
                and_(
                    HeadPose.timestamp < cutoff_date,
                    HeadPose.deleted_at.is_(None)
                )
            ).update(
                {HeadPose.deleted_at: now},
                synchronize_session=False
            )
            results['head_poses'] = pose_count
            
            # Soft-delete AudioStress
            audio_count = db.query(AudioStress).filter(
                and_(
                    AudioStress.window_start < cutoff_date,
                    AudioStress.deleted_at.is_(None)
                )
            ).update(
                {AudioStress.deleted_at: now},
                synchronize_session=False
            )
            results['audio_stress'] = audio_count
            
            # Soft-delete ProductivityMetrics
            productivity_count = db.query(ProductivityMetrics).filter(
                and_(
                    ProductivityMetrics.calculated_at < cutoff_date,
                    ProductivityMetrics.deleted_at.is_(None)
                )
            ).update(
                {ProductivityMetrics.deleted_at: now},
                synchronize_session=False
            )
            results['productivity_metrics'] = productivity_count
            
            db.commit()
            
            total = sum(results.values())
            logger.info(f"Soft-deleted {total} records older than {self.retention_days} days: {results}")
            
            return results
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error during soft-delete: {str(e)}")
            raise
    
    def hard_delete_expired_data(
        self,
        db: Session,
        *,
        current_time: Optional[datetime] = None,
    ) -> dict:
        """
        Permanently delete data that was soft-deleted more than hard_delete_days ago.
        
        Args:
            db: SQLAlchemy database session
            
        Returns:
            Dictionary with counts of hard-deleted records per model
        """
        now = current_time or datetime.utcnow()
        cutoff_date = now - timedelta(days=self.hard_delete_days)
        results = {}
        
        try:
            # Hard-delete Sessions
            sessions_count = db.query(SessionModel).filter(
                and_(
                    SessionModel.deleted_at.isnot(None),
                    SessionModel.deleted_at < cutoff_date
                )
            ).delete(synchronize_session=False)
            results['sessions'] = sessions_count
            
            # Hard-delete FrameMetrics
            frames_count = db.query(FrameMetrics).filter(
                and_(
                    FrameMetrics.deleted_at.isnot(None),
                    FrameMetrics.deleted_at < cutoff_date
                )
            ).delete(synchronize_session=False)
            results['frame_metrics'] = frames_count
            
            # Hard-delete GazeData
            gaze_count = db.query(GazeData).filter(
                and_(
                    GazeData.deleted_at.isnot(None),
                    GazeData.deleted_at < cutoff_date
                )
            ).delete(synchronize_session=False)
            results['gaze_data'] = gaze_count
            
            # Hard-delete HeadPose
            pose_count = db.query(HeadPose).filter(
                and_(
                    HeadPose.deleted_at.isnot(None),
                    HeadPose.deleted_at < cutoff_date
                )
            ).delete(synchronize_session=False)
            results['head_poses'] = pose_count
            
            # Hard-delete AudioStress
            audio_count = db.query(AudioStress).filter(
                and_(
                    AudioStress.deleted_at.isnot(None),
                    AudioStress.deleted_at < cutoff_date
                )
            ).delete(synchronize_session=False)
            results['audio_stress'] = audio_count
            
            # Hard-delete StressFeatures (cascade from AudioStress)
            stress_features_count = db.query(StressFeatures).filter(
                StressFeatures.audio_id.notin_(
                    db.query(AudioStress.audio_id)
                )
            ).delete(synchronize_session=False)
            results['stress_features'] = stress_features_count
            
            # Hard-delete ProductivityMetrics
            productivity_count = db.query(ProductivityMetrics).filter(
                and_(
                    ProductivityMetrics.deleted_at.isnot(None),
                    ProductivityMetrics.deleted_at < cutoff_date
                )
            ).delete(synchronize_session=False)
            results['productivity_metrics'] = productivity_count
            
            # Hard-delete UserCalibration
            calibration_count = db.query(UserCalibration).filter(
                and_(
                    UserCalibration.deleted_at.isnot(None),
                    UserCalibration.deleted_at < cutoff_date
                )
            ).delete(synchronize_session=False)
            results['user_calibrations'] = calibration_count
            
            db.commit()
            
            total = sum(results.values())
            logger.info(f"Hard-deleted {total} records older than {self.hard_delete_days} days: {results}")
            
            return results
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error during hard-delete: {str(e)}")
            raise
    
    def run_retention_job(
        self,
        db: Session,
        *,
        current_time: Optional[datetime] = None,
    ) -> dict:
        """
        Run complete retention job: soft-delete + hard-delete.
        
        Args:
            db: SQLAlchemy database session
            
        Returns:
            Dictionary with results from both operations
        """
        logger.info("Starting retention policy job...")
        
        soft_delete_results = self.soft_delete_expired_data(db, current_time=current_time)
        hard_delete_results = self.hard_delete_expired_data(db, current_time=current_time)
        
        results = {
            'soft_deleted': soft_delete_results,
            'hard_deleted': hard_delete_results,
            'timestamp': (current_time or datetime.utcnow()).isoformat()
        }
        
        logger.info(f"Retention policy job completed: {results}")
        return results
