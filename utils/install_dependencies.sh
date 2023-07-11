#!/bin/bash
echo "Installing dependencies..."

# Update repositories
sudo apt-get update

# Install OpenVPN (if not already installed)
sudo apt-get install openvpn -y