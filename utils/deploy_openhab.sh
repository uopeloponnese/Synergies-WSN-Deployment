#!/bin/bash
echo "Setting up openHAB..."

sudo docker-compose --env-file ../docker.env up -d

# Wait for OpenHAB to start
while true; do
    status=$(sudo docker exec -it openhab /openhab/runtime/bin/status)
    if echo "$status" | grep -q "Running ..."; then
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