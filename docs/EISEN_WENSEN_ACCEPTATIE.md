# Eisen, Wensen en Acceptatiecriteria - XML Automatisering

**Versie**: 1.0  
**Datum**: 16 december 2025  
**Bron**: Documentatie uit docs/ directory

---

## 1. Functionele Eisen

### 1.1 XML Generatie
- **FE-001**: De applicatie MOET XML-bestanden kunnen genereren voor drie aanvraagtypen:
  - ZBM (CdBerichtType: ZBM)
  - VM (CdBerichtType: VM)
  - Digipoort (CdBerichtType: OTP3)

- **FE-002**: De applicatie MOET de volgende velden automatisch uniek maken met datum/tijd + suffix:
  - GegevensUitwisselingsnr
  - BerichtReferentienr
  - TransactieReferentienr

- **FE-003**: De applicatie MOET gebruikers toestaan testdata in te voeren voor:
  - BSN
  - Geboortedatum (formaat: YYYYMMDD)
  - Naam
  - Loonheffingennr (optioneel)
  - IBAN (optioneel)
  - BIC (optioneel)

- **FE-004**: De applicatie MOET de correcte ApplicatieNaam gebruiken:
  - ZBM → `<ApplicatieNaam>ZBM</ApplicatieNaam>`
  - VM → `<ApplicatieNaam>VM</ApplicatieNaam>`
  - OTP3/Digipoort → `<ApplicatieNaam>Digipoort</ApplicatieNaam>`

### 1.2 Bestandsbeheer
- **FE-005**: De applicatie MOET gegenereerde XML-bestanden opslaan in type-specifieke mappen:
  - ZBM/VM: `uzs_filedrop\UZI-GAP3\UZSx_ACC1\v0428`
  - Digipoort: `uzs_filedrop\UZI-GAP3\UZSx_ACC1\UwvZwMelding_MQ_V0428`

- **FE-006**: De applicatie MOET automatisch de benodigde mappen aanmaken als deze niet bestaan

- **FE-007**: De applicatie MOET maximaal 25 gegenereerde bestanden tonen in de resultatenlijst

- **FE-008**: De applicatie MOET automatisch de oudste bestanden verwijderen wanneer meer dan 25 bestanden aanwezig zijn

- **FE-009**: De applicatie MOET gebruikers toestaan geselecteerde bestanden te verwijderen met een bevestigingsdialoog

- **FE-010**: De applicatie MOET gebruikers toestaan geselecteerde bestanden te downloaden als ZIP-archief

### 1.3 Excel Integratie
- **FE-011**: De applicatie MOET Excel-bestanden kunnen importeren voor bulk XML-generatie

- **FE-012**: De applicatie MOET de CdBerichtType kolom in Excel patchen met het geselecteerde aanvraagtype voordat XML wordt gegenereerd

- ~~**FE-013**: De applicatie MOET datasets uit `excel_datasets.yml` kunnen laden en gebruiken~~ (Verwijderd - niet in basis vereisten)

### 1.4 Resultaten en Overzichten
- **FE-014**: De applicatie MOET gegenereerde bestanden tonen gesorteerd op wijzigingstijd (nieuwste eerst)

- **FE-015**: De applicatie MOET voor elk bestand de volgende informatie tonen:
  - Bestandsnaam
  - Tijdstip van aanmaak
  - Bestandsgrootte in bytes

- **FE-016**: De applicatie MOET een teller tonen: "Toont X van Y bestand(en)"

---

## 2. Technische Eisen

### 2.1 Backend
- **TE-001**: De applicatie MOET gebouwd zijn met Flask 3.x

- **TE-002**: De applicatie MOET Python 3.8 of hoger ondersteunen

- **TE-003**: De applicatie MOET XML genereren met ElementTree/lxml

- **TE-004**: De applicatie MOET Excel-bestanden verwerken met openpyxl

- **TE-005**: De applicatie MOET AJAX-requests herkennen via de `X-Requested-With: XMLHttpRequest` header

### 2.2 Security
- **TE-006**: De applicatie MOET weigeren te starten in productie zonder `U_XMLATOR_SECRET` environment variabele

- **TE-007**: De applicatie MOET sessiecookies beveiligen met:
  - HTTPOnly flag (standaard enabled)
  - Secure flag (standaard enabled, configureerbaar via `U_XMLATOR_COOKIE_SECURE`)
  - SameSite=Lax (configureerbaar via `U_XMLATOR_SAMESITE`)

- **TE-008**: De applicatie MOET bestandsnamen valideren om path traversal te voorkomen:
  - Geen `.xml` extensie → afwijzen
  - Bevat `/` of `..` → afwijzen

### 2.3 Frontend
- **TE-009**: De applicatie MOET Bootstrap 5 gebruiken voor UI-styling

- **TE-010**: De applicatie MOET Bootstrap Icons gebruiken voor iconen

- **TE-011**: De applicatie MOET Jinja2 templates gebruiken voor server-side rendering

