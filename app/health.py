"""Cloud-agnostic, bounded health checks for the API."""
from __future__ import annotations

import json
import os
import socket
import time
import base64
from dataclasses import dataclass
from typing import Callable
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from .metrics import observe_check, set_gauge


@dataclass(frozen=True)
class CheckResult:
    status: str
    duration_ms: float
    detail: str | None = None


def _timeout() -> float:
    try:
        return max(0.05, min(float(os.getenv("HEALTH_CHECK_TIMEOUT_SECONDS", "2")), 10))
    except ValueError:
        return 2.0


def _http(url: str, predicate: Callable[[bytes], bool] | None = None) -> None:
    request = Request(url, headers={"User-Agent": "rag-health/1"})
    with urlopen(request, timeout=_timeout()) as response:
        if response.status >= 400:
            raise RuntimeError("unhealthy response")
        body = response.read(16384)
    if predicate and not predicate(body):
        raise RuntimeError("unexpected response")


def _kafka() -> None:
    value = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "")
    if not value:
        raise LookupError("not configured")
    host_port = value.split(",", 1)[0].strip()
    if "://" in host_port:
        host_port = host_port.split("://", 1)[1]
    host, _, port = host_port.rpartition(":")
    if not host:
        host, port = host_port, "9092"
    with socket.create_connection((host.strip("[]"), int(port)), timeout=_timeout()):
        return


def _chroma() -> None:
    url = os.getenv("CHROMA_URL", os.getenv("CHROMA_HOST", ""))
    if not url:
        raise LookupError("not configured")
    if "://" not in url:
        url = f"http://{url}"
    base = url.rstrip("/")
    try:
        _http(f"{base}/api/v2/heartbeat")
    except Exception:
        _http(f"{base}/api/v1/heartbeat")


def _minio() -> None:
    url = os.getenv("MINIO_ENDPOINT_URL", os.getenv("S3_ENDPOINT_URL", ""))
    if not url:
        raise LookupError("not configured")
    _http(url.rstrip("/") + "/minio/health/live")


def _ollama() -> None:
    url = os.getenv("OLLAMA_BASE_URL", "")
    if not url:
        raise LookupError("not configured")
    model = os.getenv("OLLAMA_MODEL", "")
    if not model:
        raise LookupError("not configured")

    def has_model(body: bytes) -> bool:
        try:
            return any(item.get("name") == model for item in json.loads(body).get("models", []))
        except (TypeError, ValueError):
            return False

    _http(url.rstrip("/") + "/api/tags", has_model)


def _schema_registry() -> None:
    url = os.getenv("SCHEMA_REGISTRY_URL", "")
    if not url:
        raise LookupError("not configured")
    request = Request(url.rstrip("/") + "/subjects", headers={"User-Agent": "rag-health/1"})
    key, secret = os.getenv("SCHEMA_REGISTRY_API_KEY"), os.getenv("SCHEMA_REGISTRY_API_SECRET")
    if key and secret:
        token = base64.b64encode(f"{key}:{secret}".encode("utf-8")).decode("ascii")
        request.add_header("Authorization", f"Basic {token}")
    with urlopen(request, timeout=_timeout()) as response:
        if response.status >= 400:
            raise RuntimeError("unhealthy response")


def _audit_store() -> None:
    if os.getenv("ENABLE_AUDIT_STORE", "false").lower() != "true":
        raise LookupError("not configured")
    from .audit import AuditSink

    sink = AuditSink()
    if sink.s3 is not None:
        sink.s3.head_bucket(Bucket=sink.bucket)
    elif sink.azure_container is not None:
        sink.azure_container.get_container_properties(timeout=_timeout())
    else:
        raise RuntimeError("audit store client unavailable")


def _vector_store() -> None:
    if os.getenv("ENABLE_VECTOR_STORE", "false").lower() != "true":
        raise LookupError("not configured")
    from .storage import RetrievalStore

    store = RetrievalStore()
    if store.collection is None or store.embedder is None:
        raise RuntimeError("vector store unavailable")


def _spiffe_svid() -> None:
    """Confirm that the CSI-projected workload SVID is present and non-empty.

    This is intentionally a local check: the SPIFFE CSI driver owns renewal and
    the application must not log or copy its key material.  A mesh deployment
    that explicitly requires an SVID is not ready until the projected identity
    exists, preventing STRICT mTLS from accepting an identity-less workload.
    """
    if os.getenv("REQUIRE_SPIFFE_SVID", "false").lower() != "true":
        raise LookupError("not configured")
    path = os.getenv("SPIFFE_SVID_PATH", "/run/spiffe/workload")
    required = ("svid.pem", "svid.key", "svid_bundle.pem")
    missing = [name for name in required if not os.path.isfile(os.path.join(path, name))]
    empty = [name for name in required if not missing and os.path.getsize(os.path.join(path, name)) == 0]
    if missing or empty:
        raise RuntimeError("SPIFFE workload identity unavailable")


_CHECKS: dict[str, Callable[[], None]] = {
    "kafka": _kafka,
    "schema_registry": _schema_registry,
    "chromadb": _chroma,
    "minio": _minio,
    "ollama": _ollama,
    "audit_store": _audit_store,
    "vector_store": _vector_store,
    "spiffe_svid": _spiffe_svid,
}


class HealthService:
    def __init__(
        self, checks: dict[str, Callable[[], None]] | None = None, required_checks: set[str] | None = None
    ):
        self.checks = checks or _CHECKS
        self.required_checks = required_checks

    def dependency_status(self) -> dict[str, dict[str, object]]:
        results: dict[str, dict[str, object]] = {}
        for name, check in self.checks.items():
            started = time.monotonic()
            try:
                check()
                status, detail = "ok", None
            except LookupError:
                status, detail = "disabled", None
            except Exception:
                status, detail = "failed", "dependency unavailable"
            duration_ms = round((time.monotonic() - started) * 1000, 2)
            observe_check(name, status, duration_ms / 1000)
            results[name] = {"status": status, "duration_ms": duration_ms}
            if detail:
                results[name]["detail"] = detail
        return results

    def _hard_dependencies(self) -> set[str]:
        if self.required_checks is not None:
            return self.required_checks
        # Injected checks in unit tests model only hard dependencies. In the
        # runtime, optional integrations stay diagnostic unless explicitly
        # selected as a hard requirement.
        if self.checks is not _CHECKS:
            return set(self.checks)
        required = {
            item.strip()
            for item in os.getenv("READINESS_REQUIRED_DEPENDENCIES", "").split(",")
            if item.strip()
        }
        if os.getenv("ENABLE_AUDIT_STORE", "false").lower() == "true":
            required.add("audit_store")
        if os.getenv("ENABLE_VECTOR_STORE", "false").lower() == "true":
            required.add("vector_store")
        if os.getenv("REQUIRE_SPIFFE_SVID", "false").lower() == "true":
            required.add("spiffe_svid")
        return required

    def report(self, phase: str) -> dict[str, object]:
        if phase == "live":
            return {"status": "ok", "checks": {}}
        checks = self.dependency_status()
        required = self._hard_dependencies()
        healthy = all(checks.get(name, {}).get("status") == "ok" for name in required)
        set_gauge("rag_ready", float(healthy))
        return {"status": "ok" if healthy else "failed", "checks": checks}
