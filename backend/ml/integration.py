"""
Wave 2 integration pipeline utilities.
Combines preprocessing, ML estimators, KPI aggregation, and alerting into a
single orchestrated component that can feed both REST ingestion and WebSocket
streams.
"""

from __future__ import annotations

import statistics
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from time import perf_counter
from typing import Any, Dict, List, Optional
from uuid import uuid4

import numpy as np

from backend.ml.calibration import get_calibration_service
from backend.ml.gaze_estimator import get_gaze_estimator
from backend.ml.kpi_calculator import get_kpi_calculator
from backend.ml.pose_estimator import get_pose_estimator
from backend.ml.preprocessing import (
    get_audio_preprocessor,
    get_frame_preprocessor,
)
from backend.ml.stress_analyzer import get_stress_analyzer


@dataclass
class PipelineTelemetry:
    """Runtime metadata collected for each pipeline pass."""

    timestamp: datetime
    frame_id: str
    audio_id: str
    latencies_ms: Dict[str, float] = field(default_factory=dict)


@dataclass
class PipelineResult:
    """Structured result returned by :class:`IntegrationPipeline`."""

    telemetry: PipelineTelemetry
    gaze: Dict[str, Any]
    pose: Dict[str, Any]
    stress: Dict[str, Any]
    metrics: Dict[str, Any]
    rest_payloads: Dict[str, Dict[str, Any]]
    websocket_messages: List[Dict[str, Any]]
    rolling_summary: Dict[str, float]

    def to_dict(self) -> Dict[str, Any]:
        """Return JSON-serialisable representation."""
        return {
            "timestamp": self.telemetry.timestamp.isoformat(),
            "frame_id": self.telemetry.frame_id,
            "audio_id": self.telemetry.audio_id,
            "latencies_ms": self.telemetry.latencies_ms,
            "gaze": self.gaze,
            "pose": self.pose,
            "stress": self.stress,
            "metrics": self.metrics,
            "rest_payloads": self.rest_payloads,
            "websocket_messages": self.websocket_messages,
            "rolling_summary": self.rolling_summary,
        }


