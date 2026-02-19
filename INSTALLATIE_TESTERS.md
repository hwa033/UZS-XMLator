# Installatie XMLator

Dit is de korte handleiding voor testers. Alles staat al klaar in het zipbestand.

Stap 1 Uitpakken
Pak het zipbestand uit via de Verkenner naar een map, bijvoorbeeld E:\xmlator
Open daarna de map E:\xmlator

Stap 2 Starten
Start de app met het startscripts
.\run-xmlator.ps1
De app opent automatisch in de browser
Wil je een ander adres openen gebruik
.\run-xmlator.ps1 -OpenUrl http://<adres>:<poort>

Stap 3 Inloggen
Gebruik deze standaardgegevens
Gebruikersnaam admin
Wachtwoord admin

Wil je andere inloggegevens dan kun je dit vooraf instellen
U_XMLATOR_ADMIN_USER
U_XMLATOR_ADMIN_PASS

Stap 4 Controleren of het werkt
In dezelfde map kun je dit draaien
.\check-health.ps1
Je hoort Ready status 200 te zien

Waar komen de bestanden terecht
Als er geen filedrop pad is ingesteld schrijft de app naar
E:\xmlator\build\excel_generated
Zodra je filedrop paden invult worden die gebruikt

Instellingen aanpassen
Ga naar http://localhost:5000/instellingen
Daar kun je omgeving en filedrop paden opslaan

Stoppen
Druk Ctrl+C in het PowerShell venster

Problemen oplossen
Poort bezet Pas in run-xmlator.ps1 aan naar --port 5001
Wachtwoord kwijt Start opnieuw en gebruik admin admin
Health check werkt niet Check Windows Firewall voor poort 5000
PowerShell fout bij token generatie Start handmatig met
.\run-xmlator.ps1 -Secret <wachtwoord> -AdminToken <wachtwoord>

Wat zit er in de map
xmlator.exe de applicatie
run-xmlator.ps1 het startscript
check-health.ps1 de health check
instellingen.json de configuratie
docs de XSDs en voorbeelden
- `instellingen.json` - configuratie (omgeving, paden)
