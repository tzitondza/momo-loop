"""Simple in-memory rate limiter for login attempts."""

from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import Lock

_lock = Lock()
_attempts: dict[str, deque[float]] = defaultdict(deque)


def too_many_attempts(key: str, *, limit: int = 8, window_seconds: int = 60) -> bool:
    now = time.time()
    with _lock:
        bucket = _attempts[key]
        while bucket and now - bucket[0] > window_seconds:
            bucket.popleft()
        if len(bucket) >= limit:
            return True
        bucket.append(now)
        return False


def clear_attempts(key: str) -> None:
    with _lock:
        _attempts.pop(key, None)
