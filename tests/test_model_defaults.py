"""D-O13 changes only the default; no model is downloaded or invoked."""
from pathlib import Path
import re
import subprocess

from fastapi.testclient import TestClient

import app.main as api

ROOT = Path(__file__).resolve().parents[1]
MODEL = "phi4-mini:3.8b"


def test_application_uses_owner_approved_default_model(monkeypatch):
    import langchain_ollama

    observed = []

    def fake_llm(**kwargs):
        observed.append(kwargs["model"])
        return object()

    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    monkeypatch.setenv("ENABLE_OLLAMA_INFERENCE", "true")
    monkeypatch.setattr(langchain_ollama, "OllamaLLM", fake_llm)
    monkeypatch.setattr(api.retrieval, "llm", None)
    monkeypatch.setattr(api.retrieval, "ask_with_outcome", lambda *_args, **_kwargs: ("synthetic answer", [], []))
    assert TestClient(api.app).post("/ask", json={"question": "synthetic default check"}).status_code == 200
    assert observed == [MODEL]


def test_retired_model_is_only_in_removal_note_and_existing_guard_test():
    register = (ROOT / "THIRD-PARTY.md").read_text(encoding="utf-8")
    note = next(line for line in register.splitlines() if line.startswith("Removed: `"))
    retired = re.search(r"Removed: `([^`]+)`", note).group(1).split(":")[0]
    paths = subprocess.check_output(["git", "ls-files"], cwd=ROOT, text=True).splitlines()
    found = []
    for name in paths:
        if name == "tests/test_baseline_harness.py":
            continue
        path = ROOT / name
        if path.is_symlink() or not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if name == "THIRD-PARTY.md":
            text = text.replace(note, "")
        if retired in text:
            found.append(name)
    assert found == []
