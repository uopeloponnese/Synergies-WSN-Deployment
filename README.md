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

4. **Execute the script:**

   ```bash
   ./deploy.sh GRC-XXX wsn.uopcloud.net 62832 my_password
   ```
   
*[NOTE: The site ID (GRC-XXX) and the vpn password will be provided by the UoP WSN Technical Consultant upon request]*
   

5. **Configure the exporter:**

   Open `config.env` and adjust the exporter section:

   - `EXPORTER_TARGET_URL` – HTTPS endpoint that will receive the payload.
   - `EXPORTER_API_KEY` – Optional API key sent as the `X-API-Key` header.
   - `EXPORTER_INTERVAL_SECONDS` – How often the exporter posts measurements (default: 300 seconds).

   The deployment script stores the provided `site_id` in both the `ID` file and `config.env` so that the exporter can reuse it.

6. **Optional – dry run the exporter payload:**

   ```bash
   python utils/test_exporter_payload.py --openhab-url http://<openhab-host>:8080
   ```

   Add `--send --target-url https://example/api` to perform a real POST request using the same logic as the running container.


## Measurement Exporter

The `openhab-exporter` container is part of `docker-compose.yml` and runs alongside openHAB and InfluxDB. It:

- Reads the `SITE_ID` from the shared `ID` file (falling back to the `SITE_ID` environment variable if necessary).
- Queries openHAB for all things/channels and resolves the linked items.
- Grabs the latest value for each item and, when configured, the corresponding entry from the selected persistence service (default: `influxdb`).
- Posts a structured JSON payload to the remote endpoint defined in `config.env`.

> The exporter service honours additional tuning options such as `EXPORTER_HTTP_TIMEOUT_SECONDS`, `EXPORTER_MAX_RETRIES`, `OPENHAB_HTTP_TIMEOUT_SECONDS`, and `OPENHAB_PERSISTENCE_SERVICE`.


## License

This project is licensed under MIT License.