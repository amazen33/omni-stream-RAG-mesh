"""Small dependency-free Prometheus metrics registry for service diagnostics."""
from __future__ import annotations

from collections import defaultdict
from threading import Lock

_lock = Lock()
_counters: dict[tuple[str, str], float] = defaultdict(float)
_gauges: dict[tuple[str, str], float] = {}


def observe_check(name: str, status: str, duration_seconds: float) -> None:
    """Record a check without putting target URLs, models, or error text in labels."""
    with _lock:
        _counters[("rag_health_checks_total", f'{name}|{status}')] += 1
        _gauges[("rag_health_check_duration_seconds", name)] = duration_seconds


def set_gauge(name: str, value: float) -> None:
    with _lock:
        _gauges[(name, "")] = value


def exposition() -> str:
    lines = [
        "# HELP rag_health_checks_total Number of dependency health checks.",
        "# TYPE rag_health_checks_total counter",
    ]
    with _lock:
        for (metric, labels), value in sorted(_counters.items()):
            name, status = labels.split("|", 1)
            lines.append(f'{metric}{{check="{name}",status="{status}"}} {value:g}')
        lines.extend([
            "# HELP rag_health_check_duration_seconds Duration of the latest dependency check.",
            "# TYPE rag_health_check_duration_seconds gauge",
        ])
        for (metric, check), value in sorted(_gauges.items()):
            if metric == "rag_health_check_duration_seconds":
                lines.append(f'{metric}{{check="{check}"}} {value:.6f}')
            else:
                lines.extend([
                    f"# HELP {metric} Service health gauge.",
                    f"# TYPE {metric} gauge",
                    f"{metric} {value:g}",
                ])
    return "\n".join(lines) + "\n"
