# Install UZSXMLator as Windows Service using NSSM
# Run as Administrator on target server (E: drive machine)

param(
    [string]$ServiceName = "UZSXMLator",
    [string]$ServicePath = "E:\App-data\xmlator\xmlator.exe",
    [string]$DisplayName = "UZS XMLator Web Server",
    [string]$Secret = ""
)

$ErrorActionPreference = 'Stop'

# Require admin rights
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")
if (-not $isAdmin) {
    Write-Host "FOUT: Dit script moet als Administrator draaien!" -ForegroundColor Red
    exit 1
}

Write-Host "=== UZS XMLator Windows Service Setup ===" -ForegroundColor Cyan
Write-Host "Service Naam: $ServiceName" -ForegroundColor Yellow
Write-Host "Exe Pad: $ServicePath" -ForegroundColor Yellow

# Check if NSSM is available
$nssm = Get-Command nssm -ErrorAction SilentlyContinue
if (-not $nssm) {
    Write-Host "`nFOUT: NSSM niet gevonden in PATH" -ForegroundColor Red
    Write-Host "Download NSSM van https://nssm.cc/download" -ForegroundColor Cyan
    Write-Host "En voeg C:\nssm\win64 (of win32) toe aan PATH" -ForegroundColor Cyan
    exit 1
}

# Check if EXE exists
if (-not (Test-Path $ServicePath)) {
    Write-Host "FOUT: EXE niet gevonden: $ServicePath" -ForegroundColor Red
    exit 1
}

# Check if service already exists
$existingService = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if ($existingService) {
    Write-Host "`nWaarschuwing: Service '$ServiceName' bestaat al!" -ForegroundColor Yellow
    $response = Read-Host "Verwijder en herinstalleer? (j/n)"
    if ($response -eq 'j') {
        Write-Host "Service stoppen..." -ForegroundColor Yellow
        nssm stop $ServiceName
        Start-Sleep -Seconds 2
        Write-Host "Service verwijderen..." -ForegroundColor Yellow
        nssm remove $ServiceName confirm
    } else {
        Write-Host "Afgebroken." -ForegroundColor Yellow
        exit 0
    }
}

# Create logs directory
$LogsDir = Split-Path $ServicePath | Join-Path -ChildPath "logs"
if (-not (Test-Path $LogsDir)) {
    Write-Host "Logs directory aanmaken: $LogsDir" -ForegroundColor Cyan
    New-Item -ItemType Directory -Path $LogsDir -Force | Out-Null
}

# Generate secret if not provided
if (-not $Secret) {
    $Secret = ([System.BitConverter]::ToString([System.Security.Cryptography.RandomNumberGenerator]::GetBytes(32)) -replace '-').ToLower()
    Write-Host "Gegenereerd geheim (32 bytes): $Secret" -ForegroundColor Green
}

# Install service
Write-Host "`nService installeren..." -ForegroundColor Cyan
nssm install $ServiceName $ServicePath

# Configure service
Write-Host "Service configureren..." -ForegroundColor Cyan
nssm set $ServiceName DisplayName $DisplayName
nssm set $ServiceName Description "Genereert UZS XML documenten uit Excel"
nssm set $ServiceName Start SERVICE_AUTO_START
nssm set $ServiceName Type SERVICE_WIN32_OWN_PROCESS

# Set logging
nssm set $ServiceName AppStdout "$LogsDir\stdout.txt"
nssm set $ServiceName AppStderr "$LogsDir\stderr.txt"
nssm set $ServiceName AppStdoutCreationDisposition 4  # Append instead of overwrite

# Set environment variables
nssm set $ServiceName AppEnvironmentExtra "FLASK_ENV=production"
nssm set $ServiceName AppEnvironmentExtra "U_XMLATOR_SECRET=$Secret"

# Create startup script to verify filedrop directories
Write-Host "Verifying filedrop directories have write permissions..." -ForegroundColor Cyan

$filedropBase = "D:\GUP\UZS\filedrop\UZI-GAP3"
@("UZSTA_OMG", "UZSA_ACC1", "UZSC_ACC1", "UZSD_ACC1", "UZSP_ACC1") | ForEach-Object {
    $env = $_
    @("UwvZwMelding_MQ_V0428", "v0428\UwvZwMelding") | ForEach-Object {
        $path = Join-Path $filedropBase $env | Join-Path -ChildPath $_
        if (-not (Test-Path $path)) {
            Write-Host "Creeer directory: $path" -ForegroundColor Yellow
            New-Item -ItemType Directory -Path $path -Force | Out-Null
        }
        # Grant SYSTEM write access
        try {
            icacls $path /grant "NT AUTHORITY`\SYSTEM:(OI)(CI)F" /T | Out-Null
            Write-Host "✓ Permissions set: $path" -ForegroundColor Green
        } catch {
            Write-Host "⚠ Kon permissions niet zetten: $path" -ForegroundColor Yellow
        }
    }
}

# Start service
Write-Host "`nService starten..." -ForegroundColor Cyan
nssm start $ServiceName
Start-Sleep -Seconds 3

# Check status
$status = nssm status $ServiceName
Write-Host "Service Status: $status" -ForegroundColor Green

if ($status -eq "SERVICE_RUNNING") {
    Write-Host "`n✓ Service succesvol geinstalleerd en gestart!" -ForegroundColor Green
    Write-Host "`nCommando's:" -ForegroundColor Cyan
    Write-Host "  Status:  nssm status $ServiceName" -ForegroundColor White
    Write-Host "  Stoppen: nssm stop $ServiceName" -ForegroundColor White
    Write-Host "  Starten: nssm start $ServiceName" -ForegroundColor White
    Write-Host "  Logs:    Get-Content '$LogsDir\stdout.txt' -Tail 50" -ForegroundColor White
    Write-Host "`nWeb Dashboard: http://localhost:5000" -ForegroundColor Cyan
    Write-Host "Health Check:  curl http://localhost:5000/health" -ForegroundColor Cyan
} else {
    Write-Host "`n⚠ Service status onbekend: $status" -ForegroundColor Yellow
    Write-Host "Kijk logs: $LogsDir" -ForegroundColor Yellow
}

Write-Host "`nGeheim (zet in Safe Place): $Secret" -ForegroundColor Yellow
