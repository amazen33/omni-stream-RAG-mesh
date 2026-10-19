import sys
from types import SimpleNamespace

import pytest

from app import metrics


def test_process_metrics_skipped_on_other_operating_systems(monkeypatch):
    monkeypatch.setattr(metrics, "sys", SimpleNamespace(platform="win32"))
    assert "process_resident_memory_bytes" not in metrics.exposition()
    assert "process_cpu_seconds_total" not in metrics.exposition()
    assert "process_open_fds" not in metrics.exposition()


def test_linux_proc_units_types_and_parenthesized_comm(tmp_path, monkeypatch):
    monkeypatch.setattr(metrics, "sys", SimpleNamespace(platform="linux"))
    monkeypatch.setattr(metrics, "_PROC_SELF", tmp_path)
    monkeypatch.setattr(metrics, "os", SimpleNamespace(
        sysconf=lambda key: {"SC_PAGE_SIZE": 4096, "SC_CLK_TCK": 100}[key],
        listdir=lambda _path: ["0", "1", "2", "enumeration-fd"],
    ))
    (tmp_path / "statm").write_text("100 10 0 0 0 0 0\n")
    (tmp_path / "stat").write_text("123 (synthetic ) process) S " + "0 " * 10 + "123 77 0 0\n")
    body = metrics.exposition()
    for name, kind, value in (("process_resident_memory_bytes", "gauge", "40960"),
                              ("process_cpu_seconds_total", "counter", "2"),
                              ("process_open_fds", "gauge", "3")):
        assert f"# HELP {name} " in body
        assert f"# TYPE {name} {kind}\n" in body
        assert f"{name} {value}\n" in body


def test_unavailable_proc_is_omitted(tmp_path, monkeypatch):
    monkeypatch.setattr(metrics, "sys", SimpleNamespace(platform="linux"))
    monkeypatch.setattr(metrics, "_PROC_SELF", tmp_path)
    assert metrics._process_metrics() == {}


@pytest.mark.skipif(sys.platform != "linux", reason="Actual /proc/self requires Linux")
def test_real_linux_proc():
    values = metrics._process_metrics()
    assert values["process_resident_memory_bytes"][1] > 0
    assert values["process_cpu_seconds_total"][1] >= 0
    assert values["process_open_fds"][1] >= 3
