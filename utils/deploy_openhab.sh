#!/bin/bash
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

  read -p ""
done

echo "Continue with the rest of the deployment process ..."

# Running docker compose
sudo docker-compose --env-file ../docker.env up -d

# Wait for OpenHAB to start
while true; do
    status=$(sudo docker exec -it openhab /openhab/runtime/bin/status)
    if [[ ("$status" == *"Running ..."*) && ("$status" != *"Not Running ..."*)]]; then
        echo "OpenHAB is running."
        break
    else
        echo "OpenHAB is not running yet. Waiting..."
        sleep 5
    fi
done

# Continue with the rest of your deployment steps
# ...
echo "openHAB started!"
echo "Continuing..."
