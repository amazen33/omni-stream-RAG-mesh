"""Failure isolation checks: stalled workers stay bounded; payments stay usable."""
from threading import Event

import pytest
from fastapi.testclient import TestClient

from app.main import app
from contexts.ai.resilience import BulkheadRejected, CallTimedOut, ResiliencePolicy
from contexts.ai.services import RetrievalService


def test_timed_out_worker_retains_bulkhead_until_completion():
    release = Event()
    policy = ResiliencePolicy(max_concurrency=1, timeout_seconds=0.02)
    try:
        with pytest.raises(CallTimedOut):
            policy.call(lambda: release.wait(2))
        with pytest.raises(BulkheadRejected):
            policy.call(lambda: "must not run")
        assert policy._active_workers == 1
        assert ResiliencePolicy(boundary="payments").call(lambda: "healthy") == "healthy"
    finally:
        release.set()


@pytest.mark.parametrize("error", [ConnectionError, ValueError, RuntimeError])
def test_failed_retrieval_does_not_break_payments_or_liveness(monkeypatch, error):
    class FailedStore:
        def query(self, *_):
            raise error("sensitive downstream details")

    monkeypatch.setattr("app.main.retrieval", RetrievalService(FailedStore()))
    client = TestClient(app)
    answer = client.post("/ask", json={"question": "evidence?"})
    assert answer.status_code == 200
    assert answer.json()["retrieved"] == []
    assert "sensitive" not in answer.text
    payment = client.post("/payments/transactions", json={
        "transaction_id": "isolated", "merchant_id": "m", "amount_minor": 1, "currency": "USD"
    })
    assert payment.status_code == 200
    assert client.get("/health/live").status_code == 200


def test_rate_budget_is_shared_across_requests_and_separate_from_llm():
    class Store:
        calls = 0

        def query(self, *_):
            self.calls += 1
            return [{"text": "evidence"}]

    store = Store()
    service = RetrievalService(store, resilience=ResiliencePolicy(rate_per_second=1))
    assert service.ask("q", 1, "first")[1]
    assert service.ask("q", 1, "second")[1] == []
    assert store.calls == 1
    assert service.llm_resilience.call(lambda: "independent") == "independent"
