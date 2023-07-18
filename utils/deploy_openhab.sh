#!/bin/bash
echo "Setting up openHAB..."

sudo docker-compose --env-file ../docker.env up -d

# Wait for OpenHAB to start
while [[ $(sudo docker exec -it openhab /openhab/runtime/bin/status) != "Running ..." ]]; do
    sleep 5
    echo "Not started yet..."
done

# Continue with the rest of your deployment steps
# ...
echo "openHAB started!"
echo "Continuing..."