Kort: als je browser CDN's blokkeert (Tracking Prevention) moet je Chart.js lokaal plaatsen zodat de grafiek kan renderen.

Stappen:
1. Open een PowerShell in de repository root (bijv. `D:\ZW\XML-automation-clean`).
2. Voer het download-script uit:

   powershell -ExecutionPolicy Bypass -File .\scripts\download_chartjs.ps1

3. Herlaad de dashboardpagina in je browser (Ctrl+F5). In DevTools → Console zou je een melding moeten zien: "Chart.js loaded from local fallback" of "Chart.js loaded from CDN".

Alternatief: schakel tracking prevention/AD-blocker uit of whitelist `cdn.jsdelivr.net`.

Favicon: de 404 voor `/favicon.ico` is onschuldig; als je wilt voeg ik een favicon in `web/static/favicon.ico`.