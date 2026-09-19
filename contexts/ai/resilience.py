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
    boundary: str = "retrieval"
    operation: str = "query"

    def __post_init__(self) -> None:
        if self.max_concurrency < 1 or self.rate_per_second <= 0 or self.timeout_seconds <= 0:
            raise ValueError("resilience limits must be positive")
        self._bulkhead = BoundedSemaphore(self.max_concurrency)
        self._rate_lock = Lock()
        self._tokens = self.rate_per_second
        self._last_refill = monotonic()
        self._active_workers = 0

    def _take_token(self) -> None:
        now = monotonic()
        with self._rate_lock:
            elapsed = now - self._last_refill
            self._tokens = min(self.rate_per_second, self._tokens + elapsed * self.rate_per_second)
            self._last_refill = now
            if self._tokens < 1:
                self._record_ratelimit_rejection()
                raise RateLimitExceeded(f"{self.boundary} rate limit exceeded")
            self._tokens -= 1

    def _record_ratelimit_rejection(self) -> None:
        try:
            from app.metrics import observe_ratelimit_rejection
            observe_ratelimit_rejection(self.boundary)
        except Exception:
            pass

    def _record_bulkhead_rejection(self) -> None:
        try:
            from app.metrics import observe_bulkhead_rejection
            observe_bulkhead_rejection(self.boundary)
        except Exception:
            pass

    def _record_bulkhead_active(self, count: int) -> None:
        try:
            from app.metrics import observe_bulkhead_active
            observe_bulkhead_active(self.boundary, float(count))
        except Exception:
            pass

    def _record_boundary_duration(self, duration: float) -> None:
        try:
            from app.metrics import observe_boundary_duration
            observe_boundary_duration(self.boundary, self.operation, duration)
        except Exception:
            pass

    def _record_downstream_failure(self, dependency: str) -> None:
        try:
            from app.metrics import observe_downstream_failure
            observe_downstream_failure(self.boundary, dependency)
        except Exception:
            pass

    def call(self, operation: Callable[[], T]) -> T:
        self._take_token()
        if not self._bulkhead.acquire(blocking=False):
            self._record_bulkhead_rejection()
            raise BulkheadRejected(f"{self.boundary} concurrency limit reached")

        with self._rate_lock:
            self._active_workers += 1
            current_active = self._active_workers
        self._record_bulkhead_active(current_active)

        started = monotonic()
        def release_slot(_future=None):
            with self._rate_lock:
                self._active_workers -= 1
                remaining_active = self._active_workers
            self._record_bulkhead_active(remaining_active)
            self._bulkhead.release()

        executor = ThreadPoolExecutor(max_workers=1)
        try:
            future = executor.submit(operation)
        except BaseException:
            release_slot()
            executor.shutdown(wait=False, cancel_futures=True)
            raise
        # A timeout does not stop a running thread. Keep its slot until it exits.
        future.add_done_callback(release_slot)
        try:
            try:
                result = future.result(timeout=self.timeout_seconds)
                self._record_boundary_duration(monotonic() - started)
                return result
            except TimeoutError as exc:
                future.cancel()
                self._record_boundary_duration(monotonic() - started)
                self._record_downstream_failure("timeout")
                raise CallTimedOut(f"{self.boundary} dependency timed out") from exc
            except Exception as exc:
                self._record_boundary_duration(monotonic() - started)
                self._record_downstream_failure(type(exc).__name__)
                raise
        finally:
            executor.shutdown(wait=False, cancel_futures=True)
