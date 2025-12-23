# Windows Service Setup voor UZS XMLator

De XMLator kan als Windows Service draaien zodat het automatisch opstart en in de achtergrond blijft lopen.

## Optie 1: NSSM (Aanbevolen - Easiest)

### Stap 1: Download NSSM
```powershell
# Download NSSM van https://nssm.cc/download
# Pak uit naar C:\nssm
# (of voeg C:\nssm\win64 toe aan PATH)
```

### Stap 2: Service Installeren
```powershell
# PowerShell als Administrator
cd "E:\App-data\xmlator"

# Maak service aan
nssm install UZSXMLator "E:\App-data\xmlator\xmlator.exe"

# Zet service om automatisch te starten
nssm set UZSXMLator Start SERVICE_AUTO_START

# Zet de output logs
nssm set UZSXMLator AppStdout "E:\App-data\xmlator\logs\stdout.txt"
nssm set UZSXMLator AppStderr "E:\App-data\xmlator\logs\stderr.txt"

# Start de service
nssm start UZSXMLator
```

### Stap 3: Beheer de Service
```powershell
# Status controleren
nssm status UZSXMLator

# Stoppen
nssm stop UZSXMLator

# Starten
nssm start UZSXMLator

# Verwijderen
nssm remove UZSXMLator confirm
```

## Optie 2: Python Service Wrapper (Geavanceerd)

### Installeer pywin32
```powershell
.venv\Scripts\pip install pywin32
.venv\Scripts\pywin32_postinstall.py -install
```

### Maak service script
```python
# xmlator_service.py
import win32serviceutil
import win32service
import win32event
import servicemanager
import socket
import sys
import os
from pathlib import Path

class UZSXMLatorService(win32serviceutil.ServiceFramework):
    _svc_name_ = 'UZSXMLator'
    _svc_display_name_ = 'UZS XMLator Web Server'
    _svc_description_ = 'Generates UZS XML documents from Excel'

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.isAlive = True
        self.proc_handle = None

    def SvcStop(self):
        self.isAlive = False
        win32event.SetEvent(self.hWaitStop)

    def SvcDoRun(self):
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, '')
        )
        
        # Start xmlator.exe
        import subprocess
        exe_path = r'E:\App-data\xmlator\xmlator.exe'
        self.proc_handle = subprocess.Popen([exe_path])
        
        # Keep service running
        while self.isAlive:
            win32event.WaitForMultipleObjects(
                (self.hWaitStop,), False, 1000
            )

if __name__ == '__main__':
    win32serviceutil.HandleCommandLine(UZSXMLatorService)
```

### Installeer service
```powershell
python xmlator_service.py install
python xmlator_service.py start
```

## Optie 3: Windows Task Scheduler (Simpel)

Als je niet iedere 24/7 nodig hebt, kan je ook Task Scheduler gebruiken:

```powershell
# PowerShell als Administrator
$trigger = New-ScheduledTaskTrigger -AtStartup
$action = New-ScheduledTaskAction -Execute 'E:\App-data\xmlator\xmlator.exe'
$principal = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest
Register-ScheduledTask -TaskName 'UZSXMLator' -Trigger $trigger -Action $action -Principal $principal
```

## Configuratie voor Service

Als de service draait, zorg dat:

1. **Omgeving variabelen zijn gezet** - Voeg toe in NSSM:
```powershell
nssm set UZSXMLator AppEnvironmentExtra "FLASK_ENV=production"
nssm set UZSXMLator AppEnvironmentExtra "U_XMLATOR_SECRET=je-lange-geheim-hier"
```

2. **Logs directory bestaat**:
```powershell
New-Item -ItemType Directory -Path "E:\App-data\xmlator\logs" -Force
```

3. **Filedrop directories zijn toegankelijk** - Service draait als SYSTEM, dus zorg voor schrijfrechten naar D:\GUP\UZS\filedrop\

## Monitoring

### Logs controleren
```powershell
# Via NSSM (laatste 100 regels)
nssm queryex UZSXMLator

# Via File
Get-Content -Path "E:\App-data\xmlator\logs\stdout.txt" -Tail 50
```

### Health Check
```powershell
# App draait als service op 0.0.0.0:5000
curl http://localhost:5000/health

# Zou moeten terugkeren: {"status":"healthy"}
```

## Troubleshooting

### Service start niet
```powershell
# Kijk logs
nssm status UZSXMLator
Get-EventLog -LogName System -Source NSSM

# Test EXE handmatig
E:\App-data\xmlator\xmlator.exe
```

### Schrijfrechten
```powershell
# Als service geen bestanden kan schrijven naar D:\GUP\UZS\filedrop\:
# SYSTEM gebruiker toevoegen met Write permissies
icacls "D:\GUP\UZS\filedrop" /grant "NT AUTHORITY\SYSTEM:(OI)(CI)F"
```

### Port al in gebruik
```powershell
# Controleer welke app poort 5000 gebruikt
netstat -ano | findstr :5000

# Kill proces (vervang PID)
taskkill /PID 1234 /F
```

## Production Checklist

- [ ] Service geïnstalleerd en auto-start ingesteld
- [ ] Logs directory aangemaakt
- [ ] U_XMLATOR_SECRET omgevingsvariabele gezet
- [ ] Filedrop directories hebben SYSTEM write-rechten
- [ ] Health endpoint test: `curl http://localhost:5000/health`
- [ ] Web dashboard bereikbaar: `http://localhost:5000`
- [ ] Configuratie omgeving ingesteld in `instellingen.json`
