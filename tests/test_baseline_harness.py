from pathlib import Path
import re

import yaml


ROOT = Path(__file__).resolve().parents[1]


def test_baseline_resources_ephemeral_mode_and_production_command():
    services = yaml.safe_load((ROOT / "deploy/load/docker-compose.baseline.yaml").read_text())["services"]
    api = services["rag-api"]
    assert "@sha256:${OMNI_IMAGE_SHA256:?" in api["image"]
    assert "build" not in api
    assert api["cpus"] == 2
    assert api["mem_limit"] == "2g"
    assert api["read_only"] is True
    assert api["tmpfs"] and "volumes" not in api
    assert api["command"] == ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
    assert api["environment"]["RUNTIME_PROFILE"] == "production"
    for name in ("AUDIT_STORE", "KAFKA", "VECTOR_STORE", "SEARCH_STORE"):
        assert api["environment"][f"ENABLE_{name}"] == "false"
    assert api["environment"]["ENABLE_OLLAMA_INFERENCE"] == "${BASELINE_INFERENCE:-false}"


def test_optional_llm_is_digest_pinned_and_checks_the_preseeded_model():
    services = yaml.safe_load((ROOT / "deploy/load/docker-compose.baseline.yaml").read_text())["services"]
    llm = services["ollama"]
    assert llm["profiles"] == ["llm"]
    assert re.fullmatch(r"ollama/ollama:[0-9.]+@sha256:[0-9a-f]{64}", llm["image"])
    cache = llm["volumes"][0]
    assert cache["read_only"] is True
    assert cache["bind"]["create_host_path"] is False
    command = llm["command"][0]
    assert "phi4-mini:*|granite3.*:*" in command
    assert "sha256sum -c -" in command
    assert "pull" not in command and "llama3.2" not in command
