# Python compatibility policy

The current pinned dependency set supports **Python 3.12 and 3.13** on
Windows, Ubuntu/Linux, GitHub-hosted runners, Docker, and Kubernetes. Python
3.12 is the preferred runtime because it is the image and primary CI baseline.

Python **3.14 is unsupported** for this repository's current dependency set.
`pydantic-core` and `tokenizers` may fall back to native PyO3 source builds
when a compatible wheel is unavailable, and the current PyO3 toolchain
constraints do not include Python 3.14. Changing the operating system,
runner, container host, or Kubernetes node does not make Python 3.14
compatible; the interpreter version and available dependency wheels are the
controlling factors.

## Enforcement

- `.github/workflows/ci.yml` runs the test suite on Python 3.12 and 3.13.
- `.github/workflows/chaos.yml` runs deterministic failure-injection tests on
  both supported versions.
- `Dockerfile` uses `python:3.12-slim`, labels the supported runtime, and
  fails the image build if the base interpreter is not Python 3.12 or 3.13.
- Kubernetes uses the same published image; the Python compatibility contract
  is enforced at image build time rather than by the node operating system.
- Windows local development uses the local-only PowerShell launcher, which
  prefers 3.12, supports 3.13, accepts `-PythonPath`, and rejects 3.14 before
  creating a virtual environment.

Do not set `PYO3_USE_ABI3_FORWARD_COMPATIBILITY` as a workaround. Install a
supported interpreter and recreate the virtual environment instead. Keep
dependency pins reproducible and update them only through a compatibility
review and CI validation.
