<#
Package EXE and supporting files for transfer to a locked-down server.
Usage: run from repo root in PowerShell.
Produces: xmlator-release.zip ready to copy to target server.

Parameters:
 -TargetDir           Destination folder for staging the package (default D:\xmlator-release)
 -ZipPath             Output zip path (default D:\xmlator-release.zip)
 -Environment         Target omgeving to use in instellingen.json (default UZSTA_OMG)
 -IncludeFiledrop     Include uzs_filedrop sample directories (default: $true)
 -BuildIfMissing      Run build_windows_exe.ps1 if dist\xmlator.exe is missing (default: $true)
#>

param(
    [string]$TargetDir = 'D:\\xmlator-release',
    [string]$ZipPath = 'D:\\xmlator-release.zip',
    [ValidateSet('UZSTA_OMG','UZSA_ACC1','UZSC_ACC1','UZSD_ACC1','UZSP_ACC1')]
    [string]$Environment = 'UZSTA_OMG',
    [switch]$IncludeFiledrop,
    [switch]$BuildIfMissing
)

$ErrorActionPreference = 'Stop'
$repoRoot = (Get-Location).Path

Write-Host "Preparing release package..." -ForegroundColor Cyan

# Ensure EXE exists (optionally build)
$exePath = Join-Path (Join-Path $repoRoot 'dist') 'xmlator.exe'
if (-not (Test-Path $exePath)) {
    if ($BuildIfMissing.IsPresent) {
        Write-Host "xmlator.exe not found; building via scripts/build_windows_exe.ps1..." -ForegroundColor Yellow
        & (Join-Path $repoRoot 'scripts' 'build_windows_exe.ps1')
        if (-not (Test-Path $exePath)) { throw "Build completed but dist\\xmlator.exe not found." }
    } else {
        throw "dist\\xmlator.exe not found. Set -BuildIfMissing:
scripts/build_windows_exe.ps1"
    }
}

# Clean previous
if (Test-Path $TargetDir) { Remove-Item $TargetDir -Recurse -Force }
if (Test-Path $ZipPath) { Remove-Item $ZipPath -Force }

New-Item -ItemType Directory -Force -Path $TargetDir | Out-Null

Write-Host "Copying EXE..." -ForegroundColor Cyan
Copy-Item $exePath $TargetDir -Force

Write-Host "Copying docs (XSDs, examples)..." -ForegroundColor Cyan
Copy-Item (Join-Path $repoRoot 'docs') $TargetDir -Recurse -Force

Write-Host "Copying installation guide..." -ForegroundColor Cyan
Copy-Item (Join-Path $repoRoot 'INSTALLATIE_TESTERS.md') (Join-Path $TargetDir 'README.txt') -Force

if ($IncludeFiledrop.IsPresent) {
    Write-Host "Including uzs_filedrop samples..." -ForegroundColor Cyan
    if (Test-Path (Join-Path $repoRoot 'uzs_filedrop')) {
        Copy-Item (Join-Path $repoRoot 'uzs_filedrop') $TargetDir -Recurse -Force
    }
}

Write-Host "Copying instellingen.json..." -ForegroundColor Cyan
Copy-Item (Join-Path (Join-Path $repoRoot 'web') 'instellingen.json') $TargetDir -Force

Write-Host "Creating output directories..." -ForegroundColor Cyan
New-Item -ItemType Directory -Force -Path (Join-Path (Join-Path $TargetDir 'build') 'excel_generated') | Out-Null

# Patch instellingen.json (omgeving only; filedrop paths remain as provided)
try {
    $instPath = Join-Path $TargetDir 'instellingen.json'
    $json = Get-Content $instPath -Raw | ConvertFrom-Json
    $json.omgeving = $Environment
    ($json | ConvertTo-Json -Depth 6) | Out-File $instPath -Encoding UTF8
    Write-Host "instellingen.json patched to omgeving=$Environment" -ForegroundColor Green
} catch {
    Write-Host "Warning: could not patch instellingen.json: $_" -ForegroundColor Yellow
}

Write-Host "Creating run script for target server..." -ForegroundColor Cyan
@"
# Run this on the target server
# Usage: .\run-xmlator.ps1 [-Secret <value>] [-AdminToken <value>]
# If values are omitted, secure randoms will be generated.

param(
    [string]`$Secret = "",
    [string]`$AdminToken = ""
)

function New-HexToken([int]`$bytes = 32) {
    return ([System.BitConverter]::ToString([System.Security.Cryptography.RandomNumberGenerator]::GetBytes(`$bytes)) -replace '-').ToLower()
}

if (-not `$Secret) {
    `$Secret = New-HexToken 32
    Write-Host "Generated U_XMLATOR_SECRET: `$Secret" -ForegroundColor Yellow
}
if (-not `$AdminToken) {
    `$AdminToken = `$Secret
    Write-Host "Using same token for admin (U_XMLATOR_ADMIN_TOKEN)." -ForegroundColor Yellow
}

`$env:FLASK_ENV = 'production'
`$env:U_XMLATOR_SECRET = `$Secret
`$env:U_XMLATOR_ADMIN_TOKEN = `$AdminToken

Write-Host "Starting XMLator on 0.0.0.0:5000..." -ForegroundColor Green
Write-Host "Open: http://localhost:5000 (or server IP)" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop." -ForegroundColor Yellow

.\xmlator.exe --host 0.0.0.0 --port 5000
"@ | Out-File (Join-Path $TargetDir 'run-xmlator.ps1') -Encoding UTF8

# Add quick health check script
@"
try {
    `$r = Invoke-WebRequest -Uri 'http://127.0.0.1:5000/ready' -UseBasicParsing -TimeoutSec 5
    Write-Host "Ready status: `$($r.StatusCode) `$($r.Content)" -ForegroundColor Green
} catch {
    Write-Host "Health/ready check failed: `$($_.Exception.Message)" -ForegroundColor Red
}
"@ | Out-File (Join-Path $TargetDir 'check-health.ps1') -Encoding UTF8

Write-Host "Zipping package..." -ForegroundColor Cyan
Compress-Archive -Path (Join-Path $TargetDir '*') -DestinationPath $ZipPath -Force

Write-Host "`n=== PACKAGE READY ===" -ForegroundColor Green
Write-Host "File: $ZipPath" -ForegroundColor Green
Write-Host "Size: $([math]::Round((Get-Item $ZipPath).Length / 1MB, 2)) MB" -ForegroundColor Green
Write-Host "`nNext steps:" -ForegroundColor Cyan
Write-Host "1. Copy $ZipPath to target server" -ForegroundColor White
Write-Host "2. On target: Expand-Archive -Path '$ZipPath' -DestinationPath 'E:\AppData\xmlator' -Force" -ForegroundColor Yellow
Write-Host "3. Then: cd E:\AppData\xmlator ; .\run-xmlator.ps1" -ForegroundColor Yellow
