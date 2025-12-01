# web/ README — Active routes and how to run

This file documents the simplified web app routes and how to run the app locally.

Active routes
- `/` — Dashboard (renders `web/templates/dashboard.html`).
-- `/genereer_xml` (GET, POST) — Generator page (renders `web/templates/genereer_xml.html`). POST generates an XML using the internal skeleton and saves it to the configured output folder.
- `/resultaten` — Results page (renders `web/templates/resultaten.html`) and lists generated XMLs.
- `/resultaten/download/<filename>` — Download a generated XML file.
- `/upload_xml_validatie` — POST endpoint to upload an XML file and validate it against the XSD in `docs/` (if present).

- `/login` (GET, POST) — Login page. Admin credentials are read from environment variables `U_XMLATOR_ADMIN_USER` and `U_XMLATOR_ADMIN_PASS`. Defaults: `admin` / `admin123`.
- `/logout` — Logout (clears session).
- `/favicon.ico` — Serves `static/favicon.ico` if present.
- `/logo.png` — Serves the project root logo (e.g. `uzs_logo.png`) or `static/img/uzs_logo.png` if present.

Template selection
-- Template management has been removed in this build; the generator uses an internal minimal XML skeleton.

Optional admin blueprints (registered if present)
- `/beheer/*` — Management UI (requires admin login). Implemented in `web/beheer.py`.
- `/instellingen/*` — Settings UI (requires admin login). Implemented in `web/instellingen.py`.

Running locally (PowerShell)
```powershell
# Activate venv
d:\ZW\XML-automation-clean\.venv\Scripts\Activate.ps1

# Run the app (example)
d:\ZW\XML-automation-clean\.venv\Scripts\python.exe run_app.py
# or
python -m web.app
```

Environment variables (recommended for production)
- `U_XMLATOR_SECRET` — Flask secret key (override default `dev-simplified`).
- `U_XMLATOR_ADMIN_USER` — Admin username (default `admin`).
- `U_XMLATOR_ADMIN_PASS` — Admin password (default `admin123`).

Notes
- The admin blueprints are lightweight and require the session flag `beheer_ingelogd` to be set by the login route; the blueprint routes are protected by their `login_required` decorators.
- If you want additional endpoints restored (events API, Robot test runner, etc.), tell me which ones and I'll re-introduce them incrementally so we keep scope controlled.
