"""Startup and failure-path security checks in isolated application processes."""
import ast
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.settings import RuntimeSettings
from domain import events


def isolated(code, *, profile=None, key=None, docs="false", tracebacks="false"):
    env = dict(os.environ, ENABLE_API_DOCS=docs, LOG_INCLUDE_TRACEBACKS=tracebacks)
    for name, value in (("RUNTIME_PROFILE", profile), ("PII_TOKEN_SALT", key)):
        if value is None:
            env.pop(name, None)
        else:
            env[name] = value
    return subprocess.run([sys.executable, "-c", code], env=env, capture_output=True,
                          text=True, timeout=30)


@pytest.mark.parametrize("profile,key", [(None, None), (None, "change-me"),
    ("production", ""), ("production", "local-demo-only"), ("unknown", "synthetic-key")])
def test_unsafe_startup_is_rejected(profile, key):
    result = isolated("import app.main", profile=profile, key=key)
    assert result.returncode != 0
    assert "RUNTIME_PROFILE" in result.stderr or "PII_TOKEN_SALT" in result.stderr


def test_local_profile_starts_without_an_external_key():
    result = isolated("import app.main; print('started')", profile="local")
    assert result.returncode == 0, result.stderr
    assert "started" in result.stdout


def test_unset_profile_is_production_with_a_valid_key():
    result = isolated("from app.main import settings; print(settings.profile)", key="synthetic-production-key")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "production"


@pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json"])
def test_api_documentation_is_disabled_by_default(path):
    with TestClient(app) as client:
        assert client.get(path).status_code == 404


@pytest.mark.parametrize("profile,expected", [("test", 200), ("production", 404)])
def test_docs_opt_in_is_limited_to_development_profiles(profile, expected):
    code = "from fastapi.testclient import TestClient; from app.main import app; print(TestClient(app).get('/openapi.json').status_code)"
    result = isolated(code, profile=profile, key="synthetic-production-key", docs="true")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == str(expected)


def test_all_boundaries_use_the_same_validated_key(monkeypatch):
    from app.audit import AuditSink
    from contexts.governance.publisher import EventPublisher, NullPublisher
    monkeypatch.setenv("PII_TOKEN_SALT", "synthetic-shared-key")
    settings = RuntimeSettings.from_environment()
    assert {AuditSink(settings).pii_token_key, NullPublisher(settings).pii_token_key,
            EventPublisher(settings=settings).pii_token_key} == {settings.token_key}


@pytest.mark.parametrize("boundary,status", [("store", 502), ("audit", 503)])
def test_production_failure_logs_only_structured_metadata(boundary, status):
    method = "main.store.add" if boundary == "store" else "main.audit.write"
    code = f'''from fastapi.testclient import TestClient
from app import main
def fail(*args, **kwargs):
    raise RuntimeError("synthetic-private-error-text")
{method} = fail
print(TestClient(main.app).post("/ingest-sample", json={{"text": "synthetic evidence"}}).status_code)
'''
    result = isolated(code, profile="production", key="synthetic-production-key", tracebacks="true")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == str(status)
    assert "Traceback" not in result.stderr
    assert "synthetic-private-error-text" not in result.stderr
    records = [json.loads(line) for line in result.stderr.splitlines() if line.startswith('{')]
    assert records
    assert all(set(record) == {"event", "request_id", "correlation_id", "exception_type"} for record in records)
    assert all(record["request_id"] and record["correlation_id"] for record in records)
    assert all(record["exception_type"] == "RuntimeError" for record in records)


def test_spark_default_subscribes_to_all_concrete_domain_event_topics():
    source = Path("streaming/spark_job.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    default = next(node.args[1].value for node in ast.walk(tree)
                   if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                   and node.func.attr == "getenv" and node.args
                   and isinstance(node.args[0], ast.Constant) and node.args[0].value == "STREAMING_TOPICS")
    produced = {cls.topic for cls in vars(events).values() if isinstance(cls, type)
                and issubclass(cls, events.DomainEvent)
                and cls not in {events.DomainEvent, events.CompensatingEvent}}
    assert set(default.split(',')) == produced
