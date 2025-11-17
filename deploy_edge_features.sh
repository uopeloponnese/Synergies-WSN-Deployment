#!/bin/bash

# Second-stage deployment script for edge features (edge agent, exporter, etc.)
# This script assumes that:
#   1) The core stack has already been deployed via ./deploy.sh ...
#   2) OpenHAB is running and reachable.
#
# Responsibilities:
#   - Read the site ID from the ID file created by deploy.sh.
#   - Source config.env to determine configuration defaults.
#   - Prompt the operator for the OpenHAB API token and any missing MQTT/exporter settings.
#   - Generate/update the edge_agent/.env and openhab_exporter/.env files.
#   - Start the edge services via docker-compose.yml with edge profile.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EDGE_AGENT_ENV_FILE="${REPO_ROOT}/edge_agent/.env"
EXPORTER_ENV_FILE="${REPO_ROOT}/openhab_exporter/.env"
CONFIG_ENV_FILE="${REPO_ROOT}/config.env"
ID_FILE="${REPO_ROOT}/ID"
COMPOSE_FILE="${REPO_ROOT}/docker-compose.yml"

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

# Load core config to get defaults
if [[ ! -f "${CONFIG_ENV_FILE}" ]]; then
  echo "Error: config.env not found at ${CONFIG_ENV_FILE}."
  echo "This file is required for configuration."
  exit 1
fi

# shellcheck disable=SC1090
source "${CONFIG_ENV_FILE}"

echo
echo "Now we will collect configuration for the edge services."
echo "Values will be stored in ${EDGE_AGENT_ENV_FILE} and ${EXPORTER_ENV_FILE}."
echo

read -r -p "OpenHAB API token (OH_TOKEN): " OH_TOKEN
if [[ -z "${OH_TOKEN}" ]]; then
  echo "Error: OpenHAB API token cannot be empty."
  exit 1
fi

echo
echo "MQTT configuration:"
echo "You can pre-fill MQTT_* values in config.env; any missing values will be requested interactively."
echo

if [[ -n "${MQTT_HOST:-}" ]]; then
  echo "Using MQTT_HOST from config.env: ${MQTT_HOST}"
else
  read -r -p "MQTT broker host (MQTT_HOST): " MQTT_HOST
  if [[ -z "${MQTT_HOST}" ]]; then
    echo "Error: MQTT_HOST cannot be empty."
    exit 1
  fi
fi

if [[ -n "${MQTT_PORT:-}" ]]; then
  echo "Using MQTT_PORT from config.env: ${MQTT_PORT}"
else
  read -r -p "MQTT broker port (MQTT_PORT) [8883]: " MQTT_PORT_INPUT
  MQTT_PORT="${MQTT_PORT_INPUT:-8883}"
fi

if [[ -z "${MQTT_USERNAME:-}" ]]; then
  read -r -p "MQTT username (MQTT_USERNAME) [optional]: " MQTT_USERNAME
fi

if [[ -z "${MQTT_PASSWORD:-}" ]]; then
  read -r -s -p "MQTT password (MQTT_PASSWORD) [optional]: " MQTT_PASSWORD
  echo
fi

if [[ -z "${MQTT_CA:-}" ]]; then
  read -r -p "Path to MQTT CA certificate (MQTT_CA) [/etc/ssl/certs/ca-certificates.crt]: " MQTT_CA_INPUT
  MQTT_CA="${MQTT_CA_INPUT:-/etc/ssl/certs/ca-certificates.crt}"
fi

if [[ -z "${MQTT_CERT:-}" ]]; then
  read -r -p "Path to MQTT client certificate (MQTT_CERT) [optional]: " MQTT_CERT
fi

if [[ -z "${MQTT_KEY:-}" ]]; then
  read -r -p "Path to MQTT client key (MQTT_KEY) [optional]: " MQTT_KEY
fi

echo
echo "Exporter configuration:"
echo "You can pre-fill EXPORTER_* values in config.env; any missing values will be requested interactively."
echo

read -r -p "Exporter target URL (EXPORTER_TARGET_URL) [leave empty to skip exporter]: " EXPORTER_TARGET_URL_INPUT
EXPORTER_TARGET_URL="${EXPORTER_TARGET_URL_INPUT:-${EXPORTER_TARGET_URL:-}}"

