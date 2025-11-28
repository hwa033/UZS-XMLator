"""`web` package for UZS XMLator.

This file exposes the Flask `app` at package level so callers can do
`from web import app` or `import web` and access `web.app` when running
via `run_app.py` or `python -m web.app`.
"""

from .app import app

__all__ = ["app"]
