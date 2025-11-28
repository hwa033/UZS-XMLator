# Download Chart.js UMD build to web/static/vendor/chart.umd.min.js
# Run this from the repository root in PowerShell:
#   powershell -ExecutionPolicy Bypass -File .\scripts\download_chartjs.ps1

$dest = Join-Path -Path $PSScriptRoot -ChildPath "..\web\static\vendor\chart.umd.min.js"
$dest = (Resolve-Path $dest).Path
$dir = Split-Path $dest -Parent
if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }

$uri = 'https://cdn.jsdelivr.net/npm/chart.js@4.3.0/dist/chart.umd.min.js'
Write-Host "Downloading Chart.js from $uri to $dest ..."
try {
    Invoke-WebRequest -Uri $uri -OutFile $dest -UseBasicParsing -ErrorAction Stop
    Write-Host 'Download complete.' -ForegroundColor Green
} catch {
    Write-Error "Download failed: $($_.Exception.Message)"
}
