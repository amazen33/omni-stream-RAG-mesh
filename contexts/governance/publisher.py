"""Optional Kafka publisher; importing the API never requires Kafka."""
from __future__ import annotations
import json
import logging
import os
from typing import Any

log = logging.getLogger(__name__)


class NullPublisher:
    def publish(self, event: Any) -> None:
        return None


class EventPublisher:
    def __init__(self, bootstrap: str | None = None) -> None:
        self._producer = None
        if os.getenv("ENABLE_KAFKA", "false").lower() == "true":
            try:
                from kafka import KafkaProducer
                self._producer = KafkaProducer(
                    bootstrap_servers=bootstrap or os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092"),
                    value_serializer=lambda value: json.dumps(value).encode(),
                )
            except Exception as exc:
                log.warning("Kafka disabled during startup: %s", exc)

    def publish(self, event: Any) -> None:
        if self._producer:
            self._producer.send(event.topic, event.to_dict())
