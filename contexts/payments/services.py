"""Application services for sanitized payment streams."""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from domain.events import PaymentCompensated, PaymentRiskScored, PaymentTransactionIngested
from contexts.ai.resilience import ResiliencePolicy


@dataclass(frozen=True)
class PaymentIngestionService:
    """Validates the payment envelope and emits a schema-versioned event."""

    publisher: Any | None = None

    def ingest(
        self, payload: dict[str, Any], correlation_id: str | None = None, traceparent: str | None = None
    ) -> PaymentTransactionIngested:
        required = ("transaction_id", "merchant_id", "amount_minor", "currency")
        if any(not payload.get(key) and payload.get(key) != 0 for key in required):
            raise ValueError("payment envelope is missing required fields")
        amount = int(Decimal(str(payload["amount_minor"])))
        if amount < 0:
            raise ValueError("amount_minor must not be negative")
        tx_id = str(payload["transaction_id"])
        cid = correlation_id or tx_id
        event = PaymentTransactionIngested(
            correlation_id=cid,
            traceparent=traceparent or "",
            transaction_id=tx_id,
            merchant_id=str(payload["merchant_id"]),
            amount_minor=amount,
            currency=str(payload["currency"]).upper(),
            payment_network=str(payload.get("payment_network", "unknown")),
        )
        if self.publisher:
            self.publisher.publish(event, traceparent=traceparent)
        return event


@dataclass(frozen=True)
class RiskScoringService:
    """Deterministic baseline scorer; replace with a governed model adapter."""

    model_version: str = "baseline-v1"
    publisher: Any | None = None
    resilience: ResiliencePolicy = field(default_factory=lambda: ResiliencePolicy(boundary="payment_risk_scoring", operation="score"))

    def score(self, event: PaymentTransactionIngested, traceparent: str | None = None) -> PaymentRiskScored:
        policy = self.resilience or ResiliencePolicy(boundary="payment_risk_scoring", operation="score")
        failure_reason = ""
        try:
            score = policy.call(lambda: min(1.0, round(event.amount_minor / 1_000_000, 4)))
            decision = "review" if score >= 0.7 else "allow"
        except Exception as exc:
            # A risk decision cannot be safely inferred after a dependency
            # failure.  Fail closed and leave an explicit compensating trail.
            score, decision = 0.0, "review"
            failure_reason = "DOWNSTREAM_TIMEOUT_FAIL_CLOSED"
            if self.publisher:
                self.publisher.publish(
                    PaymentCompensated(
                        correlation_id=event.correlation_id,
                        causation_id=event.event_id,
                        traceparent=traceparent or event.traceparent,
                        transaction_id=event.transaction_id,
                        decision="review",
                        error_detail=str(exc),
                        reason=failure_reason,
                        original_event_type=type(event).__name__,
                    ),
                    traceparent=traceparent,
                )
        result = PaymentRiskScored(
            correlation_id=event.correlation_id,
            causation_id=event.event_id,
            traceparent=traceparent or event.traceparent,
            transaction_id=event.transaction_id,
            risk_score=score,
            decision=decision,
            model_version=self.model_version,
            failure_reason=failure_reason,
        )
        if self.publisher:
            self.publisher.publish(result, traceparent=traceparent)
        return result


@dataclass(frozen=True)
class AnomalyDetectionService:
    """Governed anomaly adapter with a fail-closed review decision."""

    detector: Any | None = None
    resilience: ResiliencePolicy = field(default_factory=lambda: ResiliencePolicy(boundary="payment_anomaly", operation="detect"))

    def detect(self, event: PaymentTransactionIngested) -> bool:
        if self.detector is None:
            return False
        policy = self.resilience or ResiliencePolicy()
        try:
            return bool(policy.call(lambda: self.detector(event)))
        except Exception:
            return True
