"""Regression tests for the RAG privacy boundary and trace ownership."""
import pytest
from fastapi.testclient import TestClient

import app.main as main
from app.redaction import token_for
from contexts.governance import NullPublisher
from domain.events import PaymentTransactionIngested, TelemetryIngested


def test_rag_boundary_indexes_and_audits_only_hmac_tokens() -> None:
    client = TestClient(main.app)
    raw_email = "alice@example.com"
    raw_source = "alice@example.com"
    raw_transaction = "alice-transaction"
    raw_merchant = "alice-merchant"
    main.audit.records.clear()
    main.publisher.published.clear()

    ingestion = client.post(
        "/ingest-sample",
        headers={
            "X-Request-ID": "caller-request-id",
            "X-Correlation-ID": "caller-correlation-id",
        },
        json={"text": f"Contact {raw_email} for the evidence.", "source": raw_source},
    )
    assert ingestion.status_code == 200
    assert ingestion.headers["X-Request-ID"] != "caller-request-id"
    assert ingestion.headers["X-Correlation-ID"] != "caller-correlation-id"

    telemetry = next(event for event, _ in main.publisher.published if isinstance(event, TelemetryIngested))
    assert telemetry.source_token == token_for("source", raw_source, main.redactor.salt)
    assert raw_source not in telemetry.to_json()

    query = client.post("/ask", json={"question": f"Find {raw_email}"})
    assert query.status_code == 200
    assert raw_email not in str(query.json())

    payment = client.post(
        "/payments/transactions",
        json={
            "transaction_id": raw_transaction,
            "merchant_id": raw_merchant,
            "amount_minor": 100,
            "currency": "USD",
        },
    )
    assert payment.status_code == 200
    assert payment.json()["transaction_token"] == token_for(
        "payment_transaction", raw_transaction, main.redactor.salt
    )
    assert raw_transaction not in str(payment.json())

    payment_event = next(
        event for event, _ in main.publisher.published if isinstance(event, PaymentTransactionIngested)
    )
    assert raw_transaction not in payment_event.to_json()
    assert raw_merchant not in payment_event.to_json()

    boundary_data = f"{list(main.audit.records)!r}{main.publisher.published!r}"
    for raw_value in (raw_email, raw_source, raw_transaction, raw_merchant, "caller-request-id"):
        assert raw_value not in boundary_data


def test_publisher_refuses_an_event_with_an_untokenized_sensitive_field() -> None:
    with pytest.raises(ValueError, match="unsanitized"):
        NullPublisher().publish(TelemetryIngested(source_token="raw-source"))
