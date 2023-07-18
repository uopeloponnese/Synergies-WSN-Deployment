#!/bin/bash
echo "Installing dependencies..."

# Update repositories
sudo apt-get update
sudo apt-get -y upgrade

##### OVPN #####
sudo apt-get install openvpn -y

# Check if OpenVPN is installed
if ! command -v openvpn &>/dev/null; then
    echo "OpenVPN installation failed. Please check the installation steps and try again."
    sleep 2
    exit 1
else
    echo "OpenVPN installation successful."
fi

##### Docker #####
# uninstall all conflicting packages
for pkg in docker.io docker-doc docker-compose podman-docker containerd runc; do sudo apt-get remove $pkg; done

# Set up the repository
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg

# Add Docker’s official GPG key
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/raspbian/gpg | sudo gpg --yes --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# Install Docker Engine
sudo apt-get update
sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Use the following command to set up the repository
echo \
  "deb [arch="$(dpkg --print-architecture)" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/raspbian \
  "$(. /etc/os-release && echo "$VERSION_CODENAME")" stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null


# Check if Docker is installed
if ! command -v docker &>/dev/null; then
    echo "Docker installation failed. Please check the installation steps and try again."
    sleep 2
    exit 1
else
    echo "Docker installation successful. Version: $(docker --version)"
fi

##### Docker-Compose #####
sudo apt update
sudo apt install -y python3-pip libffi-dev
sudo pip3 install docker-compose

# Check if Docker Compose is installed
if ! command -v docker-compose &>/dev/null; then
    echo "Docker Compose installation failed. Please check the installation steps and try again."
    sleep 2
    exit 1
else
    echo "Docker Compose installation successful. Version: $(docker-compose --version)"
fi