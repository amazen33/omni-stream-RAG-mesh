"""Deterministic failure-injection checks for the retrieval resilience contract."""
import time

from contexts.ai.services import RetrievalService
from contexts.ai.resilience import ResiliencePolicy


def test_llm_timeout_does_not_cascade_to_request_failure():
    class Store:
        def query(self, *_):
            return [{"text": "evidence"}]

    class SlowModel:
        def invoke(self, _):
            time.sleep(0.05)

    service = RetrievalService(
        Store(), llm=SlowModel(), resilience=ResiliencePolicy(timeout_seconds=0.01)
    )
    answer, retrieved = service.ask("question", 1, "request")
    assert retrieved
    assert answer
