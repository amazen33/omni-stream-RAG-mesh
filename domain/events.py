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
    topic: ClassVar[str] = "domain.events"

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["event_type"] = type(self).__name__
        value["topic"] = self.topic
        return value

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True)
class TelemetryIngested(DomainEvent):
    topic: ClassVar[str] = "telemetry.ingested"
    request_id: str = ""
    source: str = ""
    chunk_count: int = 0
    pii_counts: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class TransactionProcessed(DomainEvent):
    topic: ClassVar[str] = "transaction.processed"
    request_id: str = ""
    transaction_id: str = ""
    status: str = "processed"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PaymentTransactionIngested(DomainEvent):
    """Sanitized payment event contract; raw PAN/CVV never enters this event."""

    topic: ClassVar[str] = "payments.transaction.ingested.v1"
    transaction_id: str = ""
    merchant_id: str = ""
    amount_minor: int = 0
    currency: str = ""
    payment_network: str = ""
    pii_tokenized: bool = True


@dataclass(frozen=True)
class PaymentRiskScored(DomainEvent):
    topic: ClassVar[str] = "payments.risk.scored.v1"
    transaction_id: str = ""
    risk_score: float = 0.0
    decision: str = "review"
    model_version: str = ""


@dataclass(frozen=True)
class AuditRecordLogged(DomainEvent):
    topic: ClassVar[str] = "audit.record.logged"
    request_id: str = ""
    object_key: str = ""
    record_type: str = ""
