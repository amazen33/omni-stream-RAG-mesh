# Windows Python support

The local Windows launcher requires **Python 3.12 or 3.13** and prefers
Python 3.12. Python 3.14 is not supported for this dependency set: packages
such as `pydantic-core` and `tokenizers` can fall back to native PyO3 source
builds, whose current toolchain constraints do not include Python 3.14.

Install Python 3.12 or 3.13 from the official Python distribution, ensure the
Python Launcher (`py.exe`) is available, and run the local launcher with
`-Install`. When multiple interpreters are installed, select one explicitly:

```powershell
.\scripts\run-local.ps1 -PythonPath "C:\Python312\python.exe" -Install
```

The launcher validates the interpreter before creating `.venv`; it does not
set `PYO3_USE_ABI3_FORWARD_COMPATIBILITY` and does not bypass the version
check. If only Python 3.14 is installed, install Python 3.12 or 3.13 and
rerun. Existing `.venv` directories created with an unsupported interpreter
should be removed and recreated after selecting a supported executable.

For a manual setup:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\uvicorn.exe app.main:app --host 127.0.0.1 --port 8000
```

Do not commit `.env`, virtual environments, package caches, or credentials.
