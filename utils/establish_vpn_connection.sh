#!/bin/bash
echo "Installing remote connection..."

# Extract arguments - $site_id $vpn_ip $vpn_port $vpn_password
site_id=$1
vpn_ip=$2
vpn_port=$3
vpn_password=$4

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VPN_SECRETS_DIR="${SCRIPT_DIR}/openvpn"
CA_FILE="${VPN_SECRETS_DIR}/ca.crt"
CERT_FILE="${VPN_SECRETS_DIR}/client.crt"
KEY_FILE="${VPN_SECRETS_DIR}/client.key"

for required_file in "$CA_FILE" "$CERT_FILE" "$KEY_FILE"; do
    if [[ ! -f "$required_file" ]]; then
        echo "Error: Missing VPN file: $required_file"
        echo "Place ca.crt, client.crt, and client.key in utils/openvpn/ (provided by UoP WSN Technical Consultant)."
        exit 1
    fi
done

# OpenVPN configuration variables
SERVER_ADDRESS="${vpn_ip}"
SERVER_PORT="${vpn_port}"
USERNAME="wsn-${site_id}"
PASSWORD="${vpn_password}"
OVPN_FILE="client.conf"

sudo cp "$CA_FILE" /etc/openvpn/ca.crt
sudo cp "$CERT_FILE" /etc/openvpn/client.crt
sudo cp "$KEY_FILE" /etc/openvpn/client.key
sudo chmod 600 /etc/openvpn/client.key

# Create OpenVPN configuration file
sudo rm -f /etc/openvpn/$OVPN_FILE
sudo tee /etc/openvpn/$OVPN_FILE > /dev/null <<EOT
client
dev tun
persist-tun
proto tcp
remote $SERVER_ADDRESS $SERVER_PORT
resolv-retry infinite
nobind
tun-mtu 1500
auth sha256
cipher AES-256-CBC
auth-nocache
resolv-retry infinite
verb 3
auth-user-pass /etc/openvpn/credentials
remote-cert-tls server
ca /etc/openvpn/ca.crt
cert /etc/openvpn/client.crt
key /etc/openvpn/client.key
EOT

# Create credentials file
sudo rm -rf /etc/openvpn/credentials
sudo tee /etc/openvpn/credentials > /dev/null <<EOT
$USERNAME
$PASSWORD

EOT

# Start OpenVPN on system startup
sudo sed -i 's/#AUTOSTART="all"/AUTOSTART="all"/' /etc/default/openvpn

# Start OpenVPN service
sudo systemctl start openvpn@client.service

# Enable OpenVPN service on startup
sudo systemctl enable openvpn@client.service

# Wait for 15 seconds
echo "Establishing remote connection..."
sleep 15

# Check if OpenVPN connection is up
if ip link show tun0 >/dev/null 2>&1; then
    echo "VPN connection is UP"
else
    echo "VPN connection is DOWN"
    exit 1
fi
