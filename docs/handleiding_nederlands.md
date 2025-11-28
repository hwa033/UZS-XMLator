# Handleiding — XML Automatisering

Deze handleiding beschrijft in begrijpelijke taal hoe u de applicatie gebruikt om XML-aanvragen te genereren, valideren en beheren.

## Inhoud

- Wat de applicatie doet
- Installatie en starten
-- Gebruik van de webinterface
-- Bulk generatie en tests
- Veelgestelde vragen en oplossingen

## Wat doet de applicatie?

De tool maakt het eenvoudig om test-XML-bestanden te genereren voor UZS-processen (zoals ZBM, VM en Digipoort). De applicatie ondersteunt:

-- Automatisch invullen van unieke referentienummers
- Opslaan van bestanden in juiste output-mappen
- Validatie tegen XSD wanneer beschikbaar
- Overzicht van gegenereerde bestanden en eenvoudige statistieken

## Installatie

1. Maak en activeer een virtuele omgeving:

```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1
```

2. Installeer afhankelijkheden:

```powershell
pip install -r requirements.txt
```

## Starten

Start de webapp vanuit de projectroot:

```powershell
python -m web.app
```

Open `http://localhost:5000` in uw browser.

## Webinterface — hoofdpunten

- Dashboard: overzicht van KPI-tegels en grafieken
-- Genereer XML: formulier voor één bericht
-- Resultaten: download en bekijk eerder gegenereerde bestanden

## Output

- Output wordt standaard weggeschreven naar `uzs_filedrop/` in submappen per aanvraagtype.
- De mappen en bestandsnamen zijn geconfigureerd in `web/app.py` via `OUTPUT_MAP`.

## Validatie

Upload een XML bestand via de dashboard validatie-functie. Als er een XSD in `docs/` staat, controleert het systeem het bestand en geeft het fouten terug.

## Bulk generatie

Gebruik `generate_xml.py` samen met een YAML-bestand (`testdata.yml`) voor bulkgeneratie. Per record wordt een XML-bestand aangemaakt met unieke referenties.

## Tests

Voer Robot Framework-tests uit met:

```powershell
robot tests.robot
```

Of start tests via de API endpoint `POST /api/test/uitvoeren`.

## Veelgestelde vragen

- "Bestanden worden niet aangemaakt": controleer schrijfrechten en `OUTPUT_MAP`.
- "Validatie faalt": controleer of het juiste XSD aanwezig is in `docs/`.
- Stylingproblemen: maak de cache leeg (Ctrl+F5) en controleer `web/static/css/dashboard.css`.

## Contact

Voor vragen of support neem contact op met de beheerder of het ontwikkelteam.
