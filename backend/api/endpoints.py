from __future__ import annotations

import asyncio
import base64
import json
import logging
import time
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

import cv2
import numpy as np
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    WebSocket,
    WebSocketDisconnect,
)
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession

from backend.api.rate_limit import RateLimitExceeded, SimpleRateLimiter
from backend.db.database import get_db
from backend.db.models import (
    AudioStress,
    FrameMetrics,
    GazeData,
    HeadPose,
    ProductivityMetrics,
    Session as SessionModel,
    StressFeatures,
    UserCalibration,
)
from backend.ml.calibration import get_calibration_service
from backend.ml.gaze_estimator import get_gaze_estimator
from backend.ml.integration import IntegrationPipeline
from backend.ml.pose_estimator import get_pose_estimator
from backend.ml.stress_analyzer import get_stress_analyzer
from backend.ws.manager import gaze_broker, pose_broker, stress_broker

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["eaglearn"])
api_router = APIRouter(prefix="/api", tags=["sessions"])

_session_create_limiter = SimpleRateLimiter(limit=10, window_seconds=60)
_session_read_limiter = SimpleRateLimiter(limit=60, window_seconds=60)
_calibration_limiter = SimpleRateLimiter(limit=30, window_seconds=60)
_metrics_limiter = SimpleRateLimiter(limit=120, window_seconds=60)

_pipeline = IntegrationPipeline()
_pipeline_lock = asyncio.Lock()


def _client_key(request: Request) -> str:
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _enforce_limit(limiter: SimpleRateLimiter, request: Request) -> None:
    try:
        limiter.hit(_client_key(request))
    except RateLimitExceeded as exc:
        retry_after = max(0, int(exc.reset_timestamp - time.time()))
        raise HTTPException(
            status_code=429,
            detail={"message": "Rate limit exceeded", "retry_after": retry_after},
        ) from exc


async def _session_create_rate_limit(request: Request) -> None:
    _enforce_limit(_session_create_limiter, request)


async def _session_read_rate_limit(request: Request) -> None:
    _enforce_limit(_session_read_limiter, request)


async def _calibration_rate_limit(request: Request) -> None:
    _enforce_limit(_calibration_limiter, request)


async def _metrics_rate_limit(request: Request) -> None:
    _enforce_limit(_metrics_limiter, request)


def reset_rate_limiters() -> None:
    """Utility to clear in-memory rate limiter state (useful for tests)."""
    _session_create_limiter.reset()
    _session_read_limiter.reset()
    _calibration_limiter.reset()
    _metrics_limiter.reset()


class GazePredictRequest(BaseModel):
    frame_id: str
    timestamp: str
    frame_data: str
    calibration_id: str
    metadata: Dict[str, Any]


class GazePredictResponse(BaseModel):
    frame_id: str
    processing_timestamp: str
    gaze_result: Dict[str, Any]
    calibration_info: Dict[str, Any]
    error: Optional[Dict[str, Any]] = None


class PoseEstimateRequest(BaseModel):
    frame_id: str
    timestamp: str
    frame_data: str
    face_bbox: Dict[str, int]


class PoseEstimateResponse(BaseModel):
    frame_id: str
    processing_timestamp: str
    pose_result: Dict[str, Any]
    error: Optional[Dict[str, Any]] = None


class StressAnalyzeRequest(BaseModel):
    audio_id: str
    session_id: str
    window_start: str
    window_end: str
    audio_data: str
    sample_rate: int
    channels: int
    metadata: Dict[str, Any]


class StressAnalyzeResponse(BaseModel):
    audio_id: str
    processing_timestamp: str
    stress_result: Dict[str, Any]
    error: Optional[Dict[str, Any]] = None


class PipelineCalibrationPayload(BaseModel):
    screen_points: List[List[float]]
    gaze_points: Optional[List[List[float]]] = None


class PipelineProcessRequest(BaseModel):
    session_id: Optional[str] = None
    timestamp: Optional[datetime] = None
    frame_data: str
    frame_encoding: str = "jpeg"
    audio_data: str
    audio_format: str = "float32"
    original_sample_rate: int = 16_000
    reset_calibration: bool = False
    calibration: Optional[PipelineCalibrationPayload] = None


class PipelineProcessResponse(BaseModel):
    timestamp: datetime
    frame_id: str
    audio_id: str
    latencies_ms: Dict[str, float]
    gaze: Dict[str, Any]
    pose: Dict[str, Any]
    stress: Dict[str, Any]
    metrics: Dict[str, Any]
    rest_payloads: Dict[str, Dict[str, Any]]
    websocket_messages: List[Dict[str, Any]]
    rolling_summary: Dict[str, float]


class SessionMetricsPayload(BaseModel):
    productivity_score: float
    total_breaks: int
    avg_break_duration: float
    break_pattern_type: str
    latest_stress_score: Optional[float] = None
    latest_posture_class: Optional[str] = None


class SessionCreateRequest(BaseModel):
    user_id: str
    user_consent: bool
    calibration_id: Optional[str] = Field(
        default=None, description="Existing calibration identifier"
    )
    estimated_duration_minutes: int = Field(default=60, ge=1, le=480)
    device_info: Optional[str] = None
    os_version: Optional[str] = None


