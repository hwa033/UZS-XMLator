#!/usr/bin/env bash
set -euo pipefail

# Minimal single-container deployment (no TLS, no nginx)
# Usage: run on a Linux server from repo root

# Ensure required dirs exist on host
mkdir -p uzs_filedrop/UZI-GAP3/UZSx_ACC1/v0428
mkdir -p uzs_filedrop/UZI-GAP3/UZSx_ACC1/UwvZwMelding_MQ_V0428
mkdir -p build/excel_generated

# Build image
docker build -t xmlator:latest .

# Stop/remove previous container if present
if docker ps -a --format '{{.Names}}' | grep -q '^xmlator$'; then
  docker stop xmlator || true
  docker rm xmlator || true
fi

# Run new container
docker run -d --name xmlator \
  -p 0.0.0.0:5000:5000 \
  -e FLASK_ENV=production \
  -e U_XMLATOR_SECRET="$(openssl rand -hex 32)" \
  -v "$(pwd)/uzs_filedrop/UZI-GAP3/UZSx_ACC1/v0428:/app/uzs_filedrop/UZI-GAP3/UZSx_ACC1/v0428" \
  -v "$(pwd)/uzs_filedrop/UZI-GAP3/UZSx_ACC1/UwvZwMelding_MQ_V0428:/app/uzs_filedrop/UZI-GAP3/UZSx_ACC1/UwvZwMelding_MQ_V0428" \
  -v "$(pwd)/build/excel_generated:/app/build/excel_generated" \
  xmlator:latest

# Show status
sleep 2
docker ps --filter name=xmlator

echo "App is reachable at: http://$(hostname -I | awk '{print $1}'):5000"