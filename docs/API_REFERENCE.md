# API Reference (XMLator)

## Health & Readiness
- `GET /health` → `{ "status": "healthy" }` (200)
- `GET /ready`  → `{ "status": "ready" }` (200)

## Generation (UI-backed endpoints)
- `POST /upload_excel` (form-data):
  - `excel_file`: file (.xlsx/.xls)
  - `validate`: "on" | "off" (optional, defaults to on)
  - Behavior: writes generated XML to filedrop based on `aanvraag_type` auto-detected from Excel content. Returns HTML response with result list.
- `POST /genereer_xml_json/upload_json` (form-data):
  - `json_file`: file (.json) with request payload
  - `aanvraag_type`: "Digipoort" | "OTP3" | "ZBM" | "VM"
  - `validate`: "on" | "off" (default on)
  - Behavior: generates XML and writes to filedrop; returns HTML response.

## Metrics / Monitoring
- `GET /api/xml/throughput`
  - Response: `{ "count": <int>, "last24h": <int> }`
- `GET /api/xml/latest-errors`
  - Response: array of recent error entries from `build/logs/xmlator_errors.jsonl` (fields: `type`, `aanvraag_type`, `omgeving`, `stderr`, `filename`, `tijdstip`).

## File Listing
- `GET /genereer_xml`
  - Renders HTML with latest generated files (prunes to limit 25 by default).

## Configuration (Admin UI)
- `GET /instellingen/` → dashboard
- `GET/POST /instellingen/configuratie` → manage omgeving, filedrop paths, upload limits, validation flags
- `GET /instellingen/logs` → shows tails of generator logs

## Request/Response Examples

### Health
```bash
curl -s http://localhost:5000/health
```
Response:
```json
{"status":"healthy"}
```

### Readiness
```bash
curl -s http://localhost:5000/ready
```
Response:
```json
{"status":"ready"}
```

### Throughput
```bash
curl -s http://localhost:5000/api/xml/throughput
```
Response (example):
```json
{"count": 1234, "last24h": 42}
```

### Latest Errors
```bash
curl -s http://localhost:5000/api/xml/latest-errors
```
Response (example):
```json
[
  {
    "type": "excel",
    "aanvraag_type": "OTP3",
    "omgeving": "UZSTA_OMG",
    "stderr": "<stacktrace>",
    "filename": "UwvZwMelding_20250101_101500.xml",
    "tijdstip": "2025-12-12T10:15:00"
  }
]
```

### JSON Upload (form-data)
```bash
curl -s -X POST http://localhost:5000/genereer_xml_json/upload_json \
  -F aanvraag_type=Digipoort \
  -F validate=on \
  -F json_file=@sample.json
```

### Excel Upload (form-data)
```bash
curl -s -X POST http://localhost:5000/upload_excel \
  -F excel_file=@"docs/Input XML electr ziekmeldingen.xlsx" \
  -F validate=on
```

## Notes
- Upload size limit is controlled by `upload_max_size_mb` in instellingen.json.
- File output location respects `filedrop_locaties` per omgeving; can be overridden via `XMLATOR_FILEDROP_BASE` env var.
- Validation uses XSD at `docs/UwvZwMeldingInternBody-v0428-b01.xsd` (do not disable in production).
- Auth: Not enabled; rely on network controls / reverse proxy for now.
