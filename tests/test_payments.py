import pytest
import json
from pathlib import Path
from fastapi.testclient import TestClient

from contexts.ai.resilience import ResiliencePolicy
from contexts.payments import AnomalyDetectionService, PaymentIngestionService, RiskScoringService
from app.main import app, audit


def test_payment_event_is_sanitized_and_versioned():
    event = PaymentIngestionService().ingest({
        "transaction_id": "tx-1",
        "merchant_id": "merchant-token-1",
        "amount_minor": 850000,
        "currency": "usd",
        "payment_network": "card",
    })
    assert event.topic == "payments.transaction.ingested.v2"
    assert event.currency == "USD"
    assert event.pii_tokenized is True

    with pytest.raises(ValueError, match="raw cardholder"):
        PaymentIngestionService().ingest({
            "transaction_id": "tx-1", "merchant_id": "merchant-token-1",
            "amount_minor": 1, "currency": "USD", "pan": "must-not-be-serialized",
        })


def test_risk_scoring_fails_safe_to_review():
    event = PaymentIngestionService().ingest(
        {"transaction_id": "tx-2", "merchant_id": "m-2", "amount_minor": 900000, "currency": "EUR"}
    )
    score = RiskScoringService().score(event)
    assert score.topic == "payments.risk.scored.v2"
    assert score.decision == "review"
    assert 0 <= score.risk_score <= 1


def test_payment_validation_rejects_negative_amount():
    with pytest.raises(ValueError, match="must not be negative"):
        PaymentIngestionService().ingest(
            {"transaction_id": "tx-3", "merchant_id": "m-3", "amount_minor": -1, "currency": "USD"}
        )


def test_risk_scoring_fails_closed_when_policy_rejects():
    policy = ResiliencePolicy(rate_per_second=1)
    policy._take_token()
    event = PaymentIngestionService().ingest(
        {"transaction_id": "tx-5", "merchant_id": "m-5", "amount_minor": 10, "currency": "USD"}
    )
    assert RiskScoringService(resilience=policy).score(event).decision == "review"


def test_anomaly_detector_timeout_is_review_signal():
    detector = AnomalyDetectionService(detector=lambda _: (_ for _ in ()).throw(RuntimeError("offline")))
    assert detector.detect(PaymentIngestionService().ingest(
        {"transaction_id": "tx-6", "merchant_id": "m-6", "amount_minor": 10, "currency": "USD"}
    )) is True


def test_payment_route_returns_risk_decision_without_raw_card_fields():
    response = TestClient(app).post(
        "/payments/transactions",
        json={"transaction_id": "tx-4", "merchant_id": "m-4", "amount_minor": 10, "currency": "usd", "pan": "ignored"},
    )
    assert response.status_code == 422
    # Validation may identify the rejected input field, but the endpoint never
    # invokes payment processing or persists the raw card value.
    assert not any("ignored" in str(record) for record in audit.records)


def test_avro_payment_contracts_match_the_tokenized_v2_events() -> None:
    root = Path(__file__).resolve().parents[1]
    transaction_schema = json.loads(
        (root / "infrastructure/fintech/schemas/payment_transaction_ingested.avsc").read_text(encoding="utf-8")
    )
    risk_schema = json.loads(
        (root / "infrastructure/fintech/schemas/payment_risk_scored.avsc").read_text(encoding="utf-8")
    )
    event = PaymentIngestionService().ingest(
        {"transaction_id": "tx-schema", "merchant_id": "merchant-schema", "amount_minor": 1, "currency": "USD"}
    )
    score = RiskScoringService().score(event)

    assert transaction_schema["namespace"] == "omni.payments.v2"
    assert [field["name"] for field in transaction_schema["fields"]] == list(event.to_dict())
    assert risk_schema["namespace"] == "omni.payments.v2"
    assert [field["name"] for field in risk_schema["fields"]] == list(score.to_dict())
