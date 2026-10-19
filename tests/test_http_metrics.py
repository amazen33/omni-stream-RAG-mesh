"""Public exposition and middleware lifecycle contracts for OMNI-WO-00."""
import asyncio
from collections import defaultdict
from types import SimpleNamespace

from fastapi import FastAPI, Response
from fastapi.testclient import TestClient
import pytest

from app import metrics
from app.http_metrics import HTTPMetricsMiddleware
from app.main import app


@pytest.fixture(autouse=True)
def isolated_registry(monkeypatch):
    for name in ("_counters", "_histogram_sums"):
        monkeypatch.setattr(metrics, name, defaultdict(float))
    for name in ("_histogram_counts", "_histogram_observations"):
        monkeypatch.setattr(metrics, name, defaultdict(int))
    monkeypatch.setattr(metrics, "_gauges", {("rag_http_requests_in_flight", ()): 0.0})


def samples(name):
    return [line for line in metrics.exposition().splitlines() if line.startswith(name + "{")]


def test_thousand_raw_paths_have_one_unmatched_series():
    with TestClient(app) as client:
        for index in range(1000):
            assert client.get(f"/missing-synthetic-{index}?private={index}").status_code == 404
    assert samples("rag_http_requests_total") == [
        'rag_http_requests_total{method="GET",route="unmatched",status_class="4xx"} 1000'
    ]
    assert samples("rag_http_request_duration_seconds_count") == [
        'rag_http_request_duration_seconds_count{method="GET",route="unmatched"} 1000'
    ]
    assert "missing-synthetic" not in metrics.exposition()
    assert "private" not in metrics.exposition()


def test_route_templates_status_classes_and_redirects():
    test_app = FastAPI()
    test_app.add_middleware(HTTPMetricsMiddleware)

    @test_app.get("/items/{item_id}")
    def item(item_id: str, status: int = 200):
        return Response(status_code=status)

    with TestClient(test_app, follow_redirects=False) as client:
        for status in (200, 302, 404, 503, 600):
            assert client.get(f"/items/synthetic-{status}?status={status}").status_code == status
        assert client.get("/items/synthetic-redirect/").status_code == 307
    counters = samples("rag_http_requests_total")
    for category in ("2xx", "3xx", "4xx", "5xx", "other"):
        assert f'rag_http_requests_total{{method="GET",route="/items/{{item_id}}",status_class="{category}"}} 1' in counters
    assert 'rag_http_requests_total{method="GET",route="unmatched",status_class="3xx"} 1' in counters
    total = sum(float(line.rsplit(" ", 1)[1]) for line in counters)
    observations = sum(float(line.rsplit(" ", 1)[1]) for line in samples("rag_http_request_duration_seconds_count"))
    assert total == observations == 6


def test_health_and_metrics_routes_are_instrumented():
    with TestClient(app) as client:
        assert client.get("/healthz").status_code == 200
        assert client.get("/metrics").status_code == 200
    body = metrics.exposition()
    for route in ("/healthz", "/metrics"):
        assert f'route="{route}",status_class="2xx"' in body
    for name, kind in (("rag_http_requests_total", "counter"),
                       ("rag_http_request_duration_seconds", "histogram"),
                       ("rag_http_requests_in_flight", "gauge")):
        assert f"# HELP {name} " in body
        assert f"# TYPE {name} {kind}\n" in body
    assert "rag_http_requests_in_flight 0\n" in body


def test_http_histogram_buckets_are_cumulative():
    for seconds in (0.01, 30, 60, 120, 121):
        metrics.observe_http_request("/ask", "POST", 200, seconds)
    buckets = samples("rag_http_request_duration_seconds_bucket")
    values = [int(line.rsplit(" ", 1)[1]) for line in buckets]
    assert values == sorted(values)
    for le, count in (("30", 2), ("60", 3), ("120", 4), ("+Inf", 5)):
        assert f'rag_http_request_duration_seconds_bucket{{method="POST",route="/ask",le="{le}"}} {count}' in buckets
    assert samples("rag_http_request_duration_seconds_sum") == [
        'rag_http_request_duration_seconds_sum{method="POST",route="/ask"} 331.010000'
    ]


def test_unknown_methods_are_bounded():
    for index in range(1000):
        metrics.observe_http_request("unmatched", f"SYNTHETIC{index}", 405, 0.01)
    assert samples("rag_http_requests_total") == [
        'rag_http_requests_total{method="OTHER",route="unmatched",status_class="4xx"} 1000'
    ]


def test_unhandled_exception_is_counted_and_in_flight_recovers():
    test_app = FastAPI()
    test_app.add_middleware(HTTPMetricsMiddleware)

    @test_app.get("/failure")
    def failure():
        raise RuntimeError("synthetic failure")

    assert TestClient(test_app, raise_server_exceptions=False).get("/failure").status_code == 500
    assert samples("rag_http_requests_total") == [
        'rag_http_requests_total{method="GET",route="/failure",status_class="5xx"} 1'
    ]
    assert "rag_http_requests_in_flight 0\n" in metrics.exposition()


def test_streaming_in_flight_and_disconnect_cleanup():
    async def scenario():
        entered = asyncio.Event()
        release = asyncio.Event()

        async def streaming(scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"part", "more_body": True})
            entered.set()
            await release.wait()
            await send({"type": "http.response.body", "body": b"done"})

        async def send(_message):
            assert "rag_http_requests_in_flight 1\n" in metrics.exposition()

        async def receive():
            return {"type": "http.disconnect"}

        scope = {"type": "http", "method": "GET", "route": SimpleNamespace(path="/stream")}
        task = asyncio.create_task(HTTPMetricsMiddleware(streaming)(scope, receive, send))
        await entered.wait()
        assert samples("rag_http_requests_total") == []
        release.set()
        await task
        assert "rag_http_requests_in_flight 0\n" in metrics.exposition()
        # A cancellation must also release the gauge and record one observation.
        entered.clear()
        release.clear()
        task = asyncio.create_task(HTTPMetricsMiddleware(streaming)(scope, receive, send))
        await entered.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert "rag_http_requests_in_flight 0\n" in metrics.exposition()

    asyncio.run(scenario())
    assert samples("rag_http_request_duration_seconds_count") == [
        'rag_http_request_duration_seconds_count{method="GET",route="/stream"} 2'
    ]
