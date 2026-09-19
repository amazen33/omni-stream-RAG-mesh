"""Optional Kafka publisher; importing the API never requires Kafka."""
from __future__ import annotations
import json
import logging
import os
from typing import Any, Iterable

log = logging.getLogger(__name__)


def _headers_for(
    event: Any, traceparent: str | None, custom_headers: Iterable[tuple[str, bytes | str]] | None
) -> list[tuple[str, bytes]]:
    """Compose stable event headers with optional transport-specific context.

    Mandatory correlation fields are never overridden by injected headers.
    This prevents a caller from making a Kafka header disagree with the
    immutable event payload.
    """
    if hasattr(event, "headers"):
        headers = event.headers(traceparent=traceparent)
    elif hasattr(event, "kafka_headers"):
        headers = event.kafka_headers(traceparent=traceparent)
    else:
        headers = []
    mandatory = {name for name, _ in headers}
    for name, value in custom_headers or ():
        if name in mandatory:
            continue
        headers.append((name, value if isinstance(value, bytes) else str(value).encode("utf-8")))
    return headers


class NullPublisher:
    def __init__(self) -> None:
        self.published: list[tuple[Any, list[tuple[str, bytes]]]] = []

    def publish(
        self, event: Any, traceparent: str | None = None, headers: Iterable[tuple[str, bytes | str]] | None = None
    ) -> None:
        headers = _headers_for(event, traceparent, headers)
        self.published.append((event, headers))
        return None


class EventPublisher:
    def __init__(self, bootstrap: str | None = None) -> None:
        self._producer = None
        self.published: list[tuple[Any, list[tuple[str, bytes]]]] = []
        if os.getenv("ENABLE_KAFKA", "false").lower() == "true":
            try:
                from kafka import KafkaProducer
                self._producer = KafkaProducer(
                    bootstrap_servers=bootstrap or os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092"),
                    value_serializer=lambda value: json.dumps(value).encode(),
                )
            except Exception as exc:
                log.warning("Kafka disabled during startup: %s", exc)

    def publish(
        self, event: Any, traceparent: str | None = None, headers: Iterable[tuple[str, bytes | str]] | None = None
    ) -> None:
        headers = _headers_for(event, traceparent, headers)
        self.published.append((event, headers))

        if self._producer:
            try:
                future = self._producer.send(event.topic, value=event.to_dict(), headers=headers)
                # kafka-python delivery errors occur asynchronously; account
                # for those too instead of only synchronous serialization or
                # connection failures.
                if hasattr(future, "add_errback"):
                    future.add_errback(self._record_delivery_failure)
            except Exception as exc:
                log.warning("Kafka publish failed for topic %s: %s", getattr(event, "topic", "unknown"), exc)
                self._record_delivery_failure(exc)

    @staticmethod
    def _record_delivery_failure(exc: BaseException) -> None:
        log.warning("Kafka delivery failed: %s", exc)
        try:
            from app.metrics import observe_downstream_failure
            observe_downstream_failure("kafka_publisher", type(exc).__name__)
        except Exception:
            pass
