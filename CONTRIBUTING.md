# Contributing

Thanks for contributing! This document explains the workflow, code style, and tests policy.

1. Fork the repo and create a feature branch from `main`.

2. Run tests and linters locally before opening a PR:

```powershell
& .\.venv_dev\Scripts\Activate.ps1
pip install -r requirements-pinned-minimal.txt
pip install -r requirements-dev.txt
ruff check .
black --check .
pytest -q
```

3. Code style and pre-commit hooks
- This project uses `ruff`, `black`, and `isort`. Install `pre-commit` and run `pre-commit install`.
- Run `pre-commit run --all-files` to auto-fix many issues.

4. Pull request checklist
- Include tests for new behaviors.
- Update `DEVELOPER-SETUP.md` or `README.md` if you change developer-facing steps.
- All CI checks must pass.

5. Releases and packaging
- Packaging uses minimal pinned runtime dependencies in `requirements-pinned-minimal.txt`.
- For binary builds use `pyinstaller` per instructions in `DEVELOPER-SETUP.md`.

If your change requires larger refactors (e.g. removing large dependencies), open an issue first so we can coordinate.
