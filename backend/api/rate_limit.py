
"""
Lightweight in-memory rate limiter utilities for FastAPI endpoints.

The limiter is intentionally simple (per-process) and suitable for the desktop
offline-first environment targeted by Eaglearn. It keeps counters in memory and
resets them after a configurable time window.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass


class RateLimitExceeded(Exception):
    """Raised when a client exceeds the configured rate limit."""

    def __init__(self, reset_timestamp: float) -> None:
        super().__init__("Rate limit exceeded")
        self.reset_timestamp = reset_timestamp


@dataclass
class _Counter:
    count: int
    reset_at: float


class SimpleRateLimiter:
    """A thread-safe in-memory token bucket."""

    def __init__(self, limit: int, window_seconds: int) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._lock = threading.Lock()
        self._counters: dict[str, _Counter] = {}

    def hit(self, key: str) -> float:
        """
        Record a request for the given key.

        Args:
            key: Identifier (typically client host or user id).

        Returns:
            Timestamp (epoch seconds) when the window resets.

        Raises:
            RateLimitExceeded: If the request exceeds the configured limit.
        """
        now = time.time()
        with self._lock:
            counter = self._counters.get(key)
            if counter is None or counter.reset_at <= now:
                counter = _Counter(count=0, reset_at=now + self.window_seconds)
            if counter.count >= self.limit:
                raise RateLimitExceeded(counter.reset_at)
            counter.count += 1
            self._counters[key] = counter
            return counter.reset_at

    def reset(self) -> None:
        """Clear all recorded counters (primarily for testing)."""
        with self._lock:
            self._counters.clear()
