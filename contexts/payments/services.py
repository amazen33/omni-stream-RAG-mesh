"""Application services for sanitized payment streams."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from domain.events import PaymentRiskScored, PaymentTransactionIngested


@dataclass(frozen=True)
class PaymentIngestionService:
    """Validates the payment envelope and emits a schema-versioned event."""

    publisher: Any | None = None

    def ingest(self, payload: dict[str, Any]) -> PaymentTransactionIngested:
        required = ("transaction_id", "merchant_id", "amount_minor", "currency")
        if any(not payload.get(key) and payload.get(key) != 0 for key in required):
            raise ValueError("payment envelope is missing required fields")
        amount = int(Decimal(str(payload["amount_minor"])))
        if amount < 0:
            raise ValueError("amount_minor must not be negative")
        event = PaymentTransactionIngested(
            transaction_id=str(payload["transaction_id"]),
            merchant_id=str(payload["merchant_id"]),
            amount_minor=amount,
            currency=str(payload["currency"]).upper(),
            payment_network=str(payload.get("payment_network", "unknown")),
        )
        if self.publisher:
            self.publisher.publish(event)
        return event


@dataclass(frozen=True)
class RiskScoringService:
    """Deterministic baseline scorer; replace with a governed model adapter."""

    model_version: str = "baseline-v1"
    publisher: Any | None = None

    def score(self, event: PaymentTransactionIngested) -> PaymentRiskScored:
        score = min(1.0, round(event.amount_minor / 1_000_000, 4))
        decision = "review" if score >= 0.7 else "allow"
        result = PaymentRiskScored(
            transaction_id=event.transaction_id,
            risk_score=score,
            decision=decision,
            model_version=self.model_version,
        )
        if self.publisher:
            self.publisher.publish(result)
        return result