class IntegrationPipeline:
    """High-level orchestrator for multimodal inference and KPI generation."""

    def __init__(
        self,
        *,
        frame_preprocessor=None,
        audio_preprocessor=None,
        gaze_estimator=None,
        pose_estimator=None,
        stress_analyzer=None,
        kpi_calculator=None,
        calibration_service=None,
        latency_window: int = 50,
        metrics_window: int = 120,
    ) -> None:
        self.frame_preprocessor = frame_preprocessor or get_frame_preprocessor()
        self.audio_preprocessor = audio_preprocessor or get_audio_preprocessor()
        self.gaze_estimator = gaze_estimator or get_gaze_estimator()
        self.pose_estimator = pose_estimator or get_pose_estimator()
        self.stress_analyzer = stress_analyzer or get_stress_analyzer()
        self.kpi_calculator = kpi_calculator or get_kpi_calculator()
        self.calibration_service = calibration_service or get_calibration_service()

        self._latencies = deque(maxlen=latency_window)
        self._metrics_history: deque[Dict[str, float]] = deque(maxlen=metrics_window)
        self.calibration_matrix: Optional[np.ndarray] = None
        self.calibration_accuracy: Optional[float] = None

    # ------------------------------------------------------------------
    # Calibration helpers
    # ------------------------------------------------------------------
    def update_calibration(
        self,
        screen_points: List[List[float]],
        gaze_points: Optional[List[List[float]]] = None,
    ) -> Dict[str, Any]:
        """Calculate and persist a new calibration matrix."""
        gaze_points = gaze_points or screen_points
        matrix, accuracy = self.calibration_service.calculate_transformation_matrix(
            screen_points, gaze_points
        )
        self.calibration_matrix = matrix
        self.calibration_accuracy = float(accuracy)
        return {
            "matrix": matrix.tolist(),
            "accuracy": accuracy,
        }

    def reset_calibration(self) -> None:
        """Drop current calibration matrix."""
        self.calibration_matrix = None
        self.calibration_accuracy = None

    # ------------------------------------------------------------------
    # Primary processing entry point
    # ------------------------------------------------------------------
    def process(
        self,
        *,
        frame: np.ndarray,
        audio: np.ndarray,
        original_sample_rate: int,
        session_id: Optional[str] = None,
        timestamp: Optional[datetime] = None,
    ) -> PipelineResult:
        """Run the complete multimodal pipeline for a single frame/audio window."""
        ts = timestamp or datetime.utcnow()
        frame_id = str(uuid4())
        audio_id = str(uuid4())

        latencies: Dict[str, float] = {}
        total_start = perf_counter()

        # Frame preprocessing -------------------------------------------------
        start = perf_counter()
        processed_frame = (
            self.frame_preprocessor.preprocess(frame)
            if self.frame_preprocessor
            else frame
        )
        latencies["frame_preprocess"] = (perf_counter() - start) * 1000.0

        # Gaze estimation -----------------------------------------------------
        start = perf_counter()
        gaze_result = self.gaze_estimator.estimate(
            processed_frame, self.calibration_matrix
        )
        latencies["gaze"] = (perf_counter() - start) * 1000.0

        # Pose estimation -----------------------------------------------------
        start = perf_counter()
        pose_result = self.pose_estimator.estimate(processed_frame)
        latencies["pose"] = (perf_counter() - start) * 1000.0

        # Audio preprocessing & stress analysis ------------------------------
        start = perf_counter()
        processed_audio = (
            self.audio_preprocessor.preprocess(audio, original_sample_rate)
            if self.audio_preprocessor
            else audio
        )
        latencies["audio_preprocess"] = (perf_counter() - start) * 1000.0

        start = perf_counter()
        stress_result = self.stress_analyzer.analyze(processed_audio)
        latencies["stress"] = (perf_counter() - start) * 1000.0

        # KPI aggregation -----------------------------------------------------
        gaze_payload = self._build_gaze_payload(gaze_result)
        pose_payload = self._build_pose_payload(pose_result)
        stress_payload = self._build_stress_payload(stress_result)

        start = perf_counter()
        metrics = self.kpi_calculator.calculate_productivity_metrics(
            [gaze_payload],
            [pose_payload],
            [stress_payload],
            ts,
            ts,
        )
        latencies["kpi"] = (perf_counter() - start) * 1000.0

        latencies["total"] = (perf_counter() - total_start) * 1000.0
        self._latencies.append(latencies["total"])
        self._metrics_history.append(metrics)

        telemetry = PipelineTelemetry(
            timestamp=ts,
            frame_id=frame_id,
            audio_id=audio_id,
            latencies_ms={k: round(v, 3) for k, v in latencies.items()},
        )

        rest_payloads = self._build_rest_payloads(
            session_id=session_id,
            frame_id=frame_id,
            audio_id=audio_id,
            timestamp=ts,
            gaze_payload=gaze_payload,
            pose_payload=pose_payload,
            stress_payload=stress_payload,
            metrics=metrics,
        )
        websocket_messages = self._build_websocket_messages(
            session_id=session_id,
            telemetry=telemetry,
            metrics=metrics,
            rest_payloads=rest_payloads,
        )
        rolling_summary = self._compute_rolling_summary()

        return PipelineResult(
            telemetry=telemetry,
            gaze=gaze_result,
            pose=pose_result,
            stress=stress_result,
            metrics=metrics,
            rest_payloads=rest_payloads,
            websocket_messages=websocket_messages,
            rolling_summary=rolling_summary,
        )

    # ------------------------------------------------------------------
    # Derived statistics/helpers
    # ------------------------------------------------------------------
    def latency_snapshot(self) -> Dict[str, float]:
        """Return aggregate latency information for observability dashboards."""
        if not self._latencies:
            return {"count": 0, "avg_ms": 0.0, "p95_ms": 0.0, "max_ms": 0.0}
        sorted_latencies = sorted(self._latencies)
        count = len(sorted_latencies)
        avg = statistics.fmean(sorted_latencies)
        p95 = sorted_latencies[int(0.95 * (count - 1))]
        return {
            "count": count,
            "avg_ms": round(avg, 3),
            "p95_ms": round(p95, 3),
            "max_ms": round(max(sorted_latencies), 3),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _build_gaze_payload(self, gaze: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "gaze_x": float(gaze.get("gaze_x", 0.5)),
            "gaze_y": float(gaze.get("gaze_y", 0.5)),
            "gaze_direction": gaze.get("gaze_direction", "center"),
            "gaze_angle": float(gaze.get("gaze_angle", 0.0)),
            "confidence": float(gaze.get("confidence", 0.0)),
        }

    def _build_pose_payload(self, pose: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "yaw": float(pose.get("yaw", 0.0)),
            "pitch": float(pose.get("pitch", 0.0)),
            "roll": float(pose.get("roll", 0.0)),
            "posture": pose.get("posture", pose.get("posture_class", "neutral")),
            "confidence": float(pose.get("confidence", 0.0)),
        }

    def _build_stress_payload(self, stress: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "stress_level": float(stress.get("stress_level", 0.0)),
            "confidence": float(stress.get("confidence", 0.0)),
            "signal_quality": float(stress.get("signal_quality", 1.0)),
        }

    def _build_rest_payloads(
        self,
        *,
        session_id: Optional[str],
        frame_id: str,
        audio_id: str,
        timestamp: datetime,
        gaze_payload: Dict[str, Any],
        pose_payload: Dict[str, Any],
        stress_payload: Dict[str, Any],
        metrics: Dict[str, Any],
    ) -> Dict[str, Dict[str, Any]]:
        gaze_rest = {
            "session_id": session_id,
            "frame_id": frame_id,
            "timestamp": timestamp.isoformat(),
            **gaze_payload,
        }

        pose_rest = {
            "session_id": session_id,
            "frame_id": frame_id,
            "timestamp": timestamp.isoformat(),
            **pose_payload,
        }

        stress_rest = {
            "session_id": session_id,
            "audio_id": audio_id,
            "window_start": timestamp.isoformat(),
            "window_end": timestamp.isoformat(),
            "stress_score": stress_payload["stress_level"],
            "vocal_effort": stress_payload["confidence"],
            "smoothing_count": 0,
            "signal_quality": stress_payload["signal_quality"],
        }

        productivity_rest = {
            "session_id": session_id,
            "total_breaks": metrics.get("total_breaks", 0),
            "avg_break_duration": metrics.get("avg_break_duration", 0.0),
            "break_pattern_type": metrics.get("break_pattern_type", "unknown"),
            "productivity_score": metrics.get("overall_productivity", 0.0),
        }

        return {
            "gaze": gaze_rest,
            "pose": pose_rest,
            "stress": stress_rest,
            "productivity": productivity_rest,
        }

    def _build_websocket_messages(
        self,
        *,
        session_id: Optional[str],
        telemetry: PipelineTelemetry,
        metrics: Dict[str, Any],
        rest_payloads: Dict[str, Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        frame_message = {
            "type": "frame_metrics",
            "payload": {
                "session_id": session_id,
                "frame_id": telemetry.frame_id,
                "timestamp": telemetry.timestamp.isoformat(),
                "latencies_ms": telemetry.latencies_ms,
                "metrics": metrics,
            },
        }

        session_message = {
            "type": "session_update",
            "payload": {
                "session_id": session_id,
                "overall_productivity": metrics.get("overall_productivity"),
                "focus_score": metrics.get("focus_score"),
                "stress_score": metrics.get("stress_score"),
                "timestamp": telemetry.timestamp.isoformat(),
                "rest_payloads": rest_payloads,
            },
        }

        messages = [frame_message, session_message]

        if metrics.get("stress_score", 0.0) >= 0.8:
            messages.append(
                {
                    "type": "alert",
                    "payload": {
                        "session_id": session_id,
                        "severity": "high",
                        "category": "stress",
                        "value": metrics.get("stress_score"),
                        "timestamp": telemetry.timestamp.isoformat(),
                    },
                }
            )

        posture = rest_payloads["pose"].get("posture")
        if posture and posture.lower() not in {"neutral", "good", "optimal"}:
            messages.append(
                {
                    "type": "alert",
                    "payload": {
                        "session_id": session_id,
                        "severity": "medium",
                        "category": "posture",
                        "value": posture,
                        "timestamp": telemetry.timestamp.isoformat(),
                    },
                }
            )

        return messages

    def _compute_rolling_summary(self) -> Dict[str, float]:
        if not self._metrics_history:
            return {}
        keys = [
            "focus_score",
            "engagement_score",
            "stress_score",
            "posture_score",
            "overall_productivity",
        ]
        summary = {}
        for key in keys:
            summary[key] = round(
                statistics.fmean(metric.get(key, 0.0) for metric in self._metrics_history),
                3,
            )
        return summary


# ----------------------------------------------------------------------
# Backwards-compatible helper
# ----------------------------------------------------------------------

def run_end_to_end_pipeline(
    frame: np.ndarray,
    audio_data: np.ndarray,
    original_sample_rate: int,
    calibration_matrix: Optional[np.ndarray] = None,
    window_start: Optional[datetime] = None,
    window_end: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Convenience wrapper used by legacy callers/tests."""
    pipeline = IntegrationPipeline()
    if calibration_matrix is not None:
        pipeline.calibration_matrix = calibration_matrix
    result = pipeline.process(
        frame=frame,
        audio=audio_data,
        original_sample_rate=original_sample_rate,
        timestamp=window_end or window_start,
    )
    return result.to_dict()
