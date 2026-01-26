# Deployment & Operational Guide

## Project Purpose

**UZS XML Automation Framework** – Flask-based web application for generating, validating, and managing XML messages for UZS (Uitvoering Ziektewettolerance) processes. Supports ZBM (Ziekmeldingsbericht), VM (Verzuimmelding), and OTP3 (Digipoort) message types.

### Target Audiences
- **Testers**: Generate and validate XML messages via web UI.
- **Admins**: Configure environments, monitor KPIs, manage file retention.
- **Integration teams**: Use API endpoints (`/api/xml/throughput`, `/health`, `/ready`).

### Deployment Scope
- **Current**: Fits testing/staging environments (internal UWV networks).
- **Future**: Productionizable with TLS, secret rotation, centralized logging.
- **Python**: 3.11+ (tested on 3.13.5).

---

## Deployment Paths

### Path 1: Docker Compose (Recommended for Teams)
Full stack (nginx reverse proxy + Flask app):
```bash
docker-compose up -d
# Access: https://<host> (with TLS certs in ./certs/)
```
**Pros**: Load-balanced, TLS-ready, reproducible.  
**Cons**: Requires Docker, cert management.

### Path 2: Minimal Docker (Single Container)
Quick standalone deployment:
```bash
scripts/deploy_minimal_docker.sh
# Access: http://<host>:5000 (no TLS)
```
**Pros**: Zero-config, fast, lightweight.  
**Cons**: No reverse proxy, no TLS.

### Path 3: Windows EXE (Locked-Down Networks)
PyInstaller-based executable for air-gapped servers:
```powershell
scripts/build_windows_exe.ps1              # Build EXE
scripts/package_for_transfer.ps1 -Environment UZSTA_OMG  # Package for transfer
# On target: Expand-Archive, run .\run-xmlator.ps1
```
**Pros**: No Python required on target, minimal dependencies.  
**Cons**: Larger file, Windows-only.

---

## Configuration

### Environment Variables (Priority Order)
1. **Required (production)**:
   - `U_XMLATOR_SECRET` – Flask session secret (min 32 chars, alphanumeric + symbols).
   
2. **Optional**:
   - `FLASK_ENV` – `development` (default) or `production` (enforces secret).
   - `U_XMLATOR_COOKIE_SECURE` – `1` (default, HTTPS only) or `0` (HTTP, dev-only).
   - `U_XMLATOR_SAMESITE` – `Lax` (default), `Strict`, or `None`.
   - `U_XMLATOR_SESSION_SECONDS` – Session lifetime (default 604800 = 7 days).

### Configuration File (`web/instellingen.json`)
Managed via web UI at `/instellingen/configuratie`. Controls:
- **omgeving** – Active environment (UZSTA_OMG, UZSA_ACC1, UZSC_ACC1, UZSD_ACC1, UZSP_ACC1).
- **filedrop_locaties** – Output paths per environment & message type.
- **upload_max_size_mb** – Excel file upload limit (default 16 MB).
- **xsd_path** – Path to XSD schema for validation.
- **file_retention_days** – Auto-cleanup interval for old XML files.

---

## Health & Readiness

### Endpoints
- **`GET /health`** – Liveness probe (returns 200 if process running).
- **`GET /ready`** – Readiness probe (returns 200 if downloads dir writable + openpyxl available).

Use in Kubernetes or load balancer health checks:
```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 5000
  initialDelaySeconds: 10
readinessProbe:
  httpGet:
    path: /ready
    port: 5000
  initialDelaySeconds: 5
```

---

## API Overview

### XML Generation & Throughput
- **`GET /api/xml/throughput?days=N`** – Daily aggregate stats (success count, success %).
- **`GET /api/xml/latest-errors`** – Last 20 generation errors (JSON lines from `build/logs/xmlator_errors.jsonl`).

### File Management
- **`POST /upload_excel`** – Upload Excel dataset → generate XML.
- **`GET /resultaten/fragment`** – List recent generated files (HTML snippet).
- **`GET /resultaten/download/<filename>`** – Download XML file.
- **`POST /resultaten/download-zip`** – Download multiple XML files as ZIP.
- **`POST /resultaten/delete-selected`** – Delete selected XML files.

---

## Security Checklist

- [ ] **Secrets**: Generate strong `U_XMLATOR_SECRET` (≥32 chars), never hardcode.
- [ ] **Session**: Cookie flags (HTTPOnly, Secure, SameSite) enforced by default.
- [ ] **XSD Validation**: Enabled by default; verify `xsd_path` exists.
- [ ] **File Paths**: Check `web/instellingen.json` filedrop paths are reachable (not missing network shares).
- [ ] **TLS**: Use reverse proxy (nginx) with valid certs; never expose port 5000 to untrusted networks.
- [ ] **Input Validation**: Excel upload restricted to `.xlsx`, `.xls`; file names sanitized.
- [ ] **Logging**: Monitor `build/logs/xmlator_errors.jsonl` for generation failures.

---

## Monitoring & Logs

### Application Logs
- **stdout/stderr**: Flask access + debug logs (redirect to systemd journal or log aggregation).
- **`build/logs/xmlator_errors.jsonl`**: Generation errors (one per line, JSON).

### KPI Dashboard
- Web UI at `/` shows real-time stats: throughput, latest file, success rate.
- API `/api/xml/throughput` provides 14-day trend.

### Expected Throughput
- **Small messages** (~100 fields): ~10–20 XML/sec (single process).
- **Scaling**: Use `docker-compose` with multiple app replicas behind nginx load balancer.

---

## Maintenance

### File Cleanup
- Auto-retention configured in `web/instellingen.json` (`file_retention_days`, default 30).
- Manual cleanup via UI: `/resultaten` → select files → delete.

### Database/Schema
- No persistent DB (stateless design).
- Config stored in JSON (`web/instellingen.json`); back up if customized.

### Updates
- Pull latest from repo, rebuild Docker image (or EXE).
- Pre-commit hooks enforce code quality; tests must pass.

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| App won't start; "U_XMLATOR_SECRET not set" | Set env var: `$env:U_XMLATOR_SECRET = "..."` (production only). |
| No XML files generated | Check `filedrop_locaties` paths in config; verify network share is mounted. |
| XSD validation fails | Ensure `docs/UwvZwMeldingInternBody-v0428-b01.xsd` exists; check `xsd_path` in config. |
| Upload hangs | Check `upload_max_size_mb` limit; verify disk space. |
| Health check fails | Check `/ready` endpoint; ensure `build/static/downloads` writable; verify openpyxl installed. |

---

## Support & Feedback

- **Issues**: Create GitHub issue with log snippet from `xmlator_errors.jsonl`.
- **Features**: Open discussion in CONTRIBUTING.md.
- **Deployment Help**: See DEPLOY.md for infrastructure-specific guidance.
