"""Failure lifecycle tests for correlation, boundary metrics, and rollback audit."""
from __future__ import annotations

import threading
import time

import pytest
from fastapi.testclient import TestClient

import app.main as main
from app.metrics import exposition
from contexts.ai.resilience import BulkheadRejected, CallTimedOut, RateLimitExceeded, ResiliencePolicy
from contexts.governance import NullPublisher
from contexts.payments import PaymentIngestionService, RiskScoringService
from domain.events import IngestionCompensated, PaymentCompensated, TelemetryIngested, TransactionCompensated


TRACEPARENT = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"


def test_structured_correlation_contract_is_immutable_in_payload_and_headers():
    event = TelemetryIngested(correlation_id="correlation-1", causation_id="cause-1", traceparent=TRACEPARENT, request_id="r-1")

    payload = event.to_dict()
    headers = dict(event.headers())
    assert payload["correlation_id"] == "correlation-1"
    assert payload["causation_id"] == "cause-1"
    assert payload["traceparent"] == TRACEPARENT
    assert headers == {
        "correlation_id": b"correlation-1",
        "causation_id": b"cause-1",
        "event_id": event.event_id.encode(),
        "event_type": b"TelemetryIngested",
        "traceparent": TRACEPARENT.encode(),
    }

    publisher = NullPublisher()
    publisher.publish(event, headers=[("tenant", "redacted"), ("correlation_id", "cannot-replace")])
    published_event, published_headers = publisher.published[-1]
    assert published_event is event
    assert dict(published_headers)["correlation_id"] == b"correlation-1"
    assert dict(published_headers)["tenant"] == b"redacted"


def test_boundary_metrics_cover_timeout_rate_limit_and_bulkhead():
    timeout = ResiliencePolicy(timeout_seconds=0.01, boundary="chaos_timeout", operation="invoke")
    with pytest.raises(CallTimedOut):
        timeout.call(lambda: time.sleep(0.05))

    rate_limited = ResiliencePolicy(rate_per_second=1, boundary="chaos_rate_limit", operation="query")
    rate_limited.call(lambda: "ok")
    with pytest.raises(RateLimitExceeded):
        rate_limited.call(lambda: "rejected")

    bulkhead = ResiliencePolicy(max_concurrency=1, boundary="chaos_bulkhead", operation="query")
    started, release = threading.Event(), threading.Event()
    worker = threading.Thread(target=lambda: bulkhead.call(lambda: (started.set(), release.wait())[1]))
    worker.start()
    assert started.wait(timeout=1)
    with pytest.raises(BulkheadRejected):
        bulkhead.call(lambda: "rejected")
    release.set()
    worker.join(timeout=1)

    metrics = exposition()
    assert 'rag_bulkhead_active{boundary="chaos_bulkhead"}' in metrics
    assert 'rag_bulkhead_rejections_total{boundary="chaos_bulkhead"}' in metrics
    assert 'rag_ratelimit_rejections_total{boundary="chaos_rate_limit"}' in metrics
    assert 'rag_boundary_duration_seconds_bucket{boundary="chaos_timeout",operation="invoke"' in metrics
    assert 'rag_downstream_failures_total{boundary="chaos_timeout",dependency="timeout"}' in metrics


def test_ingestion_failure_emits_compensation_and_immutable_audit_transition(monkeypatch):
    def unavailable(*_args, **_kwargs):
        raise RuntimeError("vector store unavailable")

    main.audit.records.clear()
    main.publisher.published.clear()
    monkeypatch.setattr(main.store, "add", unavailable)

    response = TestClient(main.app).post(
        "/ingest-sample",
        headers={"X-Request-ID": "failure-request", "X-Correlation-ID": "failure-correlation", "traceparent": TRACEPARENT},
        json={"text": "evidence", "source": "chaos"},
    )

    assert response.status_code == 502
    transitions = [record for record in main.audit.records if record.get("record_type") == "state_transition"]
    assert [(record["state_from"], record["state_to"]) for record in transitions] == [
        ("INITIALIZED", "PROCESSING"),
        ("PROCESSING", "COMPENSATED"),
    ]
    compensations = [record for record in main.audit.records if record.get("record_type") == "compensation"]
    assert compensations[-1]["correlation_id"] != "failure-correlation"
    assert compensations[-1]["reason"] == "STORE_ADD_FAILED"
    assert "client_request_id" not in transitions[0]["payload"]
    assert "client_correlation_id" not in transitions[0]["payload"]
    assert transitions[0]["payload"]["source_token"].startswith("<PII_SOURCE_")
    assert "failure-request" not in str(transitions)
    assert "failure-correlation" not in str(transitions)
    assert response.headers["X-Correlation-ID"] != "failure-correlation"
    assert any(isinstance(event, IngestionCompensated) for event, _ in main.publisher.published)
    assert 'rag_compensating_events_total{boundary="retrieval_store",reason="STORE_ADD_FAILED"}' in exposition()


def test_retrieval_and_payment_downstream_failures_compensate_and_fail_closed():
    publisher = NullPublisher()
    retrieval = main.RetrievalService(
        store=type("OfflineStore", (), {"query": lambda *_: (_ for _ in ()).throw(RuntimeError("offline"))})(),
        publisher=publisher,
        resilience=ResiliencePolicy(boundary="chaos_retrieval", operation="query"),
    )
    answer, retrieved, compensations = retrieval.ask_with_outcome("question", 1, "r-1", "c-1", TRACEPARENT)
    assert answer and retrieved == []
    assert len(compensations) == 1
    assert isinstance(compensations[0], TransactionCompensated)

    risk_policy = ResiliencePolicy(rate_per_second=1, boundary="chaos_payment", operation="score")
    risk_policy._take_token()
    payment = PaymentIngestionService().ingest({"transaction_id": "tx-1", "merchant_id": "merchant", "amount_minor": 1, "currency": "USD"}, "c-1", TRACEPARENT)
    result = RiskScoringService(publisher=publisher, resilience=risk_policy).score(payment, TRACEPARENT)
    assert result.decision == "review"
    assert result.failure_reason == "DOWNSTREAM_TIMEOUT_FAIL_CLOSED"
    assert any(isinstance(event, PaymentCompensated) for event, _ in publisher.published)
