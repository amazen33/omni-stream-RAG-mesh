from fastapi.testclient import TestClient

from app.health import HealthService
from app.main import app


def test_liveness_does_not_run_dependency_checks(monkeypatch):
    monkeypatch.setattr("app.main.health", HealthService({"bad": lambda: (_ for _ in ()).throw(AssertionError())}))
    response = TestClient(app).get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "checks": {}}


def test_readiness_returns_503_without_leaking_failure(monkeypatch):
    service = HealthService({"kafka": lambda: (_ for _ in ()).throw(RuntimeError("secret=never"))})
    monkeypatch.setattr("app.main.health", service)
    response = TestClient(app).get("/health/ready")
    assert response.status_code == 503
    assert response.json()["status"] == "failed"
    assert "secret" not in response.text


def test_metrics_has_safe_fixed_labels(monkeypatch):
    monkeypatch.setattr("app.main.health", HealthService({"kafka": lambda: None}))
    TestClient(app).get("/health/ready")
    body = TestClient(app).get("/metrics").text
    assert "rag_health_checks_total" in body
    assert "secret" not in body


def test_schema_registry_is_part_of_readiness_when_configured(monkeypatch):
    monkeypatch.setenv("SCHEMA_REGISTRY_URL", "http://registry.invalid")
    service = HealthService({"schema_registry": lambda: None})
    assert service.report("ready")["checks"]["schema_registry"]["status"] == "ok"


def test_required_spiffe_workload_api_is_a_readiness_dependency(monkeypatch):
    monkeypatch.setenv("REQUIRE_SPIFFE_SVID", "true")
    endpoint = "/run/spiffe/workload/agent.sock"
    monkeypatch.setenv("SPIFFE_ENDPOINT_SOCKET", f"unix://{endpoint}")
    connected: list[str] = []
    available = False

    class FakeSocket:
        def __enter__(self):
            return self

        def __exit__(self, *_args) -> None:
            return None

        def settimeout(self, _timeout: float) -> None:
            return None

        def connect(self, path: str) -> None:
            if not available:
                raise OSError("socket unavailable")
            connected.append(path)

    monkeypatch.setattr("app.health.socket.AF_UNIX", 1, raising=False)
    monkeypatch.setattr("app.health.socket.socket", lambda *_args: FakeSocket())
    service = HealthService()
    assert service.report("ready")["status"] == "failed"
    available = True
    report = service.report("ready")
    assert report["status"] == "ok"
    assert report["checks"]["spiffe_workload_api"]["status"] == "ok"
    assert connected == [endpoint]
