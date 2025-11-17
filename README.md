# Synergies-WSN-Deployment

Developed by the University of Peloponnese for the Synergies project, this streamlined repository provides configuration files, scripts, and documentation for the easy deployment and management of the Wireless Sensor Network (WSN) in the project's energy data collection system.

## WSN Architecture

The WSN architecture forms the foundation of the Wireless Sensor Network solution, providing a robust and scalable framework for data collection, analysis, and management. The following image shows the high-level architecture of the WSN.

![WSN Architecture](misc/wsn.png?raw=true "WSN Architecture")

## Overview

This repository includes scripts and configuration files for the automated deployment of the Synergies WSN. It streamlines the process of setting up and managing the WSN components, ensuring a consistent and reliable deployment across different environments.

## Features

- **Automated Deployment:** The deployment process automatically installs the necessary packages, eliminating the need for manual intervention.

- **Z-Wave Network Integration:** Utilize the Z-Wave network for efficient and reliable communication among sensors and actuators.

- **OpenHab Integration:** OpenHab serves as the central hub for the WSN, providing a versatile platform for data processing and management.

- **SYNERGIES Edge Integration:** The Single Board Computer (SBC) acts as the SYNERGIES EDGE, creating Docker containers for seamless integration with the SYNERGIES Edge Data Fabric.

- **Remote Management:** The deployment process establishes a VPN connection to a UoP server, enabling remote management capabilities.

- **Measurement Exporter:** A dedicated container periodically forwards the latest openHAB item measurements to a remote data service.

## Usage

1. **Clone this repository:**

   ```bash
   git clone https://github.com/uopeloponnese/Synergies-WSN-Deployment.git
   ```


2. **Change to the directory of the downloaded repository:**

   ```bash
   cd Synergies-WSN-Deployment
   ```

3. **Make the script executable:**

   ```bash
   chmod +x deploy.sh
   ```

4. **Execute the script (core stack deployment):**

   ```bash
   ./deploy.sh GRC-XXX wsn.uopcloud.net 62832 my_password
   ```
   *[NOTE: The site ID (GRC-XXX) and the VPN password will be provided by the UoP WSN Technical Consultant upon request]*

5. **(Optional) Deploy edge features (edge agent + exporter):**

   After the core stack is up and the OpenHAB UI is reachable:

   - Log into OpenHAB and create/copy an API token.
   - Then run:

   ```bash
   ./deploy_edge_features.sh
   ```

   The script will:

   - Read the site ID from the `ID` file (created by `deploy.sh`).
   - Source `config.env` to get existing configuration values.
   - Read MQTT settings (`MQTT_HOST`, `MQTT_PORT`, etc.) from `config.env` when available, and only prompt for any missing values.
   - Prompt you for the OpenHAB API token.
   - Prompt for exporter target URL (optional - skip if not needed).
   - Create/update `edge_agent/.env` with edge-agent configuration.
   - Create/update `openhab_exporter/.env` with exporter configuration.
   - Start the edge services using `docker-compose.yml` with the `edge` profile.

