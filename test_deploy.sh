#!/bin/bash

# Script to automate the installation and setup of the openHAB platform and utilities

# Main script starts here

# Change to the utils directory
cd utils || { echo "Error - No utils folder"; exit 1; }

chmod +x console_command.sh
chmod +x deploy_openhab.sh
chmod +x perform_operational_checks.sh

./deploy_openhab.sh 0
./perform_operational_checks.sh

# Display completion message
echo "Deployment completed successfully."