class SessionCreateResponse(BaseModel):
    session_id: str
    status: str
    start_time: datetime
    estimated_duration_minutes: int
    calibration_status: str


class SessionDetailResponse(BaseModel):
    session_id: str
    user_id: str
    status: str
    start_time: datetime
    end_time: Optional[datetime]
    duration_minutes: int
    on_task_ratio: float
    avg_engagement_score: Optional[float]
    avg_fatigue_score: Optional[float]
    metrics: Optional[SessionMetricsPayload] = None


class SessionListItem(BaseModel):
    session_id: str
    status: str
    start_time: datetime
    end_time: Optional[datetime]
    duration_minutes: int


class SessionListResponse(BaseModel):
    sessions: List[SessionListItem]
    total_count: int
    limit: int
    offset: int


class CalibrationCreateRequest(BaseModel):
    user_id: str
    gaze_model_version: str
    calibration_error: float = Field(..., ge=0.0)
    screen_dimensions: str
    camera_position: str


class CalibrationResponse(BaseModel):
    calibration_id: str
    user_id: str
    calibration_date: datetime
    gaze_model_version: str
    calibration_error: float
    status: str
    screen_dimensions: str
    camera_position: str


class GazeMetricsRequest(BaseModel):
    session_id: str
    frame_id: str
    timestamp: datetime
    gaze_x: float
    gaze_y: float
    gaze_direction: Optional[str] = None
    gaze_angle: Optional[float] = None
    gaze_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class PoseMetricsRequest(BaseModel):
    session_id: str
    frame_id: str
    timestamp: datetime
    pitch_angle: float = Field(..., ge=-90.0, le=90.0)
    yaw_angle: float = Field(..., ge=-90.0, le=90.0)
    roll_angle: float = Field(..., ge=-90.0, le=90.0)
    posture_class: str
    head_pose_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class StressMetricsRequest(BaseModel):
    session_id: str
    audio_id: str
    window_start: datetime
    window_end: datetime
    stress_score: float = Field(..., ge=0.0, le=100.0)
    vocal_effort: float = Field(..., ge=0.0)
    smoothing_count: int = Field(default=0, ge=0)
    signal_quality: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class ProductivityMetricsRequest(BaseModel):
    session_id: str
    total_breaks: int = Field(..., ge=0)
    avg_break_duration: float = Field(..., ge=0.0)
    break_pattern_type: str
    productivity_score: float = Field(..., ge=0.0, le=100.0)


class GenericSuccessResponse(BaseModel):
    status: str = "ok"
    resource_id: Optional[str] = None


class DashboardSessionSummary(BaseModel):
    session_id: str
    status: str
    productivity_score: Optional[float]
    stress_score: Optional[float]
    started_at: datetime


class DashboardSummaryResponse(BaseModel):
    total_sessions: int
    active_sessions: int
    completed_sessions: int
    avg_productivity_score: Optional[float]
    avg_stress_score: Optional[float]
    recent_sessions: List[DashboardSessionSummary]


class TrendPointResponse(BaseModel):
    label: str
    value: float


class AnalyticsTrendsResponse(BaseModel):
    productivity: List[TrendPointResponse]
    stress: List[TrendPointResponse]
    engagement: List[TrendPointResponse]


class CalibrationSubmitRequest(BaseModel):
    screen_points: List[List[float]]
    gaze_points: Optional[List[List[float]]] = None


class CalibrationSubmitResponse(BaseModel):
    calibration_id: str
    transform_matrix: List[List[float]]
    accuracy: float
    status: Optional[str] = None

@router.websocket("/ws/gaze")
async def websocket_gaze(websocket: WebSocket) -> None:
    # CRITICAL: Accept HARUS dipanggil di handler, BUKAN di broker
    await websocket.accept()
    
    # Setelah accept, baru register ke broker (tanpa accept lagi)
    connection_id = await gaze_broker.register_connection(websocket)
    
    try:
        while True:
            data = None
            try:
                data = await websocket.receive_json()
            except Exception:
                try:
                    text = await websocket.receive_text()
                    data = json.loads(text) if text else None
                except Exception:
                    data = None

            if isinstance(data, dict) and data.get("type") == "pong":
                gaze_broker.handle_pong(websocket)
                continue
    except WebSocketDisconnect:
        gaze_broker.disconnect(websocket)


@router.websocket("/ws/pose")
async def websocket_pose(websocket: WebSocket) -> None:
    # CRITICAL: Accept HARUS dipanggil di handler, BUKAN di broker
    await websocket.accept()
    
    # Setelah accept, baru register ke broker (tanpa accept lagi)
    connection_id = await pose_broker.register_connection(websocket)
    
    try:
        while True:
            data = None
            try:
                data = await websocket.receive_json()
            except Exception:
                try:
                    text = await websocket.receive_text()
                    data = json.loads(text) if text else None
                except Exception:
                    data = None

            if isinstance(data, dict) and data.get("type") == "pong":
                pose_broker.handle_pong(websocket)
                continue
    except WebSocketDisconnect:
        pose_broker.disconnect(websocket)


