#!/bin/bash

# Source the config.env file to load the variables
source ../config.env

echo "Setting up openHAB..."

# Check if Z-Wave controller is connected and /dev/ttyACM0 (or /dev/ttyUSB0 for Z-Stick 7) is available
while true
do
  if ! lsusb | grep -q "$Z_STICK_MANUFACTURER"; then
    echo "Z-Wave controller not detected. Please connect the $Z_STICK_NAME controller and press Enter to continue ..."
  else
    echo "Z-Wave controller connected."
    if [ ! -e "$Z_STICK_PORT" ]; then
      echo "$Z_STICK_PORT device not found. Please contact the UoP WSN Technical Consultant."
      exit 1
    fi
    break
  fi

  # shellcheck disable=SC2162
  read -p ""
done

echo "Continue with the rest of the deployment process ..."

# Running docker compose
sudo ../pythonvenv/bin/docker-compose --env-file ../config.env up --build -d

echo -n "openHAB is not running yet. Waiting"
# Wait for OpenHAB to start
while true; do
    status=$(sudo docker exec -it openhab /openhab/runtime/bin/status)
    if [[ ("$status" == *"Running ..."*) && ("$status" != *"Not Running ..."*)]]; then
        echo ""
        echo "openHAB is running."
        break
    else
        echo -n "."
    fi
    sleep 3  # Wait for 3 seconds before checking again
done

# Continue with the rest of your deployment steps
echo ""

URL="http://$WSN_HOSTNAME:$OPENHAB_HTTP_PORT"

echo -n "The openHAB URL is not accessible yet. Waiting"
while true; do
  response=$(curl -s -o /dev/null -w "%{http_code}" "$URL")

  if [[ $response -eq 200 ]]; then
    echo ""
    echo "The openHAB URL is accessible."
    break
  else
    echo -n "."
  fi
  sleep 3  # Wait for 3 seconds before checking again
done

## Add openhab user - skipped. added user from configs/users.json -> mounted
#echo "Adding openhab user"
#./console_command.sh "openhab:users add openhab openhab administrator"
