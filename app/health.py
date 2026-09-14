"""Cloud-agnostic, bounded health checks for the API."""
from __future__ import annotations

import json
import os
import socket
import time
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
    _http(url.rstrip("/") + "/subjects")


_CHECKS: dict[str, Callable[[], None]] = {
    "kafka": _kafka,
    "schema_registry": _schema_registry,
    "chromadb": _chroma,
    "minio": _minio,
    "ollama": _ollama,
}


class HealthService:
    def __init__(self, checks: dict[str, Callable[[], None]] | None = None):
        self.checks = checks or _CHECKS

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
        set_gauge("rag_ready", float(all(v["status"] in {"ok", "disabled"} for v in results.values())))
        return results

    def report(self, phase: str) -> dict[str, object]:
        if phase == "live":
            return {"status": "ok", "checks": {}}
        checks = self.dependency_status()
        healthy = all(item["status"] in {"ok", "disabled"} for item in checks.values())
        return {"status": "ok" if healthy else "failed", "checks": checks}
