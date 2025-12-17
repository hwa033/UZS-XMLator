# Deployment guide (test server)

This document provides minimal, reproducible deployment options for the XML Automation app on a government test server. It includes a Docker-based flow (recommended for reproducibility) and a systemd-based flow for directly running with a Python virtual environment.

Prerequisites
- A Linux host (Ubuntu/Debian recommended) or container host with Docker.
- A non-root service account (e.g., `webapp` or `www-data`).
- TLS certificate for the test domain (use org PKI or a trusted CA for test environment).

Option 1 — Docker (recommended)

1. Build and run with Docker Compose (keeps things reproducible):

```bash
# build image
docker-compose build

# start services (nginx + web)
docker-compose up -d
```

2. Place TLS certs in `./certs/fullchain.pem` and `./certs/key.pem` or mount your system cert location into the container. Edit `deploy/nginx.conf` and `docker-compose.yml` as needed.

3. Visit `https://<your-test-host>` after adjusting DNS or `/etc/hosts` for `example.test`.

Minimal run (single-container)
--------------------------------
If you prefer the absolute minimal maintenance surface, run the app as a single container and let the organisation provide TLS termination and proxying at the network edge.

Build and run the single image:

```bash
docker build -t xml-automation:latest .
docker run -d --name xml-automation -p 127.0.0.1:5000:5000 \
  -e SECRET_KEY=change-me \
  -v $(pwd)/web/static/downloads:/app/web/static/downloads \
  xml-automation:latest
```

Then configure the organisation's reverse proxy to forward traffic to `127.0.0.1:5000` and perform TLS termination there.
Minimal run — no TLS, no nginx (testers use server IP)
------------------------------------------------------
Fastest way to get testers on the app without domains or certificates.

```bash
# From repo root on a Linux server
scripts/deploy_minimal_docker.sh
```

This builds and runs a single container exposing `http://<server-ip>:5000` and persists output into:
- uzs_filedrop/UZI-GAP3/UZSx_ACC1/v0428
- uzs_filedrop/UZI-GAP3/UZSx_ACC1/UwvZwMelding_MQ_V0428
- build/excel_generated

Stop/update:
```bash
docker stop xmlator ; docker rm xmlator
scripts/deploy_minimal_docker.sh
```

Option 3 — Windows standalone EXE (PyInstaller)
------------------------------------------------
Build a single-file EXE on a Windows machine (Python required only for build), then copy to a Windows test server (no Python needed there).

1) Build on a Windows box:
```powershell
# from repo root
scripts/build_windows_exe.ps1
```
This produces `dist/xmlator.exe`.

2) Copy to the Windows test server:
  - `dist/xmlator.exe`
  - Optionally `docs/` (XSDs) and `uzs_filedrop/` (to keep outputs together)

3) Run on the server (no Python required):
```powershell
# in the folder containing xmlator.exe
set FLASK_ENV=production
set U_XMLATOR_SECRET=some-long-secret
xmlator.exe --host 0.0.0.0 --port 5000
```
Testers connect to: http://<server-ip>:5000

Stop: Ctrl+C

Health & readiness
------------------
The app exposes two lightweight endpoints useful for monitoring and load balancers:

- `GET /health` — quick liveness probe. Returns `200` when the app process is running.
- `GET /ready` — readiness probe; returns `200` only when basic conditions are met (downloads directory writable and `openpyxl` installed). Returns `503` when not ready.

Use these in your monitoring or container orchestrator to keep the deployment simple and robust.

Option 2 — Systemd + virtualenv (non-container)

1. Create service user and directories:

```bash
sudo useradd -r -s /bin/false webapp
sudo mkdir -p /opt/xml-automation-clean
sudo chown webapp:webapp /opt/xml-automation-clean
```

2. Copy repository to `/opt/xml-automation-clean` and create virtualenv:

```bash
cd /opt/xml-automation-clean
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

3. Create `web.static/downloads` directory and set ownership:

```bash
mkdir -p web/static/downloads
chown -R webapp:webapp web/static/downloads
```

4. Create a systemd unit using `deploy/web.service` (adjust paths and user), then:

```bash
sudo cp deploy/web.service /etc/systemd/system/xml-automation.service
sudo systemctl daemon-reload
sudo systemctl enable --now xml-automation.service
```

5. Put an NGINX reverse proxy in front (see `deploy/nginx.conf`) and obtain TLS certs. Configure firewall to allow only 443 from allowed networks.

Operational notes
- Secrets: do not commit `SECRET_KEY` or other secrets. Use environment variables or a secret store.
- Logs & monitoring: configure systemd journal forwarding and central log collection per org policy.
- Cleanup: review `web/static/downloads` lifecycle and configure retention/cleanup.

CI/CD
- For test environments, provide a simple pipeline that builds the Docker image and deploys to the test host via `docker-compose` or pushes to an internal registry.

Support
- If you want, I can:
  - add the `Dockerfile` and `docker-compose.yml` (done),
  - add a `Makefile` for build/run tasks, or
  - implement a health endpoint and readiness probe for K8s.
