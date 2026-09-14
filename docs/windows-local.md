# Windows local launcher

The repository includes [`scripts/run-local.ps1`](../scripts/run-local.ps1) for
native Windows development. It is written for Windows PowerShell 5.1 and also
works with newer PowerShell versions. The default checkout is
`E:\omni-stream-RAG-mesh`; pass `-ProjectPath` (or `-Path`) to use another
location.

## Prerequisites

- Windows PowerShell 5.1 or PowerShell 7+
- Git for Windows on `PATH`
- Python 3.10 or newer on `PATH`
- Docker Desktop with Compose v2 only when `-DockerCompose` is used

The launcher does not install or start Docker automatically. It starts only the
local FastAPI process unless `-DockerCompose` is explicitly supplied. The
Compose option starts `minio`, `opensearch`, `ollama`, `chroma`, `kafka`, and
`spark`; it intentionally does not start `rag-api`, because the API is being
run by the local virtual environment.

## Usage

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\run-local.ps1 -Install
```

The first run clones the repository if the default path is absent, creates
`.venv`, and installs `requirements.txt`. Later runs reuse the environment;
use `-Install` to refresh dependencies. The script copies `.env.example` to
`.env` only if `.env` does not exist. It imports simple `KEY=value` entries
into the uvicorn process without displaying their values. Edit `.env` locally
and do not commit it.

Examples:

```powershell
# Run an existing checkout without Git operations.
.\scripts\run-local.ps1 -ProjectPath E:\omni-stream-RAG-mesh -SkipClone -SkipUpdate

# Bind another port and interface.
.\scripts\run-local.ps1 -Port 8080 -Host 0.0.0.0

# Start Compose dependencies, then run the API natively.
.\scripts\run-local.ps1 -Install -DockerCompose
```

If a checkout contains uncommitted changes, the launcher skips its update
instead of merging or overwriting work. Use `-SkipUpdate` to make that choice
explicit. A missing E: drive or missing prerequisite produces a clear error;
the launcher does not silently fall back to another drive.

## Stop and cleanup

Stop uvicorn with `Ctrl+C`. If Compose dependencies were started, run:

```powershell
Set-Location E:\omni-stream-RAG-mesh
docker compose down
```

To rebuild only the Python environment, remove `.venv` and rerun with
`-Install`. Keep `.env` and rotate its values through your normal secret
management process; do not delete it as part of routine cleanup.
