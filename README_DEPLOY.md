# UZS XMLator — Deployment Quickstart (Docker)

Dit bestand beschrijft hoe u de applicatie in Docker kunt draaien voor een eenvoudige standalone deployment.

Vereisten
- Docker en Docker Compose geïnstalleerd op de host
- Het project beschikbaar op de doelserver (kopiëren of clone)

Voorbereiding omgeving
1. Kopieer `.env.example` naar `.env` en werk de waarden bij (met name `SECRET_KEY`).

PowerShell (Windows) voorbeeld:

```powershell
Copy-Item .env.example .env
notepad .env  # pas SECRET_KEY en overige waarden aan
```

Linux/macOS voorbeeld:

```bash
cp .env.example .env
# bewerk .env met je favoriete editor
```

Bouw en start met Docker Compose

```powershell
# Vanuit de projectroot
docker compose up -d --build
```

Controleer services
- Bekijk logs:

```powershell
docker compose logs -f web
docker compose logs -f nginx
```

- Test endpoints (host / browser):
  - `http://<host>/ping` zou `pong` moeten retourneren
  - `http://<host>/genereer_xml` zou de generatorpagina moeten tonen

Opmerkingen en aanbevelingen
- De repository bevat `docs/excel_datasets.yml` (voorgenereerde datasets). De app gebruikt bij voorkeur dit YAML-bestand in productie om Excel-afhankelijkheden te vermijden.
- Als je wilt dat de app Excel direct leest, zorg dat `docs/PROD-v0008-b01_Cws-v49.xlsx` aanwezig is in `docs/` en dat de container de benodigde Excel-pakketten bevat.
- Voor productie: beveilig `SECRET_KEY`, draai achter een HTTPS-terminatie en voeg monitoring/healthchecks toe.

Secrets and session hardening

Set a strong `U_XMLATOR_SECRET` in production. When running with `FLASK_ENV=production` the application will refuse to start if `U_XMLATOR_SECRET` is not set. Ensure your deployment sets the following environment variables securely:

- `U_XMLATOR_SECRET` — required in production
- `U_XMLATOR_COOKIE_SECURE=1` — ensures cookies are marked Secure
- `U_XMLATOR_SAMESITE=Lax` — recommended SameSite policy

If you use Docker Compose, ensure these are set in the environment section or via an external secret mechanism.

Optionele vervolgstappen die ik voor je kan doen
- Voeg een `systemd` unit toe voor hosts zonder Docker.
- Voeg Certbot+Nginx voorbeeld toe aan `docker-compose.yml` voor geautomatiseerde TLS.
- Voer containerized smoke-tests uit (vereist Docker op deze machine).

