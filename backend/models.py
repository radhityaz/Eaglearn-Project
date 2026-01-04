from pydantic import BaseModel, Field, validator, root_validator
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from enum import Enum

class GazeDirection(str, Enum):
    """Enum untuk arah pandangan"""
    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"
    OFF_SCREEN = "off-screen"

class Session(BaseModel):
    """Model untuk sesi belajar pengguna"""
    session_id: UUID = Field(..., description="Unique identifier for the session (PK)")
    start_time: datetime = Field(..., description="Start time of the session")
    end_time: Optional[datetime] = Field(None, description="End time of the session (optional jika sesi masih berjalan)")
    duration_minutes: int = Field(..., description="Durasi sesi dalam menit; maksimal 480 (8 jam)")
    on_task_ratio: float = Field(..., ge=0.0, le=1.0, description="Proporsi waktu yang dihabiskan pada tugas (0-1)")
    avg_engagement_score: float = Field(..., ge=0.0, le=100.0, description="Rata-rata skor keterlibatan (0-100)")
    avg_fatigue_score: float = Field(..., ge=0.0, le=100.0, description="Rata-rata skor kelelahan (0-100)")
    device_info: Optional[str] = Field(None, description="Informasi perangkat")
    os_version: Optional[str] = Field(None, description="Versi sistem operasi")

    @validator('duration_minutes')
    def validate_duration_minutes(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("duration_minutes must be positive")
        if v > 480:
            raise ValueError("duration_minutes cannot exceed 480 (8 hours)")
        return v

    @validator('on_task_ratio')
    def validate_on_task_ratio(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError("on_task_ratio must be between 0.0 and 1.0")
        return v

    @validator('avg_engagement_score')
    def validate_engagement(cls, v: float) -> float:
        if not (0.0 <= v <= 100.0):
            raise ValueError("avg_engagement_score must be between 0 and 100")
        return v

    @validator('avg_fatigue_score')
    def validate_fatigue(cls, v: float) -> float:
        if not (0.0 <= v <= 100.0):
            raise ValueError("avg_fatigue_score must be between 0 and 100")
        return v

    @validator('end_time')
    def validate_end_after_start(cls, v: Optional[datetime], values):
        start = values.get('start_time')
        if v is None or start is None:
            return v
        if v < start:
            raise ValueError("end_time must be after start_time")
        return v

    @root_validator
    def check_duration_consistency(cls, values):
        start = values.get('start_time')
        end = values.get('end_time')
        duration = values.get('duration_minutes')
        if start and end and duration is not None:
            diff = int((end - start).total_seconds() / 60)
            if diff < 0:
                raise ValueError("Invalid time range: end_time before start_time")
            if diff > 480:
                raise ValueError("Session duration exceeds maximum of 480 minutes (8 hours)")
            # Ensure duration_minutes reflects the time delta (when both provided)
            if diff != duration:
                raise ValueError("duration_minutes does not match the difference between start_time and end_time")
        return values

class FrameMetrics(BaseModel):
    """Model untuk metrik frame individu dalam sesi"""
    frame_id: UUID = Field(..., description="Unique identifier for the frame")
    session_id: UUID = Field(..., description="Reference to parent session")
    timestamp: datetime = Field(..., description="Timestamp of the frame measurement")
    gaze_confidence: float = Field(..., description="Gaze confidence score (0.0-1.0)")
    head_pose_confidence: float = Field(..., description="Head pose confidence score (0.0-1.0)")
    processing_latency_ms: int = Field(..., description="Processing latency in milliseconds")

    @validator('gaze_confidence', 'head_pose_confidence')
    def validate_confidence(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError("Confidence must be between 0.0 and 1.0")
        return v

    @validator('processing_latency_ms')
    def validate_latency(cls, v: int) -> int:
        if v < 0:
            raise ValueError("processing_latency_ms must be non-negative")
        if v > 200:
            raise ValueError("processing_latency_ms cannot exceed 200 ms")
        return v

class GazeData(BaseModel):
    """Model untuk data per-entry gaze tracking pada frame"""
    gaze_id: UUID = Field(..., description="Unique identifier for the gaze data record")
    frame_id: UUID = Field(..., description="Reference to the associated frame")
    gaze_x: float = Field(..., description="Gaze X coordinate (normalized 0.0-1.0)")
    gaze_y: float = Field(..., description="Gaze Y coordinate (normalized 0.0-1.0)")
    gaze_direction: GazeDirection = Field(..., description="Direction of gaze")
    gaze_angle: float = Field(..., description="Gaze angle relative to forward direction")

    @validator('gaze_x', 'gaze_y')
    def validate_coordinates(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError("gaze_x and gaze_y must be within screen bounds (0.0-1.0)")
        return v

    @validator('gaze_angle')
    def validate_angle(cls, v: float) -> float:
        if not (-180.0 <= v <= 180.0):
            raise ValueError("gaze_angle must be between -180.0 and 180.0 degrees")
        return v
# ----------------------------
# Extended Phase 0: Missing Models (Pydantic)
# Added: HeadPose, AudioStress, StressFeatures, ProductivityMetrics, UserCalibration
# ----------------------------

class HeadPose(BaseModel):
    pose_id: UUID = Field(..., description="Unique identifier for the head pose record")
    frame_id: UUID = Field(..., description="Reference to frame metrics")
    session_id: UUID = Field(..., description="Reference to session")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Estimated time of capture")
    
    # Pose Angles (degrees)
    yaw_angle: float = Field(..., description="Yaw angle in degrees")
    pitch_angle: float = Field(..., description="Pitch angle in degrees")
    roll_angle: float = Field(..., description="Roll angle in degrees")
    
    # Posture Classification
    posture_class: str = Field(..., description="Posture classification (e.g., upright, forward, tilted, slouched)")
    
    # Optional confidence
    confidence: Optional[float] = Field(None, description="Confidence score (0.0 - 1.0)")

class AudioStress(BaseModel):
    audio_id: UUID = Field(..., description="Unique identifier for audio stress window")
    session_id: UUID = Field(..., description="Session reference")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Timestamp of the measurement")
    
    # Audio features
    pitch_mean: float = Field(..., description="Mean pitch")
    pitch_std: float = Field(..., description="Pitch standard deviation")
    energy_mean: float = Field(..., description="Mean energy")
    energy_std: float = Field(..., description="Energy standard deviation")
    speaking_rate: float = Field(..., description="Speaking rate")
    
    # Stress indicators
    stress_level: float = Field(..., ge=0.0, le=1.0, description="Stress level 0.0 - 1.0")
    stress_category: str = Field(..., description="Stress category: e.g., low, medium, high")
    
    # Confidence
    confidence: Optional[float] = Field(None, description="Confidence score 0.0 - 1.0")
    
    # Optional nested features
    stress_features: Optional["StressFeatures"] = Field(None, description="Linked StressFeatures")

class StressFeatures(BaseModel):
    feature_id: UUID = Field(..., description="Feature set identifier")
    audio_id: UUID = Field(..., description="Reference to AudioStress (audio_id)")
    
    # MFCC features (13 coefficients)
    mfcc_1: float = Field(..., description="MFCC 1")
    mfcc_2: float = Field(..., description="MFCC 2")
    mfcc_3: float = Field(..., description="MFCC 3")
    mfcc_4: float = Field(..., description="MFCC 4")
    mfcc_5: float = Field(..., description="MFCC 5")
    mfcc_6: float = Field(..., description="MFCC 6")
    mfcc_7: float = Field(..., description="MFCC 7")
    mfcc_8: float = Field(..., description="MFCC 8")
    mfcc_9: float = Field(..., description="MFCC 9")
    mfcc_10: float = Field(..., description="MFCC 10")
    mfcc_11: float = Field(..., description="MFCC 11")
    mfcc_12: float = Field(..., description="MFCC 12")
    mfcc_13: float = Field(..., description="MFCC 13")
    
    # Spectral features
    spectral_centroid: float = Field(..., description="Spectral centroid")
    spectral_bandwidth: float = Field(..., description="Spectral bandwidth")
    spectral_rolloff: float = Field(..., description="Spectral rolloff")
    zero_crossing_rate: float = Field(..., description="Zero-crossing rate")
    
    # HRV indicators (optional)
    hrv_estimate: Optional[float] = Field(None, description="HRV estimate")

class ProductivityMetrics(BaseModel):
    productivity_id: UUID = Field(..., description="Productivity metrics identifier")
    session_id: UUID = Field(..., description="Session reference")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Timestamp of the window")
    
    # Aggregated metrics (calculated every 5 minutes)
    focus_score: float = Field(..., ge=0.0, le=1.0, description="Focus score (0.0 - 1.0)")
    engagement_score: float = Field(..., ge=0.0, le=1.0, description="Engagement score (0.0 - 1.0)")
    stress_score: float = Field(..., ge=0.0, le=1.0, description="Stress score (0.0 - 1.0)")
    posture_score: float = Field(..., ge=0.0, le=1.0, description="Posture score (0.0 - 1.0)")
    
    # Composite KPI
    overall_productivity: float = Field(..., ge=0.0, le=1.0, description="Overall productivity (0.0 - 1.0)")
    
    # Time window
    window_start: datetime = Field(..., description="Start of the measurement window")
    window_end: datetime = Field(..., description="End of the measurement window")

class UserCalibration(BaseModel):
    calibration_id: UUID = Field(..., description="Calibration identifier")
    session_id: UUID = Field(..., description="Session reference")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    
    # Calibration status
    status: str = Field(..., description='Status: "pending" | "in_progress" | "completed" | "failed"')
    
    # Calibration points (4-point calibration)
    point_1_x: Optional[float] = Field(None, description="Calibration point 1 X")
    point_1_y: Optional[float] = Field(None, description="Calibration point 1 Y")
    point_2_x: Optional[float] = Field(None, description="Calibration point 2 X")
    point_2_y: Optional[float] = Field(None, description="Calibration point 2 Y")
    point_3_x: Optional[float] = Field(None, description="Calibration point 3 X")
    point_3_y: Optional[float] = Field(None, description="Calibration point 3 Y")
    point_4_x: Optional[float] = Field(None, description="Calibration point 4 X")
    point_4_y: Optional[float] = Field(None, description="Calibration point 4 Y")
    
    # Transformation matrix (JSON string)
    transform_matrix: Optional[EncryptedString] = Field(None, description="3x3 homography matrix in JSON/string form")
    
    # Calibration quality
    accuracy_score: Optional[float] = Field(None, description="Calibration accuracy (0.0 - 1.0)")
<![CDATA[
class SessionStartRequest(BaseModel):
    """Request schema for starting a new session."""
    user_id: str = Field(..., description="User identifier")
    device_info: Optional[str] = Field(None, description="Device information")
    os_version: Optional[str] = Field(None, description="OS version")

class SessionStartResponse(BaseModel):
    """Response schema for session start."""
    session_id: str = Field(..., description="Unique session identifier")
    start_time: datetime = Field(..., description="Session start timestamp")
    status: str = Field(..., description="Session status")

class SessionEndRequest(BaseModel):
    """Request schema for ending a session."""
    end_time: Optional[datetime] = Field(None, description="Session end time")

class SessionEndResponse(BaseModel):
    """Response schema for session end."""
    session_id: str
    end_time: datetime
    duration_seconds: float
    status: str

class SessionDetailResponse(BaseModel):
    """Response schema for session details."""
    session_id: str
    user_id: str
    start_time: datetime
    end_time: Optional[datetime]
    duration_seconds: Optional[float]
    status: str
    device_info: Optional[str]
    os_version: Optional[str]

class SessionListResponse(BaseModel):
    """Response schema for session list."""
    sessions: List[SessionDetailResponse]
    total: int
    page: int
    page_size: int

class CalibrationStartRequest(BaseModel):
    """Request schema for starting calibration."""
    session_id: str = Field(..., description="Session ID for calibration")

class CalibrationStartResponse(BaseModel):
    """Response schema for calibration start."""
    calibration_id: str
    session_id: str
    status: str
    created_at: datetime

class CalibrationPointSubmit(BaseModel):
    """Request schema for submitting calibration point."""
    point_number: int = Field(..., ge=1, le=4, description="Point number (1-4)")
    x: float = Field(..., description="X coordinate")
    y: float = Field(..., description="Y coordinate")

class CalibrationSubmitResponse(BaseModel):
    """Response schema for calibration point submission."""
    calibration_id: str
    points_completed: int
    total_points: int
    status: str
    accuracy_score: Optional[float]

class SessionMetricsResponse(BaseModel):
    """Response schema for session metrics."""
    session_id: str
    total_frames: int
    avg_focus_score: float
    avg_engagement_score: float
    avg_stress_score: float
    avg_posture_score: float
    overall_productivity: float

class FrameMetricsResponse(BaseModel):
    """Response schema for frame metrics."""
    frame_id: str
    session_id: str
    timestamp: datetime
    focus_score: float
    engagement_score: float
    has_gaze_data: bool
    has_pose_data: bool

class DashboardSummaryResponse(BaseModel):
    """Response schema for dashboard summary."""
    total_sessions: int
    active_sessions: int
    total_duration_hours: float
    avg_focus_score: float
    avg_productivity: float
    recent_sessions: List[SessionDetailResponse]
]]>