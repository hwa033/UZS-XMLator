# Installatie XMLator

## Starten in 3 stappen

### 1. Uitpakken
```powershell
Expand-Archive -Path D:\xmlator-release.zip -DestinationPath E:\xmlator -Force
cd E:\xmlator
```

### 2. Draaien
```powershell
.\run-xmlator.ps1
```
Het script maakt zelf een wachtwoord aan en start de app.

### 3. Browser openen
```
http://localhost:5000
```

## Werkt het?
Draai dit om te checken:
```powershell
.\check-health.ps1
```
Je moet "Ready status: 200" zien.

## Instellingen aanpassen
De configuratie-pagina's zitten op `/instellingen`. Daarvoor heb je het wachtwoord nodig dat bij stap 2 op het scherm kwam.

Twee manieren om in te loggen:
- Header toevoegen: `X-Admin-Token: <wachtwoord>`
- Of gewoon in de browser: `http://localhost:5000/instellingen?admin_token=<wachtwoord>`

## Stoppen
`Ctrl+C` in PowerShell

## Problemen oplossen
- **Poort bezet?** Pas in `run-xmlator.ps1` aan naar `--port 5001`
- **Wachtwoord kwijt?** Start opnieuw, er komt een nieuw wachtwoord
- **Health check werkt niet?** Check Windows Firewall voor poort 5000

## Wat zit er in de map
- `xmlator.exe` - de applicatie
- `run-xmlator.ps1` - startscript
- `check-health.ps1` - health check
- `instellingen.json` - configuratie (omgeving, paden)
- `docs/` - XSD's en voorbeelden
