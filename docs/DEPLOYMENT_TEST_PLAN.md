# Deployment Test Plan (Staging/Testserver)

## Scope
Covers three deployment modes: Docker Compose (nginx + app), Minimal Docker (single container), Windows EXE. Goal: verify connectivity to filedrop, health/ready endpoints, and basic XML generation.

## Prereqs
- Filedrop root mounted/accessible (see SECURITY_NOTES.md for XMLATOR_FILEDROP_BASE override)
- Env secret set: U_XMLATOR_SECRET (>=32 chars)
- XSD present: docs/UwvZwMeldingInternBody-v0428-b01.xsd
- Network egress to Digipoort not required for this test plan

## Common Checklist (all modes)
1) Set omgeving to target (UZSTA_OMG/ACC1) in instellingen.json or via UI
2) Set XMLATOR_FILEDROP_BASE to mounted root (e.g., /data/filedrop or Z:\\UZS\\filedrop)
3) Confirm health/ready:
   - curl http://<host>/health -> 200 {"status":"healthy"}
   - curl http://<host>/ready  -> 200 {"status":"ready"}
4) Generate sample: upload docs/Input XML electr ziekmeldingen.xlsx via UI
5) Verify output written to filedrop (OTP3/ZBM/VM) and visible in UI list
6) Check logs: build/logs/xmlator_errors.jsonl empty or benign

## Docker Compose (primary deployment path)
- Build/Run: `docker-compose up -d`
- Env: set in compose file
  - XMLATOR_FILEDROP_BASE=/app/filedrop
  - U_XMLATOR_SECRET=<secret>
- Volumes:
  - /mnt/filedrop:/app/filedrop (ro/rw as needed)
- Tests:
  - Steps from common checklist
  - Ensure nginx reverse proxy serves / and /instellingen/*

## Minimal Docker
- Build: `docker build -t xmlator:local .`
- Run: `docker run -p 5000:5000 -e XMLATOR_FILEDROP_BASE=/app/filedrop -e U_XMLATOR_SECRET=<secret> -v /mnt/filedrop:/app/filedrop xmlator:local`
- Tests: common checklist via http://localhost:5000

## Windows EXE
- Inputs: dist/xmlator.exe, web/instellingen.json, docs/
- Set env before start:
  - set U_XMLATOR_SECRET=<secret>
  - set XMLATOR_FILEDROP_BASE=Z:\\UZS\\filedrop (or UNC)
- Run: `xmlator.exe`
- Tests: common checklist via http://localhost:5000

## Validation Matrix
- Health/ready: pass
- Upload Excel: pass
- Output files: created under filedrop per omgeving/berichttype
- Logs: no errors in xmlator_errors.jsonl

## Rollback
- Docker: `docker-compose down` or stop container
- EXE: stop process

## Sign-off
- Capture evidence: screenshots of UI, curl outputs, file listings, log tail
- Approver: deployment lead
