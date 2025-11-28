# PowerShell build script to create a Windows executable using PyInstaller
# Usage: Open PowerShell in the repo root and run: .\build.ps1

$ErrorActionPreference = 'Stop'
$cwd = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $cwd

$venvPython = Join-Path $cwd ".venv\Scripts\python.exe"

Write-Host "Installing build deps (pyinstaller) into venv using venv python..."
& $venvPython -m pip install -r requirements-dev.txt

# Ensure dist folder is clean
if (Test-Path .\dist) { Remove-Item -Recurse -Force .\dist }
if (Test-Path .\build) { Remove-Item -Recurse -Force .\build }
if (Test-Path .\UZS_XMLator.spec) { Remove-Item -Force .\UZS_XMLator.spec }

# Build single-file executable via python -m PyInstaller
Write-Host "Running PyInstaller (onefile) via venv python - this may take a while..."
& $venvPython -m PyInstaller --noconfirm --onefile `
    --add-data "web\templates;web/templates" `
    --add-data "web\static;web/static" `
    --add-data "docs;docs" `
    --add-data "bronnen;bronnen" `
    --add-data "resources;resources" `
    --name UZS_XMLator `
    run_app.py

Write-Host "Build finished. See .\dist\UZS_XMLator.exe"
