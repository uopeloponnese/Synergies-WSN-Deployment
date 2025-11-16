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
   - Use `config.env` to determine the OpenHAB URL.
   - Read MQTT settings (`MQTT_HOST`, `MQTT_PORT`, etc.) from `config.env` when available, and only prompt for any missing values.
   - Prompt you for the OpenHAB API token.
   - Create/update `edge_agent/.env`.
   - Start the edge-agent container using `docker-compose.edge.yml`.
   - Optionally (if you provide an exporter target URL), start the `openhab-exporter` container using `docker-compose.yml`, reusing the same OpenHAB API token.

5. **Configure the exporter:**

   Open `config.env` and adjust the exporter section. See the [Measurement Exporter](#measurement-exporter) section below for detailed configuration instructions.

   The deployment script stores the provided `site_id` in the `ID` file so that the exporter can reuse it via the shared volume.

6. **Optional – dry run the exporter payload:**

   ```bash
   python utils/test_exporter_payload.py --openhab-url http://<openhab-host>:8080
   ```

   Add `--send --target-url https://example/api` to perform a real POST request using the same logic as the running container.


## Measurement Exporter

The `openhab-exporter` container is part of `docker-compose.yml` and runs alongside openHAB and InfluxDB. It periodically collects the latest state for all items grouped by thing/channel and forwards the payload to a remote HTTP endpoint.

### Quick Test Containers (MQTT + Exporter)

You can run a minimal test setup with:

1. **Start a test MQTT broker (for edge-agent tests):**

   ```bash
   docker run -d --name test-mqtt -p 1883:1883 eclipse-mosquitto
   ```

   Then set in `config.env`:

   ```env
   MQTT_HOST="127.0.0.1"
   MQTT_PORT=1883
   MQTT_TLS=false
   ```

   and re-run `./deploy_edge_features.sh` so the edge agent uses this broker.

2. **Start only the exporter container (core stack + config.env required):**

   Make sure:

   - Core stack (`openhab`, `influxdb`) is running.
   - `config.env` has `OPENHAB_BASE_URL`, `OPENHAB_API_TOKEN` (or user/password),
     `EXPORTER_TARGET_URL`, and any other required exporter settings.

   Then run:

   ```bash
   docker-compose --env-file config.env up -d openhab-exporter
   ```

3. **Check logs:**

   ```bash
   docker logs -f test-mqtt
   docker logs -f openhab-exporter
   ```

4. **Stop and remove the test containers:**

   ```bash
   docker stop openhab-exporter test-mqtt
   docker rm openhab-exporter test-mqtt
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
- Posts a structured JSON payload to the remote endpoint defined in `config.env`

### Configuration

Configure the exporter by editing `config.env`:

#### OpenHAB Connection

- **`OPENHAB_BASE_URL`** – Base URL for the openHAB REST API
  - For local docker: `http://oh:8080`
  - For remote: `http://remote-host:8080` or `https://remote-host:8443`

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

The exporter is automatically started with docker-compose:

```bash
docker-compose --env-file config.env up -d openhab-exporter
```

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