"""Integration events emitted by the platform.

The event names are deliberately stable: they are the Kafka topic contract.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, ClassVar
import json
import uuid


@dataclass(frozen=True)
class DomainEvent:
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    occurred_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    # A root event has no predecessor, so it receives its own immutable
    # causation id.  Child events explicitly use the triggering event id.
    causation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    traceparent: str = ""
    topic: ClassVar[str] = "domain.events"

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["event_type"] = type(self).__name__
        value["topic"] = self.topic
        return value

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))

    def headers(self, traceparent: str | None = None) -> list[tuple[str, bytes]]:
        """Return the portable Kafka header contract for this event.

        Correlation metadata is intentionally also part of ``to_dict`` via the
        dataclass fields.  That keeps consumers that cannot inspect Kafka
        headers (for example archived payloads) fully traceable.
        """
        headers: list[tuple[str, bytes]] = [
            ("correlation_id", str(self.correlation_id).encode("utf-8")),
            ("causation_id", str(self.causation_id).encode("utf-8")),
            ("event_id", str(self.event_id).encode("utf-8")),
            ("event_type", type(self).__name__.encode("utf-8")),
        ]
        active_traceparent = traceparent or self.traceparent
        if active_traceparent:
            headers.append(("traceparent", active_traceparent.encode("utf-8")))
        return headers

    # Kept as a compatibility alias for consumers introduced before the public
    # ``headers`` method was named in the event contract.
    def kafka_headers(self, traceparent: str | None = None) -> list[tuple[str, bytes]]:
        return self.headers(traceparent=traceparent)


@dataclass(frozen=True)
class TelemetryIngested(DomainEvent):
    topic: ClassVar[str] = "telemetry.ingested"
    request_id: str = ""
    # HMAC token created at the RAG ingress boundary; raw source labels never
    # leave that boundary for telemetry, Kafka, or audit storage.
    source_token: str = ""
    chunk_count: int = 0
    pii_counts: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class TransactionProcessed(DomainEvent):
    topic: ClassVar[str] = "transaction.processed"
    request_id: str = ""
    # This is the server-generated operation/request identifier, not a caller
    # transaction reference.  The name prevents a future producer from placing
    # a raw payment identifier into the generic retrieval event contract.
    operation_id: str = ""
    status: str = "processed"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PaymentTransactionIngested(DomainEvent):
    """Sanitized payment event contract; raw identifiers never enter this event."""

    topic: ClassVar[str] = "payments.transaction.ingested.v1"
    transaction_token: str = ""
    merchant_token: str = ""
    amount_minor: int = 0
    currency: str = ""
    payment_network: str = ""
    pii_tokenized: bool = True


@dataclass(frozen=True)
class PaymentRiskScored(DomainEvent):
    topic: ClassVar[str] = "payments.risk.scored.v1"
    transaction_token: str = ""
    risk_score: float = 0.0
    decision: str = "review"
    model_version: str = ""
    failure_reason: str = ""


@dataclass(frozen=True)
class AuditRecordLogged(DomainEvent):
    topic: ClassVar[str] = "audit.record.logged"
    request_id: str = ""
    object_key: str = ""
    record_type: str = ""


@dataclass(frozen=True)
class CompensatingEvent(DomainEvent):
    """Base for compensating events emitted when downstream steps fail."""
    topic: ClassVar[str] = "domain.compensations"
    reason: str = ""
    original_event_type: str = ""


@dataclass(frozen=True)
class IngestionCompensated(CompensatingEvent):
    topic: ClassVar[str] = "ingestion.compensated"
    request_id: str = ""
    source_token: str = ""
    error_detail: str = ""


@dataclass(frozen=True)
class TransactionCompensated(CompensatingEvent):
    topic: ClassVar[str] = "transaction.compensated"
    request_id: str = ""
    operation_id: str = ""
    error_detail: str = ""


@dataclass(frozen=True)
class PaymentCompensated(CompensatingEvent):
    topic: ClassVar[str] = "payments.compensated.v1"
    transaction_token: str = ""
    decision: str = "review"
    error_detail: str = ""


@dataclass(frozen=True)
class StateTransitionLogged(DomainEvent):
    """CQRS state transition record for end-to-end tracing."""
    topic: ClassVar[str] = "state.transition.logged"
    request_id: str = ""
    entity_id: str = ""
    state_from: str = ""
    state_to: str = ""
    reason: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
