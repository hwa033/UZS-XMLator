# Package EXE and supporting files for transfer to locked-down server
# Usage: run from repo root in PowerShell
# Produces: xmlator-release.zip ready to copy to E: drive

$ErrorActionPreference = 'Stop'

$TargetDir = "D:\xmlator-release"
$ZipPath = "D:\xmlator-release.zip"

Write-Host "Cleaning up previous package..." -ForegroundColor Cyan
if (Test-Path $TargetDir) { Remove-Item $TargetDir -Recurse -Force }
if (Test-Path $ZipPath) { Remove-Item $ZipPath -Force }

Write-Host "Creating package directory..." -ForegroundColor Cyan
New-Item -ItemType Directory -Force -Path $TargetDir | Out-Null

Write-Host "Copying EXE..." -ForegroundColor Cyan
Copy-Item ".\dist\xmlator.exe" "$TargetDir\"

Write-Host "Copying support folders..." -ForegroundColor Cyan
Copy-Item ".\docs" "$TargetDir\" -Recurse -Force
Copy-Item ".\uzs_filedrop" "$TargetDir\" -Recurse -Force

Write-Host "Creating output directories..." -ForegroundColor Cyan
New-Item -ItemType Directory -Force -Path "$TargetDir\build\excel_generated" | Out-Null

Write-Host "Creating run script for target server..." -ForegroundColor Cyan
@"
# Run this on E: drive server
# Usage: .\run-xmlator.ps1 [secret]
# If no secret provided, one will be generated

param([string]`$Secret = "")

if (-not `$Secret) {
    `$Secret = ([System.BitConverter]::ToString([System.Security.Cryptography.RandomNumberGenerator]::GetBytes(32)) -replace '-').ToLower()
    Write-Host "Generated secret: `$Secret" -ForegroundColor Yellow
}

`$env:FLASK_ENV = 'production'
`$env:U_XMLATOR_SECRET = `$Secret

Write-Host "Starting XMLator on 0.0.0.0:5000..." -ForegroundColor Green
Write-Host "Open browser to: http://localhost:5000" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop." -ForegroundColor Yellow

.\xmlator.exe --host 0.0.0.0 --port 5000
"@ | Out-File "$TargetDir\run-xmlator.ps1" -Encoding UTF8

Write-Host "Zipping package..." -ForegroundColor Cyan
Compress-Archive -Path "$TargetDir\*" -DestinationPath $ZipPath -Force

Write-Host "`n=== PACKAGE READY ===" -ForegroundColor Green
Write-Host "File: $ZipPath" -ForegroundColor Green
Write-Host "Size: $([math]::Round((Get-Item $ZipPath).Length / 1MB, 2)) MB" -ForegroundColor Green
Write-Host "`nNext steps:" -ForegroundColor Cyan
Write-Host "1. Copy $ZipPath to USB or network" -ForegroundColor White
Write-Host "2. On target server (E: drive), run:" -ForegroundColor White
Write-Host "   Expand-Archive -Path 'E:\xmlator-release.zip' -DestinationPath 'E:\AppData\xmlator' -Force" -ForegroundColor Yellow
Write-Host "3. Then run:" -ForegroundColor White
Write-Host "   cd E:\AppData\xmlator" -ForegroundColor Yellow
Write-Host "   .\run-xmlator.ps1" -ForegroundColor Yellow
