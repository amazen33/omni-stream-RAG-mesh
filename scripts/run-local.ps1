[CmdletBinding()]
param(
    [Alias("Path")]
    [string]$ProjectPath = "E:\omni-stream-RAG-mesh",

    [switch]$Install,

    [int]$Port = 8000,

    # "Host" is an alias so the script does not overwrite PowerShell's
    # read-only $Host automatic variable.
    [Alias("Host")]
    [string]$BindHost = "127.0.0.1",

    [switch]$SkipClone,

    [switch]$SkipUpdate,

    # Starts only the Compose dependencies; the API remains a local uvicorn
    # process so this switch does not create a port collision.
    [switch]$DockerCompose
)

$ErrorActionPreference = "Stop"

function Fail([string]$Message) {
    Write-Error $Message
    exit 1
}

function Require-Command([string]$Name, [string]$InstallHint) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        Fail "$Name was not found on PATH. $InstallHint"
    }
}

if ($PSVersionTable.PSVersion.Major -lt 5) {
    Fail "Windows PowerShell 5.1 or PowerShell 7+ is required."
}

Require-Command "git" "Install Git for Windows and reopen PowerShell."
Require-Command "python" "Install Python 3.10+ and enable the 'Add Python to PATH' option."

if ($Port -lt 1 -or $Port -gt 65535) {
    Fail "Port must be between 1 and 65535."
}

if ([string]::IsNullOrWhiteSpace($BindHost)) {
    Fail "Host must not be empty."
}

$ProjectPath = [Environment]::ExpandEnvironmentVariables($ProjectPath)
$repoUrl = "https://github.com/amazen33/omni-stream-RAG-mesh.git"

if (-not (Test-Path -LiteralPath (Split-Path -Parent $ProjectPath) -PathType Container)) {
    Fail "Parent directory for '$ProjectPath' does not exist. Create the E: drive/path or pass -ProjectPath."
}

if (-not (Test-Path -LiteralPath $ProjectPath -PathType Container)) {
    if ($SkipClone) {
        Fail "Project path '$ProjectPath' does not exist and -SkipClone was supplied."
    }

    Write-Host "Cloning omni-stream-RAG-mesh into $ProjectPath ..."
    & git clone $repoUrl $ProjectPath
    if ($LASTEXITCODE -ne 0) {
        Fail "git clone failed with exit code $LASTEXITCODE."
    }
}

if (-not (Test-Path -LiteralPath (Join-Path $ProjectPath ".git") -PathType Container)) {
    Fail "'$ProjectPath' is not a Git repository."
}

Push-Location $ProjectPath
try {
    if (-not $SkipUpdate) {
        $status = @(git status --porcelain)
        if ($LASTEXITCODE -ne 0) {
            Fail "Unable to inspect Git status."
        }

        if ($status.Count -gt 0) {
            Write-Warning "Local changes detected; skipping update to avoid overwriting work. Use -SkipUpdate to silence this warning."
        }
        else {
            Write-Host "Updating repository with fast-forward-only pull ..."
            & git pull --ff-only
            if ($LASTEXITCODE -ne 0) {
                Fail "Safe update failed. Resolve the repository state manually, or rerun with -SkipUpdate."
            }
        }
    }

    $envFile = Join-Path $ProjectPath ".env"
    $envExample = Join-Path $ProjectPath ".env.example"
    if (-not (Test-Path -LiteralPath $envFile -PathType Leaf)) {
        if (-not (Test-Path -LiteralPath $envExample -PathType Leaf)) {
            Fail "Neither .env nor .env.example exists in '$ProjectPath'."
        }

        Copy-Item -LiteralPath $envExample -Destination $envFile
        Write-Warning "Created .env from .env.example. Replace placeholder values before enabling external services."
    }
    else {
        Write-Host "Using existing .env; it will not be overwritten."
    }

    # Uvicorn does not load dotenv files itself. Import only simple KEY=value
    # entries into this process; values are never printed.
    $lineNumber = 0
    foreach ($line in Get-Content -LiteralPath $envFile) {
        $lineNumber++
        $trimmed = $line.Trim()
        if ($trimmed.Length -eq 0 -or $trimmed.StartsWith("#")) {
            continue
        }
        if ($trimmed -notmatch "^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)\s*$") {
            Write-Warning "Ignoring malformed .env entry at line $lineNumber."
            continue
        }

        $name = $Matches[1]
        $value = $Matches[2].Trim()
        if (($value.Length -ge 2) -and
            (($value.StartsWith('"') -and $value.EndsWith('"')) -or
             ($value.StartsWith("'") -and $value.EndsWith("'")))) {
            $value = $value.Substring(1, $value.Length - 2)
        }
        Set-Item -Path ("Env:" + $name) -Value $value
    }

    $venvPath = Join-Path $ProjectPath ".venv"
    $venvPython = Join-Path $venvPath "Scripts\python.exe"
    $venvUvicorn = Join-Path $venvPath "Scripts\uvicorn.exe"
    $createdVenv = $false
    if (-not (Test-Path -LiteralPath $venvPython -PathType Leaf)) {
        Write-Host "Creating Python virtual environment in $venvPath ..."
        & python -m venv $venvPath
        if ($LASTEXITCODE -ne 0) {
            Fail "Python virtual environment creation failed with exit code $LASTEXITCODE."
        }
        $createdVenv = $true
    }

    if ($Install -or $createdVenv) {
        $requirementsFile = Join-Path $ProjectPath "requirements.txt"
        if (-not (Test-Path -LiteralPath $requirementsFile -PathType Leaf)) {
            Fail "requirements.txt is missing from '$ProjectPath'."
        }
        Write-Host "Installing Python dependencies ..."
        & $venvPython -m pip install --upgrade pip
        if ($LASTEXITCODE -ne 0) {
            Fail "pip upgrade failed with exit code $LASTEXITCODE."
        }
        & $venvPython -m pip install -r $requirementsFile
        if ($LASTEXITCODE -ne 0) {
            Fail "Dependency installation failed with exit code $LASTEXITCODE."
        }
    }
    elseif (-not (Test-Path -LiteralPath $venvUvicorn -PathType Leaf)) {
        Fail "The virtual environment has no uvicorn executable. Rerun with -Install."
    }

    if ($DockerCompose) {
        Require-Command "docker" "Install Docker Desktop or omit -DockerCompose."
        & docker compose version *> $null
        if ($LASTEXITCODE -ne 0) {
            Fail "Docker Compose v2 is unavailable. Install/enable Docker Desktop or omit -DockerCompose."
        }
        Write-Host "Starting Compose dependencies (not the rag-api container) ..."
        & docker compose up -d minio opensearch ollama chroma kafka spark
        if ($LASTEXITCODE -ne 0) {
            Fail "Docker Compose dependency startup failed with exit code $LASTEXITCODE."
        }
    }

    Write-Host "Starting omni-stream-RAG-mesh at http://$BindHost`:$Port"
    Write-Host "Stop with Ctrl+C. The virtual environment and .env are retained for reuse."
    & $venvUvicorn "app.main:app" "--host" $BindHost "--port" ([string]$Port)
    if ($LASTEXITCODE -ne 0) {
        Fail "uvicorn exited with code $LASTEXITCODE."
    }
}
finally {
    Pop-Location
}
