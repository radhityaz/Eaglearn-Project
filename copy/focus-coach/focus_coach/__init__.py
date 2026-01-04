"""Focus Coach package providing CLI utilities for study session analytics."""

from .analyzer import SessionAnalyzer, load_events_from_csv
from .simulation import generate_session_events

__all__ = [
    "SessionAnalyzer",
    "load_events_from_csv",
    "generate_session_events",
]
