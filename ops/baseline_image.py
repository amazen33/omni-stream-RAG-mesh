"""Fail closed on unpinned or lab images before starting the baseline API."""
import os
import re
import sys

_GHCR = re.compile(r"ghcr\.io/amazen33/omni-stream-rag-mesh@sha256:[0-9a-f]{64}")
_LOCAL = re.compile(r"sha256:[0-9a-f]{64}")
_COMMAND = ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]


def validate_image(image: str, profile: str, phase: str = "B0") -> str:
    """Return the receipt form; a local ID is allowed only for B0 and main."""
    if profile != "main":
        raise ValueError("Baseline requires a main image; lab or unmarked images are rejected")
    if phase not in {"B0", "B1", "B2"}:
        raise ValueError("BASELINE_PHASE must be B0, B1 or B2")
    if _GHCR.fullmatch(image):
        return "ghcr-manifest-digest"
    if phase == "B0" and _LOCAL.fullmatch(image):
        return "local-main-image-id"
    raise ValueError("Use the Omni GHCR reference by digest, or a local main-image ID for B0 only; tags are rejected")


def main() -> None:
    try:
        phase = os.environ.get("BASELINE_PHASE", "B0")
        form = validate_image(os.environ.get("BASELINE_IMAGE", ""), os.environ.get("OMNI_IMAGE_PROFILE", ""), phase)
    except ValueError as error:
        raise SystemExit(str(error)) from error
    if sys.argv[1:] != _COMMAND:
        raise SystemExit("Baseline requires the production uvicorn command")
    print(f"Baseline image validated: phase={phase}, form={form}; record the form and full reference in the receipt", flush=True)
    os.execvp("python", _COMMAND)


if __name__ == "__main__":
    main()
