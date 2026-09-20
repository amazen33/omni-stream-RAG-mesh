"""Application services for sanitized payment streams."""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
import os
import re
from typing import Any
import uuid

from app.redaction import token_for
from domain.events import PaymentCompensated, PaymentRiskScored, PaymentTransactionIngested
from contexts.ai.resilience import ResiliencePolicy


_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_CURRENCY = re.compile(r"^[A-Z]{3}$")
_PROHIBITED_PAYMENT_FIELDS = {"pan", "card_number", "cvv", "cvc", "pin", "track_data"}
_CURRENCY_EXPONENTS = {"BHD": 3, "JPY": 0, "KWD": 3, "OMR": 3, "TND": 3}


def _validate_identifier(name: str, value: object) -> str:
    normalized = str(value)
    if not _IDENTIFIER.fullmatch(normalized):
        raise ValueError(f"{name} must be a tokenized safe identifier")
    return normalized


@dataclass(frozen=True)
class PaymentIngestionService:
    """Tokenizes identifiers before emitting a schema-versioned event."""

    publisher: Any | None = None
    token_key: str = field(default_factory=lambda: os.getenv("PII_TOKEN_SALT", "change-me"))

    def ingest(
        self, payload: dict[str, Any], correlation_id: str | None = None, traceparent: str | None = None
    ) -> PaymentTransactionIngested:
        required = ("transaction_id", "merchant_id", "amount_minor", "currency")
        if any(not payload.get(key) and payload.get(key) != 0 for key in required):
            raise ValueError("payment envelope is missing required fields")
        prohibited = _PROHIBITED_PAYMENT_FIELDS.intersection(payload)
        if prohibited:
            raise ValueError("payment envelope must not contain raw cardholder fields")
        amount = int(Decimal(str(payload["amount_minor"])))
        if amount < 0:
            raise ValueError("amount_minor must not be negative")
        tx_id = _validate_identifier("transaction_id", payload["transaction_id"])
        merchant_id = _validate_identifier("merchant_id", payload["merchant_id"])
        currency = str(payload["currency"]).upper()
        if not _CURRENCY.fullmatch(currency):
            raise ValueError("currency must be a three-letter ISO code")
        payment_network = str(payload.get("payment_network", "unknown"))
        if not _IDENTIFIER.fullmatch(payment_network):
            raise ValueError("payment_network must be a safe identifier")
        if not self.token_key:
            raise ValueError("PII token key must not be empty")
        # The raw values remain only in this ingress service long enough to
        # validate and deterministically HMAC-tokenize them.  The event is the
        # first value allowed to reach Kafka or another bounded context.
        transaction_token = token_for("payment_transaction", tx_id, self.token_key)
        merchant_token = token_for("payment_merchant", merchant_id, self.token_key)
        cid = correlation_id or str(uuid.uuid4())
        event = PaymentTransactionIngested(
            correlation_id=cid,
            traceparent=traceparent or "",
            transaction_token=transaction_token,
            merchant_token=merchant_token,
            amount_minor=amount,
            currency=currency,
            payment_network=payment_network,
            pii_tokenized=True,
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
    anomaly_detector: Any | None = None

    def score(self, event: PaymentTransactionIngested, traceparent: str | None = None) -> PaymentRiskScored:
        policy = self.resilience or ResiliencePolicy(boundary="payment_risk_scoring", operation="score")
        failure_reason = ""
        try:
            exponent = _CURRENCY_EXPONENTS.get(event.currency, 2)
            amount_major = Decimal(event.amount_minor) / (Decimal(10) ** exponent)
            score = policy.call(lambda: min(1.0, round(float(amount_major / Decimal("10000")), 4)))
            if self.anomaly_detector is not None and self.anomaly_detector.detect(event):
                score = max(score, 0.7)
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
                        transaction_token=event.transaction_token,
                        decision="review",
                        error_detail=type(exc).__name__,
                        reason=failure_reason,
                        original_event_type=type(event).__name__,
                    ),
                    traceparent=traceparent,
                )
        result = PaymentRiskScored(
            correlation_id=event.correlation_id,
            causation_id=event.event_id,
            traceparent=traceparent or event.traceparent,
            transaction_token=event.transaction_token,
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
