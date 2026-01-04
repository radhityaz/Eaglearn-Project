"""Synthetic data generation for the Focus Coach CLI."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from random import Random
from typing import Iterable, List, Optional

from .analyzer import Event


def generate_session_events(
    study_minutes: int = 120,
    focus_block: int = 25,
    break_block: int = 5,
    attention_baseline: float = 78.0,
    attention_noise: float = 6.0,
    stress_probability: float = 0.08,
    start_time: Optional[datetime] = None,
    seed: Optional[int] = None,
) -> List[Event]:
    """Create a synthetic session timeline following a pomodoro-like pattern."""
    if study_minutes <= 0:
        raise ValueError("study_minutes must be positive.")
    if focus_block <= 0:
        raise ValueError("focus_block must be positive.")
    if break_block < 0:
        raise ValueError("break_block cannot be negative.")

    rng = Random(seed)
    start = start_time or datetime.now(timezone.utc).replace(second=0, microsecond=0)
    events: List[Event] = []
    cursor = start
    elapsed = 0

    while elapsed < study_minutes:
        current_focus = min(focus_block, study_minutes - elapsed)
        if current_focus <= 0:
            break
        events.append(Event(timestamp=cursor, event_type="focus_start"))

        # Emit attention ticks every 5 minutes within the focus block.
        for offset in range(5, current_focus + 1, 5):
            attention_time = cursor + timedelta(minutes=offset)
            jitter = rng.gauss(0, attention_noise)
            score = max(0.0, min(100.0, attention_baseline + jitter))
            events.append(Event(timestamp=attention_time, event_type="attention", value=score))
            if rng.random() < stress_probability:
                events.append(Event(timestamp=attention_time, event_type="stress", value=1.0))

        cursor += timedelta(minutes=current_focus)
        events.append(Event(timestamp=cursor, event_type="focus_end"))
        elapsed += current_focus

        if elapsed >= study_minutes:
            break

        current_break = min(break_block, study_minutes - elapsed)
        if current_break > 0:
            events.append(Event(timestamp=cursor, event_type="break_start"))
            cursor += timedelta(minutes=current_break)
            events.append(Event(timestamp=cursor, event_type="break_end"))
            elapsed += current_break

    events.sort(key=lambda ev: ev.timestamp)
    return events


def write_events_to_csv(events: Iterable[Event], path: Path | str) -> Path:
    """Persist events to disk in CSV format."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        handle.write("timestamp,event_type,value\n")
        for event in sorted(events, key=lambda ev: ev.timestamp):
            value = "" if event.value is None else f"{event.value:.2f}"
            handle.write(f"{event.timestamp.isoformat()},{event.event_type},{value}\n")
    return path
