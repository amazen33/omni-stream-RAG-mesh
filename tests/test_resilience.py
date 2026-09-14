import time

from contexts.ai.resilience import CallTimedOut, RateLimitExceeded, ResiliencePolicy


def test_timeout_returns_safe_error():
    policy = ResiliencePolicy(timeout_seconds=0.01)
    try:
        policy.call(lambda: time.sleep(0.05))
    except CallTimedOut:
        pass
    else:
        raise AssertionError("expected timeout")


def test_rate_limit_rejects_burst():
    policy = ResiliencePolicy(rate_per_second=1)
    policy.call(lambda: "ok")
    try:
        policy.call(lambda: "rejected")
    except RateLimitExceeded:
        pass
    else:
        raise AssertionError("expected rate limit rejection")


def test_retrieval_falls_back_when_dependency_times_out():
    from contexts.ai.services import RetrievalService

    service = RetrievalService(
        store=type("Store", (), {"query": lambda *_: time.sleep(0.05)})(),
        resilience=ResiliencePolicy(timeout_seconds=0.01),
    )
    answer, retrieved = service.ask("question", 1, "request")
    assert retrieved == []
    assert answer
