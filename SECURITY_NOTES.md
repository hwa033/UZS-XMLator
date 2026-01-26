# Security & Configuration Notes

## Configuration Safety

### Paths in `web/instellingen.json`
- **Network shares** (`D:\GUP\UZS\filedrop\...`): Ensure mounted at container start.
- **Docker**: Use volume mounts to override; avoid hardcoding UNC paths.
- **Example override**:
  ```yaml
  # docker-compose.yml
  volumes:
    - /mnt/filedrop/UZSTA_OMG:/app/filedrop
  ```
  Then update config via web UI to use `/app/filedrop`.

### File Retention
- Auto-cleanup runs on each file list operation.
- Manual cleanup available in UI.
- **Recommended**: Set `file_retention_days: 30` for compliance.

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
- Excel: `.xlsx`, `.xls` only; max 16 MB (configurable).
- BSN: Empty check (not format validation; consider adding).
- XML filenames: Sanitized (no `../`, etc.).

---

## Logging & Audit

### Error Log
- **Path**: `build/logs/xmlator_errors.jsonl` (one JSON per line).
- **Retention**: No auto-cleanup; consider centralized logging (e.g., ELK, Datadog).
- **Fields**: `type`, `aanvraag_type`, `omgeving`, `stderr`, `filename`, `tijdstip`.

### Example integration:
```bash
# Stream errors to syslog
tail -f build/logs/xmlator_errors.jsonl | jq -r '.tijdstip + " " + .type + " " + .error' | logger
```

---

## Compliance Notes

- **Data Handling**: BSN (Dutch citizen ID) is PII; logs contain filenames (may include BSN).
  - Recommendation: Rotate `file_retention_days` to ≤30; archive old logs separately.
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

## Further Hardening (Optional)

1. **Rate limiting**: Flask-Limiter + Redis.
2. **CORS**: Flask-CORS with origin whitelist.
3. **CSP headers**: Flask-Talisman.
4. **Audit logging**: Log all user actions (uploads, deletes, config changes).
5. **2FA**: For web UI admin access.
6. **Encryption at rest**: Encrypt `instellingen.json` or vault config.