- **TE-012**: De applicatie MOET vanilla JavaScript gebruiken (geen jQuery/framework)

### 2.4 API Endpoints
- **TE-013**: De applicatie MOET de volgende endpoints aanbieden:
  - `POST /upload_excel` - Excel upload en XML generatie
  - `GET /resultaten/fragment` - HTML snippet van resultatenlijst
  - `GET /resultaten/download/<filename>` - Download enkel bestand
  - `POST /resultaten/download-zip` - Download meerdere bestanden als ZIP
  - `POST /resultaten/delete-selected` - Verwijder geselecteerde bestanden
  - `GET /genereer_xml` - Formulierpagina voor XML generatie

---

## 3. Wensen (Nice-to-have)

### 3.1 Gebruikerservaring
- **W-001**: De applicatie ZOU gebruikers kunnen waarschuwen bij lage succespercentages of dalende throughput

- **W-002**: De applicatie ZOU een dashboard kunnen tonen met KPI's:
  - Throughput (aantal verwerkte bestanden per dag)
  - Success Rate (percentage succesvolle verwerkingen)
  - Failures (aantal mislukkingen)
  - Processing Time (gemiddelde verwerkingstijd)
  - Backlog (aantal wachtende bestanden)

- **W-003**: De applicatie ZOU drilldown-functionaliteit kunnen bieden om details per dag te bekijken

### 3.2 Data Management
- **W-004**: De applicatie ZOU data-driven testing kunnen ondersteunen via YAML-bestanden

- **W-005**: De applicatie ZOU meerdere testcases automatisch kunnen verwerken uit YAML

### 3.3 Validatie
- **W-006**: De applicatie ZOU gegenereerde XML kunnen valideren tegen XSD-schema's

- **W-007**: De applicatie ZOU validatieresultaten kunnen tonen in de UI

---

## 4. Acceptatiecriteria

### 4.1 AC voor XML Generatie (FE-001 t/m FE-004)
**Gegeven** een gebruiker op de "Genereer XML" pagina  
**Wanneer** de gebruiker:
- Aanvraagtype "ZBM" selecteert
- BSN "123456789" invult
- Geboortedatum "19900101" invult
- Naam "Test Gebruiker" invult
- Op "Genereer XML" klikt

**Dan** moet:
- Een XML-bestand worden aangemaakt in `uzs_filedrop\UZI-GAP3\UZSx_ACC1\v0428`
- Het bestand `<ApplicatieNaam>ZBM</ApplicatieNaam>` bevatten
- GegevensUitwisselingsnr, BerichtReferentienr en TransactieReferentienr uniek zijn
- De opgegeven testdata (BSN, geboortedatum, naam) correct in het XML staan

### 4.2 AC voor Bestandslijst (FE-007, FE-008, FE-014, FE-015, FE-016)
**Gegeven** er zijn 30 gegenereerde XML-bestanden  
**Wanneer** een gebruiker de resultatenlijst ververst  
**Dan** moet:
- Maximaal 25 bestanden worden getoond
- De 5 oudste bestanden automatisch zijn verwijderd
- Bestanden gesorteerd zijn op wijzigingstijd (nieuwste eerst)
- Elke regel bestandsnaam, tijdstip en grootte tonen
- De teller "Toont 25 van 25 bestand(en)" tonen

### 4.3 AC voor Verwijderen (FE-009)
**Gegeven** een gebruiker heeft 3 bestanden geselecteerd  
**Wanneer** de gebruiker op "Verwijder geselecteerd" klikt  
**En** de bevestigingsdialoog accepteert  
**Dan** moet:
- Een bevestigingsdialoog verschijnen: "Weet je zeker dat je 3 bestand(en) wilt verwijderen?"
- Na acceptatie de 3 bestanden verwijderd worden van disk
- De bestanden verdwijnen uit de lijst
- Een melding verschijnen: "3 bestand(en) succesvol verwijderd"

### 4.4 AC voor Download ZIP (FE-010)
**Gegeven** een gebruiker heeft 5 bestanden geselecteerd  
**Wanneer** de gebruiker op "Download geselecteerd" klikt  
**Dan** moet:
- Een ZIP-bestand worden gedownload met naam `xml_bestanden_YYYYMMDD_HHMMSS.zip`
- Het ZIP-archief alle 5 geselecteerde bestanden bevatten
- De originele bestanden op disk blijven staan

### 4.5 AC voor Excel Upload (FE-011, FE-012)
**Gegeven** een gebruiker op de "Genereer XML" pagina  
**Wanneer** de gebruiker:
- Een Excel-bestand uploadt met 10 rijen testdata
- Aanvraagtype "VM" selecteert
- Op "Genereer XML" klikt

**Dan** moet:
- De CdBerichtType kolom in het Excel eerst gepatcht worden naar "VM"
- 10 XML-bestanden worden gegenereerd in `uzs_filedrop\UZI-GAP3\UZSx_ACC1\v0428`
- Elk bestand `<ApplicatieNaam>VM</ApplicatieNaam>` bevatten
- Een succesmelding getoond worden

