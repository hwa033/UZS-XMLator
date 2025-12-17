# Builds a single-file Windows EXE using PyInstaller
# Prereqs: Python installed on your build box (Windows), pip
# Usage: run from repo root in PowerShell

$ErrorActionPreference = 'Stop'

# Ensure venv
if (-not (Test-Path .\.venv)) {
    python -m venv .venv
}
. .\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pyinstaller

# Clean previous dist/build
if (Test-Path dist) { Remove-Item dist -Recurse -Force }
if (Test-Path build) { Remove-Item build -Recurse -Force }

# Build single-file executable
pyinstaller --onefile --name xmlator --add-data "web;web" run_app.py

Write-Host "\nBuild complete. EXE is at dist\\xmlator.exe" -ForegroundColor Green
Write-Host "Copy dist\\xmlator.exe and the 'docs' and 'uzs_filedrop' folders (for XSDs/output) to the target Windows server." -ForegroundColor Yellow
