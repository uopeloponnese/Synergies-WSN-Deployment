#!/bin/bash

# Script to automate the installation and setup of the openHAB platform and utilities

# Main script starts here


./deploy_openhab.sh 0
./perform_operational_checks.sh

# Display completion message
echo "Deployment completed successfully."
