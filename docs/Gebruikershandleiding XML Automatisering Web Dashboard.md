# XML Automatisering Web Dashboard – Gebruikershandleiding

## Doel van de applicatie

Deze webapplicatie is ontwikkeld om het genereren, beheren en testen van XML-aanvragen voor UZS-processen te automatiseren. De app ondersteunt verschillende aanvraagtypes (zoals ZBM, VM, Digipoort) en zorgt ervoor dat de juiste XML-bestanden met unieke en/of testdata worden aangemaakt en opgeslagen op de juiste locatie. Dit maakt het eenvoudig voor testers en ontwikkelaars om snel en foutloos testberichten te genereren en te gebruiken.

## Functionaliteiten

- Webinterface voor het genereren van XML-aanvragen op basis van testdata.
- Automatisch invullen van unieke velden (zoals referentienummers) met datum/tijd.
- Data-driven testing: velden als BSN, geboortedatum en naam kunnen per test worden opgegeven.
- Automatische opslag van gegenereerde XML-bestanden in de juiste submap, afhankelijk van het type aanvraag.
-- Overzicht van testresultaten.

## Werking en gebruik

### 1. Starten van de app

1. Zorg dat alle benodigde Python-pakketten zijn geïnstalleerd (zie `requirements.txt`).
2. Start de app met:
   ```
   python web/app.py
   ```
3. Open je browser en ga naar [http://localhost:5000].

### 2. XML-aanvraag genereren

1. Ga naar [http://localhost:5000/genereer_xml].
2. Vul het formulier in:
   - Kies het type aanvraag (ZBM, VM, Digipoort).
   - Vul BSN, geboortedatum (YYYYMMDD) en naam in.
3. Klik op “Genereer XML”.
4. De app maakt een XML-bestand aan met unieke referenties en jouw testdata, en slaat dit automatisch op in de juiste map (zie mapping in de app).
5. Je krijgt een bevestiging met het pad naar het gegenereerde bestand.

### 3. Data-driven testen

- Je kunt ook een YAML-bestand (`testdata.yml`) aanmaken met meerdere testcases.
- Gebruik het script `generate_xml.py` om automatisch voor elke testcase een XML-bestand te genereren.

<!-- Sjabloonbeheer verwijderd: externe sjabloon-upload en -beheer zijn niet beschikbaar in deze build. -->

### 5. Testresultaten

- Bekijk de resultaten van uitgevoerde tests via het dashboard.

## Mapping aanvraagtype naar opslaglocatie

- ZBM of VM: `uzs_filedrop/UZI-GAP3/UZSx_ACC1/v0428`
- Digipoort: `uzs_filedrop/UZI-GAP3/UZSx_ACC1/UwvZwMelding_MQ_V0428`

## Aanpasbare velden

- Uniek: GegevensUitwisselingsnr, BerichtReferentienr, TransactieReferentienr (worden automatisch uniek gemaakt)
- Testdata: BSN, geboortedatum, naam (zelf opgeven)

## Veelgestelde vragen

- **Moet ik zelf mappen aanmaken?**  
Nee, de app maakt automatisch de juiste mappen aan als ze nog niet bestaan.

- **Kan ik andere velden aanpassen?**  
Standaard zijn alleen de genoemde velden flexibel. Wil je meer velden aanpassen, overleg dan met de ontwikkelaar.

- **Waar vind ik de gegenereerde XML-bestanden?**  
In de submappen onder `uzs_filedrop/UZI-GAP3/UZSx_ACC1/`, afhankelijk van het type aanvraag.

---

# Gebruikershandleiding XML Automatisering Web Dashboard

## Overzicht
Deze handleiding beschrijft hoe u het XML Automatisering Web Dashboard kunt gebruiken om inzicht te krijgen in de prestaties van uw XML-verwerkingsprocessen. Het dashboard biedt verschillende KPI's en visualisaties om trends en problemen te identificeren.

## Beschikbare KPI's
1. **Throughput**: Het aantal XML-bestanden dat dagelijks wordt verwerkt.
2. **Success Rate**: Het percentage succesvolle verwerkingen per dag.
3. **Failures**: Het aantal mislukte verwerkingen per dag.
4. **Processing Time**: De gemiddelde verwerkingstijd per bestand.
5. **Sjabloongebruik**: (n.v.t. in deze build)
6. **Backlog**: Het aantal bestanden dat wacht op verwerking.

## Functionaliteiten
### Throughput + Success Chart
- **Beschrijving**: Een gecombineerde grafiek die het dagelijkse aantal succesvolle en mislukte verwerkingen toont (gestapelde balken) en het succespercentage (lijn).
- **Data**: De grafiek gebruikt gegevens van de API `/api/xml/throughput` en het bestand `web/xml_events.jsonl`.
- **Standaardweergave**: Laat gegevens zien voor de laatste 14 dagen.

### Drilldown per dag
- **Beschrijving**: Klik op een dag in de grafiek om ruwe gebeurtenisgegevens voor die datum te bekijken.
- **Data**: Gebruikt de API `/api/xml/events?date=YYYY-MM-DD` of het bestand `web/xml_events.jsonl`.
- **Details**: Toont tijdstempel, bestandsnaam, type, successtatus en grootte.

### Alerts en Drempels
- **Beschrijving**: Waarschuwingen in de UI wanneer het faalpercentage een drempel overschrijdt of de throughput daalt.
- **Instellingen**: Configureerbare drempels en visuele indicatoren op de grafiek.

## API Endpoints
### `/api/xml/throughput`
- **Beschrijving**: Geeft dagelijkse throughput- en succespercentages terug.
- **Parameters**:
  - `days` (optioneel): Het aantal dagen om op te halen (standaard: 14).
- **Voorbeeld**: `/api/xml/throughput?days=14`

### `/api/xml/events`
- **Beschrijving**: Geeft ruwe gebeurtenisgegevens terug voor een specifieke datum.
- **Parameters**:
  - `date` (vereist): De datum in `YYYY-MM-DD` formaat.
- **Voorbeeld**: `/api/xml/events?date=2025-11-20`

## Gebruik
1. **Dashboard openen**: Navigeer naar de URL van het dashboard in uw browser.
2. **Grafieken bekijken**: Gebruik de throughput + success chart om trends te analyseren.
3. **Drilldown uitvoeren**: Klik op een dag om meer details te bekijken.
4. **Waarschuwingen beheren**: Controleer visuele indicatoren en pas drempels aan in de instellingen.

## Nieuwe KPI's toevoegen
1. **API uitbreiden**: Voeg een nieuwe endpoint toe in `web/app.py`.
2. **Frontend bijwerken**: Werk de grafieklogica bij in `web/static/js/dashboard.js`.
3. **Documentatie bijwerken**: Voeg een beschrijving toe aan deze handleiding.

## Ondersteuning
Neem contact op met het ontwikkelteam voor vragen of problemen.

---

Voor vragen of uitbreidingen, neem contact op met het ontwikkelteam.