@router.websocket("/ws/stress")
async def websocket_stress(websocket: WebSocket) -> None:
    # CRITICAL: Accept HARUS dipanggil di handler, BUKAN di broker
    await websocket.accept()
    
    # Setelah accept, baru register ke broker (tanpa accept lagi)
    connection_id = await stress_broker.register_connection(websocket)
    
    try:
        while True:
            data = None
            try:
                data = await websocket.receive_json()
            except Exception:
                try:
                    text = await websocket.receive_text()
                    data = json.loads(text) if text else None
                except Exception:
                    data = None

            if isinstance(data, dict) and data.get("type") == "pong":
                stress_broker.handle_pong(websocket)
                continue
    except WebSocketDisconnect:
        stress_broker.disconnect(websocket)

@router.post("/gaze/predict", response_model=GazePredictResponse)
async def gaze_predict(
    request: GazePredictRequest, db: DBSession = Depends(get_db)
) -> GazePredictResponse:
    estimator = get_gaze_estimator()
    frame_bytes = base64.b64decode(request.frame_data)
    frame_array = np.frombuffer(frame_bytes, dtype=np.uint8)
    frame = cv2.imdecode(frame_array, cv2.IMREAD_COLOR)
    if frame is None:
        raise HTTPException(status_code=400, detail="Invalid frame data")

    result = estimator.predict(frame)
    calibration_info = {
        "calibration_id": request.calibration_id,
        "model_version": result.get("model_version", "unknown"),
        "calibration_error": result.get("calibration_error", 0.0),
    }
    now_iso = datetime.utcnow().isoformat()

    gaze_data = GazeData(
        frame_id=request.frame_id,
        gaze_x=result.get("gaze_x"),
        gaze_y=result.get("gaze_y"),
        gaze_direction=result.get("gaze_direction"),
        gaze_angle=result.get("gaze_angle"),
        timestamp=datetime.fromisoformat(request.timestamp),
    )
    db.add(gaze_data)
    db.commit()

    return GazePredictResponse(
        frame_id=request.frame_id,
        processing_timestamp=now_iso,
        gaze_result=result,
        calibration_info=calibration_info,
        error=None,
    )


@router.post("/pose/estimate", response_model=PoseEstimateResponse)
async def pose_estimate(
    request: PoseEstimateRequest, db: DBSession = Depends(get_db)
) -> PoseEstimateResponse:
    estimator = get_pose_estimator()
    frame_bytes = base64.b64decode(request.frame_data)
    frame_array = np.frombuffer(frame_bytes, dtype=np.uint8)
    frame = cv2.imdecode(frame_array, cv2.IMREAD_COLOR)
    if frame is None:
        raise HTTPException(status_code=400, detail="Invalid frame data")

    result = estimator.estimate(frame, request.face_bbox)
    now_iso = datetime.utcnow().isoformat()

    pose = HeadPose(
        frame_id=request.frame_id,
        timestamp=datetime.fromisoformat(request.timestamp),
        pitch_angle=result.get("pitch_angle"),
        yaw_angle=result.get("yaw_angle"),
        roll_angle=result.get("roll_angle"),
        posture_class=result.get("posture_class", "unknown"),
    )
    db.add(pose)
    db.commit()

    return PoseEstimateResponse(
        frame_id=request.frame_id,
        processing_timestamp=now_iso,
        pose_result=result,
        error=None,
    )


@router.post("/stress/analyze", response_model=StressAnalyzeResponse)
async def stress_analyze(
    request: StressAnalyzeRequest, db: DBSession = Depends(get_db)
) -> StressAnalyzeResponse:
    analyzer = get_stress_analyzer()
    audio_bytes = base64.b64decode(request.audio_data)

    try:
        audio_array = np.frombuffer(audio_bytes, dtype=np.float32)
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=400, detail="Unable to parse audio data") from exc

    result = analyzer.analyze(audio_array)
    window_start = datetime.fromisoformat(request.window_start)
    window_end = datetime.fromisoformat(request.window_end)

    audio_record = AudioStress(
        audio_id=request.audio_id,
        session_id=request.session_id,
        window_start=window_start,
        window_end=window_end,
        stress_score=result.get("stress_level", 0.0),
        vocal_effort=result.get("confidence", 0.0),
        smoothing_count=0,
        signal_quality=result.get("signal_quality"),
    )
    db.add(audio_record)

    features_record = StressFeatures(
        audio_stress=audio_record,
        lf_power=result.get("features", {}).get("lf_power", 0.0),
        hf_power=result.get("features", {}).get("hf_power", 0.0),
        lf_hf_ratio=result.get("features", {}).get("lf_hf_ratio", 0.0),
        heart_rate=result.get("features", {}).get("heart_rate", 75.0),
        breathing_rate=result.get("features", {}).get("breathing_rate", 0.2),
    )
    db.add(features_record)
    db.commit()

    payload = {
        "stress_level": result.get("stress_level", 0.0),
        "stress_category": result.get("stress_category", "low"),
        "confidence": result.get("confidence", 0.0),
        "features": result.get("features", {}),
    }
    await stress_broker.broadcast(json.dumps(payload))

    return StressAnalyzeResponse(
        audio_id=request.audio_id,
        processing_timestamp=datetime.utcnow().isoformat(),
        stress_result=payload,
        error=None,
    )


