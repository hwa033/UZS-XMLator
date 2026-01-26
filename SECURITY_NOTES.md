# Security & Configuration Notes

## Configuration Safety

### Paths in `web/instellingen.json`
- **Network shares** (`D:\GUP\UZS\filedrop\...`): Ensure mounted at container start.
- **Portable override**: Set `XMLATOR_FILEDROP_BASE` (e.g., `/data/filedrop` or `Z:\UZS\filedrop`). Any configured path starting with the default base is rewritten to your override at runtime.
- **Docker**: Mount the filedrop root and set `XMLATOR_FILEDROP_BASE=/app/filedrop`.
- **Example override**:
  ```yaml
  # docker-compose.yml
  services:
    xmlator:
      environment:
        - XMLATOR_FILEDROP_BASE=/app/filedrop
      volumes:
        - /mnt/filedrop:/app/filedrop
  ```
  Existing config paths will be rewritten from `D:\GUP\UZS\filedrop` to `/app/filedrop` at runtime.

### File Retention
- Auto-cleanup runs on each file list operation.
- Manual cleanup available in UI.
- **Required**: Set `file_retention_days: 30` in instellingen.json for compliance with data retention policy.

---

## Secret Management

### `U_XMLATOR_SECRET`
- **Length**: ≥32 characters (recommend 64+).
- **Content**: Alphanumeric + symbols (no spaces).
- **Storage**:
  - **Dev**: Env var in `.env.local` (gitignore'd).
  - **CI/CD**: GitHub Secrets or Azure Vault.
  - **Prod**: Kubernetes Secret or HashiCorp Vault.
- **Rotation**: Every 90 days or on deployment.

**Example secure generation** (PowerShell):
```powershell
$secret = [Convert]::ToBase64String([System.Security.Cryptography.RNGCryptoServiceProvider]::new().GetBytes(48))
Write-Host "U_XMLATOR_SECRET=$secret"
```

---

## XSD Validation

### Enabled By Default
- Path: `docs/UwvZwMeldingInternBody-v0428-b01.xsd`
- Enforced in `/upload_excel` and batch generators.

### Disable (Dev-Only)
In `web/app.py`, set `validate_flag=False` in `validate_normalized_rows_for_generator()` call.  
**⚠️ Never disable in production.**

---

## API Security

### CORS
- Currently: No CORS headers (same-origin only).
- To enable third-party access: Add Flask-CORS with origin whitelist.

### Rate Limiting
- Not implemented; add if exposing `/api/*` to untrusted clients.
- Recommendation: 100 req/min per IP.

### Input Validation
- Excel: `.xlsx`, `.xls` only; max 16 MB (configurable via upload_max_size_mb).
- BSN: Must be 8-9 digits (regex enforced); empty not allowed.
- XML filenames: Sanitized (no `../`, etc.).

### Admin UI (/instellingen/*)
- Dev: Open.
- Non-dev: Require admin token (`X-Admin-Token` header, Bearer token, of `admin_token` query param).
- Token source: `U_XMLATOR_ADMIN_TOKEN` (falls back op `U_XMLATOR_SECRET`).

### CORS
- Disabled by default.
- Enable by setting `XMLATOR_CORS_ORIGINS` to comma-separated origins (e.g., `https://example.com,https://admin.example.com`). Applies to `/api/*`.

### Rate Limiting
- Default: 100 req/min per client IP (memory backend).
- Upload endpoint `/upload_excel`: 20 req/min per IP.
- Configure storage via `XMLATOR_LIMITER_STORAGE` (e.g., `redis://localhost:6379/0`).

---

## Logging & Audit

### Error Log
- **Path**: `build/logs/xmlator_errors.jsonl` (one JSON per line).
- **Retention**: No auto-cleanup; implement centralized logging (ELK, Datadog, or syslog forwarder) for production.
- **Fields**: `type`, `aanvraag_type`, `omgeving`, `stderr`, `filename`, `tijdstip`.
- **Health**: `/ready` returns 503 if it cannot append to the error log or access the filedrop root.

### Example integration:
```bash
# Stream errors to syslog
tail -f build/logs/xmlator_errors.jsonl | jq -r '.tijdstip + " " + .type + " " + .error' | logger
```

---

## Compliance Notes

- **Data Handling**: BSN (Dutch citizen ID) is PII; logs contain filenames (which may include BSN).
  - Action: Set `file_retention_days: 30` in instellingen.json; archive logs separately per UWV policy.
- **Audit Trail**: Not implemented; add if required (e.g., Digipoort compliance).
- **TLS**: Enforce in production; use `U_XMLATOR_COOKIE_SECURE=1` (default).

---

## Deployment Security Checklist

- [ ] `U_XMLATOR_SECRET` set (production).
- [ ] `FLASK_ENV=production` set.
- [ ] Filedrop paths verified reachable.
- [ ] XSD file exists at `xsd_path`.
- [ ] TLS certs valid (if using HTTPS reverse proxy).
- [ ] Cookie flags: HTTPOnly, Secure, SameSite=Lax.
- [ ] Session timeout: 7 days (or configure per policy).
- [ ] Log rotation configured (if on-disk).
- [ ] Secrets not in git (check `.gitignore`).
- [ ] /health and /ready endpoints responding.

---

## Further Hardening (Backlog for Phase 2)

1. **Rate limiting**: Flask-Limiter + Redis.
2. **CORS**: Flask-CORS with origin whitelist.
3. **CSP headers**: Flask-Talisman.
4. **Audit logging**: Log all user actions (uploads, deletes, config changes).
5. **2FA**: For web UI admin access.
6. **Encryption at rest**: Encrypt `instellingen.json` or vault config.
