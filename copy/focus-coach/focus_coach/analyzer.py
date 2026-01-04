"""Core analysis logic for Focus Coach CLI."""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, pstdev
from typing import Iterable, List, Optional, Sequence

SUPPORTED_EVENT_TYPES = {
    "focus_start",
    "focus_end",
    "break_start",
    "break_end",
    "attention",
    "stress",
}


def _coerce_timestamp(raw: str) -> datetime:
    raw = raw.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    dt = datetime.fromisoformat(raw)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _coerce_value(raw: Optional[str]) -> Optional[float]:
    if raw is None:
        return None
    raw = raw.strip()
    if not raw:
        return None
    return float(raw)


@dataclass(frozen=True)
class Event:
    """Represents a single time-stamped event from a study session log."""

    timestamp: datetime
    event_type: str
    value: Optional[float] = None


@dataclass
class FocusBlock:
    start: datetime
    end: datetime
    minutes: float


@dataclass
class AnalysisSummary:
    focus_minutes: float
    break_minutes: float
    focus_ratio: float
    average_focus_streak_minutes: float
    longest_focus_streak_minutes: float
    attention_average: Optional[float]
    attention_stddev: Optional[float]
    attention_samples: int
    stress_event_count: int
    stress_timestamps: List[datetime] = field(default_factory=list)
    focus_blocks: List[FocusBlock] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "focus_minutes": round(self.focus_minutes, 2),
            "break_minutes": round(self.break_minutes, 2),
            "focus_ratio": round(self.focus_ratio, 4),
            "average_focus_streak_minutes": round(self.average_focus_streak_minutes, 2),
            "longest_focus_streak_minutes": round(self.longest_focus_streak_minutes, 2),
            "attention_average": None if self.attention_average is None else round(self.attention_average, 2),
            "attention_stddev": None if self.attention_stddev is None else round(self.attention_stddev, 2),
            "attention_samples": self.attention_samples,
            "stress_event_count": self.stress_event_count,
            "stress_timestamps": [ts.isoformat() for ts in self.stress_timestamps],
            "focus_blocks": [
                {
                    "start": block.start.isoformat(),
                    "end": block.end.isoformat(),
                    "minutes": round(block.minutes, 2),
                }
                for block in self.focus_blocks
            ],
            "warnings": self.warnings,
        }


def load_events_from_csv(path: Path | str) -> List[Event]:
    """Load events from a CSV file and return a sorted list of Event."""
    path = Path(path)
    events: List[Event] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = {"timestamp", "event_type"} - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"CSV missing required columns: {', '.join(sorted(missing))}")
        for idx, row in enumerate(reader, start=2):
            try:
                timestamp = _coerce_timestamp(row["timestamp"])
            except Exception as exc:  # noqa: BLE001
                raise ValueError(f"Row {idx}: invalid timestamp {row['timestamp']!r}") from exc
            event_type = (row.get("event_type") or "").strip().lower()
            if event_type not in SUPPORTED_EVENT_TYPES:
                raise ValueError(f"Row {idx}: unsupported event_type {event_type!r}")
            try:
                value = _coerce_value(row.get("value"))
            except Exception as exc:  # noqa: BLE001
                raise ValueError(f"Row {idx}: invalid value {row.get('value')!r}") from exc
            events.append(Event(timestamp=timestamp, event_type=event_type, value=value))
    events.sort(key=lambda ev: ev.timestamp)
    return events