@router.post("/pipeline/process", response_model=PipelineProcessResponse)
async def process_multimodal_payload(
    request: PipelineProcessRequest,
) -> PipelineProcessResponse:
    if not request.audio_data:
        raise HTTPException(status_code=400, detail="audio_data is required")

    try:
        frame_bytes = base64.b64decode(request.frame_data)
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=400, detail="Invalid frame data encoding") from exc

    encoding = (request.frame_encoding or "jpeg").lower()
    if encoding not in {"jpeg", "jpg", "png"}:
        raise HTTPException(
            status_code=400,
            detail="Unsupported frame_encoding; expected jpeg or png",
        )

    frame_array = np.frombuffer(frame_bytes, dtype=np.uint8)
    frame = cv2.imdecode(frame_array, cv2.IMREAD_COLOR)
    if frame is None:
        raise HTTPException(status_code=400, detail="Unable to decode frame data")

    if request.audio_format.lower() != "float32":
        raise HTTPException(
            status_code=400, detail="Unsupported audio_format; expected float32"
        )

    try:
        audio_bytes = base64.b64decode(request.audio_data)
        audio = np.frombuffer(audio_bytes, dtype=np.float32)
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=400, detail="Invalid audio data encoding") from exc

    if audio.size == 0:
        # Ensure downstream components receive a non-empty buffer.
        audio = np.zeros(1, dtype=np.float32)

    async with _pipeline_lock:
        if request.reset_calibration:
            _pipeline.reset_calibration()
        if request.calibration:
            _pipeline.update_calibration(
                screen_points=request.calibration.screen_points,
                gaze_points=request.calibration.gaze_points,
            )

        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None,
            lambda: _pipeline.process(
                frame=frame,
                audio=audio,
                original_sample_rate=request.original_sample_rate,
                session_id=request.session_id,
                timestamp=request.timestamp,
            ),
        )

    telemetry = result.telemetry
    return PipelineProcessResponse(
        timestamp=telemetry.timestamp,
        frame_id=telemetry.frame_id,
        audio_id=telemetry.audio_id,
        latencies_ms=telemetry.latencies_ms,
        gaze=result.gaze,
        pose=result.pose,
        stress=result.stress,
        metrics=result.metrics,
        rest_payloads=result.rest_payloads,
        websocket_messages=result.websocket_messages,
        rolling_summary=result.rolling_summary,
    )

@api_router.post("/sessions", response_model=SessionCreateResponse)
async def create_session_endpoint(
    payload: SessionCreateRequest,
    db: DBSession = Depends(get_db),
    _: None = Depends(_session_create_rate_limit),
) -> SessionCreateResponse:
    # DEBUG LOGGING
    print(f"DEBUG: RAW Session Payload: {payload.dict()}")
    logger.info(f"Session create request received: {payload.dict()}")
    
    if not payload.user_consent:
        logger.warning("Session creation denied: User consent missing")
        raise HTTPException(status_code=400, detail="User consent required")

    calibration_status = "missing"
    calibration_ref: Optional[UserCalibration] = None
    if payload.calibration_id:
        calibration_ref = (
            db.query(UserCalibration)
            .filter(
                UserCalibration.calibration_id == payload.calibration_id,
                UserCalibration.deleted_at.is_(None),
            )
            .order_by(UserCalibration.calibration_date.desc())
            .first()
        )
        if calibration_ref is None:
            raise HTTPException(status_code=422, detail="Calibration not found")
        if calibration_ref.calibration_error > 15:
            raise HTTPException(
                status_code=422,
                detail="Calibration error exceeds acceptable threshold",
            )
        calibration_status = "valid"

    try:
        session_record = SessionModel(
            user_id=payload.user_id,
            calibration_id=calibration_ref.calibration_id if calibration_ref else None,
            estimated_duration_minutes=payload.estimated_duration_minutes,
            device_info=payload.device_info,
            os_version=payload.os_version,
            on_task_ratio=0.0,
        )
        db.add(session_record)
        db.flush()

        productivity_record = ProductivityMetrics(
            session_id=session_record.session_id,
            total_breaks=0,
            avg_break_duration=0.0,
            break_pattern_type="unknown",
            productivity_score=0.0,
        )
        db.add(productivity_record)
        db.commit()
        db.refresh(session_record)
    except Exception as exc:  # pragma: no cover - defensive
        db.rollback()
        logger.exception(f"Session creation failed for user {payload.user_id}", exc_info=exc)
        print(f"DEBUG: Session creation failed exception: {exc}")
        raise HTTPException(status_code=500, detail=f"Failed to create session: {str(exc)}") from exc

    logger.info(f"Session created successfully: {session_record.session_id}")
    return SessionCreateResponse(
        session_id=session_record.session_id,
        status=session_record.status,
        start_time=session_record.start_time,
        estimated_duration_minutes=session_record.estimated_duration_minutes,
        calibration_status=calibration_status,
    )


