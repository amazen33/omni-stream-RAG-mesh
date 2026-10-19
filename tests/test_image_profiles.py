"""The shipped lock cannot pull in the lab-only native dependency tree."""
import builtins
from pathlib import Path
import re

from app.health import HealthService
from ops.verify_adapters import CHROMA_ONLY


def test_main_lock_excludes_chroma_tree_and_gcc_exception():
    lock = Path('requirements.txt').read_text()
    names = {name.lower().replace('_', '-') for name in re.findall(r'^([\w.-]+)==', lock, re.M)}
    assert not (CHROMA_ONLY & names)
    assert 'GCC-exception' not in lock
    assert 'chromadb==' in Path('requirements-lab.txt').read_text()


def test_missing_chroma_is_a_clear_readiness_failure_without_a_traceback(monkeypatch, caplog):
    original = builtins.__import__
    def without_chroma(name, *args, **kwargs):
        if name == 'chromadb':
            raise ModuleNotFoundError('synthetic private error', name='chromadb')
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, '__import__', without_chroma)
    monkeypatch.setenv('ENABLE_VECTOR_STORE', 'true')
    report = HealthService().report('startup')
    assert report['status'] == 'failed'
    assert report['checks']['vector_store']['detail'] == 'Chroma is available only in the lab image (PROFILE=lab)'
    assert 'Traceback' not in caplog.text and 'synthetic private error' not in caplog.text
