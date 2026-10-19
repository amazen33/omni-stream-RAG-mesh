from pathlib import Path
import re

import pytest
import yaml

from ops.baseline_image import validate_image

ROOT = Path(__file__).resolve().parents[1]


def test_baseline_resources_ephemeral_mode_and_production_command():
    services = yaml.safe_load((ROOT / "deploy/load/docker-compose.baseline.yaml").read_text())["services"]
    api = services["rag-api"]
    assert api["image"].startswith("${OMNI_IMAGE:?")
    assert api["entrypoint"] == ["python", "-m", "ops.baseline_image"]
    assert api["environment"]["BASELINE_IMAGE"].startswith("${OMNI_IMAGE:?")
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


def test_baseline_has_no_literal_token_key():
    services = yaml.safe_load((ROOT / "deploy/load/docker-compose.baseline.yaml").read_text())["services"]
    environment = services["rag-api"]["environment"]
    assert environment["PII_TOKEN_SALT"] == "${BASELINE_TOKEN_KEY:?Generate a random key for this run}"
    assert environment["RUNTIME_PROFILE"] == "production"


@pytest.mark.parametrize("phase", ["B0", "B1", "B2"])
def test_published_main_digest_is_allowed(phase):
    assert validate_image("ghcr.io/amazen33/omni-stream-rag-mesh@sha256:" + "a" * 64, "main", phase) == "ghcr-manifest-digest"


def test_local_main_id_is_allowed_only_for_b0():
    image = "sha256:" + "a" * 64
    assert validate_image(image, "main", "B0") == "local-main-image-id"
    for phase in ("B1", "B2"):
        with pytest.raises(ValueError, match="B0 only"):
            validate_image(image, "main", phase)


@pytest.mark.parametrize("image", [
    "", "local/omni-wo00:main", "local/omni-wo00:lab",
    "ghcr.io/amazen33/omni-stream-rag-mesh:latest",
    "ghcr.io/amazen33/omni-stream-rag-mesh:main",
    "ghcr.io/amazen33/omni-stream-rag-mesh-lab@sha256:" + "a" * 64,
    "example.invalid/main@sha256:" + "a" * 64,
    "sha256:" + "a" * 63, "sha256:" + "A" * 64,
    "sha256:" + "a" * 64 + "\n",
])
def test_unpinned_or_other_image_forms_are_rejected(image):
    with pytest.raises(ValueError):
        validate_image(image, "main")


@pytest.mark.parametrize("image", ["sha256:" + "a" * 64, "ghcr.io/amazen33/omni-stream-rag-mesh@sha256:" + "a" * 64])
@pytest.mark.parametrize("profile", ["lab", ""])
def test_even_digest_pinned_lab_and_unmarked_images_are_rejected(image, profile):
    with pytest.raises(ValueError, match="main image"):
        validate_image(image, profile)


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