@api_router.get("/sessions/{session_id}", response_model=SessionDetailResponse)
async def get_session_endpoint(
    session_id: str,
    include_metrics: bool = False,
    db: DBSession = Depends(get_db),
    _: None = Depends(_session_read_rate_limit),
) -> SessionDetailResponse:
    session = (
        db.query(SessionModel)
        .filter(
            SessionModel.session_id == session_id,
            SessionModel.deleted_at.is_(None),
        )
        .first()
    )
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    metrics_payload: Optional[SessionMetricsPayload] = None
    if include_metrics and session.productivity_metrics:
        productivity = session.productivity_metrics
        latest_stress = (
            db.query(AudioStress.stress_score)
            .filter(AudioStress.session_id == session_id)
            .order_by(AudioStress.window_end.desc())
            .limit(1)
            .scalar()
        )
        latest_posture = (
            db.query(HeadPose.posture_class)
            .join(FrameMetrics, HeadPose.frame_id == FrameMetrics.frame_id)
            .filter(FrameMetrics.session_id == session_id)
            .order_by(HeadPose.timestamp.desc())
            .limit(1)
            .scalar()
        )
        metrics_payload = SessionMetricsPayload(
            productivity_score=productivity.productivity_score,
            total_breaks=productivity.total_breaks,
            avg_break_duration=productivity.avg_break_duration,
            break_pattern_type=productivity.break_pattern_type,
            latest_stress_score=float(latest_stress) if latest_stress is not None else None,
            latest_posture_class=latest_posture,
        )

    return SessionDetailResponse(
        session_id=session.session_id,
        user_id=session.user_id,
        status=session.status,
        start_time=session.start_time,
        end_time=session.end_time,
        duration_minutes=session.duration_minutes,
        on_task_ratio=session.on_task_ratio,
        avg_engagement_score=session.avg_engagement_score,
        avg_fatigue_score=session.avg_fatigue_score,
        metrics=metrics_payload,
    )


