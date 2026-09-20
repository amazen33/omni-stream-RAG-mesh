"""Small dependency-free Prometheus metrics registry for service diagnostics and boundary metrics."""
from __future__ import annotations

from collections import defaultdict
from threading import Lock
from typing import Dict, Tuple

_lock = Lock()
_counters: dict[tuple[str, tuple[tuple[str, str], ...]], float] = defaultdict(float)
_gauges: dict[tuple[str, tuple[tuple[str, str], ...]], float] = {}
_histogram_counts: dict[tuple[str, tuple[tuple[str, str], ...], float], int] = defaultdict(int)
_histogram_sums: dict[tuple[str, tuple[tuple[str, str], ...]], float] = defaultdict(float)
_histogram_observations: dict[tuple[str, tuple[tuple[str, str], ...]], int] = defaultdict(int)
_DURATION_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)

# Help text and type catalog for standard metrics
_METRIC_HELP: dict[str, str] = {
    "rag_health_checks_total": "Number of dependency health checks.",
    "rag_health_check_duration_seconds": "Duration of the latest dependency check.",
    "rag_ready": "Service readiness status gauge.",
    "rag_bulkhead_active": "Currently active concurrent operations in bulkhead.",
    "rag_bulkhead_rejections_total": "Total operations rejected by bulkhead saturation.",
    "rag_ratelimit_rejections_total": "Total operations rejected by rate limiters.",
    "rag_boundary_duration_seconds": "Duration of operation at service boundary.",
    "rag_downstream_failures_total": "Total downstream dependency failures caught at boundary.",
    "rag_compensating_events_total": "Total compensating events triggered due to failure.",
}

_METRIC_TYPES: dict[str, str] = {
    "rag_health_checks_total": "counter",
    "rag_health_check_duration_seconds": "gauge",
    "rag_ready": "gauge",
    "rag_bulkhead_active": "gauge",
    "rag_bulkhead_rejections_total": "counter",
    "rag_ratelimit_rejections_total": "counter",
    "rag_boundary_duration_seconds": "histogram",
    "rag_downstream_failures_total": "counter",
    "rag_compensating_events_total": "counter",
}


def _label_tuple(labels: dict[str, str] | None) -> tuple[tuple[str, str], ...]:
    if not labels:
        return ()
    return tuple(sorted((k, str(v)) for k, v in labels.items()))


def inc_counter(name: str, labels: dict[str, str] | None = None, value: float = 1.0) -> None:
    with _lock:
        _counters[(name, _label_tuple(labels))] += value


def set_gauge(name: str, value: float, labels: dict[str, str] | None = None) -> None:
    with _lock:
        _gauges[(name, _label_tuple(labels))] = value


def observe_check(name: str, status: str, duration_seconds: float) -> None:
    """Record a health check without putting target URLs, models, or secrets in labels."""
    inc_counter("rag_health_checks_total", {"check": name, "status": status})
    set_gauge("rag_health_check_duration_seconds", duration_seconds, {"check": name})


def observe_bulkhead_active(boundary: str, active: float) -> None:
    set_gauge("rag_bulkhead_active", active, {"boundary": boundary})


def observe_bulkhead_rejection(boundary: str) -> None:
    inc_counter("rag_bulkhead_rejections_total", {"boundary": boundary})


def observe_ratelimit_rejection(boundary: str) -> None:
    inc_counter("rag_ratelimit_rejections_total", {"boundary": boundary})


def observe_boundary_duration(boundary: str, operation: str, duration_seconds: float) -> None:
    labels = _label_tuple({"boundary": boundary, "operation": operation})
    with _lock:
        metric = "rag_boundary_duration_seconds"
        _histogram_sums[(metric, labels)] += duration_seconds
        _histogram_observations[(metric, labels)] += 1
        for bucket in _DURATION_BUCKETS:
            if duration_seconds <= bucket:
                _histogram_counts[(metric, labels, bucket)] += 1


def observe_downstream_failure(boundary: str, dependency: str) -> None:
    inc_counter("rag_downstream_failures_total", {"boundary": boundary, "dependency": dependency})


