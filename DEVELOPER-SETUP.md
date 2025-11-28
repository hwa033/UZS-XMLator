# Developer setup

This document explains how to create a clean development environment, install minimal runtime and development dependencies, and produce pinned requirements for reproducible installs.

1) Create a fresh virtual environment for development (Windows PowerShell).

We recommend creating a dedicated development venv (`.venv_dev`) so your
main environment remains unchanged. This venv will install only the
minimal runtime and development dependencies.

```powershell
python -m venv .venv_dev
& .\.venv_dev\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

2) Install minimal runtime requirements (for running the app):

```powershell
pip install -r requirements-pinned-minimal.txt
```

3) Install development dependencies (for testing and linting):

```powershell
pip install -r requirements-dev.txt
```

4) Generate a pinned requirements file from your current venv (for CI/production):

```powershell
pip freeze > requirements-pinned.txt
```

5) We already provide a pinned minimal runtime file generated from a
    temporary clean venv: `requirements-pinned-minimal.txt`. Use this in CI to
    reproduce the minimal runtime environment.

6) Run tests and linters locally (from `.venv_dev`):

```powershell
ruff check .
black --check .
pytest -q
```

Notes
- `requirements-pinned.txt` can include large packages (e.g. `pandas`, `numpy`).
   If you need a small runtime footprint in CI/production, prefer
   `requirements-pinned-minimal.txt`.
- To remove heavy packages from an existing venv (destructive), run:

```powershell
& .\.venv\Scripts\Activate.ps1
pip uninstall pandas numpy -y
```

   Prefer creating `.venv_dev` instead to avoid removing packages from your
   existing environment.
