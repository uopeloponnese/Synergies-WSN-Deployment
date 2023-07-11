#!/bin/bash
echo "Installing remote connection..."

# Extract arguments - $site_id $vpn_ip $vpn_port $vpn_password
site_id=$1
vpn_ip=$2
vpn_port=$3
vpn_password=$4

# OpenVPN configuration variables
SERVER_ADDRESS="${vpn_ip}"
SERVER_PORT="${vpn_port}"
USERNAME="wsn-${site_id}"
PASSWORD="${vpn_password}"
OVPN_FILE="client.conf"


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
# askpass $KEY_PASSWORD_FILE
remote-cert-tls server
<ca>
-----BEGIN CERTIFICATE-----
MIIDCjCCAfKgAwIBAgIIfIvIVm7sJFkwDQYJKoZIhvcNAQELBQAwEDEOMAwGA1UE
AwwFdW9wQ0EwHhcNMjMwNzExMTk0OTEwWhcNMzMwNzA4MTk0OTEwWjAQMQ4wDAYD
VQQDDAV1b3BDQTCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBAMcWCqbG
I0lI1TibOjHHReLcIr2GyTE5UYeoHwG6fWasUnTab0+LV/014JQdoNvSqHoSs/NU
34OPiZZdCOzIGM1DbJ9Eg6SII7KeAn2rXeJVAWFbnNPV8R01qUiLdyhZrNFlYatP
AYhIInbkFpiQ/SPtR3IIPRyYs7qqIx0Uvq2EaDZ8aZ4AsoFSr6zfa73yBUDSROBW
nrsgaJK4e/fsz4YiMrI3oI76nnGxtkUbGSuqh6GmDkLfsGHF7gt1rgbu1sZZDhJ9
ASTnSwGJ9Aya1TySiYy2AIWIt8KS+zCR7EjtupaOu2qEzecF1k5HYQrUWwslT9G6
EcS4FgDmQOFjTEkCAwEAAaNoMGYwDwYDVR0TAQH/BAUwAwEB/zAOBgNVHQ8BAf8E
BAMCAQYwHQYDVR0OBBYEFCedxhoA2hpagk9YXj5Xc/zQ5pJAMCQGCWCGSAGG+EIB
DQQXFhVHZW5lcmF0ZWQgYnkgUm91dGVyT1MwDQYJKoZIhvcNAQELBQADggEBACRy
Wf0idRbEf22mNy3dGZQeIhRCeVFvJCmcjfMRWa0AKawBTtCnTAkBDU73+81O1JaP
xql3I598i5dmPkmjhEDFhEu6uyf7iMoYdBn4jvMWyBaNHWw0WGI4q3uxkaTinANB
K6sNCB6UcgtiXRehaEifHpUAmh6Kp7YLAxskZcO+1w9YifhBY0KXXY5QM6tzGBq5
BrBgbrt/yDj2gJcgXeevzjDT4Gqfk7fT+Pdghrswcvh1MR/s+W6T9LLwkYbaeYwW
lgGn2uCHPma+9NsHG95iSe4x5UorakCgqw/KzJ1aejKq+Hr1xDXfbCbNqzsCIuzr
zC3kHNI9jbj2VZUNdds=
-----END CERTIFICATE-----
</ca>
<cert>
-----BEGIN CERTIFICATE-----
MIIDJTCCAg2gAwIBAgIIKEvAdOt0KJgwDQYJKoZIhvcNAQELBQAwEDEOMAwGA1UE
AwwFdW9wQ0EwHhcNMjMwNzExMTk0OTIxWhcNMzMwNzA4MTk0OTIxWjAWMRQwEgYD
VQQDDAtjbGllbnQwLXdzbjCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEB
ALZfanTCJ21aVTmlOERStyrTFeItnN8pRhxsQj8f/yIMSqipM2D6xM2UKWIlOd/5
VaBfHXkFgqFLzluzixFuDcFnQqJlNFXc1FoYxNUSm7Le+q7Rb9rOdTt6gpq/w/fY
c1Il9Xk0Xt2G1fLDx+SjBjDalQKdun1b/Mpa0sNjQ+uu+aLCp++ArMY6Fhvr9mlT
fD9egeO5pOFXkHu1zU+mL7jI+iB/Xi/cISyDlsbMSRNqBOyH/GiqRzxIHsiRe4sy
REuIO2K40Z71Fszk9mVKGB+0PWIaXVd8EXPky0zYwSciRtqp+NHalKgKwZBqY66w
aldDnfnej6qvETNPEVfnjgMCAwEAAaN9MHswEwYDVR0lBAwwCgYIKwYBBQUHAwIw
HQYDVR0OBBYEFLxOoMsNkVIEd94pUu9OfBvJrTPdMB8GA1UdIwQYMBaAFCedxhoA
2hpagk9YXj5Xc/zQ5pJAMCQGCWCGSAGG+EIBDQQXFhVHZW5lcmF0ZWQgYnkgUm91
dGVyT1MwDQYJKoZIhvcNAQELBQADggEBACoUYHaicRm91uAp55fleHFpYsy/105F
L/D+gqODwT1EQDZxDQfwfqgnyeRwBQf6y0E+tTabGhMKGrmjPi5yyLm2wxxRU4Sf
1gdpy34AGWV9fIMlZEgGu75jE52+DY9Kynzr1wXrfZ7eJ6uaCVIqyxwWjQ4Yojim
4tnz56PZUHFMCNhWc07jAUqkNyzYly5T7Cp3tKroa2qMKf041VvQCX+mh49W4zXX
OeDJh+1qeqtnegFhC4HPLFCmr7Ms2xF0+Incc8jp08ByyfcH969yuGHiRqD7iH9v
PXMWlFB5zcvMGbPNnlZ2/4WYq4QsMA+Ia2kGYURoy/zuRCKDvQjot+4=
-----END CERTIFICATE-----
</cert>
<key>
-----BEGIN RSA PRIVATE KEY-----
MIIEowIBAAKCAQEAtl9qdMInbVpVOaU4RFK3KtMV4i2c3ylGHGxCPx//IgxKqKkz
YPrEzZQpYiU53/lVoF8deQWCoUvOW7OLEW4NwWdComU0VdzUWhjE1RKbst76rtFv
2s51O3qCmr/D99hzUiX1eTRe3YbV8sPH5KMGMNqVAp26fVv8ylrSw2ND6675osKn
74CsxjoWG+v2aVN8P16B47mk4VeQe7XNT6YvuMj6IH9eL9whLIOWxsxJE2oE7If8
aKpHPEgeyJF7izJES4g7YrjRnvUWzOT2ZUoYH7Q9YhpdV3wRc+TLTNjBJyJG2qn4
0dqUqArBkGpjrrBqV0Od+d6Pqq8RM08RV+eOAwIDAQABAoIBAQCcUs19p68EHRpQ
fz7r0bsQCkAHz/FXmJlwY5ulYFfhZ4fXarGPv2RSk12lsyMYyTCMdvtccUy31bLd
B9l850kDLu//I6DouJGNaQ3PVlP/zwIyN3QZqj7y7OBmpVnlaLPxBniTnEB0ws9B
eHAvm04DMlnoFCt2qRLWoWNn9/6QVchcjn0+974po7KjzLz34wDchgvdP7R1tFY7
Hn3rtLm04E4PP/XvyzVvDJqTsdSd96HCurqjxODnvVvpTfyfCd1JOhxke1gbXe3A
lz5nCxmf2BHxWhVgVlKP9rf5I2+hsVEu4W1yN7rlelHYg6eczzNPVB2WHZkAHl3a
WUtwdq6BAoGBAOhqn1/ZButrTsUrpa+dG27l1Z5rn2DQSR7k2fxl4N0k1kl7UbaX
p8quBwN8eCTYCuEaIfs/HDF5Vzjtiw2pbRtR6cHi+LE+uq4qG2mrash/+554GWwh
dayzh8KPJ4Y+T4+eaHdOc9HePoOGmjDRI0TsCNIjvXp3X74D0ZvZf1blAoGBAMjg
1DLO/1ilEF+PYAL3h6JQiOxZf8EEHFDagESnVZgYBaJbLhGKDdDL6WRCeGooNmHl
qeYw6+dUtBI6yeJEBzyTJD7iAL5Za3AnGle5wY8nn+UWR8ifn6UbBphhsjYAOV16
SyWyxY/Vlgi5up2b5eGwUWnd4UmQGG4ftUjTfNrHAoGAEdEapp5ciW+Qekz+Rpgk
oju8RIi7jxBoipXAoDivJETOqJNrkDPQCRmOMBY6n5hwPRFjyX7tCl3i8dpD7qgu
VQnSgaqEphHI/dD8iP07EmO9RkiuqjtmafbZUXDn9sKQFtJt77dz6YLACBUpfNSL
f50YkANtYxYDoO1qBCiIOoECgYAK1198coGDdj0g+yryXgua7f/FybrEXwVsM66y
hdlvwPQk5Ajjd3DxcN/iwlefWxY8SFnYC5HfxUmGpleY95TwZvyQzD/ABjFvNx0L
2QGiSUAu6/np0PubvI6pkLQ+h9qQufXuTeytq5hSVjvFH9HTUWHDde8fukAnSVzO
VmOppwKBgHUNg1cwf657hxeUI+6DQsI2QQUW3qirlaijIQtQ4rCGrGPIHyZB4WMB
VSnvdxfMUGLb/pExq4UNaShtn6C9CEqBu7R/EQhfC5UHg6Dxbox5tK7T4rwJsEJf
Q91PdwLavlZE4+esm/svI5H2fE1qmEOpIoc6dw+re9gS85zX7rn1
-----END RSA PRIVATE KEY-----
</key>

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
#if sudo systemctl is-active --quiet openvpn@client.service >/dev/null; then
if ip link show tun0 >/dev/null 2>&1; then
    echo "VPN connection is UP"
    # Continue with the rest of the script
    # ...
else
    echo "VPN connection is DOWN"
    exit 1  # Exit the script with a non-zero status code
fi