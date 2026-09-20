"""Bounded, non-blocking Kafka publication for immutable domain events."""
from __future__ import annotations

import atexit
from collections import deque
import json
import logging
import os
from threading import Lock
from typing import Any, Iterable

from app.redaction import sanitize_for_boundary


log = logging.getLogger(__name__)


def _positive_int(name: str, default: int) -> int:
    try:
        return max(1, int(os.getenv(name, str(default))))
    except ValueError:
        return default


def _headers_for(
    event: Any, traceparent: str | None, custom_headers: Iterable[tuple[str, bytes | str]] | None
) -> list[tuple[str, bytes]]:
    if hasattr(event, "headers"):
        headers = event.headers(traceparent=traceparent)
    elif hasattr(event, "kafka_headers"):
        headers = event.kafka_headers(traceparent=traceparent)
    else:
        headers = []
    mandatory = {name for name, _ in headers}
    for name, value in custom_headers or ():
        if name not in mandatory:
            headers.append((name, value if isinstance(value, bytes) else str(value).encode("utf-8")))
    return headers


def _assert_boundary_safe(
    event: Any, headers: Iterable[tuple[str, bytes | str]] | None = None
) -> None:
    """Fail closed rather than serializing unredacted material to Kafka.

    The route/service layers tokenize data before constructing an event.  This
    final guard makes a future bypass observable in local tests and production
    before a message leaves the RAG process.
    """
    if not hasattr(event, "to_dict"):
        raise ValueError("only serializable domain events may cross the publisher boundary")
    token_key = os.getenv("PII_TOKEN_SALT", "change-me")
    payload = event.to_dict()
    if sanitize_for_boundary(payload, token_key) != payload:
        raise ValueError("refusing to publish an event containing unsanitized boundary data")
    for name, value in headers or ():
        decoded = value.decode("utf-8", errors="replace") if isinstance(value, bytes) else str(value)
        if sanitize_for_boundary(decoded, token_key, name) != decoded:
            raise ValueError("refusing to publish an unsanitized custom header")


class NullPublisher:
    """Bounded test/local publisher that exposes only recent event evidence."""

    def __init__(self) -> None:
        self.published: deque[tuple[Any, list[tuple[str, bytes]]]] = deque(
            maxlen=_positive_int("EVENT_IN_MEMORY_MAX_RECORDS", 1_000)
        )

    def publish(
        self, event: Any, traceparent: str | None = None, headers: Iterable[tuple[str, bytes | str]] | None = None
    ) -> None:
        _assert_boundary_safe(event, headers)
        self.published.append((event, _headers_for(event, traceparent, headers)))


class EventPublisher:
    """Kafka adapter with bounded caller latency and lazy, recoverable startup."""

    def __init__(self, bootstrap: str | None = None) -> None:
        self.bootstrap = bootstrap or os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
        self.enabled = os.getenv("ENABLE_KAFKA", "false").lower() == "true"
        self._producer = None
        self._producer_lock = Lock()
        self.published: deque[tuple[Any, list[tuple[str, bytes]]]] = deque(
            maxlen=_positive_int("EVENT_IN_MEMORY_MAX_RECORDS", 1_000)
        )
        atexit.register(self.close)

    def _get_producer(self):
        if not self.enabled:
            return None
        with self._producer_lock:
            if self._producer is not None:
                return self._producer
            try:
                from kafka import KafkaProducer

                timeout_ms = _positive_int("KAFKA_REQUEST_TIMEOUT_MS", 3_000)
                self._producer = KafkaProducer(
                    bootstrap_servers=self.bootstrap,
                    value_serializer=lambda value: json.dumps(value, sort_keys=True).encode("utf-8"),
                    max_block_ms=_positive_int("KAFKA_MAX_BLOCK_MS", 500),
                    request_timeout_ms=timeout_ms,
                    api_version_auto_timeout_ms=min(timeout_ms, 3_000),
                    retries=_positive_int("KAFKA_SEND_RETRIES", 3),
                )
            except Exception as exc:
                log.warning("Kafka producer unavailable; will retry on the next event: %s", type(exc).__name__)
                self._record_delivery_failure(exc)
                self._producer = None
            return self._producer

    def publish(
        self, event: Any, traceparent: str | None = None, headers: Iterable[tuple[str, bytes | str]] | None = None
    ) -> None:
        _assert_boundary_safe(event, headers)
        resolved_headers = _headers_for(event, traceparent, headers)
        self.published.append((event, resolved_headers))
        producer = self._get_producer()
        if producer is None:
            return
        try:
            future = producer.send(event.topic, value=event.to_dict(), headers=resolved_headers)
            if hasattr(future, "add_errback"):
                future.add_errback(self._record_delivery_failure)
        except Exception as exc:
            log.warning("Kafka publish failed for topic %s: %s", getattr(event, "topic", "unknown"), type(exc).__name__)
            self._record_delivery_failure(exc)

    def close(self) -> None:
        with self._producer_lock:
            producer, self._producer = self._producer, None
        if producer is not None:
            try:
                producer.flush(timeout=_positive_int("KAFKA_FLUSH_TIMEOUT_SECONDS", 3))
                producer.close(timeout=_positive_int("KAFKA_FLUSH_TIMEOUT_SECONDS", 3))
            except Exception as exc:
                self._record_delivery_failure(exc)

    @staticmethod
    def _record_delivery_failure(exc: BaseException) -> None:
        log.warning("Kafka delivery failed: %s", type(exc).__name__)
        try:
            from app.metrics import observe_downstream_failure

            observe_downstream_failure("kafka_publisher", type(exc).__name__)
        except Exception:
            pass
