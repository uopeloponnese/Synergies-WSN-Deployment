#!/bin/bash

# Second-stage deployment script for edge features (edge agent, exporter, etc.)
# This script assumes that:
#   1) The core stack has already been deployed via ./deploy.sh ...
#   2) OpenHAB is running and reachable.
#
# Responsibilities:
#   - Read the site ID from the ID file created by deploy.sh.
#   - Source config.env to determine the OpenHAB URL.
#   - Prompt the operator for the OpenHAB API token and basic MQTT settings.
#   - Generate/update the edge_agent/.env file.
#   - Start the edge stack via docker-compose.edge.yml.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EDGE_ENV_FILE="${REPO_ROOT}/edge_agent/.env"
CONFIG_ENV_FILE="${REPO_ROOT}/config.env"
ID_FILE="${REPO_ROOT}/ID"
EDGE_COMPOSE_FILE="${REPO_ROOT}/docker-compose.edge.yml"

echo "=== Synergies WSN: Edge Features Deployment ==="

# Check for site ID
if [[ ! -f "${ID_FILE}" ]]; then
  echo "Error: ID file not found at ${ID_FILE}."
  echo "Please run the core deployment first:"
  echo "  ./deploy.sh GRC-XXX wsn.uopcloud.net 62832 my_password"
  exit 1
fi

SITE_ID="$(< "${ID_FILE}")"
echo "Detected SITE_ID: ${SITE_ID}"

# Load core config to determine OpenHAB host/ports
if [[ ! -f "${CONFIG_ENV_FILE}" ]]; then
  echo "Error: config.env not found at ${CONFIG_ENV_FILE}."
  echo "This file is required to determine the OpenHAB URL."
  exit 1
fi

# shellcheck disable=SC1090
source "${CONFIG_ENV_FILE}"

OPENHAB_HTTP_PORT="${OPENHAB_HTTP_PORT:-8080}"
WSN_HOSTNAME="${WSN_HOSTNAME:-wsn.local}"
OPENHAB_BASE_URL="http://${WSN_HOSTNAME}:${OPENHAB_HTTP_PORT}"

echo "Assuming OpenHAB base URL: ${OPENHAB_BASE_URL}"
echo

# Basic reachability check (optional, non-fatal)
if command -v curl >/dev/null 2>&1; then
  if curl -s --max-time 5 "${OPENHAB_BASE_URL}" >/dev/null; then
    echo "OpenHAB appears reachable."
  else
    echo "Warning: Unable to confirm OpenHAB is reachable at ${OPENHAB_BASE_URL}."
    echo "Make sure the core stack is up and OpenHAB is running."
  fi
else
  echo "Note: curl not available; skipping OpenHAB reachability check."
fi

echo
echo "Now we will collect configuration for the edge agent."
echo "Values will be stored in ${EDGE_ENV_FILE}."
echo

read -r -p "OpenHAB API token (OH_TOKEN): " OH_TOKEN
if [[ -z "${OH_TOKEN}" ]]; then
  echo "Error: OpenHAB API token cannot be empty."
  exit 1
fi

read -r -p "MQTT broker host (MQTT_HOST): " MQTT_HOST
if [[ -z "${MQTT_HOST}" ]]; then
  echo "Error: MQTT_HOST cannot be empty."
  exit 1
fi

read -r -p "MQTT broker port (MQTT_PORT) [8883]: " MQTT_PORT
MQTT_PORT="${MQTT_PORT:-8883}"

read -r -p "MQTT username (MQTT_USERNAME) [optional]: " MQTT_USERNAME
read -r -s -p "MQTT password (MQTT_PASSWORD) [optional]: " MQTT_PASSWORD
echo

read -r -p "Path to MQTT CA certificate (MQTT_CA) [/etc/ssl/certs/ca-certificates.crt]: " MQTT_CA
MQTT_CA="${MQTT_CA:-/etc/ssl/certs/ca-certificates.crt}"

read -r -p "Path to MQTT client certificate (MQTT_CERT) [optional]: " MQTT_CERT
read -r -p "Path to MQTT client key (MQTT_KEY) [optional]: " MQTT_KEY

echo
echo "Writing edge agent environment to ${EDGE_ENV_FILE}..."

cat > "${EDGE_ENV_FILE}" <<EOF
SITE_ID=${SITE_ID}

# OpenHAB configuration
OH_BASE_URL=${OPENHAB_BASE_URL}
OH_TOKEN=${OH_TOKEN}

# MQTT configuration
MQTT_HOST=${MQTT_HOST}
MQTT_PORT=${MQTT_PORT}
MQTT_TLS=true
MQTT_USERNAME=${MQTT_USERNAME}
MQTT_PASSWORD=${MQTT_PASSWORD}
MQTT_CA=${MQTT_CA}
MQTT_CERT=${MQTT_CERT}
MQTT_KEY=${MQTT_KEY}

# Optional tuning parameters
TELEMETRY_INTERVAL_SEC=60
HEARTBEAT_INTERVAL_SEC=30
CACHE_TTL_SEC=300
CACHE_SIZE=1000
EOF

echo "Environment file created."
echo

if [[ ! -f "${EDGE_COMPOSE_FILE}" ]]; then
  echo "Error: Edge compose file not found at ${EDGE_COMPOSE_FILE}."
  exit 1
fi

echo "Starting edge stack (edge agent) using docker-compose.edge.yml..."

if command -v docker-compose >/dev/null 2>&1; then
  docker-compose -f "${EDGE_COMPOSE_FILE}" up -d
else
  docker compose -f "${EDGE_COMPOSE_FILE}" up -d
fi

echo
echo "Edge agent started."
echo

read -r -p "Exporter target URL (EXPORTER_TARGET_URL) [leave empty to skip starting exporter]: " EXPORTER_TARGET_URL

if [[ -n "${EXPORTER_TARGET_URL}" ]]; then
  read -r -p "Exporter API key (EXPORTER_API_KEY) [optional]: " EXPORTER_API_KEY

  echo
  echo "Starting openhab-exporter container using docker-compose.yml..."

  if command -v docker-compose >/dev/null 2>&1; then
    SITE_ID="${SITE_ID}" OPENHAB_API_TOKEN="${OH_TOKEN}" EXPORTER_TARGET_URL="${EXPORTER_TARGET_URL}" EXPORTER_API_KEY="${EXPORTER_API_KEY}" \
      docker-compose --env-file "${CONFIG_ENV_FILE}" up -d openhab-exporter
  else
    SITE_ID="${SITE_ID}" OPENHAB_API_TOKEN="${OH_TOKEN}" EXPORTER_TARGET_URL="${EXPORTER_TARGET_URL}" EXPORTER_API_KEY="${EXPORTER_API_KEY}" \
      docker compose --env-file "${CONFIG_ENV_FILE}" up -d openhab-exporter
  fi

  echo
  echo "Exporter started."
else
  echo
  echo "No exporter target URL provided. Skipping exporter startup."
fi

echo
echo "Edge features deployment completed."
echo "You can check running containers with:"
echo "  docker ps"


