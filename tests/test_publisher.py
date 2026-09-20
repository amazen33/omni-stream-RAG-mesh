"""Kafka publishing stays bounded while retaining tokenized payment ordering."""
from __future__ import annotations

import kafka

from app.redaction import token_for
from contexts.governance.publisher import EventPublisher
from contexts.payments import PaymentIngestionService
from domain.events import TelemetryIngested


class _Future:
    def add_errback(self, _callback) -> None:
        return None


def test_kafka_outage_is_backed_off_instead_of_retrying_every_event(monkeypatch) -> None:
    attempts = 0

    class UnavailableProducer:
        def __init__(self, **_kwargs) -> None:
            nonlocal attempts
            attempts += 1
            raise OSError("broker unavailable")

    monkeypatch.setenv("ENABLE_KAFKA", "true")
    monkeypatch.setenv("KAFKA_RECONNECT_BACKOFF_SECONDS", "60")
    monkeypatch.setattr(kafka, "KafkaProducer", UnavailableProducer)
    publisher = EventPublisher()
    event = TelemetryIngested(source_token=token_for("source", "test", "change-me"))

    publisher.publish(event)
    publisher.publish(event)

    assert attempts == 1


def test_kafka_uses_all_acks_and_a_tokenized_payment_partition_key(monkeypatch) -> None:
    created: dict[str, object] = {}
    sent: dict[str, object] = {}

    class Producer:
        def __init__(self, **kwargs) -> None:
            created.update(kwargs)

        def send(self, topic, *, key, value, headers):
            sent.update(topic=topic, key=key, value=value, headers=headers)
            return _Future()

        def flush(self, timeout) -> None:
            return None

        def close(self, timeout) -> None:
            return None

    monkeypatch.setenv("ENABLE_KAFKA", "true")
    monkeypatch.setattr(kafka, "KafkaProducer", Producer)
    event = PaymentIngestionService(token_key="change-me").ingest(
        {"transaction_id": "tx-key", "merchant_id": "merchant-key", "amount_minor": 1, "currency": "USD"}
    )
    publisher = EventPublisher()

    publisher.publish(event)

    assert created["acks"] == "all"
    assert sent["topic"] == "payments.transaction.ingested.v2"
    assert sent["key"] == event.transaction_token.encode("utf-8")
    assert "tx-key" not in str(sent)
    publisher.close()
