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

## Usage

1. **Clone this repository:**

   ```bash
   git clone https://github.com/uopeloponnese/Synergies-WSN-Deployment.git


2. **Change to the directory of the downloaded repository:**

   ```bash
   cd Synergies-WSN-Deployment

3. **Make the script executable:**

   ```bash
   chmod +x deploy.sh

4. **Execute the script (core stack deployment):**

   ```bash
   ./deploy.sh GRC-XXX wsn.uopcloud.net 62832 my_password
   ```

   *[NOTE: The site ID (GRC-XXX) and the VPN password will be provided by the UoP WSN Technical Consultant upon request]*

5. **(Optional) Deploy edge features (edge agent, exporter, etc.):**

   After the core stack is up and the OpenHAB UI is reachable:

   - Log into OpenHAB and create/copy an API token.
   - Then run:

   ```bash
   ./deploy_edge_features.sh
   ```

   The script will:

   - Read the site ID from the `ID` file (created by `deploy.sh`).
   - Use `config.env` to determine the OpenHAB URL.
   - Prompt you for the OpenHAB API token and MQTT configuration.
   - Create/update `edge_agent/.env`.
   - Start the edge stack using `docker-compose.edge.yml`.
   

## License

This project is licensed under MIT License.