#!/bin/bash

# Script to automate the installation and setup of the openHAB platform and utilities

# Main script starts here

# Check the number of arguments
if [[ $# -ne 3 ]]; then
    echo "Usage: $0 <site_id> <vpn_ip> <vpn_password>"
    exit 1
fi

# Extract arguments
site_id=$1
vpn_ip=$2
vpn_password=$3

# Change to the utils directory
cd utils

# Execute the separate scripts for each task
./install_prerequisites.sh
./establish_vpn_connection.sh $vpn_ip $site_id $vpn_password
./deploy_openhab.sh $site_id
./perform_operational_checks.sh

# Display completion message
echo "Deployment completed successfully."
