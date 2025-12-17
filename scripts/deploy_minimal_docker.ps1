# Minimal single-container deployment for Windows
# Run on Windows server from repo root with Docker Desktop installed

# Ensure required dirs exist on host
New-Item -ItemType Directory -Force -Path "uzs_filedrop\UZI-GAP3\UZSx_ACC1\v0428" | Out-Null
New-Item -ItemType Directory -Force -Path "uzs_filedrop\UZI-GAP3\UZSx_ACC1\UwvZwMelding_MQ_V0428" | Out-Null
New-Item -ItemType Directory -Force -Path "build\excel_generated" | Out-Null

Write-Host "Building Docker image..." -ForegroundColor Cyan
docker build -t xmlator:latest .

# Stop/remove previous container if present
Write-Host "Cleaning up old container..." -ForegroundColor Cyan
$existingContainer = docker ps -a --filter "name=xmlator" --format "{{.Names}}" 2>$null
if ($existingContainer) {
    docker stop xmlator 2>$null
    docker rm xmlator 2>$null
}

Write-Host "Starting container..." -ForegroundColor Cyan
$secret = ([System.BitConverter]::ToString([System.Security.Cryptography.RandomNumberGenerator]::GetBytes(32)) -replace '-').ToLower()

$repoRoot = (Get-Location).Path
docker run -d --name xmlator `
  -p 0.0.0.0:5000:5000 `
  -e FLASK_ENV=production `
  -e U_XMLATOR_SECRET=$secret `
  -v "$repoRoot\uzs_filedrop\UZI-GAP3\UZSx_ACC1\v0428:/app/uzs_filedrop/UZI-GAP3/UZSx_ACC1/v0428" `
  -v "$repoRoot\uzs_filedrop\UZI-GAP3\UZSx_ACC1\UwvZwMelding_MQ_V0428:/app/uzs_filedrop/UZI-GAP3/UZSx_ACC1/UwvZwMelding_MQ_V0428" `
  -v "$repoRoot\build\excel_generated:/app/build/excel_generated" `
  xmlator:latest

Write-Host "Waiting for container to start..." -ForegroundColor Cyan
Start-Sleep -Seconds 3

Write-Host "`nContainer status:" -ForegroundColor Green
docker ps --filter name=xmlator

$hostname = (Get-ComputerInfo).CsComputerName
$ipaddr = (Get-NetIPConfiguration | Where-Object {$_.IPv4DefaultGateway -ne $null}).IPv4Address.IPAddress | Select-Object -First 1

Write-Host "`nApp is reachable at: http://$ipaddr:5000" -ForegroundColor Green
Write-Host "Or: http://localhost:5000 (if accessing from this machine)" -ForegroundColor Green

Write-Host "`nTo stop and update:
  docker stop xmlator
  docker rm xmlator
  .\scripts\deploy_minimal_docker.ps1
" -ForegroundColor Yellow