@api_router.get("/sessions", response_model=SessionListResponse)
async def list_sessions_endpoint(
    limit: int = 20,
    offset: int = 0,
    status: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    db: DBSession = Depends(get_db),
    _: None = Depends(_session_read_rate_limit),
) -> SessionListResponse:
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 100")
    if offset < 0:
        raise HTTPException(status_code=400, detail="offset must be >= 0")

    query = db.query(SessionModel).filter(SessionModel.deleted_at.is_(None))
    if status:
        query = query.filter(SessionModel.status == status)
    if date_from:
        query = query.filter(SessionModel.start_time >= date_from)
    if date_to:
        query = query.filter(SessionModel.start_time <= date_to)

    total = query.count()
    records = (
        query.order_by(SessionModel.start_time.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return SessionListResponse(
        sessions=[
            SessionListItem(
                session_id=record.session_id,
                status=record.status,
                start_time=record.start_time,
                end_time=record.end_time,
                duration_minutes=record.duration_minutes,
            )
            for record in records
        ],
        total_count=total,
        limit=limit,
        offset=offset,
    )


@api_router.delete("/sessions/{session_id}", response_model=GenericSuccessResponse)
async def delete_session_endpoint(
    session_id: str,
    db: DBSession = Depends(get_db),
    _: None = Depends(_session_read_rate_limit),
) -> GenericSuccessResponse:
    session = (
        db.query(SessionModel)
        .filter(
            SessionModel.session_id == session_id,
            SessionModel.deleted_at.is_(None),
        )
        .first()
    )
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        now = datetime.utcnow()
        session.status = "deleted"
        session.deleted_at = now
        if session.productivity_metrics:
            session.productivity_metrics.deleted_at = now
        db.commit()
    except Exception as exc:  # pragma: no cover - defensive
        db.rollback()
        logger.exception("Session delete failed", exc_info=exc)
        raise HTTPException(status_code=500, detail="Failed to delete session") from exc

    return GenericSuccessResponse(status="deleted", resource_id=session_id)

@api_router.post("/calibration", response_model=CalibrationResponse)
async def create_calibration_endpoint(
    payload: CalibrationCreateRequest,
    db: DBSession = Depends(get_db),
    _: None = Depends(_calibration_rate_limit),
) -> CalibrationResponse:
    logger.info(f"Calibration create request: {payload.dict()}")
    try:
        calibration = UserCalibration(
            user_id=payload.user_id,
            gaze_model_version=payload.gaze_model_version,
            calibration_error=payload.calibration_error,
            screen_dimensions=payload.screen_dimensions,
            camera_position=payload.camera_position,
            status="completed" if payload.calibration_error <= 15 else "needs_review",
        )
        db.add(calibration)
        db.commit()
        db.refresh(calibration)
    except Exception as exc:  # pragma: no cover - defensive
        db.rollback()
        logger.exception(f"Calibration save failed for user {payload.user_id}", exc_info=exc)
        raise HTTPException(status_code=500, detail="Failed to save calibration") from exc

    logger.info(f"Calibration created: {calibration.calibration_id}")
    return CalibrationResponse(
        calibration_id=calibration.calibration_id,
        user_id=calibration.user_id,
        calibration_date=calibration.calibration_date,
        gaze_model_version=calibration.gaze_model_version,
        calibration_error=calibration.calibration_error,
        status=calibration.status,
        screen_dimensions=calibration.screen_dimensions,
        camera_position=calibration.camera_position,
    )


@api_router.get("/calibration/{user_id}", response_model=CalibrationResponse)
async def get_calibration_endpoint(
    user_id: str,
    db: DBSession = Depends(get_db),
    _: None = Depends(_calibration_rate_limit),
) -> CalibrationResponse:
    calibration = (
        db.query(UserCalibration)
        .filter(
            UserCalibration.user_id == user_id,
            UserCalibration.deleted_at.is_(None),
        )
        .order_by(UserCalibration.calibration_date.desc())
        .first()
    )
    if calibration is None:
        raise HTTPException(status_code=404, detail="Calibration not found")

    return CalibrationResponse(
        calibration_id=calibration.calibration_id,
        user_id=calibration.user_id,
        calibration_date=calibration.calibration_date,
        gaze_model_version=calibration.gaze_model_version,
        calibration_error=calibration.calibration_error,
        status=calibration.status,
        screen_dimensions=calibration.screen_dimensions,
        camera_position=calibration.camera_position,
    )

@api_router.post("/metrics/gaze", response_model=GenericSuccessResponse)
async def ingest_gaze_metrics(
    payload: GazeMetricsRequest,
    db: DBSession = Depends(get_db),
    _: None = Depends(_metrics_rate_limit),
) -> GenericSuccessResponse:
    session_exists = (
        db.query(SessionModel.session_id)
        .filter(
            SessionModel.session_id == payload.session_id,
            SessionModel.deleted_at.is_(None),
        )
        .first()
    )
    if session_exists is None:
        raise HTTPException(status_code=404, detail="Session not found")

    frame = db.query(FrameMetrics).filter_by(frame_id=payload.frame_id).first()
    if frame is None:
        frame = FrameMetrics(
            frame_id=payload.frame_id,
            session_id=payload.session_id,
            timestamp=payload.timestamp,
            gaze_confidence=payload.gaze_confidence,
        )
        db.add(frame)
    else:
        frame.session_id = payload.session_id
        frame.timestamp = payload.timestamp
        frame.gaze_confidence = payload.gaze_confidence

    gaze = GazeData(
        frame_id=payload.frame_id,
        gaze_x=payload.gaze_x,
        gaze_y=payload.gaze_y,
        gaze_direction=payload.gaze_direction,
        gaze_angle=payload.gaze_angle,
        timestamp=payload.timestamp,
    )
    db.add(gaze)

    try:
        db.commit()
        db.refresh(gaze)
    except Exception as exc:  # pragma: no cover - defensive
        db.rollback()
        logger.exception("Gaze metrics ingestion failed", exc_info=exc)
        raise HTTPException(status_code=500, detail="Failed to store gaze metrics") from exc

    return GenericSuccessResponse(resource_id=gaze.gaze_id)


@api_router.post("/metrics/pose", response_model=GenericSuccessResponse)
async def ingest_pose_metrics(
    payload: PoseMetricsRequest,
    db: DBSession = Depends(get_db),
    _: None = Depends(_metrics_rate_limit),
) -> GenericSuccessResponse:
    session_exists = (
        db.query(SessionModel.session_id)
        .filter(
            SessionModel.session_id == payload.session_id,
            SessionModel.deleted_at.is_(None),
        )
        .first()
    )
    if session_exists is None:
        raise HTTPException(status_code=404, detail="Session not found")

    frame = db.query(FrameMetrics).filter_by(frame_id=payload.frame_id).first()
    if frame is None:
        frame = FrameMetrics(
            frame_id=payload.frame_id,
            session_id=payload.session_id,
            timestamp=payload.timestamp,
            head_pose_confidence=payload.head_pose_confidence,
        )
        db.add(frame)
    else:
        frame.session_id = payload.session_id
        frame.timestamp = payload.timestamp
        frame.head_pose_confidence = payload.head_pose_confidence

    pose = db.query(HeadPose).filter_by(frame_id=payload.frame_id).first()
    if pose is None:
        pose = HeadPose(
            frame_id=payload.frame_id,
            timestamp=payload.timestamp,
            pitch_angle=payload.pitch_angle,
            yaw_angle=payload.yaw_angle,
            roll_angle=payload.roll_angle,
            posture_class=payload.posture_class,
        )
        db.add(pose)
    else:
        pose.timestamp = payload.timestamp
        pose.pitch_angle = payload.pitch_angle
        pose.yaw_angle = payload.yaw_angle
        pose.roll_angle = payload.roll_angle
        pose.posture_class = payload.posture_class

    try:
        db.commit()
        db.refresh(pose)
    except Exception as exc:  # pragma: no cover - defensive
        db.rollback()
        logger.exception("Pose metrics ingestion failed", exc_info=exc)
        raise HTTPException(status_code=500, detail="Failed to store pose metrics") from exc

    return GenericSuccessResponse(resource_id=pose.pose_id)


@api_router.post("/metrics/stress", response_model=GenericSuccessResponse)
async def ingest_stress_metrics(
    payload: StressMetricsRequest,
    db: DBSession = Depends(get_db),
    _: None = Depends(_metrics_rate_limit),
) -> GenericSuccessResponse:
    if payload.window_end <= payload.window_start:
        raise HTTPException(
            status_code=400, detail="window_end must be after window_start"
        )

    session_exists = (
        db.query(SessionModel.session_id)
        .filter(
            SessionModel.session_id == payload.session_id,
            SessionModel.deleted_at.is_(None),
        )
        .first()
    )
    if session_exists is None:
        raise HTTPException(status_code=404, detail="Session not found")

    audio_record = AudioStress(
        audio_id=payload.audio_id,
        session_id=payload.session_id,
        window_start=payload.window_start,
        window_end=payload.window_end,
        stress_score=payload.stress_score,
        vocal_effort=payload.vocal_effort,
        smoothing_count=payload.smoothing_count,
        signal_quality=payload.signal_quality,
    )
    db.add(audio_record)

    features_record = StressFeatures(
        audio_stress=audio_record,
        lf_power=0.0,
        hf_power=0.0,
        lf_hf_ratio=0.0,
        heart_rate=75.0,
        breathing_rate=0.2,
    )
    db.add(features_record)

    try:
        db.commit()
        db.refresh(audio_record)
    except Exception as exc:  # pragma: no cover - defensive
        db.rollback()
        logger.exception("Stress metrics ingestion failed", exc_info=exc)
        raise HTTPException(status_code=500, detail="Failed to store stress metrics") from exc

    return GenericSuccessResponse(resource_id=audio_record.audio_id)


@api_router.post("/metrics/productivity", response_model=GenericSuccessResponse)
async def ingest_productivity_metrics(
    payload: ProductivityMetricsRequest,
    db: DBSession = Depends(get_db),
    _: None = Depends(_metrics_rate_limit),
) -> GenericSuccessResponse:
    session_exists = (
        db.query(SessionModel.session_id)
        .filter(
            SessionModel.session_id == payload.session_id,
            SessionModel.deleted_at.is_(None),
        )
        .first()
    )
    if session_exists is None:
        raise HTTPException(status_code=404, detail="Session not found")

    record = db.query(ProductivityMetrics).filter_by(session_id=payload.session_id).first()
    try:
        if record is None:
            record = ProductivityMetrics(
                session_id=payload.session_id,
                total_breaks=payload.total_breaks,
                avg_break_duration=payload.avg_break_duration,
                break_pattern_type=payload.break_pattern_type,
                productivity_score=payload.productivity_score,
            )
            db.add(record)
        else:
            record.total_breaks = payload.total_breaks
            record.avg_break_duration = payload.avg_break_duration
            record.break_pattern_type = payload.break_pattern_type
            record.productivity_score = payload.productivity_score
            record.calculated_at = datetime.utcnow()
            record.deleted_at = None
        db.commit()
        db.refresh(record)
    except Exception as exc:  # pragma: no cover - defensive
        db.rollback()
        logger.exception("Productivity metrics ingestion failed", exc_info=exc)
        raise HTTPException(
            status_code=500, detail="Failed to store productivity metrics"
        ) from exc

    return GenericSuccessResponse(resource_id=record.productivity_id)

@api_router.get("/dashboard/summary", response_model=DashboardSummaryResponse)
async def get_dashboard_summary(
    db: DBSession = Depends(get_db),
    _: None = Depends(_session_read_rate_limit),
) -> DashboardSummaryResponse:
    total_sessions = (
        db.query(SessionModel)
        .filter(SessionModel.deleted_at.is_(None))
        .count()
    )
    active_sessions = (
        db.query(SessionModel)
        .filter(SessionModel.deleted_at.is_(None), SessionModel.status == "active")
        .count()
    )
    completed_sessions = (
        db.query(SessionModel)
        .filter(SessionModel.deleted_at.is_(None), SessionModel.status == "completed")
        .count()
    )

    avg_productivity = (
        db.query(func.avg(ProductivityMetrics.productivity_score))
        .filter(ProductivityMetrics.deleted_at.is_(None))
        .scalar()
    )
    avg_stress = db.query(func.avg(AudioStress.stress_score)).scalar()

    recent_records = (
        db.query(SessionModel)
        .filter(SessionModel.deleted_at.is_(None))
        .order_by(SessionModel.start_time.desc())
        .limit(5)
        .all()
    )

    recent_payload: List[DashboardSessionSummary] = []
    for record in recent_records:
        productivity_score = (
            record.productivity_metrics.productivity_score
            if record.productivity_metrics
            else None
        )
        latest_stress = (
            db.query(AudioStress.stress_score)
            .filter(AudioStress.session_id == record.session_id)
            .order_by(AudioStress.window_end.desc())
            .limit(1)
            .scalar()
        )
        recent_payload.append(
            DashboardSessionSummary(
                session_id=record.session_id,
                status=record.status,
                productivity_score=productivity_score,
                stress_score=float(latest_stress) if latest_stress is not None else None,
                started_at=record.start_time,
            )
        )

    return DashboardSummaryResponse(
        total_sessions=total_sessions,
        active_sessions=active_sessions,
        completed_sessions=completed_sessions,
        avg_productivity_score=float(avg_productivity) if avg_productivity is not None else None,
        avg_stress_score=float(avg_stress) if avg_stress is not None else None,
        recent_sessions=recent_payload,
    )


@api_router.get("/analytics/trends", response_model=AnalyticsTrendsResponse)
async def get_analytics_trends(
    db: DBSession = Depends(get_db),
    _: None = Depends(_session_read_rate_limit),
) -> AnalyticsTrendsResponse:
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    window_start = today - timedelta(days=6)
    window_end = today + timedelta(days=1)

    def _label(raw_day: object) -> str:
        if isinstance(raw_day, str):
            return raw_day
        if isinstance(raw_day, (datetime, date)):
            return raw_day.strftime("%Y-%m-%d")
        return str(raw_day)

    productivity_rows = (
        db.query(
            func.date(SessionModel.start_time).label("day"),
            func.avg(ProductivityMetrics.productivity_score).label("avg_score"),
        )
        .join(
            SessionModel,
            ProductivityMetrics.session_id == SessionModel.session_id,
        )
        .filter(
            SessionModel.start_time >= window_start,
            SessionModel.start_time < window_end,
            SessionModel.deleted_at.is_(None),
            ProductivityMetrics.deleted_at.is_(None),
        )
        .group_by("day")
        .all()
    )
    stress_rows = (
        db.query(
            func.date(AudioStress.window_start).label("day"),
            func.avg(AudioStress.stress_score).label("avg_score"),
        )
        .filter(
            AudioStress.window_start >= window_start,
            AudioStress.window_start < window_end,
            AudioStress.deleted_at.is_(None),
        )
        .group_by("day")
        .all()
    )
    engagement_rows = (
        db.query(
            func.date(SessionModel.start_time).label("day"),
            func.avg(SessionModel.avg_engagement_score).label("avg_score"),
        )
        .filter(
            SessionModel.start_time >= window_start,
            SessionModel.start_time < window_end,
            SessionModel.deleted_at.is_(None),
        )
        .group_by("day")
        .all()
    )

    productivity_map = {
        _label(row.day): float(row.avg_score)
        for row in productivity_rows
        if row.avg_score is not None
    }
    stress_map = {
        _label(row.day): float(row.avg_score)
        for row in stress_rows
        if row.avg_score is not None
    }
    engagement_map = {
        _label(row.day): float(row.avg_score)
        for row in engagement_rows
        if row.avg_score is not None
    }

    productivity_points: List[TrendPointResponse] = []
    stress_points: List[TrendPointResponse] = []
    engagement_points: List[TrendPointResponse] = []

    for offset in range(6, -1, -1):
        day_start = today - timedelta(days=offset)
        label = day_start.strftime("%Y-%m-%d")

        productivity_points.append(
            TrendPointResponse(
                label=label,
                value=productivity_map.get(label, 0.0),
            )
        )
        stress_points.append(
            TrendPointResponse(
                label=label,
                value=stress_map.get(label, 0.0),
            )
        )
        engagement_points.append(
            TrendPointResponse(
                label=label,
                value=engagement_map.get(label, 0.0),
            )
        )

    return AnalyticsTrendsResponse(
        productivity=productivity_points,
        stress=stress_points,
        engagement=engagement_points,
    )

@api_router.post(
    "/calibration/{calibration_id}/submit", response_model=CalibrationSubmitResponse
)
async def submit_calibration_point(
    calibration_id: str,
    request: CalibrationSubmitRequest,
    db: DBSession = Depends(get_db),
) -> CalibrationSubmitResponse:
    # DEBUG LOGGING
    print(f"DEBUG: Calibration Submit ID: {calibration_id}")
    print(f"DEBUG: Calibration Points Count: {len(request.screen_points)}")
    print(f"DEBUG: Calibration Request Dump: {request.dict()}")
    
    calibration = (
        db.query(UserCalibration)
        .filter(UserCalibration.calibration_id == calibration_id)
        .first()
    )
    if calibration is None:
        raise HTTPException(status_code=404, detail="Calibration not found")

    if not request.screen_points or len(request.screen_points) != 4:
        print(f"DEBUG: Invalid screen points count: {len(request.screen_points)}")
        raise HTTPException(
            status_code=400, detail=f"screen_points must contain 4 points, got {len(request.screen_points)}"
        )

    screen_points = [(p[0], p[1]) for p in request.screen_points]
    if request.gaze_points and len(request.gaze_points) == 4:
        gaze_points = [(p[0], p[1]) for p in request.gaze_points]
    else:
        gaze_points = screen_points

    calib_service = get_calibration_service()
    matrix, accuracy = calib_service.calculate_transformation_matrix(
        screen_points, gaze_points
    )

    if hasattr(calibration, "transform_matrix"):
        calibration.transform_matrix = calib_service.matrix_to_json(matrix)
    if hasattr(calibration, "accuracy_score"):
        calibration.accuracy_score = accuracy
    if hasattr(calibration, "status"):
        calibration.status = "completed"
    if hasattr(calibration, "completed_at"):
        calibration.completed_at = datetime.utcnow()

    try:
        db.commit()
    except Exception as exc:  # pragma: no cover - defensive
        db.rollback()
        logger.exception("Calibration submission failed", exc_info=exc)
        raise HTTPException(
            status_code=500, detail="Failed to commit calibration result"
        ) from exc

    return CalibrationSubmitResponse(
        calibration_id=calibration_id,
        transform_matrix=matrix.tolist(),
        accuracy=accuracy,
        status=getattr(calibration, "status", None),
    )
