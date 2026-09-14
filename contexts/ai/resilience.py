"""Dependency-free resilience primitives for synchronous retrieval calls.

These are Python equivalents of the bulkhead, rate-limiter, and timeout
patterns commonly supplied by Resilience4j in JVM services.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError
from dataclasses import dataclass
from threading import BoundedSemaphore, Lock
from time import monotonic
from typing import Callable, TypeVar

T = TypeVar("T")


class ResilienceError(RuntimeError):
    """Base error for rejected or time-bounded dependency calls."""


class BulkheadRejected(ResilienceError):
    pass


class RateLimitExceeded(ResilienceError):
    pass


class CallTimedOut(ResilienceError):
    pass


@dataclass
class ResiliencePolicy:
    max_concurrency: int = 8
    rate_per_second: float = 20.0
    timeout_seconds: float = 10.0

    def __post_init__(self) -> None:
        if self.max_concurrency < 1 or self.rate_per_second <= 0 or self.timeout_seconds <= 0:
            raise ValueError("resilience limits must be positive")
        self._bulkhead = BoundedSemaphore(self.max_concurrency)
        self._rate_lock = Lock()
        self._tokens = self.rate_per_second
        self._last_refill = monotonic()

    def _take_token(self) -> None:
        now = monotonic()
        with self._rate_lock:
            elapsed = now - self._last_refill
            self._tokens = min(self.rate_per_second, self._tokens + elapsed * self.rate_per_second)
            self._last_refill = now
            if self._tokens < 1:
                raise RateLimitExceeded("retrieval rate limit exceeded")
            self._tokens -= 1

    def call(self, operation: Callable[[], T]) -> T:
        self._take_token()
        if not self._bulkhead.acquire(blocking=False):
            raise BulkheadRejected("retrieval concurrency limit reached")
        try:
            executor = ThreadPoolExecutor(max_workers=1)
            future = executor.submit(operation)
            try:
                return future.result(timeout=self.timeout_seconds)
            except TimeoutError as exc:
                future.cancel()
                raise CallTimedOut("retrieval dependency timed out") from exc
            finally:
                # Do not wait for an uncooperative dependency after the timeout.
                executor.shutdown(wait=False, cancel_futures=True)
        finally:
            self._bulkhead.release()