if [[ -z "${EXPORTER_TARGET_URL}" ]]; then
  echo "No exporter target URL provided. Exporter will not be configured."
  EXPORTER_API_KEY=""
else
  if [[ -z "${EXPORTER_API_KEY:-}" ]]; then
    read -r -p "Exporter API key (EXPORTER_API_KEY) [optional]: " EXPORTER_API_KEY
  else
    echo "Using EXPORTER_API_KEY from config.env"
  fi
fi

# Set defaults from config.env if not provided
EXPORTER_INTERVAL_SECONDS="${EXPORTER_INTERVAL_SECONDS:-300}"
EXPORTER_HTTP_TIMEOUT_SECONDS="${EXPORTER_HTTP_TIMEOUT_SECONDS:-15}"
EXPORTER_MAX_RETRIES="${EXPORTER_MAX_RETRIES:-3}"
OPENHAB_HTTP_TIMEOUT_SECONDS="${OPENHAB_HTTP_TIMEOUT_SECONDS:-10}"
OPENHAB_PERSISTENCE_SERVICE="${OPENHAB_PERSISTENCE_SERVICE:-influxdb}"

echo
echo "Writing edge agent environment to ${EDGE_AGENT_ENV_FILE}..."

cat > "${EDGE_AGENT_ENV_FILE}" <<EOF
SITE_ID=${SITE_ID}

# OpenHAB configuration
OH_BASE_URL=http://oh:8080
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

echo "Edge agent environment file created."

echo
echo "Writing exporter environment to ${EXPORTER_ENV_FILE}..."

cat > "${EXPORTER_ENV_FILE}" <<EOF
SITE_ID=${SITE_ID}

# OpenHAB configuration
OPENHAB_BASE_URL=http://oh:8080
OPENHAB_API_TOKEN=${OH_TOKEN}

# Exporter configuration
EXPORTER_TARGET_URL=${EXPORTER_TARGET_URL}
EXPORTER_API_KEY=${EXPORTER_API_KEY}
EXPORTER_INTERVAL_SECONDS=${EXPORTER_INTERVAL_SECONDS}
EXPORTER_HTTP_TIMEOUT_SECONDS=${EXPORTER_HTTP_TIMEOUT_SECONDS}
EXPORTER_MAX_RETRIES=${EXPORTER_MAX_RETRIES}
OPENHAB_HTTP_TIMEOUT_SECONDS=${OPENHAB_HTTP_TIMEOUT_SECONDS}
OPENHAB_PERSISTENCE_SERVICE=${OPENHAB_PERSISTENCE_SERVICE}
EOF

echo "Exporter environment file created."
echo

if [[ ! -f "${COMPOSE_FILE}" ]]; then
  echo "Error: Docker compose file not found at ${COMPOSE_FILE}."
  exit 1
fi

echo "Starting edge-agent using docker-compose.yml with edge profile..."

if command -v docker-compose >/dev/null 2>&1; then
  docker-compose -f "${COMPOSE_FILE}" --profile edge up -d edge-agent
else
  docker compose -f "${COMPOSE_FILE}" --profile edge up -d edge-agent
fi

echo "Edge-agent started."
echo

if [[ -n "${EXPORTER_TARGET_URL}" ]]; then
  echo "Starting openhab-exporter using docker-compose.yml with edge profile..."
  
  if command -v docker-compose >/dev/null 2>&1; then
    docker-compose -f "${COMPOSE_FILE}" --profile edge up -d openhab-exporter
  else
    docker compose -f "${COMPOSE_FILE}" --profile edge up -d openhab-exporter
  fi
  
  echo "Exporter started."
else
  echo "Note: Exporter was not configured (no target URL provided)."
  echo "The exporter .env file was created but the service was not started."
  echo "To start it later, update ${EXPORTER_ENV_FILE} with EXPORTER_TARGET_URL and run:"
  echo "  docker compose --profile edge up -d openhab-exporter"
fi

echo
echo "Edge features deployment completed."
echo "You can check running containers with:"
echo "  docker ps"