6. **Configure the exporter (if needed):**

   The `deploy_edge_features.sh` script will prompt for exporter settings. You can also pre-configure them in `config.env` or manually edit the generated `openhab_exporter/.env` file. See the [Measurement Exporter](#measurement-exporter) section below for detailed configuration instructions.

   The deployment script stores the provided `site_id` in the `ID` file so that the exporter can reuse it via the shared volume.

7. **Optional – dry run the exporter payload:**

   ```bash
   python utils/test_exporter_payload.py --openhab-url http://<openhab-host>:8080
   ```

   Add `--send --target-url https://example/api` to perform a real POST request using the same logic as the running container.


## Docker Compose Profiles

The deployment uses Docker Compose profiles to organize services:

- **`core` profile**: Core services (openhab, influxdb, data-app)
- **`edge` profile**: Edge services (edge-agent, openhab-exporter)

### Starting Services

You can start services selectively:

```bash
# Start only core services
docker compose --profile core up -d

# Start only edge services (requires core to be running)
docker compose --profile edge up -d

# Start all services
docker compose --profile core --profile edge up -d

# Start a specific service
docker compose up -d <service-name>
```

## Measurement Exporter

The `openhab-exporter` container is part of `docker-compose.yml` and runs alongside openHAB and InfluxDB. It periodically collects the latest state for all items grouped by thing/channel and forwards the payload to a remote HTTP endpoint.

### Running Only Edge Services (Testing Setup)

This guide explains how to set up and run only the edge services (edge-agent and exporter) for testing, assuming the core stack is already running.

#### Prerequisites

- Core stack (`openhab`, `influxdb`) must be running
- You have an OpenHAB API token ready
- You're in the repository root directory

#### Step-by-Step Setup

1. **Clean up any existing edge/test containers:**

   ```bash
   # Stop and remove edge services and test containers in one go
   docker stop edge-agent openhab-exporter exporter-target test-mqtt 2>/dev/null || true
   docker rm edge-agent openhab-exporter exporter-target test-mqtt 2>/dev/null || true
   ```

   This ensures a clean start and prevents port conflicts.

2. **Start a test MQTT broker (configured to accept connections from containers):**

   ```bash
   # Create mosquitto configuration file that allows network connections
   printf "listener 1883 0.0.0.0\nallow_anonymous true\n#socket_domain ipv4\n" > mosquitto.conf
   
   # Remove any existing test-mqtt container and start a new one
   # Note: Replace 'synergies-wsn-deployment_wsn-bridge' with your actual network name if different
   # Find it with: docker network ls | grep wsn-bridge
   docker rm -f test-mqtt 2>/dev/null || true
   docker run -d --name test-mqtt \
     --network synergies-wsn-deployment_wsn-bridge \
     -p 1883:1883 \
     -v "$PWD/mosquitto.conf:/mosquitto/config/mosquitto.conf:ro" \
     eclipse-mosquitto
   ```

   **Explanation:**
   - Creates a mosquitto config file that listens on all interfaces (`0.0.0.0`) and allows anonymous connections
   - Connects the broker to the same Docker network as your services (`wsn-bridge`)
   - Maps port 1883 to the host for external access
   - **To find your network name:** Run `docker network ls | grep wsn-bridge` and use the network name shown

3. **Start a test HTTP server to receive exporter payloads:**

   ```bash
   docker run -d --name exporter-target -p 8081:8080 mendhak/http-https-echo
   ```

   **Explanation:**
   - Uses a pre-built image that echoes all HTTP requests (GET, POST, etc.)
   - Maps container port 8080 to host port 8081
   - Useful for testing - you can see all POST requests in the container logs

4. **Make the deployment script executable and run it:**

   ```bash
   chmod +x deploy_edge_features.sh
   ./deploy_edge_features.sh
   ```

   **During the script execution, you'll be prompted for:**

   - **OpenHAB API token**: Enter the token you created in OpenHAB
   - **MQTT broker host**: 
     - If the MQTT broker is on the same host: Use your host's IP address (e.g., `192.168.88.191`)
     - If using the test-mqtt container on the same network: Use `test-mqtt`
   - **MQTT broker port**: `1883` (default)
   - **Enable MQTT TLS**: Press Enter for "no" (default) when testing
   - **Exporter target URL**: 
     - If the exporter-target container is on the same host: Use `http://<host_ip>:8081` (e.g., `http://192.168.88.191:8081`)
     - If on the same Docker network: Use `http://exporter-target:8080`

   **Note:** The script reads `SITE_ID` from the `ID` file and `OPENHAB_BASE_URL` from `config.env`, so make sure these are set correctly.

5. **Verify the services are running:**

   ```bash
   docker ps | grep -E "(edge-agent|openhab-exporter|test-mqtt|exporter-target)"
   ```

#### Testing the Edge Services

1. **Monitor MQTT traffic (optional):**

   ```bash
   # Subscribe to all MQTT topics to see edge-agent activity
   mosquitto_sub -h localhost -p 1883 -t "#" -v
   ```

   You should see messages on topics like:
   - `wsn/<SITE_ID>/openhab/status` - Heartbeat messages
   - `wsn/<SITE_ID>/openhab/data` - Telemetry data
   - `wsn/<SITE_ID>/openhab/response` - Responses to commands

2. **Test the edge-agent via MQTT:**

   ```bash
   # Fetch the full list of items from OpenHAB
   python3 utils/test_mqtt_openhab.py --list-items

   # Fetch the state of a specific item
   python3 utils/test_mqtt_openhab.py --item GRC00001MS009_Sensor_temperature
   ```

   **Note:** Replace `GRC00001MS009_Sensor_temperature` with an actual item name from your OpenHAB setup.

3. **Check exporter logs:**

   ```bash
   # View exporter logs to see if it's successfully posting data
   docker logs -f openhab-exporter
   ```

4. **Check exporter target logs (for testing):**

   ```bash
   # View the HTTP echo server logs to see received POST requests
   docker logs -f exporter-target
   ```

   You should see the JSON payloads being posted by the exporter, including request headers, body, and response codes.

#### Cleanup

To stop and remove all edge and test containers:

```bash
docker stop edge-agent openhab-exporter exporter-target test-mqtt
docker rm edge-agent openhab-exporter exporter-target test-mqtt
rm -f mosquitto.conf
```

This leaves your core stack running.

### Python MQTT/OpenHAB Test Script

For a quick end-to-end MQTT test against the edge agent and openHAB:

1. Ensure:
   - `ID` has the correct site ID (e.g. `GRC-00`).
   - `config.env` has `MQTT_HOST` / `MQTT_PORT` pointing to your broker (e.g. `127.0.0.1:1883`).
   - The `edge-agent` container is running.

2. Install the Python MQTT client (if not already installed):

   ```bash
   pip install paho-mqtt
   ```

3. Run the test script to read an item's state or fetch the full items list via openHAB REST, through the edge agent and MQTT:

   ```bash
   cd Synergies-WSN-Deployment
   # Fetch the state of a specific item
   python utils/test_mqtt_openhab.py --item YourItemName

   # Fetch the full /rest/items list (e.g. when you don't yet know item names)
   python utils/test_mqtt_openhab.py --list-items
   ```

   Replace `YourItemName` with a real openHAB item name. The script will:

   - Read `SITE_ID` from `ID` (fallback to `SITE_ID` in `config.env`).
   - Read `MQTT_HOST` / `MQTT_PORT` from `config.env`.
   - Publish a GET command to `wsn/<SITE_ID>/openhab/command` for `/rest/items/<item>/state` (or `/rest/items` when using `--list-items`).
   - Listen on `wsn/<SITE_ID>/openhab/response` and print the JSON response.

### How It Works

The exporter:
- Reads the `SITE_ID` from the shared `ID` file (falling back to the `SITE_ID` environment variable if necessary)
- Queries openHAB REST API for all things/channels and resolves the linked items
- Fetches the latest value for each item and, when configured, the corresponding entry from the selected persistence service (default: `influxdb`)
- Posts a structured JSON payload to the remote endpoint defined in `openhab_exporter/.env`

### Configuration

The exporter configuration is stored in `openhab_exporter/.env` (created by `deploy_edge_features.sh`). You can also pre-configure values in `config.env` which the script will use as defaults. The following settings are available:

#### OpenHAB Connection

- **`OPENHAB_BASE_URL`** – Base URL for the openHAB REST API
  - For containers on the same Docker network: `http://openhab:8080` (uses container name)
  - For remote: `http://remote-host:8080` or `https://remote-host:8443`
  - This value is read from `config.env` by the deployment script

#### OpenHAB Authentication

Choose one authentication method:

- **`OPENHAB_API_TOKEN`** – API token for Bearer token authentication (preferred for remote instances)
  - Generate in openHAB: Settings → API Tokens
  - Sent as `Authorization: Bearer <token>` header

- **`OPENHAB_USERNAME`** and **`OPENHAB_PASSWORD`** – Basic authentication credentials
  - Used if API token is not provided

#### Remote Endpoint

- **`EXPORTER_TARGET_URL`** – HTTPS endpoint that will receive the payload (required)
  - Example: `https://api.example.com/wsn/data`

- **`EXPORTER_API_KEY`** – Optional API key sent as the `X-API-Key` header to the remote endpoint
  - Leave empty if the remote endpoint doesn't require authentication

#### Timing Configuration

- **`EXPORTER_INTERVAL_SECONDS`** – How often the exporter posts measurements (default: 300 seconds = 5 minutes)
- **`EXPORTER_HTTP_TIMEOUT_SECONDS`** – HTTP timeout for requests to the remote endpoint (default: 15 seconds)
- **`EXPORTER_MAX_RETRIES`** – Maximum number of retry attempts on failure (default: 3)
- **`OPENHAB_HTTP_TIMEOUT_SECONDS`** – HTTP timeout for openHAB API requests (default: 10 seconds)

#### Persistence Service

- **`OPENHAB_PERSISTENCE_SERVICE`** – Persistence service ID to query for historical data (default: `influxdb`)
  - Set to empty string to disable persistence data fetching

### Starting the Exporter

The exporter can be started in several ways:

1. **Using the deployment script** (recommended):
   ```bash
   ./deploy_edge_features.sh
   ```
   The script will create the `openhab_exporter/.env` file and start the service.

2. **Manually using Docker Compose**:
   ```bash
   docker compose --profile edge up -d openhab-exporter
   ```
   Requires `openhab_exporter/.env` to exist with all required settings.

3. **Start all edge services**:
   ```bash
   docker compose --profile edge up -d
   ```
   This starts both edge-agent and openhab-exporter.

### Monitoring

View exporter logs:

```bash
docker logs -f openhab-exporter
```

The exporter will log:
- Successful payload deliveries with response codes
- Errors connecting to openHAB or the remote endpoint
- Retry attempts on failures

### Payload Structure

The exporter sends a JSON payload with the following structure:

```json
{
  "site_id": "GRC-XXX",
  "generated_at": "2025-11-14T12:00:00Z",
  "things": [
    {
      "uid": "zwave:device:xxx:node4",
      "thing_type_uid": "zwave:aeotec_zw175_00_000",
      "label": "Device Label",
      "location": "Room Name",
      "status": "ONLINE",
      "channels": [
        {
          "uid": "zwave:device:xxx:node4:switch_binary",
          "id": "switch_binary",
          "label": "Switch",
          "item_type": "Switch",
          "kind": "STATE",
          "linked_items": [
            {
              "name": "ItemName",
              "label": "Item Label",
              "state": "ON",
              "type": "Switch",
              "persistence": {
                "time": 1763059784543,
                "state": "ON"
              }
            }
          ]
        }
      ]
    }
  ]
}
```

### Troubleshooting

**Exporter can't connect to OpenHAB:**
- Verify `OPENHAB_BASE_URL` is correct
- Check authentication credentials (API token or username/password)
- Ensure OpenHAB is accessible from the exporter container

**Exporter can't reach remote endpoint:**
- Verify `EXPORTER_TARGET_URL` is correct and accessible
- Check network connectivity from the container
- Verify API key if required by the remote endpoint

**No persistence data:**
- Ensure `OPENHAB_PERSISTENCE_SERVICE` matches your configured persistence service ID
- Verify the persistence service is enabled and has data


## License

This project is licensed under MIT License.