class SessionAnalyzer:
    """Compute study session metrics from timeline events."""

    def __init__(self, reference_time: Optional[datetime] = None) -> None:
        self.reference_time = reference_time

    def analyze(self, events: Sequence[Event]) -> AnalysisSummary:
        if not events:
            raise ValueError("No events to analyse.")

        sorted_events = sorted(events, key=lambda ev: ev.timestamp)
        focus_total = 0.0
        break_total = 0.0
        focus_streaks: List[float] = []
        focus_blocks: List[FocusBlock] = []

        state: Optional[str] = None
        state_started_at: Optional[datetime] = None
        last_timestamp: Optional[datetime] = None

        attention_scores: List[float] = []
        stress_timestamps: List[datetime] = []
        warnings: List[str] = []

        for event in sorted_events:
            if last_timestamp and event.timestamp < last_timestamp:
                warnings.append(
                    f"Non-monotonic timestamp detected at {event.timestamp.isoformat()}."
                )
            last_timestamp = event.timestamp

            match event.event_type:
                case "attention":
                    if event.value is not None:
                        attention_scores.append(event.value)
                    else:
                        warnings.append(f"Attention event at {event.timestamp.isoformat()} missing value.")
                    continue
                case "stress":
                    stress_timestamps.append(event.timestamp)
                    continue
                case _:
                    pass  # handled below

            if event.event_type == "focus_start":
                if state == "focus":
                    warnings.append(f"Focus started while already in focus at {event.timestamp.isoformat()}.")
                if state == "break" and state_started_at is not None:
                    break_minutes = (event.timestamp - state_started_at).total_seconds() / 60
                    if break_minutes > 0:
                        break_total += break_minutes
                state = "focus"
                state_started_at = event.timestamp
            elif event.event_type == "focus_end":
                if state == "focus" and state_started_at is not None:
                    duration_minutes = (event.timestamp - state_started_at).total_seconds() / 60
                    if duration_minutes >= 0:
                        focus_total += duration_minutes
                        focus_streaks.append(duration_minutes)
                        focus_blocks.append(
                            FocusBlock(
                                start=state_started_at,
                                end=event.timestamp,
                                minutes=duration_minutes,
                            )
                        )
                else:
                    warnings.append(f"Focus ended without an active focus window at {event.timestamp.isoformat()}.")
                state = None
                state_started_at = None
            elif event.event_type == "break_start":
                if state == "break":
                    warnings.append(f"Break started while already on break at {event.timestamp.isoformat()}.")
                if state == "focus" and state_started_at is not None:
                    duration_minutes = (event.timestamp - state_started_at).total_seconds() / 60
                    if duration_minutes >= 0:
                        focus_total += duration_minutes
                        focus_streaks.append(duration_minutes)
                        focus_blocks.append(
                            FocusBlock(
                                start=state_started_at,
                                end=event.timestamp,
                                minutes=duration_minutes,
                            )
                        )
                state = "break"
                state_started_at = event.timestamp
            elif event.event_type == "break_end":
                if state == "break" and state_started_at is not None:
                    break_minutes = (event.timestamp - state_started_at).total_seconds() / 60
                    if break_minutes >= 0:
                        break_total += break_minutes
                else:
                    warnings.append(f"Break ended without an active break window at {event.timestamp.isoformat()}.")
                state = None
                state_started_at = None

        # Handle session that never closed cleanly
        if state is not None and state_started_at is not None:
            ref = self.reference_time or sorted_events[-1].timestamp
            delta_minutes = (ref - state_started_at).total_seconds() / 60
            if delta_minutes > 0:
                warnings.append(
                    f"Session ended while still in '{state}' state; ignoring last {round(delta_minutes, 2)} minutes."
                )

        total_tracked = focus_total + break_total
        focus_ratio = focus_total / total_tracked if total_tracked else 0.0
        average_streak = mean(focus_streaks) if focus_streaks else 0.0
        longest_streak = max(focus_streaks) if focus_streaks else 0.0

        attention_avg: Optional[float]
        attention_std: Optional[float]
        if attention_scores:
            attention_avg = mean(attention_scores)
            attention_std = pstdev(attention_scores) if len(attention_scores) > 1 else 0.0
        else:
            attention_avg = None
            attention_std = None

        summary = AnalysisSummary(
            focus_minutes=focus_total,
            break_minutes=break_total,
            focus_ratio=focus_ratio,
            average_focus_streak_minutes=average_streak,
            longest_focus_streak_minutes=longest_streak,
            attention_average=attention_avg,
            attention_stddev=attention_std,
            attention_samples=len(attention_scores),
            stress_event_count=len(stress_timestamps),
            stress_timestamps=stress_timestamps,
            focus_blocks=focus_blocks,
            warnings=warnings,
        )
        return summary
