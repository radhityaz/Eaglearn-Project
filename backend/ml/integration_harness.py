"""
Benchmark and smoke-test utilities for the integration pipeline.
"""

from __future__ import annotations

import json
import statistics
from datetime import datetime
from typing import Any, Dict, Optional

import numpy as np

from backend.ml.integration import IntegrationPipeline


def _generate_synthetic_frame(width: int = 640, height: int = 480) -> np.ndarray:
    rng = np.random.default_rng()
    return rng.integers(0, 255, size=(height, width, 3), dtype=np.uint8)


def _generate_synthetic_audio(sample_rate: int) -> np.ndarray:
    rng = np.random.default_rng()
    duration = max(sample_rate // 2, 1)
    return rng.normal(0, 0.05, size=duration).astype(np.float32)


def run_benchmark(
    *,
    iterations: int = 5,
    sample_rate: int = 16_000,
    pipeline: Optional[IntegrationPipeline] = None,
    session_id: str = "benchmark",
) -> Dict[str, Any]:
    """Execute the pipeline multiple times and collect latency statistics."""
    pipeline = pipeline or IntegrationPipeline()

    latencies = []
    stress_alerts = 0
    rolling = {}

    for _ in range(iterations):
        frame = _generate_synthetic_frame()
        audio = _generate_synthetic_audio(sample_rate)
        result = pipeline.process(
            frame=frame,
            audio=audio,
            original_sample_rate=sample_rate,
            session_id=session_id,
            timestamp=datetime.utcnow(),
        )
        latencies.append(result.telemetry.latencies_ms.get("total", 0.0))
        stress_alerts += sum(1 for msg in result.websocket_messages if msg.get("type") == "alert")
        rolling = result.rolling_summary

    latency_stats = {
        "avg_ms": round(statistics.fmean(latencies), 3) if latencies else 0.0,
        "max_ms": round(max(latencies), 3) if latencies else 0.0,
        "min_ms": round(min(latencies), 3) if latencies else 0.0,
    }

    return {
        "iterations": iterations,
        "latency_stats": latency_stats,
        "alerts_emitted": stress_alerts,
        "rolling_summary": rolling,
    }


if __name__ == "__main__":
    summary = run_benchmark()
    print(json.dumps(summary, indent=2))
