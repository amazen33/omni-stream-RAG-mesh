"""Scheduled, non-destructive synthetic verifier for streaming dependencies.

Every check is bounded and reports only check names and status labels.
"""
from __future__ import annotations

import argparse
import os
import socket
import time
from pathlib import Path
from urllib.request import Request, urlopen


def _timeout() -> float:
    try:
        return max(.05, min(float(os.getenv("DIAGNOSTIC_TIMEOUT_SECONDS", "3")), 10))
    except ValueError:
        return 3.0


def _url(url: str) -> None:
    with urlopen(Request(url, headers={"User-Agent": "rag-diagnostic/1"}), timeout=_timeout()) as response:
        if response.status >= 400:
            raise RuntimeError("unhealthy response")


def _kafka() -> None:
    value = os.getenv("KAFKA_BOOTSTRAP_SERVERS")
    if not value:
        raise LookupError
    endpoint = value.split(",", 1)[0].strip()
    host, _, port = endpoint.rpartition(":")
    with socket.create_connection((host or endpoint, int(port or "9092")), timeout=_timeout()):
        return


def _http_env(name: str) -> None:
    value = os.getenv(name)
    if not value:
        raise LookupError
    _url(value)


def _checkpoint() -> None:
    path = os.getenv("CHECKPOINT_PATH")
    if not path:
        raise LookupError
    if not Path(path).exists():
        raise RuntimeError("checkpoint unavailable")


CHECKS = {
    "kafka": _kafka,
    "spark": lambda: _http_env("SPARK_HEALTH_URL"),
    "checkpoint": _checkpoint,
    "telemetry_sink": lambda: _http_env("TELEMETRY_SINK_HEALTH_URL"),
    "vector_store": lambda: _http_env("CHROMA_HEALTH_URL"),
}


def verify() -> tuple[str, str, float]:
    results = []
    for name, check in CHECKS.items():
        started = time.monotonic()
        try:
            check()
            status = "ok"
        except LookupError:
            status = "disabled"
        except Exception:
            status = "failed"
        results.append((name, status, time.monotonic() - started))
    return results


def exposition(results: list[tuple[str, str, float]]) -> str:
    lines = [
        "# HELP rag_diagnostic_checks_total Synthetic diagnostic checks.",
        "# TYPE rag_diagnostic_checks_total gauge",
    ]
    for name, status, duration in results:
        lines.append(f'rag_diagnostic_checks_total{{check="{name}",status="{status}"}} 1')
        lines.append(f'rag_diagnostic_check_duration_seconds{{check="{name}"}} {duration:.6f}')
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", help="Write Prometheus exposition to this file")
    args = parser.parse_args()
    results = verify()
    payload = exposition(results)
    if args.output:
        Path(args.output).write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0 if all(status in {"ok", "disabled"} for _, status, _ in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
