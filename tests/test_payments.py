import pytest
from fastapi.testclient import TestClient

from contexts.ai.resilience import ResiliencePolicy
from contexts.payments import AnomalyDetectionService, PaymentIngestionService, RiskScoringService
from app.main import app


def test_payment_event_is_sanitized_and_versioned():
    event = PaymentIngestionService().ingest(
        {
            "transaction_id": "tx-1",
            "merchant_id": "merchant-token-1",
            "amount_minor": 850000,
            "currency": "usd",
            "payment_network": "card",
            "pan": "must-not-be-serialized",
        }
    )
    assert event.topic == "payments.transaction.ingested.v1"
    assert event.currency == "USD"
    assert not hasattr(event, "pan")


def test_risk_scoring_fails_safe_to_review():
    event = PaymentIngestionService().ingest(
        {"transaction_id": "tx-2", "merchant_id": "m-2", "amount_minor": 900000, "currency": "EUR"}
    )
    score = RiskScoringService().score(event)
    assert score.topic == "payments.risk.scored.v1"
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
    assert response.status_code == 200
    assert response.json()["decision"] == "allow"
    assert "pan" not in response.text