### 4.6 AC voor Security (TE-006, TE-008)
**Gegeven** de applicatie draait in productie  
**Wanneer** `U_XMLATOR_SECRET` niet is gezet  
**Dan** moet de applicatie weigeren te starten met een foutmelding

**Gegeven** een kwaadwillende gebruiker probeert `../../../etc/passwd` te downloaden  
**Wanneer** de download-request wordt verzonden  
**Dan** moet de applicatie een 400-fout retourneren met "Ongeldige bestandsnaam"

### 4.7 AC voor UI Consistentie
**Gegeven** een gebruiker bekijkt de resultatenlijst  
**Dan** moeten:
- Alle blauwe actieknoppen (Ververs, Download) gebruik maken van `btn-primary` styling
- De verwijderknop gebruik maken van `btn-outline-danger` (rood) styling
- Alle knoppen dezelfde font en grootte hebben als de "Genereer XML" knop
- Disabled knoppen visueel grijs/uitgegrijsd zijn

---

## 5. Out of Scope

De volgende functionaliteiten zijn NIET onderdeel van de huidige scope:

- **OOS-001**: Externe XML-sjabloon upload en beheer
- **OOS-002**: Gebruikersauthenticatie en autorisatie
- **OOS-003**: Multi-tenancy / organisatie-scheiding
- **OOS-004**: Real-time monitoring met push notifications
- **OOS-005**: Integratie met externe API's (behalve mock_api_server voor testing)
- **OOS-006**: Automatische XSD-validatie tijdens generatie (alleen handmatige validatie via tools)
- **OOS-007**: Audit logging van gebruikersacties
- **OOS-008**: Export van resultaten naar andere formaten (PDF, CSV)

---

## 6. Niet-Functionele Eisen

### 6.1 Performance
- **NFE-001**: XML-generatie uit Excel MOET binnen 5 seconden compleet zijn voor bestanden tot 100 rijen
- **NFE-002**: Resultatenlijst MOET binnen 1 seconde laden (voor max 25 items)
- **NFE-003**: ZIP-download MOET starten binnen 2 seconden na klikken

### 6.2 Usability
- **NFE-004**: Alle gebruikersacties MOETEN visuele feedback geven (spinners, disabled states)
- **NFE-005**: Foutmeldingen MOETEN duidelijk en begrijpelijk zijn voor niet-technische gebruikers
- **NFE-006**: Bevestigingsdialogen MOETEN gebruikt worden voor destructieve acties (verwijderen)

### 6.3 Maintainability
- **NFE-007**: Code MOET gestructureerd zijn volgens Flask best practices
- **NFE-008**: Herbruikbare componenten MOETEN gescheiden zijn (bijv. `results_panel.js`, `_results_panel.html`)
- **NFE-009**: Configureerbare waarden MOETEN via environment variabelen instelbaar zijn

### 6.4 Compatibility
- **NFE-010**: De applicatie MOET werken in moderne browsers (Chrome, Firefox, Edge, Safari laatste 2 versies)
- **NFE-011**: De applicatie MOET werken op Windows (PowerShell 5.1+)
- **NFE-012**: De applicatie MOET werken zonder JavaScript-frameworks (vanilla JS)

---

## 7. Testcriteria

### 7.1 Unit Tests
- Alle helper functies in `app.py` moeten unit tests hebben
- XML-generatie logica moet getest worden met verschillende inputs
- Bestandsvalidatie moet getest worden met malicious inputs

### 7.2 Integration Tests
- Excel upload flow moet end-to-end getest worden
- ZIP download met meerdere bestanden moet getest worden
- Delete functionaliteit moet getest worden inclusief bevestiging

### 7.3 UI Tests
- Alle knoppen moeten klikbaar zijn en juiste acties triggeren
- Formuliervalidatie moet werken (verplichte velden, formaten)
- AJAX-calls moeten juiste headers meesturen

### 7.4 Security Tests
- Path traversal attacks moeten geblokt worden
- Session cookies moeten secure flags hebben
- Environment variabele checks moeten werken

---

## 8. Documentatie Vereisten

- **DOC-001**: Gebruikershandleiding moet up-to-date zijn met alle features
- **DOC-002**: API-endpoints moeten gedocumenteerd zijn met voorbeelden
- **DOC-003**: Deployment instructies moeten beschikbaar zijn (DEPLOY.md)
- **DOC-004**: Developer setup moet gedocumenteerd zijn (DEVELOPER-SETUP.md)
- **DOC-005**: Contributing guidelines moeten beschikbaar zijn (CONTRIBUTING.md)

---

## 9. Wijzigingshistorie

| Versie | Datum | Auteur | Wijzigingen |
|--------|-------|--------|-------------|
| 1.0 | 16-12-2025 | GitHub Copilot | Initiële versie o.b.v. docs/ analyse |

---

**Goedkeuring**:
- [ ] Product Owner
- [ ] Tech Lead
- [ ] QA Lead

