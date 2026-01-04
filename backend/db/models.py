from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import declarative_base, relationship

from backend.db.encryption import EncryptedString

Base = declarative_base()


class Session(Base):
    """Primary session record tracking overall study sessions."""

    __tablename__ = "sessions"

    session_id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(String(36), nullable=False, index=True)
    calibration_id = Column(
        String(36), ForeignKey("user_calibration.calibration_id"), nullable=True
    )
    status = Column(String(20), nullable=False, default="active")
    start_time = Column(DateTime, nullable=False, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    duration_minutes = Column(Integer, nullable=False, default=0)
    estimated_duration_minutes = Column(Integer, nullable=False, default=60)
    on_task_ratio = Column(Float, nullable=False, default=0.0)
    avg_engagement_score = Column(Float, nullable=True)
    avg_fatigue_score = Column(Float, nullable=True)
    device_info = Column(EncryptedString(), nullable=True)
    os_version = Column(EncryptedString(), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True, default=None)

    frames = relationship(
        "FrameMetrics", back_populates="session", cascade="all, delete-orphan"
    )
    audio_streams = relationship(
        "AudioStress", back_populates="session", cascade="all, delete-orphan"
    )
    productivity_metrics = relationship(
        "ProductivityMetrics",
        back_populates="session",
        cascade="all, delete-orphan",
        uselist=False,
    )
    calibration = relationship(
        "UserCalibration", back_populates="sessions", foreign_keys=[calibration_id]
    )

    __table_args__ = (
        CheckConstraint(
            "on_task_ratio BETWEEN 0.0 AND 1.0",
            name="chk_sessions_on_task_ratio_range",
        ),
        CheckConstraint(
            "duration_minutes >= 0", name="chk_sessions_duration_non_negative"
        ),
        CheckConstraint(
            "estimated_duration_minutes BETWEEN 1 AND 480",
            name="chk_sessions_estimated_duration_range",
        ),
        Index("idx_sessions_status", "status"),
        Index("idx_sessions_deleted_at", "deleted_at"),
        Index("idx_sessions_start_time", "start_time"),
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<Session id={self.session_id} user={self.user_id} status={self.status}>"


class FrameMetrics(Base):
    """Per-frame metrics produced by the gaze and pose estimators."""

    __tablename__ = "frame_metrics"

    frame_id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    session_id = Column(String(36), ForeignKey("sessions.session_id"), nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    gaze_confidence = Column(Float, nullable=True)
    head_pose_confidence = Column(Float, nullable=True)
    processing_latency_ms = Column(Integer, nullable=True)
    deleted_at = Column(DateTime, nullable=True, default=None)

    session = relationship("Session", back_populates="frames")
    gazes = relationship(
        "GazeData", back_populates="frame", cascade="all, delete-orphan"
    )
    head_pose = relationship("HeadPose", back_populates="frame", uselist=False)

    __table_args__ = (
        CheckConstraint(
            "gaze_confidence IS NULL OR (gaze_confidence BETWEEN 0.0 AND 1.0)",
            name="chk_frame_metrics_gaze_confidence_range",
        ),
        CheckConstraint(
            "head_pose_confidence IS NULL OR (head_pose_confidence BETWEEN 0.0 AND 1.0)",
            name="chk_frame_metrics_pose_confidence_range",
        ),
        CheckConstraint(
            "processing_latency_ms IS NULL OR processing_latency_ms >= 0",
            name="chk_frame_metrics_latency_non_negative",
        ),
        Index("idx_frame_metrics_session_id", "session_id"),
        Index("idx_frame_metrics_timestamp", "timestamp"),
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<FrameMetrics id={self.frame_id} session={self.session_id}>"


class GazeData(Base):
    """Gaze estimates associated with a single frame."""

    __tablename__ = "gaze_data"

    gaze_id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    frame_id = Column(String(36), ForeignKey("frame_metrics.frame_id"), nullable=False)
    gaze_x = Column(Float, nullable=True)
    gaze_y = Column(Float, nullable=True)
    gaze_direction = Column(String(20), nullable=True)
    gaze_angle = Column(Float, nullable=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True, default=None)

    frame = relationship("FrameMetrics", back_populates="gazes")

    __table_args__ = (
        CheckConstraint(
            "gaze_x IS NULL OR gaze_x >= 0.0", name="chk_gaze_data_x_non_negative"
        ),
        CheckConstraint(
            "gaze_y IS NULL OR gaze_y >= 0.0", name="chk_gaze_data_y_non_negative"
        ),
        CheckConstraint(
            "gaze_angle IS NULL OR (gaze_angle BETWEEN -180.0 AND 180.0)",
            name="chk_gaze_data_angle_range",
        ),
        Index("idx_gaze_data_frame_id", "frame_id"),
        Index("idx_gaze_data_timestamp", "timestamp"),
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<GazeData id={self.gaze_id} frame={self.frame_id}>"


class HeadPose(Base):
    """Head pose estimation storage (pitch/yaw/roll)."""

    __tablename__ = "head_pose"

    pose_id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    frame_id = Column(
        String(36), ForeignKey("frame_metrics.frame_id"), nullable=False, unique=True
    )
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    pitch_angle = Column(Float, nullable=False)
    yaw_angle = Column(Float, nullable=False)
    roll_angle = Column(Float, nullable=False)
    posture_class = Column(String(20), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True, default=None)

    frame = relationship("FrameMetrics", back_populates="head_pose", uselist=False)

    __table_args__ = (
        CheckConstraint(
            "pitch_angle BETWEEN -90.0 AND 90.0",
            name="chk_head_pose_pitch_range",
        ),
        CheckConstraint(
            "yaw_angle BETWEEN -90.0 AND 90.0", name="chk_head_pose_yaw_range"
        ),
        CheckConstraint(
            "roll_angle BETWEEN -90.0 AND 90.0", name="chk_head_pose_roll_range"
        ),
        Index("idx_head_pose_frame_id", "frame_id"),
        Index("idx_head_pose_timestamp", "timestamp"),
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return (
            f"<HeadPose id={self.pose_id} pitch={self.pitch_angle} yaw={self.yaw_angle} "
            f"roll={self.roll_angle}>"
        )


class AudioStress(Base):
    """Aggregated audio analysis windows."""

    __tablename__ = "audio_stress"

    audio_id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    session_id = Column(String(36), ForeignKey("sessions.session_id"), nullable=False)
    window_start = Column(DateTime, nullable=False)
    window_end = Column(DateTime, nullable=False)
    stress_score = Column(Float, nullable=False)
    vocal_effort = Column(Float, nullable=False)
    smoothing_count = Column(Integer, nullable=False, default=0)
    signal_quality = Column(Float, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True, default=None)

    session = relationship("Session", back_populates="audio_streams")
    stresses = relationship(
        "StressFeatures", back_populates="audio_stress", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "stress_score BETWEEN 0 AND 100",
            name="chk_audio_stress_score_range",
        ),
        CheckConstraint(
            "vocal_effort >= 0", name="chk_audio_stress_vocal_effort_non_negative"
        ),
        CheckConstraint(
            "smoothing_count >= 0",
            name="chk_audio_stress_smoothing_non_negative",
        ),
        Index("idx_audio_stress_session_id", "session_id"),
        Index("idx_audio_stress_window_start", "window_start"),
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<AudioStress id={self.audio_id} session={self.session_id}>"


class StressFeatures(Base):
    """Detailed features extracted from audio stress windows."""

    __tablename__ = "stress_features"

    feature_id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    audio_id = Column(String(36), ForeignKey("audio_stress.audio_id"), nullable=False)
    lf_power = Column(Float, nullable=False)
    hf_power = Column(Float, nullable=False)
    lf_hf_ratio = Column(Float, nullable=False)
    heart_rate = Column(Float, nullable=False)
    breathing_rate = Column(Float, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    audio_stress = relationship("AudioStress", back_populates="stresses")

    __table_args__ = (
        CheckConstraint("lf_power >= 0", name="chk_stress_features_lf_non_negative"),
        CheckConstraint("hf_power >= 0", name="chk_stress_features_hf_non_negative"),
        CheckConstraint(
            "lf_hf_ratio >= 0", name="chk_stress_features_ratio_non_negative"
        ),
        CheckConstraint(
            "heart_rate BETWEEN 50 AND 150",
            name="chk_stress_features_heart_rate_range",
        ),
        CheckConstraint(
            "breathing_rate BETWEEN 0.1 AND 0.5",
            name="chk_stress_features_breathing_rate_range",
        ),
        Index("idx_stress_features_audio_id", "audio_id"),
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<StressFeatures id={self.feature_id} audio={self.audio_id}>"


class ProductivityMetrics(Base):
    """Aggregated productivity indicators per session."""

    __tablename__ = "productivity_metrics"

    productivity_id = Column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    session_id = Column(
        String(36), ForeignKey("sessions.session_id"), nullable=False, unique=True
    )
    total_breaks = Column(Integer, nullable=False, default=0)
    avg_break_duration = Column(Float, nullable=False, default=0.0)
    break_pattern_type = Column(String(20), nullable=False, default="unknown")
    productivity_score = Column(Float, nullable=False, default=0.0)
    calculated_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True, default=None)

    session = relationship("Session", back_populates="productivity_metrics", uselist=False)

    __table_args__ = (
        CheckConstraint(
            "total_breaks >= 0", name="chk_productivity_metrics_total_breaks_positive"
        ),
        CheckConstraint(
            "avg_break_duration >= 0",
            name="chk_productivity_metrics_avg_break_duration_positive",
        ),
        CheckConstraint(
            "productivity_score BETWEEN 0 AND 100",
            name="chk_productivity_metrics_score_range",
        ),
        Index("idx_productivity_metrics_session_id", "session_id"),
        Index("idx_productivity_metrics_calculated_at", "calculated_at"),
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<ProductivityMetrics id={self.productivity_id} session={self.session_id}>"


class UserCalibration(Base):
    """Calibration metadata per user."""

    __tablename__ = "user_calibration"

    calibration_id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(String(36), nullable=False, index=True)
    calibration_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    gaze_model_version = Column(String(20), nullable=False)
    calibration_error = Column(Float, nullable=False)
    screen_dimensions = Column(EncryptedString(), nullable=False)
    camera_position = Column(EncryptedString(), nullable=False)
    transform_matrix = Column(Text, nullable=True)
    accuracy_score = Column(Float, nullable=True)
    status = Column(String(20), nullable=False, default="pending")
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    is_active = Column(Boolean, nullable=False, default=True)
    deleted_at = Column(DateTime, nullable=True, default=None)

    sessions = relationship("Session", back_populates="calibration")

    __table_args__ = (
        CheckConstraint(
            "calibration_error >= 0", name="chk_user_calibration_error_positive"
        ),
        Index("idx_user_calibration_is_active", "is_active"),
        Index("idx_user_calibration_calibration_date", "calibration_date"),
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<UserCalibration id={self.calibration_id} user={self.user_id}>"
