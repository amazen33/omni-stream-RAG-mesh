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
