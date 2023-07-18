#!/bin/bash

# Script to automate the installation and setup of the openHAB platform and utilities

# Main script starts here

# Check the number of arguments
if [[ $# -ne 4 ]]; then
    echo "Usage: $0 <site_id> <vpn_ip> <vpn_port> <vpn_password>"
    exit 1
fi

# Extract arguments
site_id=$1
vpn_ip=$2
vpn_port=$3
vpn_password=$4

# Change to the utils directory
cd utils || { echo "Error - No utils folder"; exit 1; }
chmod +x install_dependencies.sh
chmod +x establish_vpn_connection.sh
chmod +x deploy_openhab.sh
chmod +x perform_operational_checks.sh

# Execute the separate scripts for each task
./install_dependencies.sh

# Check if OpenVPN connection is up
#if sudo systemctl is-active --quiet openvpn@client.service >/dev/null; then
if ip link show tun0 >/dev/null 2>&1; then
    echo "VPN connection is already UP"
    # Continue with the rest of the script
else
    # Establish VPN connection
    ./establish_vpn_connection.sh $site_id $vpn_ip $vpn_port $vpn_password
fi


# Check the exit code of the script
if [ $? -eq 0 ]; then
    echo "VPN tunnel is up. Proceeding with deployment..."
    # Continue with the rest of the deployment steps
else
    echo "Error: VPN connection is DOWN. Check your credentials."
    echo "Deployment cannot proceed."
    echo "Exiting..."
    # Add error handling code or exit the script if necessary
    exit 1
fi

./deploy_openhab.sh $site_id
./perform_operational_checks.sh

# Display completion message
echo "Deployment completed successfully."
