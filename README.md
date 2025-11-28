# XML Automatisering Framework

## 🚀 Snel aan de slag

# XML Automatisering

Deze repository bevat een hulpmiddel om XML-aanvragen te genereren, te valideren en te beheren voor UZS-gerelateerde processen. De applicatie bestaat uit een eenvoudige webinterface (Flask) en een set scripts/tests voor geautomatiseerde workflows.

Doelgroepen: testers, ontwikkelaars en beheerders die testberichten willen maken en analyseren.

---

## Inhoud van deze map

- `web/` – de Flask webapplicatie: `app.py`, templates en statische bestanden (CSS/JS).
-- `docs/` – documentatie en voorbeeld XSD/XML-bestanden.
- `uzs_filedrop/` – voorbeeld output-mappen (waar gegenereerde XML-bestanden terechtkomen).
- `tests.robot` – Robot Framework tests.
- `requirements.txt` – Python afhankelijkheden.

---

## Installatie

1. Maak een virtuele omgeving en activeer deze:

```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1
```

2. Installeer de vereisten:

```powershell
pip install -r requirements.txt
```

3. Optioneel (development):

```powershell
pip install -r requirements-dev.txt
```

---

## Starten van de webapp

In de projectroot:

```powershell
python -m web.app
```

Open vervolgens `http://localhost:5000` in uw browser.

## Secrets and session hardening

For production, set a strong `U_XMLATOR_SECRET` environment variable. The app will refuse to start when `FLASK_ENV=production` and `U_XMLATOR_SECRET` is not set. Recommended session cookie settings are enabled by default (HTTPOnly, Secure, SameSite=Lax). You can override these via environment variables:

- `U_XMLATOR_COOKIE_SECURE` (default `1`) — set to `0` to disable `Secure` (not recommended)
- `U_XMLATOR_SAMESITE` (default `Lax`) — options: `Lax`, `Strict`, `None`
- `U_XMLATOR_SESSION_SECONDS` (default 604800) — session lifetime in seconds

Example (PowerShell):

```powershell
$env:U_XMLATOR_SECRET = 'replace-with-a-strong-random-secret'
python -m web.app
```

De webinterface bevat:
- Dashboard: KPI-tegels, grafieken en snelle acties
- Genereer XML: formulier voor het aanmaken van testberichten
- Resultaten: overzicht van gegenereerde bestanden en details

---

## Belangrijkste onderdelen en opties

- `web/app.py`: centrale Flask-applicatie en API-endpoints (onder andere `/api/xml/throughput`, `/api/xml/events`, `/api/test/uitvoeren`).
- `web/templates/*.html`: Jinja2-templates voor de frontend.
- `web/static/css/dashboard.css`: styling voor dashboard en tegels.
-- `web/static/js/dashboard.js`: client-side logica voor grafieken en interactieve elementen.

---

## XML genereren (voorbeeld)

1. Ga naar de pagina `Genereer XML` in de webinterface of gebruik het script `generate_xml.py`.
2. Kies het type aanvraag (ZBM, VM of Digipoort) en vul de velden (BSN, geboortedatum, naam).
3. De applicatie vult unieke referentievelden automatisch in (datum/tijd + suffix) en slaat het bestand op in de bijbehorende map onder `uzs_filedrop/`.

Bestandspaden die gebruikt worden (standaard):

- ZBM / VM: `uzs_filedrop/UZI-GAP3/UZSx_ACC1/v0428`
- Digipoort (OTP3): `uzs_filedrop/UZI-GAP3/UZSx_ACC1/UwvZwMelding_MQ_V0428`

De mapping staat in `web/app.py` in `OUTPUT_MAP`.

---

## Tests

Gebruik Robot Framework tests om functionaliteit te controleren:

```powershell
# Voer alle tests uit
robot tests.robot
```

Er is ook een endpoint in de webapp om tests te starten: `POST /api/test/uitvoeren`.

---

## API overzicht

- `GET /api/xml/throughput?days=N` – dagelijkse aantallen en success-percentages (standaard N=7)
-- `GET /api/xml/events?date=YYYY-MM-DD` – ruwe events voor een datum
- `POST /api/test/uitvoeren` – start testuitvoering (Robot Framework)

Zie `web/app.py` voor details en fallback-logica.

---

## Veelvoorkomende problemen & oplossingen

- "Geen XSD gevonden" bij validatie: controleer of de XSD-bestanden in `docs/` aanwezig zijn.
- Bestanden worden niet gegenereerd: controleer schrijfrechten en de `uzs_filedrop/` mappen.
- Stijlen van het dashboard lijken anders: ververs de browsercache (Ctrl+F5) en controleer `web/static/css/dashboard.css`.

---

## Bijdragen

1. Fork de repository
2. Maak een feature-branch
3. Open een pull request met een duidelijke omschrijving

---

Als iets onduidelijk is of u extra uitleg wilt over een onderdeel, laat het weten.