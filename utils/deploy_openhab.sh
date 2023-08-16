#!/bin/bash

# Source the config.env file to load the variables
source ../config.env

echo "Setting up openHAB..."

# Check if Z-Wave controller is connected and /dev/ttyACM0 is available
while true
do
  if ! lsusb | grep -q "Aeotec"; then
    echo "Z-Wave controller not detected. Please connect the Aeotec Z-Stick Gen5+ Z-Wave controller and press Enter to continue ..."
  else
    echo "Z-Wave controller connected."
    if [ ! -e /dev/ttyACM0 ]; then
      echo "/dev/ttyACM0 device not found. Please contact the UoP WSN Technical Consultant."
      exit 1
    fi
    break
  fi

  # shellcheck disable=SC2162
  read -p ""
done

echo "Continue with the rest of the deployment process ..."

# Running docker compose
sudo docker-compose --env-file ../config.env up --build -d

echo "OpenHAB is not running yet. Waiting"
# Wait for OpenHAB to start
while true; do
    status=$(sudo docker exec -it openhab /openhab/runtime/bin/status)
    if [[ ("$status" == *"Running ..."*) && ("$status" != *"Not Running ..."*)]]; then
        echo "OpenHAB is running."
        break
    else
        echo -n "."
    fi
    sleep 3  # Wait for 3 seconds before checking again
done

# Continue with the rest of your deployment steps
echo "openHAB started!"
echo "Continuing..."
echo "Congratulations! The openHAB deployment is complete."

URL="http://$WSN_HOSTNAME:$OPENHAB_HTTP_PORT"

echo -e "The URL is not accessible yet. Waiting"
while true; do
  response=$(curl -s -o /dev/null -w "%{http_code}" "$URL")

  if [[ $response -eq 200 ]]; then
    echo "The URL is accessible."
    break
  else
    echo -n "."
  fi
  sleep 3  # Wait for 3 seconds before checking again
done

## Add openhab user - skipped. added user from configs/users.json -> mounted
#echo "Adding openhab user"
#./console_command.sh "openhab:users add openhab openhab administrator"