def observe_compensating_event(boundary: str, reason: str) -> None:
    inc_counter("rag_compensating_events_total", {"boundary": boundary, "reason": reason})


def exposition() -> str:
    """Produce standard Prometheus exposition text grouped by metric family."""
    lines: list[str] = []

    with _lock:
        # Group counters by metric name
        counter_families: dict[str, list[tuple[tuple[tuple[str, str], ...], float]]] = defaultdict(list)
        for (metric, label_tuple), val in sorted(_counters.items()):
            counter_families[metric].append((label_tuple, val))

        # Declare every supported family even before its first observation.
        # This makes dashboards and scrape-time contract checks deterministic.
        counter_names = set(counter_families) | {
            metric for metric, metric_type in _METRIC_TYPES.items() if metric_type == "counter"
        }
        for metric in sorted(counter_names):
            entries = counter_families.get(metric, [])
            help_text = _METRIC_HELP.get(metric, f"{metric} counter")
            m_type = _METRIC_TYPES.get(metric, "counter")
            lines.append(f"# HELP {metric} {help_text}")
            lines.append(f"# TYPE {metric} {m_type}")
            for label_tuple, val in entries:
                if label_tuple:
                    lbl_str = ",".join(f'{k}="{v}"' for k, v in label_tuple)
                    lines.append(f"{metric}{{{lbl_str}}} {val:g}")
                else:
                    lines.append(f"{metric} {val:g}")

        histogram_names = {
            metric for metric, metric_type in _METRIC_TYPES.items() if metric_type == "histogram"
        }
        for metric in sorted(histogram_names):
            lines.append(f"# HELP {metric} {_METRIC_HELP[metric]}")
            lines.append(f"# TYPE {metric} histogram")
            label_sets = {
                labels for (name, labels) in _histogram_observations if name == metric
            }
            for labels in sorted(label_sets):
                for bucket in _DURATION_BUCKETS:
                    count = _histogram_counts[(metric, labels, bucket)]
                    rendered = list(labels) + [("le", f"{bucket:g}")]
                    lines.append(
                        f'{metric}_bucket{{' + ",".join(f'{key}="{value}"' for key, value in rendered) + f"}} {count}"
                    )
                count = _histogram_observations[(metric, labels)]
                rendered = list(labels) + [("le", "+Inf")]
                lines.append(
                    f'{metric}_bucket{{' + ",".join(f'{key}="{value}"' for key, value in rendered) + f"}} {count}"
                )
                label_text = ",".join(f'{key}="{value}"' for key, value in labels)
                lines.append(f"{metric}_sum{{{label_text}}} {_histogram_sums[(metric, labels)]:.6f}")
                lines.append(f"{metric}_count{{{label_text}}} {count}")

        # Group gauges by metric name
        gauge_families: dict[str, list[tuple[tuple[tuple[str, str], ...], float]]] = defaultdict(list)
        for (metric, label_tuple), val in sorted(_gauges.items()):
            gauge_families[metric].append((label_tuple, val))

        gauge_names = set(gauge_families) | {
            metric for metric, metric_type in _METRIC_TYPES.items() if metric_type == "gauge"
        }
        for metric in sorted(gauge_names):
            entries = gauge_families.get(metric, [])
            help_text = _METRIC_HELP.get(metric, f"{metric} gauge")
            m_type = _METRIC_TYPES.get(metric, "gauge")
            lines.append(f"# HELP {metric} {help_text}")
            lines.append(f"# TYPE {metric} {m_type}")
            for label_tuple, val in entries:
                if label_tuple:
                    lbl_str = ",".join(f'{k}="{v}"' for k, v in label_tuple)
                    if "duration_seconds" in metric:
                        lines.append(f"{metric}{{{lbl_str}}} {val:.6f}")
                    else:
                        lines.append(f"{metric}{{{lbl_str}}} {val:g}")
                else:
                    if "duration_seconds" in metric:
                        lines.append(f"{metric} {val:.6f}")
                    else:
                        lines.append(f"{metric} {val:g}")

    return "\n".join(lines) + "\n"
