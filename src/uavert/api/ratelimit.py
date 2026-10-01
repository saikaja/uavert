"""A simple in-memory request limit per client IP, for endpoints that call outside services.
Per process only; a shared store (e.g. Redis) replaces it when the API runs on several servers."""

import time
from collections import defaultdict, deque

from fastapi import Request

from uavert.api.errors import ApiError
from uavert.config import get_settings

WINDOW_S = 60.0


class RateLimiter:
    def __init__(self, per_minute: int):
        self.per_minute = per_minute
        self._hits: dict[str, deque] = defaultdict(deque)

    def allow(self, key: str, now: float | None = None) -> bool:
        now = time.monotonic() if now is None else now
        if len(self._hits) > 10_000:  # drop clients with no hits in the current window
            self._hits = defaultdict(deque, {k: v for k, v in self._hits.items() if v and now - v[-1] < WINDOW_S})
        hits = self._hits[key]
        while hits and now - hits[0] >= WINDOW_S:
            hits.popleft()
        if len(hits) >= self.per_minute:
            return False
        hits.append(now)
        return True


limiter = RateLimiter(get_settings().outside_calls_per_minute)


def limit_outside_calls(request: Request) -> None:
    if not limiter.allow(request.client.host if request.client else "unknown"):
        raise ApiError(429, "rate_limit_exceeded", "Too many address or route lookups. Try again in a minute.")
